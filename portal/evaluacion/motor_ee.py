"""Motor de preevaluación territorial y conectividad (Earth Engine).

Portado de la aplicación Streamlit `julii5sos/julii5sos-evaluacion-corredores-panama`
(app_experiencia.py, método MT-2026.15). ESTE ARCHIVO SE GENERA con
build/armar_motor_ee.py: las funciones de Earth Engine se copian sin cambios de
lógica y solo se quitan las dependencias de Streamlit:
  · los secretos pasan a variables de entorno (EE_PROJECT, EE_ASSET_BOSQUE_2021…);
  · `obtener_area` recibe la geometría ya preparada por el portal
    (cuenca del Canal, cuenca + 10 km, subcuenca o polígono recortado al área);
  · la caché de Streamlit se sustituye por la de `servicio.py`.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from io import BytesIO

import ee
import requests
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as ReportLabImage, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from reporte_cartografico import crear_mapa_conectividad, crear_mapa_fragmentacion
from territorio_local import (
    FUENTE_CUENCA, FUENTE_SUBCUENCAS, geometria_cuenca, geometria_subcuenca, huella_territorial,
)

from metodologia_indice import (
    CLASES_VIGOR_NDVI, JUSTIFICACION_PESOS, JUSTIFICACION_UMBRALES, PERIODOS_ANALISIS, PESOS_INDICE,
    PUNTAJE_MAXIMO, PUNTAJE_MAXIMO_VISITA, REGLAS_CONSISTENCIA, REGLAS_CONTEXTO_ESTRUCTURAL,
    REGLAS_MAPA_COINCIDENCIA, REGLAS_PRIORIDAD, REGLAS_PRIORIDAD_VISITA, UMBRALES_INDICE,
    calcular_indice_prioridad, calcular_prioridad_visita, evaluar_consistencia, evaluar_senales,
    texto_recomendacion_visita,
)
from corredores import (
    FUENTE_CORTA as FUENTE_CORREDORES, URL_MAPA as URL_MAPA_CORREDORES, analizar_interseccion_corredores,
    calcular_radio_contexto, cargar_catalogo as cargar_catalogo_corredores, cargar_corredores,
)
from eri_indicativo import (
    CLASES_ERI, COLORES_COMPONENTES_ERI, ETIQUETAS_COMPONENTES_ERI, PESOS_ERI, construir_resultado_eri,
)
from modos_app import (
    MODO_CORREDORES, MODO_INTEGRAL, MODO_TERRITORIAL, MODOS_ANALISIS, TOLERANCIA_RECORTE_M,
    TIPO_AREA_DIBUJADA, TIPO_AREA_SUBCUENCA, aplicar_limite_cuenca, area_debe_recortarse_a_cuenca,
)
from bosque_conectividad import analizar_fragmentacion_geojson

TOLERANCIA_RECORTE_M = 10

APP_VERSION = "UX-5.3-HTML-EXACTO-LIMITES-LOCALES"

MAPAS_BASE = {
    "Imagen satelital": {
        "tiles": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        "attr": "Esri",
        "max_zoom": 20,
    },
    "Mapa claro": {
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": "OpenStreetMap contributors · CARTO",
        "max_zoom": 20,
        "subdomains": "abcd",
    },
    "OpenStreetMap": {
        "tiles": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "OpenStreetMap contributors",
        "max_zoom": 19,
    },
}

COLORES_FUENTES = {
    "JRC TMF": "#1F8A70",
    "Hansen GFC": "#E76F51",
    "ESRI LULC": "#3A7CA5",
    "GEDI": "#7A5195",
    "NDVI": "#9BBF30",
}
COLORES_CAMBIOS = {
    "Deforestación JRC": "#C73E3A",
    "Degradación JRC": "#F2A541",
    "Regeneración forestal JRC": "#43AA8B",
    "Pérdida Hansen post-2020": "#E76F51",
    "Salida de árboles ESRI": "#3A7CA5",
    "Disminución NDVI": "#9BBF30",
}
COLORES_CONECTIVIDAD = {
    "En corredores": "#2E7D5B",
    "Fuera de corredores": "#7B8CA5",
    "Bosque 2021": "#76B72A",
    "Otros usos 2021": "#B7791F",
    "Cercanos": "#2A9D8F",
    "Separados": "#E76F51",
}
METHODOLOGY_VERSION = "MT-2026.17-PORTAL-ERI-INDICATIVO"
PROYECTO_EE = os.environ.get("EE_PROJECT", "ee-julissaguevaravega")
FUENTE_BOSQUE_NOMBRE = "Bosque y otros usos"
FUENTE_BOSQUE_ORGANIZACION = "SINIA–MiAMBIENTE"
ANO_BOSQUE_REFERENCIA = 2021
FUENTE_BOSQUE_CORTA = (
    f"{FUENTE_BOSQUE_ORGANIZACION} · {FUENTE_BOSQUE_NOMBRE} · "
    f"{ANO_BOSQUE_REFERENCIA}"
)
CAMPO_COBERTURA_BOSQUE_2021 = "Categoria"
VALOR_COBERTURA_BOSQUE_2021 = "Bosques y Otras Tierras Boscosas"
RADIO_BUSQUEDA_CORREDOR_M = 5_000
TOLERANCIA_GEOMETRIA_CONECTIVIDAD_M = 10

ASSET_FINCAS = None  # el portal ya no usa fincas
ASSET_BOSQUE_2021 = os.environ.get(
    "EE_ASSET_BOSQUE_2021", "projects/ee-julissaguevaravega/assets/CBOTB_2021_BOSQUE"
)
ACCESO_FINCA_DURACION_SEG = 30 * 60
ACCESO_FINCA_MAX_INTENTOS = 5
ACCESO_FINCA_BLOQUEO_SEG = 60
HANSEN_ASSET = "UMD/hansen/global_forest_change_2025_v1_13"
TMF_ASSET = "projects/JRC/TMF/v1_2025/AnnualChanges"
ESRI_ASSET = (
    "projects/sat-io/open-datasets/landcover/"
    "ESRI_Global-LULC_10m_TS"
)
GEDI_ASSET = (
    "users/openforisearthmap/World_EarthMap/"
    "CanopyHeight_GEDI_V27"
)

ANO_REFERENCIA_ANALISIS = PERIODOS_ANALISIS["referencia"]
ANO_HANSEN_MAX = PERIODOS_ANALISIS["hansen_diagnostico"]
ANO_TMF_MAX = PERIODOS_ANALISIS["jrc_diagnostico"]
ANO_DIAG_TMF = PERIODOS_ANALISIS["jrc_diagnostico"]
ANO_ESRI_MIN = PERIODOS_ANALISIS["esri_inicial"]
ANO_ESRI_MAX = PERIODOS_ANALISIS["esri_final"]
ANO_NDVI_INICIAL_ANALISIS = PERIODOS_ANALISIS["ndvi_inicial"]
ANO_NDVI_FINAL_ANALISIS = PERIODOS_ANALISIS["ndvi_final"]
ANO_NDVI_MAX = PERIODOS_ANALISIS["ndvi_final_visual"]
ESCALA_ANALISIS_NDVI_M = 20
ANO_ERI_REFERENCIA = min(2024, ANO_ESRI_MAX)
ESCALA_ERI_M = 90
RADIO_CONECTIVIDAD_ERI_M = 1_500
DISTANCIA_RIPARIA_ERI_M = 1_000
ALTURA_REFERENCIA_ERI_M = 35
AREA_DRENAJE_ERI_KM2 = 1.0
CUTOFF_YEAR = 20
CUTOFF_LABEL = "31/12/2020"

UMBRAL_ALERTA_HANSEN_HA = UMBRALES_INDICE["hansen_post_2020_ha"]
UMBRAL_REVISION_TMF_DEGRAD_HA = UMBRALES_INDICE["jrc_degradacion_ha"]
UMBRAL_REVISION_TMF_DEFOR_HA = UMBRALES_INDICE["jrc_deforestacion_ha"]
UMBRAL_PCT_TMF_DEFOR = UMBRALES_INDICE["jrc_deforestacion_pct"]
UMBRAL_PCT_TMF_DEGRAD = UMBRALES_INDICE["jrc_degradacion_pct"]
UMBRAL_PCT_ESRI_SALIDA = UMBRALES_INDICE["esri_salida_arboles_pct"]
UMBRAL_ESRI_SALIDA_HA = UMBRALES_INDICE["esri_salida_arboles_ha"]
UMBRAL_DOSEL_BAJO_M = UMBRALES_INDICE["gedi_dosel_bajo_m"]
UMBRAL_COBERTURA_GEDI_PCT = UMBRALES_INDICE["gedi_cobertura_minima_pct"]
UMBRAL_LINEA_BASE_GEDI_PCT = UMBRALES_INDICE["gedi_linea_base_minima_pct"]
UMBRAL_DELTA_NDVI = UMBRALES_INDICE["ndvi_delta_disminucion"]
UMBRAL_VIGOR_INICIAL_NDVI = UMBRALES_INDICE["ndvi_vigor_inicial_minimo"]

ESRI_ORIG = [1, 2, 4, 5, 7, 8, 9, 10, 11]
ESRI_VIS = [1, 2, 3, 4, 5, 6, 7, 8, 9]
ESRI_COLORES = [
    "1A5BAB",
    "358221",
    "87D19E",
    "FFDB5C",
    "ED022A",
    "EDE9E4",
    "F2FAFF",
    "C8C8C8",
    "C6AD8D",
]

VIS_TMF = {
    "min": 1,
    "max": 6,
    "palette": ["006400", "FFCC00", "FF0000", "43AA8B", "0000FF", "BDBDBD"],
}
VIS_ESRI = {"min": 1, "max": 9, "palette": ESRI_COLORES}
VIS_HANSEN_POST = {
    "min": 21,
    "max": 25,
    "palette": ["FF1744", "D50000", "B71C1C", "7F0000", "4A0000"],
}
VIS_HANSEN_PRE = {
    "min": 1,
    "max": 20,
    "palette": ["FFF9C4", "F9A825", "E65100", "C62828"],
}
VIS_HANSEN_TOTAL = {
    "min": 1,
    "max": 25,
    "palette": ["FFF9C4", "F9A825", "E65100", "FF1744", "7F0000"],
}
VIS_LINEA_BASE = {"min": 1, "max": 1, "palette": ["00C853"]}
VIS_TMF_DEFOR = {"min": 1, "max": 1, "palette": ["FF0000"]}
VIS_TMF_DEGRAD = {"min": 1, "max": 1, "palette": ["FFCC00"]}
VIS_TMF_REGENERACION = {"min": 1, "max": 1, "palette": ["43AA8B"]}
VIS_ESRI_CAMBIO = {
    "min": 1,
    "max": 3,
    "palette": ["00FF00", "FF0000", "006400"],
}
VIS_GEDI = {
    "min": 0,
    "max": 35,
    "palette": ["FFFFCC", "C2E699", "78C679", "31A354", "006837"],
}
VIS_ERI = {
    "min": 1,
    "max": 5,
    "palette": [clase["color"].lstrip("#") for clase in CLASES_ERI],
}
VIS_NDVI_DELTA = {
    "min": -0.3,
    "max": 0.3,
    "palette": ["7F0000", "D32F2F", "FF7043", "FFF9C4", "66BB6A", "2E7D32", "1B5E20"],
}
VIS_NDVI_CLASES = {
    "min": 0,
    "max": 4,
    "palette": ["B30000", "F4A582", "FFFFBF", "78C679", "006837"],
}
VIS_COINCIDENCIA_REVISION = {
    "min": 1,
    "max": 3,
    "palette": [
        REGLAS_MAPA_COINCIDENCIA["clases"][clase]["color"].lstrip("#")
        for clase in (1, 2, 3)
    ],
}
VIS_RGB = {"min": 150, "max": 3200, "gamma": 1.15, "bands": ["B4", "B3", "B2"]}
ASSET_SUBCUENCAS = os.environ.get("EE_ASSET_SubCuencas", "projects/ee-julissaguevaravega/assets/SubCuenca_CHCP")



def obtener_area(tipo_area=None, finca_id=None, subcuenca_nombre=None, geometria_geojson=None):
    """Adaptador del portal: recibe la geometría GeoJSON (WGS 84) ya recortada al área de estudio."""
    datos = json.loads(geometria_geojson) if isinstance(geometria_geojson, str) else geometria_geojson
    return ee.FeatureCollection([ee.Feature(ee.Geometry(datos), {"Origen": tipo_area or "portal"})])

def construir_registro_metodologico(
    tipo_area,
    finca_id,
    subcuenca_nombre,
    geometria_geojson,
    anio_tmf_visual_inicial,
    anio_tmf_visual_final,
    anio_esri_visual_inicial,
    anio_esri_visual_final,
    anio_ndvi_visual_inicial,
    anio_ndvi_visual_final,
    anio_tmf_capa,
    anio_esri_capa,
    anio_ndvi_capa,
    modo_analisis,
    modo_comparador,
    capas_activas,
    resultados=None,
):
    if tipo_area == TIPO_AREA_SUBCUENCA:
        especificacion_area = {
            "tipo": "subcuenca",
            "identificador": str(subcuenca_nombre),
            "fuente": FUENTE_SUBCUENCAS,
            "geometria_vectorial_incluida": True,
            "geojson": geometria_subcuenca(subcuenca_nombre),
            "recorte": FUENTE_CUENCA,
        }
    elif tipo_area == TIPO_AREA_DIBUJADA:
        especificacion_area = {
            "tipo": "poligono_dibujado",
            "geojson": json.loads(geometria_geojson),
            "recorte": FUENTE_CUENCA,
        }
    else:
        especificacion_area = {
            "tipo": "cuenca",
            "fuente": FUENTE_CUENCA,
            "geometria_vectorial_incluida": True,
            "geojson": geometria_cuenca(),
        }

    configuracion = {
        "metodologia": METHODOLOGY_VERSION,
        "modo_analisis": modo_analisis,
        "version_limites_locales": huella_territorial(),
        "area": especificacion_area,
        "periodos": {
            "referencia_metodologica": ANO_REFERENCIA_ANALISIS,
            "diagnostico_fijo": {
                "jrc": ANO_DIAG_TMF,
                "hansen": ANO_HANSEN_MAX,
                "esri_inicial": ANO_ESRI_MIN,
                "esri_final": ANO_ESRI_MAX,
                "ndvi_inicial": ANO_NDVI_INICIAL_ANALISIS,
                "ndvi_final": ANO_NDVI_FINAL_ANALISIS,
            },
            "visualizacion": {
                "comparador": modo_comparador,
                "jrc_inicial": anio_tmf_visual_inicial,
                "jrc_final": anio_tmf_visual_final,
                "esri_inicial": anio_esri_visual_inicial,
                "esri_final": anio_esri_visual_final,
                "ndvi_inicial": anio_ndvi_visual_inicial,
                "ndvi_final": anio_ndvi_visual_final,
                "capas_un_ano": {
                    "jrc": anio_tmf_capa,
                    "esri": anio_esri_capa,
                    "ndvi": anio_ndvi_capa,
                },
                "capas_disponibles": list(capas_activas),
            },
            "corte_referencia": CUTOFF_LABEL,
        },
        "fuentes": [
            {
                "nombre": "JRC Tropical Moist Forest",
                "asset": TMF_ASSET,
                "banda": f"Dec{ANO_DIAG_TMF}",
                "escala_m": 30,
                "uso": "diagnostico",
            },
            {
                "nombre": "Hansen Global Forest Change",
                "asset": HANSEN_ASSET,
                "bandas": ["treecover2000", "loss", "lossyear"],
                "escala_m": 30,
                "uso": "diagnostico",
            },
            {
                "nombre": "ESRI Land Use Land Cover",
                "asset": ESRI_ASSET,
                "escala_m": 10,
                "uso": "diagnostico",
            },
            {
                "nombre": "GEDI Canopy Height",
                "asset": GEDI_ASSET,
                "escala_m": 100,
                "uso": "contexto",
            },
            {
                "nombre": "Índice de Resiliencia Ecológica indicativo",
                "componentes": [
                    "integridad estructural",
                    "conectividad local del bosque",
                    "estabilidad topográfica",
                    "proximidad riparia",
                ],
                "fuentes": [
                    "Dynamic World",
                    "GEDI / OpenForis",
                    "Copernicus DEM GLO-30",
                    "MERIT Hydro",
                ],
                "escala_resumen_m": ESCALA_ERI_M,
                "pesos": dict(PESOS_ERI),
                "uso": (
                    "lectura ecologica complementaria; no modifica el indice de indicios "
                    "ni la prioridad de visita"
                ),
            },
            {
                "nombre": "Sentinel-2 Surface Reflectance Harmonized",
                "asset": "COPERNICUS/S2_SR_HARMONIZED",
                "bandas": ["B8", "B4", "SCL"],
                "escala_m": 10,
                "uso": "diagnostico corroborativo de disminucion del vigor vegetal",
            },
            {
                "nombre": "Mapa de conectividad ecologica de Panama",
                "organizacion": "Fundacion Almanaque Azul",
                "version": cargar_catalogo_corredores()["version_publicada"],
                "url": URL_MAPA_CORREDORES,
                "categorias": ["alta", "mediana", "media-baja"],
                "uso": (
                    "valor estrategico de la prioridad de visita; no modifica "
                    "el indice satelital de cambios"
                ),
            },
            {
                "nombre": FUENTE_BOSQUE_NOMBRE,
                "organizacion": FUENTE_BOSQUE_ORGANIZACION,
                "ano_referencia": ANO_BOSQUE_REFERENCIA,
                "formato": "asset vectorial institucional privado de Earth Engine",
                "configurado": bool(ASSET_BOSQUE_2021),
                "campo_clase": CAMPO_COBERTURA_BOSQUE_2021,
                "valor_bosque": VALOR_COBERTURA_BOSQUE_2021,
                "uso": (
                    "fragmentacion y conectividad estructural para focalizar "
                    "la visita; no participa en el puntaje ni constituye una serie anual"
                ),
            },
        ],
        "umbrales": dict(UMBRALES_INDICE),
        "justificacion_umbrales": dict(JUSTIFICACION_UMBRALES),
        "pesos": dict(PESOS_INDICE),
        "justificacion_pesos": dict(JUSTIFICACION_PESOS),
        "reglas_prioridad": dict(REGLAS_PRIORIDAD),
        "reglas_prioridad_visita": dict(REGLAS_PRIORIDAD_VISITA),
        "reglas_contexto_estructural": dict(REGLAS_CONTEXTO_ESTRUCTURAL),
        "reglas_consistencia": dict(REGLAS_CONSISTENCIA),
        "mapa_coincidencia_espacial": {
            "nombre": REGLAS_MAPA_COINCIDENCIA["nombre"],
            "malla_referencia_m": REGLAS_MAPA_COINCIDENCIA[
                "malla_referencia_m"
            ],
            "fuentes": dict(REGLAS_MAPA_COINCIDENCIA["fuentes"]),
            "clases": {
                str(clase): dict(especificacion)
                for clase, especificacion in REGLAS_MAPA_COINCIDENCIA[
                    "clases"
                ].items()
            },
            "participa_indice": REGLAS_MAPA_COINCIDENCIA["participa_indice"],
            "limitacion": REGLAS_MAPA_COINCIDENCIA["limitacion"],
        },
        "clases_vigor_ndvi": [dict(clase) for clase in CLASES_VIGOR_NDVI],
        "eri_indicativo": {
            "clases": [dict(clase) for clase in CLASES_ERI],
            "pesos": dict(PESOS_ERI),
            "radio_conectividad_m": RADIO_CONECTIVIDAD_ERI_M,
            "distancia_riparia_m": DISTANCIA_RIPARIA_ERI_M,
            "participa_en_prioridad": False,
            "limitacion": (
                "Indicador exploratorio que requiere validacion de campo. La conectividad "
                "es un proxy de cobertura local y no demuestra movimiento de fauna."
            ),
        },
        "procesamiento": {
            "unidad_area": "hectareas",
            "reduccion": "suma de area por clase en la proyeccion de cada fuente",
            "respuesta_earth_engine": "reducciones agrupadas en una sola respuesta",
            "ndvi": "mediana anual con mascara SCL y respaldo del ano anterior",
            "formula_ndvi": "(B8 - B4) / (B8 + B4)",
            "ndvi_escala_resumen_m": ESCALA_ANALISIS_NDVI_M,
            "coincidencia_espacial": (
                "JRC conserva su malla de 30 m; Hansen se reproyecta por vecino "
                "más cercano y ESRI se agrega desde 10 m por presencia máxima "
                "antes de sumar las tres señales binarias."
            ),
            "corredores": (
                "Interseccion vectorial en Equal Earth Americas (EPSG:8857); "
                "conserva las categorias originales de Almanaque Azul. El "
                "solapamiento y la pertenencia al Corredor Biologico "
                "Mesoamericano aportan a la prioridad separada de visita."
            ),
            "estructura_bosque": (
                "Los parches de Bosque y otros usos 2021 forman una red según el "
                "umbral seleccionado. Su condición orienta la focalización de la "
                "visita sin añadir un peso ecológico no calibrado."
            ),
            "eri": (
                "Promedio ponderado normalizado entre 0 y 1: integridad estructural 35 %, "
                "conectividad local 25 %, estabilidad topográfica 20 % y proximidad "
                "riparia 20 %. Se reporta por separado del puntaje operativo."
            ),
        },
    }
    huella = hashlib.sha256(
        json.dumps(configuracion, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    registro = {
        "aplicacion": APP_VERSION,
        "fecha_generacion": date.today().isoformat(),
        "codigo_reproducibilidad": huella,
        "explicacion_codigo": (
            "Identificador técnico generado a partir del área, las fuentes, los períodos, "
            "los umbrales, los pesos y las reglas de esta configuración."
        ),
        **configuracion,
        "alcance": (
            "Preevaluacion indicativa para priorizar revisiones. No constituye validacion "
            "de campo ni determina cumplimiento EUDR."
        ),
    }
    if resultados and "puntaje" in resultados:
        registro["resultados_resumen"] = {
            "area_ha": resultados["area_ha"],
            "puntaje": resultados["puntaje"],
            "prioridad": resultados["prioridad"],
            "senal_jrc": resultados["senal_tmf"],
            "senal_hansen": resultados["senal_hansen"],
            "senal_esri": resultados["senal_esri"],
            "senal_gedi": resultados["senal_gedi"],
            "senal_ndvi": resultados["senal_ndvi"],
            "aportes_indice": resultados["aportes_indice"],
            "consistencia": resultados["consistencia"],
            "corredores": resultados.get("corredores"),
            "prioridad_visita": resultados.get("prioridad_visita"),
            "eri_indicativo": (
                {
                    "valor": resultados["eri"].get("valor"),
                    "clase": resultados["eri"].get("clase"),
                    "componente_limitante": resultados["eri"].get(
                        "componente_limitante"
                    ),
                    "participa_en_prioridad": False,
                }
                if resultados.get("eri")
                else None
            ),
            "estadisticas": {
                "cobertura_arborea_persistente_2020_ha": resultados["linea_base"],
                "hansen_pre_2021_ha": resultados["hansen_pre"],
                "hansen_post_2020_ha": resultados["hansen_post"],
                "tmf_clases_ha": {
                    "bosque_estable": resultados["tmf_estable"],
                    "degradacion": resultados["tmf_degradacion"],
                    "deforestacion": resultados["tmf_deforestacion"],
                    "recuperacion": resultados["tmf_recuperacion"],
                    "agua": resultados["tmf_agua"],
                    "otra_cobertura": resultados["tmf_otra_cobertura"],
                },
                "esri_arboles_final_ha": resultados["esri_arboles_final"],
                "esri_salida_arboles_ha": resultados["esri_salida"],
                "esri_ganancia_arboles_ha": resultados["esri_ganancia"],
                "gedi_altura_media_m": resultados["gedi_altura"],
                "gedi_cobertura_valida_pct": resultados["gedi_cobertura_pct"],
                "ndvi_inicial_medio": resultados["ndvi_inicial_medio"],
                "ndvi_final_medio": resultados["ndvi_final_medio"],
                "ndvi_delta_medio": resultados["ndvi_delta_medio"],
                "ndvi_disminucion_ha": resultados["ndvi_disminucion"],
                "ndvi_disminucion_pct": resultados["pct_ndvi_disminucion"],
                "ndvi_cobertura_valida_pct": resultados["ndvi_cobertura_pct"],
                "coincidencia_espacial_ha": {
                    "una_fuente": resultados["coincidencia_1_fuente"],
                    "dos_fuentes": resultados["coincidencia_2_fuentes"],
                    "tres_fuentes": resultados["coincidencia_3_fuentes"],
                    "dos_o_tres_fuentes": resultados[
                        "coincidencia_varias_fuentes"
                    ],
                },
            },
        }
    elif resultados:
        registro["resultados_resumen"] = {
            "area_ha": resultados.get("area_ha"),
            "corredores": resultados.get("corredores"),
            "eri_indicativo": resultados.get("eri"),
        }

    if resultados and resultados.get("fragmentacion"):
        registro["resultados_resumen"]["fragmentacion_conectividad"] = {
            "metricas_clase": resultados["fragmentacion"]["metricas_clase"],
            "metricas_red": resultados["fragmentacion"]["metricas_red"],
            "conexion_corredor": resultados["fragmentacion"].get(
                "conexion_corredor"
            ),
            "top_conectores": resultados["fragmentacion"]["top_conectores"],
            "campo_clase": resultados["fragmentacion"]["campo_clase"],
            "valores_bosque": resultados["fragmentacion"]["valores_bosque"],
            "fuente_cobertura": resultados["fragmentacion"].get(
                "fuente_cobertura", FUENTE_BOSQUE_CORTA
            ),
            "ano_referencia_cobertura": resultados["fragmentacion"].get(
                "ano_referencia_cobertura", ANO_BOSQUE_REFERENCIA
            ),
            "metodo": resultados["fragmentacion"]["metodo"],
            "participa_indice_prioridad": False,
            "papel_diagnostico": (
                "orienta la focalizacion espacial de la visita y permite "
                "identificar conectores y componentes aislados"
            ),
        }
    return registro


def convertir_imagen_byte(imagen):
    """Uniforma las colecciones categóricas antes de añadir un respaldo."""

    return ee.Image(imagen).toByte()


def obtener_tmf(anio, geometria):
    nombre_banda = f"Dec{anio}"
    coleccion_tmf = (
        ee.ImageCollection(TMF_ASSET)
        .filterBounds(geometria)
        .select([nombre_banda], [nombre_banda])
        .map(convertir_imagen_byte)
    )
    respaldo = (
        ee.Image.constant(0)
        .rename(nombre_banda)
        .updateMask(ee.Image(0))
        .toByte()
        .setDefaultProjection("EPSG:4326", None, 30)
    )
    return (
        coleccion_tmf
        .merge(ee.ImageCollection.fromImages([respaldo]))
        .mosaic()
        .setDefaultProjection("EPSG:4326", None, 30)
        .rename(f"tmf_{anio}")
        .clip(geometria)
    )


def obtener_esri(anio, geometria):
    anio_seguro = max(ANO_ESRI_MIN, min(ANO_ESRI_MAX, anio))
    nombre_banda = f"esri_{anio_seguro}"
    coleccion_anual_esri = (
        ee.ImageCollection(ESRI_ASSET)
        .filterDate(f"{anio_seguro}-01-01", f"{anio_seguro}-12-31")
    )
    coleccion_esri = (
        coleccion_anual_esri
        .filterBounds(geometria)
        .select([0], [nombre_banda])
        .map(convertir_imagen_byte)
    )
    respaldo = (
        ee.Image.constant(0)
        .rename(nombre_banda)
        .updateMask(ee.Image(0))
        .toByte()
        .setDefaultProjection("EPSG:4326", None, 10)
    )
    return (
        coleccion_esri
        .merge(ee.ImageCollection.fromImages([respaldo]))
        .mosaic()
        .setDefaultProjection("EPSG:4326", None, 10)
        .rename(nombre_banda)
        .clip(geometria)
    )


def obtener_esri_visual(anio, geometria):
    return (
        obtener_esri(anio, geometria)
        .remap(ESRI_ORIG, ESRI_VIS)
        .rename(f"esri_visual_{anio}")
        .selfMask()
    )


def mascara_sentinel_scl(imagen):
    scl = imagen.select("SCL")
    mascara = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(11))
    return imagen.updateMask(mascara).select(["B8", "B4"]).toFloat()


def mascara_sentinel_rgb(imagen):
    scl = imagen.select("SCL")
    mascara = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(11))
    return imagen.updateMask(mascara).select(["B4", "B3", "B2"]).toFloat()


def obtener_rgb_sentinel(anio, geometria):
    coleccion = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometria)
        .filterDate(f"{anio}-01-01", f"{anio}-12-31")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .map(mascara_sentinel_rgb)
    )
    respaldo = (
        ee.Image.constant([0, 0, 0])
        .rename(["B4", "B3", "B2"])
        .updateMask(ee.Image(0))
        .toFloat()
    )
    return (
        coleccion.merge(ee.ImageCollection.fromImages([respaldo]))
        .median()
        .clip(geometria)
    )


def obtener_ndvi(anio, geometria):
    anio_respaldo = max(anio - 1, 2017)

    def coleccion(anio_consulta):
        return (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(geometria)
            .filterDate(f"{anio_consulta}-01-01", f"{anio_consulta}-12-31")
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
            .map(mascara_sentinel_scl)
        )

    fallback = (
        ee.Image.constant([0, 0])
        .rename(["B8", "B4"])
        .updateMask(ee.Image(0))
        .toFloat()
    )

    def mediana_con_fallback(coleccion_s2):
        return coleccion_s2.merge(
            ee.ImageCollection.fromImages([fallback])
        ).median()

    actual = mediana_con_fallback(coleccion(anio))
    anterior = mediana_con_fallback(coleccion(anio_respaldo))
    compuesto = ee.ImageCollection.fromImages(
        [fallback, anterior, actual]
    ).mosaic().setDefaultProjection("EPSG:4326", None, 10)

    return (
        compuesto.normalizedDifference(["B8", "B4"])
        .rename(f"ndvi_{anio}")
        .toFloat()
        .clip(geometria)
    )


def clasificar_ndvi(ndvi):
    clases = (
        ee.Image(0)
        .where(ndvi.lt(0.0), 0)
        .where(ndvi.gte(0.0).And(ndvi.lt(0.2)), 1)
        .where(ndvi.gte(0.2).And(ndvi.lt(0.4)), 2)
        .where(ndvi.gte(0.4).And(ndvi.lt(0.6)), 3)
        .where(ndvi.gte(0.6), 4)
    )
    return clases.updateMask(ndvi.mask()).rename("ndvi_clases").toInt()


def imagenes_hansen(geometria):
    hansen = ee.Image(HANSEN_ASSET)
    cobertura_2000 = hansen.select("treecover2000").unmask(0).gte(30)
    perdida = hansen.select("loss").unmask(0)
    anio_perdida = hansen.select("lossyear")

    perdida_post = (
        anio_perdida.updateMask(anio_perdida.gt(CUTOFF_YEAR))
        .rename("perdida_post")
        .clip(geometria)
    )
    perdida_pre = (
        anio_perdida.updateMask(
            anio_perdida.gt(0).And(anio_perdida.lte(CUTOFF_YEAR))
        )
        .rename("perdida_pre")
        .clip(geometria)
    )
    linea_base = (
        cobertura_2000.And(
            perdida.eq(0).Or(anio_perdida.unmask(0).gt(CUTOFF_YEAR))
        )
        .selfMask()
        .rename("linea_base_2020")
        .clip(geometria)
    )
    return perdida_post, perdida_pre, linea_base


def imagen_coincidencia_revision(
    geometria,
    tmf=None,
    perdida_post=None,
    esri_inicial=None,
    esri_final=None,
):
    """Estandariza tres señales de deterioro en la malla JRC de 30 m."""
    if tmf is None:
        tmf = obtener_tmf(ANO_DIAG_TMF, geometria)
    if perdida_post is None:
        perdida_post, _, _ = imagenes_hansen(geometria)
    if esri_inicial is None:
        esri_inicial = obtener_esri(ANO_ESRI_MIN, geometria)
    if esri_final is None:
        esri_final = obtener_esri(ANO_ESRI_MAX, geometria)

    proyeccion_referencia = ee.Image(tmf).projection()
    proyeccion_esri = ee.Image(esri_inicial).projection()
    senal_jrc = (
        ee.Image(tmf)
        .eq(2)
        .Or(ee.Image(tmf).eq(3))
        .unmask(0)
        .rename("senal_jrc")
    )
    senal_hansen = (
        ee.Image(perdida_post)
        .gt(0)
        .unmask(0)
        .reproject(crs=proyeccion_referencia)
        .rename("senal_hansen")
    )
    senal_esri_10m = (
        ee.Image(esri_inicial)
        .eq(2)
        .And(ee.Image(esri_final).neq(2))
        .unmask(0)
        .setDefaultProjection(proyeccion_esri)
    )
    senal_esri = (
        senal_esri_10m.reduceResolution(
            reducer=ee.Reducer.max(),
            bestEffort=True,
            maxPixels=1024,
        )
        .reproject(crs=proyeccion_referencia)
        .gt(0)
        .rename("senal_esri")
    )
    return (
        senal_jrc.add(senal_hansen)
        .add(senal_esri)
        .rename("fuentes_coincidentes")
        .toByte()
        .clip(geometria)
    )


def convertir_altura_gedi_float(imagen):
    """Uniforma el tipo de píxel antes de añadir el respaldo sin datos."""

    return ee.Image(imagen).toFloat()


def imagen_gedi(geometria):
    coleccion_gedi = (
        ee.ImageCollection(GEDI_ASSET)
        .filterBounds(geometria)
        .select([0], ["altura_dosel"])
        .map(convertir_altura_gedi_float)
    )
    respaldo = (
        ee.Image.constant(0)
        .rename("altura_dosel")
        .updateMask(ee.Image(0))
        .toFloat()
        .setDefaultProjection("EPSG:4326", None, 100)
    )
    return (
        coleccion_gedi
        .merge(ee.ImageCollection.fromImages([respaldo]))
        .mosaic()
        .setDefaultProjection("EPSG:4326", None, 100)
        .rename("altura_dosel")
        .clip(geometria)
    )


def convertir_probabilidad_arboles_float(imagen):
    """Uniforma Dynamic World antes de calcular la probabilidad anual de árboles."""

    return ee.Image(imagen).select(["trees"], ["p_arboles"]).toFloat()


def obtener_probabilidad_arboles(anio, geometria):
    """Probabilidad media anual de la clase árboles según Dynamic World."""

    coleccion = (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterBounds(geometria)
        .filterDate(f"{anio}-01-01", f"{anio + 1}-01-01")
        .map(convertir_probabilidad_arboles_float)
    )
    respaldo = (
        ee.Image.constant(0)
        .rename("p_arboles")
        .updateMask(ee.Image(0))
        .toFloat()
        .setDefaultProjection("EPSG:4326", None, 10)
    )
    return (
        coleccion.merge(ee.ImageCollection.fromImages([respaldo]))
        .mean()
        .setDefaultProjection("EPSG:4326", None, 10)
        .rename("p_arboles")
        .clip(geometria)
    )


def construir_imagenes_eri(geometria):
    """Construye un ERI indicativo y sus cuatro componentes en Earth Engine.

    La conectividad se representa con la proporción local de bosque en una ventana
    de 1.5 km. Es un proxy espacial ligero, no reemplaza ECA/A ni una evaluación
    funcional por especie. Esta decisión mantiene el cálculo viable en Streamlit y
    se declara de forma explícita en la interfaz.
    """

    p_arboles = obtener_probabilidad_arboles(
        ANO_ERI_REFERENCIA,
        geometria,
    ).unmask(0).clamp(0, 1)

    altura_normalizada = (
        imagen_gedi(geometria)
        .divide(ALTURA_REFERENCIA_ERI_M)
        .clamp(0, 1)
        .unmask(p_arboles)
    )
    integridad = (
        altura_normalizada.multiply(0.5)
        .add(p_arboles.multiply(0.5))
        .rename("integridad_estructural")
    )

    proyeccion_eri = ee.Projection("EPSG:4326").atScale(ESCALA_ERI_M)
    bosque = (
        p_arboles.gte(0.5)
        .toFloat()
        .setDefaultProjection("EPSG:4326", None, 10)
    )
    bosque_eri = (
        bosque.reduceResolution(
            reducer=ee.Reducer.mean(),
            bestEffort=True,
            maxPixels=1024,
        )
        .reproject(crs=proyeccion_eri)
    )
    conectividad = (
        bosque_eri.focalMean(
            radius=RADIO_CONECTIVIDAD_ERI_M,
            kernelType="circle",
            units="meters",
        )
        .clamp(0, 1)
        .rename("conectividad")
    )

    dem_coleccion = (
        ee.ImageCollection("COPERNICUS/DEM/GLO30")
        .filterBounds(geometria)
        .select("DEM")
    )
    dem = (
        dem_coleccion.mosaic()
        .setDefaultProjection(ee.Image(dem_coleccion.first()).projection())
        .clip(geometria)
    )
    pendiente = ee.Terrain.slope(dem).divide(45).clamp(0, 1)
    estabilidad = (
        ee.Image(1)
        .subtract(pendiente.multiply(ee.Image(1).subtract(p_arboles)))
        .clamp(0, 1)
        .rename("estabilidad_topografica")
    )

    acumulacion = ee.Image("MERIT/Hydro/v1_0_1").select("upa")
    proyeccion_merit = acumulacion.projection()
    cauces = (
        acumulacion.gte(AREA_DRENAJE_ERI_KM2)
        .unmask(0)
        .setDefaultProjection(proyeccion_merit)
    )
    distancia_cauce_m = (
        cauces.fastDistanceTransform(256, "pixels", "squared_euclidean")
        .sqrt()
        .multiply(proyeccion_merit.nominalScale())
    )
    proximidad_riparia = (
        ee.Image(1)
        .subtract(distancia_cauce_m.divide(DISTANCIA_RIPARIA_ERI_M).clamp(0, 1))
        .rename("proximidad_riparia")
        .clip(geometria)
    )

    componentes = {
        "integridad_estructural": integridad.clip(geometria),
        "conectividad": conectividad.clip(geometria),
        "estabilidad_topografica": estabilidad.clip(geometria),
        "proximidad_riparia": proximidad_riparia,
    }
    eri = ee.Image(0)
    for clave, peso in PESOS_ERI.items():
        eri = eri.add(componentes[clave].multiply(peso))
    eri = eri.clamp(0, 1).rename("eri").clip(geometria)
    return eri, componentes


def clasificar_imagen_eri(eri):
    """Convierte el ERI continuo en cinco clases cartográficas etiquetadas."""

    clases = ee.Image(1)
    for indice, clase in enumerate(CLASES_ERI[1:], start=2):
        clases = clases.where(ee.Image(eri).gte(clase["minimo"]), indice)
    return clases.updateMask(ee.Image(eri).mask()).rename("eri_clase").toByte()


def imagen_bosque_contexto(geometria, distancia_m=RADIO_BUSQUEDA_CORREDOR_M):
    """Pinta la cobertura institucional dentro del área y su entorno de consulta."""

    limite_contexto = geometria.buffer(float(distancia_m))
    bosque = (
        ee.FeatureCollection(ASSET_BOSQUE_2021)
        .filter(
            ee.Filter.eq(
                CAMPO_COBERTURA_BOSQUE_2021,
                VALOR_COBERTURA_BOSQUE_2021,
            )
        )
        .filterBounds(limite_contexto)
    )
    return ee.Image(0).byte().paint(bosque, 1).selfMask().clip(limite_contexto)


def numero(diccionario, clave):
    valor = diccionario.get(clave)
    return float(valor) if valor is not None else 0.0


def reducir_superficies(imagen, geometria, escala, proyeccion=None):
    parametros = {
        "reducer": ee.Reducer.sum(),
        "geometry": geometria,
        "scale": escala,
        "bestEffort": True,
        "maxPixels": 1e9,
        "tileScale": 4,
    }
    if proyeccion is not None:
        parametros["crs"] = proyeccion
    return ee.Dictionary(imagen.reduceRegion(**parametros))


def normalizar_histograma_gedi(histograma):
    """Convierte los intervalos devueltos por Earth Engine en columnas graficables."""

    intervalos = histograma or []
    return {
        "Altura (m)": [round((float(fila[0]) + float(fila[1])) / 2, 1) for fila in intervalos],
        "Observaciones": [int(round(float(fila[2]))) for fila in intervalos],
    }


def calcular_serie_fuente(
    tipo_area,
    finca_id,
    subcuenca_nombre,
    geometria_geojson,
    fuente,
):
    """Calcula una sola gráfica por solicitud para no sobrecargar Earth Engine."""

    area_fc = obtener_area(
        tipo_area=tipo_area,
        finca_id=finca_id,
        subcuenca_nombre=subcuenca_nombre,
        geometria_geojson=geometria_geojson,
    )
    geometria = area_fc.geometry(TOLERANCIA_RECORTE_M)
    pixel_ha = ee.Image.pixelArea().divide(10000)

    if fuente == "JRC Tropical Moist Forest":
        anios = list(range(2000, ANO_TMF_MAX + 1))
        bandas = []
        for anio in anios:
            tmf = obtener_tmf(anio, geometria)
            bandas.extend(
                [
                    tmf.eq(3).unmask(0).multiply(pixel_ha).rename(f"def_{anio}"),
                    tmf.eq(2).unmask(0).multiply(pixel_ha).rename(f"deg_{anio}"),
                    tmf.eq(4).unmask(0).multiply(pixel_ha).rename(f"regen_{anio}"),
                ]
            )
        resumen = reducir_superficies(
            ee.Image.cat(bandas),
            geometria,
            30,
            obtener_tmf(ANO_TMF_MAX, geometria).projection(),
        ).getInfo()
        return {
            "titulo": "Cambio forestal anual según JRC TMF",
            "descripcion": (
                "Superficie clasificada cada año como deforestación, degradación o "
                "regeneración forestal. Las tres series pertenecen a la misma fuente "
                "y sí pueden compararse."
            ),
            "tipo": "barras",
            "columnas": {
                "Año": anios,
                "Deforestación (ha)": [numero(resumen, f"def_{anio}") for anio in anios],
                "Degradación (ha)": [numero(resumen, f"deg_{anio}") for anio in anios],
                "Regeneración forestal (ha)": [
                    numero(resumen, f"regen_{anio}") for anio in anios
                ],
            },
        }

    if fuente == "Hansen Global Forest Change":
        anios = list(range(2001, ANO_HANSEN_MAX + 1))
        anio_perdida = ee.Image(HANSEN_ASSET).select("lossyear")
        bandas = [
            anio_perdida.eq(anio - 2000)
            .unmask(0)
            .multiply(pixel_ha)
            .rename(f"perdida_{anio}")
            for anio in anios
        ]
        resumen = reducir_superficies(
            ee.Image.cat(bandas),
            geometria,
            30,
            ee.Image(HANSEN_ASSET).projection(),
        ).getInfo()
        return {
            "titulo": "Pérdida anual de cobertura arbórea según Hansen",
            "descripcion": (
                "Hectáreas con pérdida anual de cobertura arbórea. La fuente detecta "
                "pérdida, pero por sí sola no identifica su causa."
            ),
            "tipo": "barras",
            "columnas": {
                "Año": anios,
                "Pérdida (ha)": [
                    numero(resumen, f"perdida_{anio}") for anio in anios
                ],
            },
        }

    if fuente == "ESRI Land Use / Land Cover":
        anios = list(range(ANO_ESRI_MIN, ANO_ESRI_MAX + 1))
        bandas = [
            obtener_esri(anio, geometria)
            .eq(2)
            .unmask(0)
            .multiply(pixel_ha)
            .rename(f"arboles_{anio}")
            for anio in anios
        ]
        resumen = reducir_superficies(
            ee.Image.cat(bandas),
            geometria,
            10,
            obtener_esri(ANO_ESRI_MAX, geometria).projection(),
        ).getInfo()
        return {
            "titulo": "Cobertura arbórea anual según ESRI",
            "descripcion": (
                "Superficie clasificada como árboles en cada edición anual. Cambios "
                "pequeños pueden reflejar tanto cambios reales como diferencias de clasificación."
            ),
            "tipo": "barras",
            "columnas": {
                "Año": anios,
                "Cobertura arbórea (ha)": [
                    numero(resumen, f"arboles_{anio}") for anio in anios
                ],
            },
        }

    if fuente == "Sentinel-2 · NDVI":
        anios = list(range(2017, ANO_NDVI_MAX + 1))
        bandas = [
            obtener_ndvi(anio, geometria).rename(f"ndvi_{anio}") for anio in anios
        ]
        resumen = ee.Image.cat(bandas).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometria,
            scale=max(100, ESCALA_ANALISIS_NDVI_M),
            bestEffort=True,
            maxPixels=1e9,
            tileScale=4,
        ).getInfo()
        return {
            "titulo": "Vigor medio de la vegetación según NDVI",
            "descripcion": (
                "Promedio anual del NDVI calculado con Sentinel-2. Sirve como señal "
                "corroborativa; nubes, estacionalidad y agua pueden afectar la lectura."
            ),
            "tipo": "barras",
            "columnas": {
                "Año": anios,
                "NDVI medio": [numero(resumen, f"ndvi_{anio}") for anio in anios],
            },
        }

    if fuente == "GEDI · altura del dosel":
        histograma = (
            imagen_gedi(geometria)
            .reduceRegion(
                reducer=ee.Reducer.fixedHistogram(0, 60, 12),
                geometry=geometria,
                scale=100,
                bestEffort=True,
                maxPixels=1e9,
                tileScale=4,
            )
            .get("altura_dosel")
            .getInfo()
        )
        return {
            "titulo": "Distribución de altura del dosel según GEDI",
            "descripcion": (
                "GEDI no es una serie anual comparable. Por eso se muestra la distribución "
                "de alturas disponibles y no una serie temporal artificial."
            ),
            "tipo": "barras",
            "columnas": normalizar_histograma_gedi(histograma),
        }

    raise ValueError(f"Fuente no reconocida: {fuente}")


def analizar_bosque_asset(
    asset_id,
    campo_clase,
    valor_bosque,
    aoi_geojson_serializado,
    umbral_m,
    area_min_ha,
    radio_contexto_m,
):
    aoi_geojson = json.loads(aoi_geojson_serializado)
    aoi_ee = ee.Geometry(aoi_geojson)
    radio_contexto_m = min(
        float(RADIO_BUSQUEDA_CORREDOR_M),
        max(float(umbral_m), float(radio_contexto_m)),
    )
    contexto_ee = aoi_ee.buffer(radio_contexto_m)
    bosque_en_contexto = (
        ee.FeatureCollection(asset_id)
        .filter(ee.Filter.eq(campo_clase, valor_bosque))
        .filterBounds(contexto_ee)
    )
    if int(bosque_en_contexto.size().getInfo()) == 0:
        geometria_bosque = {"type": "FeatureCollection", "features": []}
    else:
        geometria_bosque = (
            bosque_en_contexto
            .geometry(TOLERANCIA_GEOMETRIA_CONECTIVIDAD_M)
            .intersection(contexto_ee, TOLERANCIA_GEOMETRIA_CONECTIVIDAD_M)
            .simplify(TOLERANCIA_GEOMETRIA_CONECTIVIDAD_M)
            .getInfo()
        )
    return analizar_fragmentacion_geojson(
        bosque_geojson=geometria_bosque,
        aoi_geojson=aoi_geojson,
        umbral_m=umbral_m,
        area_min_ha=area_min_ha,
        incluir_contexto_exterior=True,
        corredores_geojson=cargar_corredores(),
        radio_busqueda_corredor_m=radio_contexto_m,
    )


def calcular_eri_indicativo(
    tipo_area,
    finca_id,
    subcuenca_nombre,
    geometria_geojson,
):
    """Resume el ERI y su distribución sin alterar el puntaje de prioridad."""

    area_fc = obtener_area(
        tipo_area=tipo_area,
        finca_id=finca_id,
        subcuenca_nombre=subcuenca_nombre,
        geometria_geojson=geometria_geojson,
    )
    geometria = area_fc.geometry(TOLERANCIA_RECORTE_M)
    eri, componentes = construir_imagenes_eri(geometria)
    imagen_medias = ee.Image.cat(
        [componentes[clave].rename(clave) for clave in PESOS_ERI]
        + [eri.rename("eri")]
    )
    medias = ee.Dictionary(
        imagen_medias.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometria,
            scale=ESCALA_ERI_M,
            bestEffort=True,
            maxPixels=1e9,
            tileScale=4,
        )
    )
    clases = clasificar_imagen_eri(eri)
    pixel_ha = ee.Image.pixelArea().divide(10000)
    bandas_areas = []
    for indice, clase in enumerate(CLASES_ERI, start=1):
        bandas_areas.append(
            clases.eq(indice)
            .unmask(0)
            .multiply(pixel_ha)
            .rename(f"eri_{clase['clave']}_ha")
        )
    areas = reducir_superficies(
        ee.Image.cat(bandas_areas),
        geometria,
        ESCALA_ERI_M,
    )
    resumen = medias.combine(areas, True).getInfo()
    resultado = construir_resultado_eri(resumen)
    resultado.update(
        {
            "anio_referencia": ANO_ERI_REFERENCIA,
            "escala_resumen_m": ESCALA_ERI_M,
            "radio_conectividad_m": RADIO_CONECTIVIDAD_ERI_M,
            "distancia_riparia_m": DISTANCIA_RIPARIA_ERI_M,
            "fuentes": [
                "Dynamic World",
                "GEDI / OpenForis",
                "Copernicus DEM GLO-30",
                "MERIT Hydro",
            ],
            "nota_conectividad": (
                "La conectividad usa la proporción local de bosque en una ventana de "
                "1.5 km como proxy espacial ligero. No representa conectividad funcional "
                "por especie ni sustituye ECA/A."
            ),
            "nota_estructura": (
                "La integridad combina altura GEDI normalizada y probabilidad de árboles. "
                "Cuando GEDI no tiene cobertura, la probabilidad de árboles actúa como respaldo."
            ),
        }
    )
    return resultado


def ejecutar_analisis(
    tipo_area,
    finca_id,
    subcuenca_nombre,
    geometria_geojson,
    anio_tmf_diagnostico,
    anio_esri_inicial,
    anio_esri_final,
):
    area_fc = obtener_area(
        tipo_area=tipo_area,
        finca_id=finca_id,
        subcuenca_nombre=subcuenca_nombre,
        geometria_geojson=geometria_geojson,
    )
    geometria = area_fc.geometry(TOLERANCIA_RECORTE_M)

    tmf = obtener_tmf(anio_tmf_diagnostico, geometria)
    esri_inicial = obtener_esri(anio_esri_inicial, geometria)
    esri_final = obtener_esri(anio_esri_final, geometria)
    perdida_post, perdida_pre, linea_base = imagenes_hansen(geometria)
    coincidencia_revision = imagen_coincidencia_revision(
        geometria,
        tmf=tmf,
        perdida_post=perdida_post,
        esri_inicial=esri_inicial,
        esri_final=esri_final,
    )
    gedi = imagen_gedi(geometria)
    ndvi_inicial = obtener_ndvi(ANO_NDVI_INICIAL_ANALISIS, geometria)
    ndvi_final = obtener_ndvi(ANO_NDVI_FINAL_ANALISIS, geometria)
    delta_ndvi = ndvi_final.subtract(ndvi_inicial).rename("ndvi_delta")
    mascara_ndvi_valida = ndvi_inicial.mask().And(ndvi_final.mask())
    disminucion_ndvi = (
        ndvi_inicial.gte(UMBRAL_VIGOR_INICIAL_NDVI)
        .And(delta_ndvi.lte(UMBRAL_DELTA_NDVI))
        .updateMask(mascara_ndvi_valida)
    )
    pixel_ha = ee.Image.pixelArea().divide(10000)

    # Cada fuente se reduce en su propia resolución y proyección. Esto evita
    # forzar los datos ESRI de 10 m a la malla de los productos de 30 m.
    areas_tmf = ee.Image.cat(
        [
            tmf.eq(1).unmask(0).multiply(pixel_ha).rename("tmf_estable"),
            tmf.eq(2).unmask(0).multiply(pixel_ha).rename("tmf_degradacion"),
            tmf.eq(3).unmask(0).multiply(pixel_ha).rename("tmf_deforestacion"),
            tmf.eq(4).unmask(0).multiply(pixel_ha).rename("tmf_recuperacion"),
            tmf.eq(5).unmask(0).multiply(pixel_ha).rename("tmf_agua"),
            tmf.eq(6).unmask(0).multiply(pixel_ha).rename("tmf_otra_cobertura"),
            coincidencia_revision.eq(1).unmask(0).multiply(pixel_ha).rename(
                "coincidencia_1_fuente"
            ),
            coincidencia_revision.eq(2).unmask(0).multiply(pixel_ha).rename(
                "coincidencia_2_fuentes"
            ),
            coincidencia_revision.eq(3).unmask(0).multiply(pixel_ha).rename(
                "coincidencia_3_fuentes"
            ),
        ]
    )
    areas_hansen = ee.Image.cat(
        [
            perdida_post.gt(0).unmask(0).multiply(pixel_ha).rename("hansen_post"),
            perdida_pre.gt(0).unmask(0).multiply(pixel_ha).rename("hansen_pre"),
            linea_base.unmask(0).multiply(pixel_ha).rename("linea_base"),
        ]
    )
    areas_esri = ee.Image.cat(
        [
            esri_final.eq(2).unmask(0).multiply(pixel_ha).rename("esri_arboles_final"),
            esri_inicial.eq(2).And(esri_final.neq(2)).unmask(0).multiply(pixel_ha).rename("esri_salida"),
            esri_inicial.neq(2).And(esri_final.eq(2)).unmask(0).multiply(pixel_ha).rename("esri_ganancia"),
            esri_inicial.eq(2).And(esri_final.eq(2)).unmask(0).multiply(pixel_ha).rename("esri_estable"),
        ]
    )
    areas_ndvi = ee.Image.cat(
        [
            disminucion_ndvi.unmask(0)
            .multiply(pixel_ha)
            .rename("ndvi_disminucion"),
            mascara_ndvi_valida.unmask(0)
            .multiply(pixel_ha)
            .rename("ndvi_area_datos"),
        ]
    )
    estadisticas_ndvi = ee.Image.cat(
        [
            ndvi_inicial.rename("ndvi_inicial_medio"),
            ndvi_final.rename("ndvi_final_medio"),
            delta_ndvi.rename("ndvi_delta_medio"),
        ]
    ).updateMask(mascara_ndvi_valida)

    # Las reducciones conservan la escala y proyección de cada fuente, pero se
    # agrupan en una sola respuesta para evitar varios viajes de red consecutivos.
    resumen = (
        reducir_superficies(areas_tmf, geometria, 30, tmf.projection())
        .combine(
            reducir_superficies(
                areas_hansen,
                geometria,
                30,
                ee.Image(HANSEN_ASSET).projection(),
            ),
            True,
        )
        .combine(
            reducir_superficies(
                areas_esri,
                geometria,
                10,
                esri_final.projection(),
            ),
            True,
        )
        .combine(
            reducir_superficies(
                areas_ndvi,
                geometria,
                ESCALA_ANALISIS_NDVI_M,
                ndvi_final.projection(),
            ),
            True,
        )
        .combine(
            ee.Dictionary(
                estadisticas_ndvi.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geometria,
                    scale=ESCALA_ANALISIS_NDVI_M,
                    bestEffort=True,
                    maxPixels=1e9,
                    tileScale=4,
                )
            ),
            True,
        )
        .combine(
            ee.Dictionary(
                {
                    "area_ha": geometria.area(1).divide(10000),
                    "gedi_altura": gedi.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geometria,
                        scale=100,
                        bestEffort=True,
                        maxPixels=1e9,
                        tileScale=4,
                    ).get("altura_dosel"),
                    "gedi_area_datos": gedi.mask()
                    .multiply(pixel_ha)
                    .reduceRegion(
                        reducer=ee.Reducer.sum(),
                        geometry=geometria,
                        scale=100,
                        bestEffort=True,
                        maxPixels=1e9,
                        tileScale=4,
                    )
                    .get("altura_dosel"),
                }
            ),
            True,
        )
        .getInfo()
    )

    claves_areas = [
        "tmf_estable",
        "tmf_degradacion",
        "tmf_deforestacion",
        "tmf_recuperacion",
        "tmf_agua",
        "tmf_otra_cobertura",
        "coincidencia_1_fuente",
        "coincidencia_2_fuentes",
        "coincidencia_3_fuentes",
        "hansen_post",
        "hansen_pre",
        "linea_base",
        "esri_arboles_final",
        "esri_salida",
        "esri_ganancia",
        "esri_estable",
        "ndvi_disminucion",
        "ndvi_area_datos",
    ]
    resultados = {clave: numero(resumen, clave) for clave in claves_areas}
    area_ha = numero(resumen, "area_ha")
    resultados["area_ha"] = area_ha
    resultados["gedi_altura"] = numero(resumen, "gedi_altura")
    resultados["gedi_area_datos"] = numero(resumen, "gedi_area_datos")
    resultados["gedi_cobertura_pct"] = (
        resultados["gedi_area_datos"] / area_ha * 100 if area_ha else 0
    )
    resultados["ndvi_inicial_medio"] = numero(resumen, "ndvi_inicial_medio")
    resultados["ndvi_final_medio"] = numero(resumen, "ndvi_final_medio")
    resultados["ndvi_delta_medio"] = numero(resumen, "ndvi_delta_medio")
    resultados["ndvi_cobertura_pct"] = (
        resultados["ndvi_area_datos"] / area_ha * 100 if area_ha else 0
    )
    resultados["coincidencia_varias_fuentes"] = (
        resultados["coincidencia_2_fuentes"]
        + resultados["coincidencia_3_fuentes"]
    )
    resultados["pct_coincidencia_varias_fuentes"] = (
        resultados["coincidencia_varias_fuentes"] / area_ha * 100
        if area_ha
        else 0
    )

    pct_tmf_defor = resultados["tmf_deforestacion"] / area_ha * 100 if area_ha else 0
    pct_tmf_degrad = resultados["tmf_degradacion"] / area_ha * 100 if area_ha else 0
    pct_tmf_recuperacion = (
        resultados["tmf_recuperacion"] / area_ha * 100 if area_ha else 0
    )
    pct_esri_salida = resultados["esri_salida"] / area_ha * 100 if area_ha else 0
    pct_esri_ganancia = (
        resultados["esri_ganancia"] / area_ha * 100 if area_ha else 0
    )
    pct_linea_base = resultados["linea_base"] / area_ha * 100 if area_ha else 0
    pct_ndvi_disminucion = (
        resultados["ndvi_disminucion"] / area_ha * 100 if area_ha else 0
    )

    senales, disponibilidad = evaluar_senales(
        tmf_deforestacion_ha=resultados["tmf_deforestacion"],
        tmf_deforestacion_pct=pct_tmf_defor,
        tmf_degradacion_ha=resultados["tmf_degradacion"],
        tmf_degradacion_pct=pct_tmf_degrad,
        hansen_post_2020_ha=resultados["hansen_post"],
        esri_salida_arboles_ha=resultados["esri_salida"],
        esri_salida_arboles_pct=pct_esri_salida,
        gedi_altura_media_m=resultados["gedi_altura"],
        gedi_cobertura_valida_pct=resultados["gedi_cobertura_pct"],
        linea_base_arborea_pct=pct_linea_base,
        ndvi_disminucion_ha=resultados["ndvi_disminucion"],
        ndvi_disminucion_pct=pct_ndvi_disminucion,
        ndvi_cobertura_valida_pct=resultados["ndvi_cobertura_pct"],
    )
    senal_tmf = senales["tmf"]
    senal_hansen = senales["hansen"]
    senal_esri = senales["esri"]
    senal_gedi = senales["gedi"]
    senal_ndvi = senales["ndvi"]

    aportes_indice, puntaje, prioridad = calcular_indice_prioridad(
        senal_tmf=senal_tmf,
        senal_hansen=senal_hansen,
        senal_esri=senal_esri,
        senal_gedi=senal_gedi,
        senal_ndvi=senal_ndvi,
    )
    consistencia = evaluar_consistencia(
        senal_tmf=senal_tmf,
        senal_hansen=senal_hansen,
        senal_esri=senal_esri,
        tmf_recuperacion_ha=resultados["tmf_recuperacion"],
        tmf_recuperacion_pct=pct_tmf_recuperacion,
        esri_ganancia_arboles_ha=resultados["esri_ganancia"],
        esri_ganancia_arboles_pct=pct_esri_ganancia,
    )

    resultados.update(
        {
            "pct_tmf_defor": pct_tmf_defor,
            "pct_tmf_degrad": pct_tmf_degrad,
            "pct_tmf_recuperacion": pct_tmf_recuperacion,
            "pct_esri_salida": pct_esri_salida,
            "pct_esri_ganancia": pct_esri_ganancia,
            "pct_linea_base": pct_linea_base,
            "pct_ndvi_disminucion": pct_ndvi_disminucion,
            "senal_tmf": senal_tmf,
            "senal_hansen": senal_hansen,
            "senal_esri": senal_esri,
            "senal_gedi": senal_gedi,
            "senal_ndvi": senal_ndvi,
            "gedi_disponible": disponibilidad["gedi"],
            "ndvi_disponible": disponibilidad["ndvi"],
            "aportes_indice": aportes_indice,
            "puntaje": puntaje,
            "prioridad": prioridad,
            "consistencia": consistencia,
        }
    )
    return resultados


def texto_recomendacion(prioridad):
    return {
        "Alta": "Visita de campo prioritaria en los sectores con señales coincidentes.",
        "Media": "Revisar imágenes recientes y evaluar si se justifica una visita.",
        "Preventiva": "Mantener monitoreo periódico y revisar condiciones de riesgo.",
        "Baja": "Sin acción inmediata. Continuar el monitoreo anual normal.",
    }[prioridad]


def visualizar_con_borde(imagen, visualizacion, area_fc, fondo=None):
    visual = ee.Image(imagen).visualize(**visualizacion)
    if fondo is not None:
        visual = ee.Image(fondo).visualize(**VIS_RGB).blend(visual)
    borde = (
        ee.Image()
        .byte()
        .paint(featureCollection=area_fc, color=1, width=4)
        .selfMask()
        .visualize(min=1, max=1, palette=["00E5FF"])
    )
    return visual.blend(borde)


def crear_url_miniatura(imagen, region, dimension):
    """Solicita a Earth Engine una URL temporal sin descargar todavía el PNG."""
    return ee.Image(imagen).getThumbURL(
        {
            "region": region,
            # Una dimensión conserva la proporción original del territorio.
            "dimensions": dimension,
            "format": "png",
        }
    )


def descargar_url_miniatura(url):
    """Descarga y valida una miniatura ya preparada por Earth Engine."""
    respuesta = requests.get(
        url,
        timeout=(10, 60),
        headers={"User-Agent": "visor-preevaluacion-territorial/1.0"},
    )
    respuesta.raise_for_status()
    if len(respuesta.content) < 1000 or not respuesta.content.startswith(b"\x89PNG"):
        raise RuntimeError("respuesta PNG no válida")
    return respuesta.content


def descargar_miniaturas(especificaciones, geometria, mapas_existentes=None):
    """Descarga los mapas en paralelo y reintenta únicamente los que fallan."""
    # Antes se consultaban estos límites una vez por cada mapa. Una sola consulta
    # reduce siete viajes innecesarios a Earth Engine.
    region = geometria.bounds(1).coordinates().getInfo()
    existentes_por_titulo = {
        mapa["titulo"]: mapa
        for mapa in (mapas_existentes or [])
        if mapa.get("imagen")
    }
    resultados = [
        existentes_por_titulo.get(titulo)
        for titulo, _, _ in especificaciones
    ]
    pendientes = {
        indice for indice, resultado in enumerate(resultados) if resultado is None
    }
    fallos = {indice: [] for indice in pendientes}

    # 1200 px conserva buena definición para el PDF. El segundo intento a 800 px
    # reduce el costo solo cuando Earth Engine no logra servir el mapa principal.
    for dimension in (1200, 800):
        if not pendientes:
            break

        urls = {}
        for indice in list(pendientes):
            titulo, imagen, _ = especificaciones[indice]
            try:
                urls[indice] = crear_url_miniatura(imagen, region, dimension)
            except Exception as error:
                fallos[indice].append(
                    f"{dimension}px al solicitar: {type(error).__name__}"
                )

        if not urls:
            continue

        # Tres solicitudes simultáneas acortan la espera sin saturar la cuota de
        # Earth Engine ni la memoria limitada de Streamlit Community Cloud.
        trabajadores = min(3, len(urls))
        with ThreadPoolExecutor(max_workers=trabajadores) as ejecutor:
            futuros = {
                ejecutor.submit(descargar_url_miniatura, url): indice
                for indice, url in urls.items()
            }
            for futuro in as_completed(futuros):
                indice = futuros[futuro]
                titulo, _, leyenda = especificaciones[indice]
                try:
                    resultados[indice] = {
                        "titulo": titulo,
                        "imagen": futuro.result(),
                        "leyenda": leyenda,
                    }
                    pendientes.discard(indice)
                except Exception as error:
                    # No se registran la URL ni sus tokens temporales.
                    fallos[indice].append(f"{dimension}px: {type(error).__name__}")

    errores = []
    for indice in sorted(pendientes):
        titulo, _, leyenda = especificaciones[indice]
        resultados[indice] = {"titulo": titulo, "imagen": None, "leyenda": leyenda}
        errores.append(
            f"{titulo}: Miniatura no disponible después de reintentos "
            f"({', '.join(fallos[indice]) or 'sin respuesta'})."
        )
    return resultados, errores


def generar_mapas_reporte(
    tipo_area,
    finca_id,
    subcuenca_nombre,
    geometria_geojson,
    anio_tmf_diagnostico,
    anio_esri_inicial,
    anio_esri_final,
    anio_ndvi_inicial,
    intento_cache=0,
    _mapas_existentes=None,
):
    _ = intento_cache

    area_fc = obtener_area(
        tipo_area=tipo_area,
        finca_id=finca_id,
        subcuenca_nombre=subcuenca_nombre,
        geometria_geojson=geometria_geojson,
    )

    geometria = area_fc.geometry(TOLERANCIA_RECORTE_M)
    # El número de intento forma parte de la clave de caché y permite reintentar
    # si Earth Engine no entrega alguna miniatura temporalmente.
    tmf = obtener_tmf(anio_tmf_diagnostico, geometria)
    gedi = imagen_gedi(geometria)
    ndvi_final = obtener_ndvi(ANO_NDVI_MAX, geometria)
    ndvi_inicial = obtener_ndvi(anio_ndvi_inicial, geometria)
    delta_ndvi = ndvi_final.subtract(ndvi_inicial).rename("delta_ndvi")

    hansen = ee.Image(HANSEN_ASSET).select("lossyear")
    rgb = obtener_rgb_sentinel(ANO_NDVI_MAX, geometria)
    perdida_post, _, _ = imagenes_hansen(geometria)
    coincidencia_revision = imagen_coincidencia_revision(
        geometria,
        tmf=tmf,
        perdida_post=perdida_post,
        esri_inicial=obtener_esri(ANO_ESRI_MIN, geometria),
        esri_final=obtener_esri(ANO_ESRI_MAX, geometria),
    )

    especificaciones = [
        (
            f"ESRI - Uso y cobertura {anio_esri_final}",
            visualizar_con_borde(
                obtener_esri_visual(anio_esri_final, geometria),
                VIS_ESRI,
                area_fc,
            ),
            "Azul: agua | Verde: árboles | Amarillo: cultivos | Rojo: construido | Beige: pastizal",
        ),
        (
            f"JRC TMF - Estado forestal {anio_tmf_diagnostico}",
            visualizar_con_borde(tmf, VIS_TMF, area_fc),
            "Verde oscuro: bosque no perturbado | Amarillo: degradación | Rojo: deforestación | Verde claro: regeneración forestal",
        ),
        (
            f"Hansen - Pérdida arbórea 2001-{ANO_HANSEN_MAX}",
            visualizar_con_borde(
                hansen.updateMask(hansen.gt(0)).clip(geometria),
                VIS_HANSEN_TOTAL,
                area_fc,
                fondo=rgb,
            ),
            "Amarillo: pérdida antigua | Naranja: intermedia | Rojo oscuro: pérdida más reciente",
        ),
        (
            "GEDI - Altura del dosel",
            visualizar_con_borde(gedi, VIS_GEDI, area_fc),
            "Amarillo claro: dosel bajo | Verde medio: dosel intermedio | Verde oscuro: dosel alto",
        ),
        (
            f"ΔNDVI - Cambio de vigor {anio_ndvi_inicial}-{ANO_NDVI_MAX}",
            visualizar_con_borde(delta_ndvi, VIS_NDVI_DELTA, area_fc),
            "Rojo: disminución de vigor | Crema: cambio pequeño | Verde: aumento de vigor",
        ),
        (
            f"Vigor vegetal NDVI - {ANO_NDVI_MAX}",
            visualizar_con_borde(
                clasificar_ndvi(ndvi_final),
                VIS_NDVI_CLASES,
                area_fc,
            ),
            "Rojo: NDVI inferior a 0, sin vegetación activa | Rosado: NDVI 0.0 a menos de 0.2, suelo o cobertura muy escasa | Amarillo: NDVI 0.2 a menos de 0.4, vegetación escasa | Verde claro: NDVI 0.4 a menos de 0.6, vegetación moderada | Verde oscuro: NDVI mayor o igual a 0.6, vegetación densa",
        ),
        (
            "Sectores que requieren revisión - Coincidencia espacial",
            visualizar_con_borde(
                coincidencia_revision.updateMask(coincidencia_revision.gt(0)),
                VIS_COINCIDENCIA_REVISION,
                area_fc,
                fondo=rgb,
            ),
            (
                "Amarillo: señal de 1 fuente | Naranja: coincidencia de 2 fuentes | "
                "Rojo oscuro: coincidencia de 3 fuentes. Integra JRC TMF 2025, "
                "Hansen posterior a 2020 y ESRI 2017-2024 en una malla común de "
                "30 m. GEDI y NDVI no participan en esta suma espacial; el aporte "
                "NDVI se calcula por separado y este mapa no modifica el índice."
            ),
        ),
    ]

    return descargar_miniaturas(especificaciones, geometria, _mapas_existentes)


def generar_pdf(
    nombre_area,
    resultados,
    anio_tmf_diagnostico,
    anio_esri_inicial,
    anio_esri_final,
    anio_ndvi_inicial,
    mapas=None,
):
    memoria = BytesIO()
    documento = SimpleDocTemplate(
        memoria,
        pagesize=A4,
        rightMargin=1.45 * cm,
        leftMargin=1.45 * cm,
        topMargin=1.35 * cm,
        bottomMargin=1.55 * cm,
        title="Ficha ejecutiva de preevaluación territorial y conectividad",
        author="Aplicación de preevaluación territorial y corredores",
    )

    tinta = colors.HexColor("#123b45")
    verde = colors.HexColor("#00544d")
    verde_claro = colors.HexColor("#eaf4f0")
    superficie = colors.HexColor("#f7faf8")
    azul_claro = colors.HexColor("#e9f1fb")
    borde = colors.HexColor("#b6d1c8")
    naranja_claro = colors.HexColor("#fff1e6")
    gris = colors.HexColor("#52706f")
    estilos = getSampleStyleSheet()

    def registrar_estilo(nombre, base, **opciones):
        estilos.add(ParagraphStyle(name=nombre, parent=estilos[base], **opciones))

    registrar_estilo(
        "TituloFicha", "Title", fontName="Helvetica-Bold", fontSize=17,
        leading=20, textColor=tinta, alignment=TA_CENTER, spaceAfter=4,
    )
    registrar_estilo(
        "SubtituloFicha", "BodyText", fontName="Helvetica", fontSize=8.5,
        leading=11, textColor=gris, alignment=TA_CENTER, spaceAfter=9,
    )
    registrar_estilo(
        "TituloPagina", "Heading1", fontName="Helvetica-Bold", fontSize=15,
        leading=18, textColor=tinta, spaceAfter=3,
    )
    registrar_estilo(
        "BajadaPagina", "BodyText", fontName="Helvetica", fontSize=8.5,
        leading=11.2, textColor=gris, spaceAfter=8,
    )
    registrar_estilo(
        "SeccionFicha", "Heading2", fontName="Helvetica-Bold", fontSize=10.2,
        leading=12.5, textColor=verde, spaceBefore=7, spaceAfter=4,
    )
    registrar_estilo(
        "CuerpoFicha", "BodyText", fontName="Helvetica", fontSize=8.4,
        leading=11.2, textColor=tinta, spaceAfter=4,
    )
    registrar_estilo(
        "CuerpoPequeno", "BodyText", fontName="Helvetica", fontSize=7.2,
        leading=9.1, textColor=tinta, spaceAfter=3,
    )
    registrar_estilo(
        "Etiqueta", "BodyText", fontName="Helvetica", fontSize=7,
        leading=8.4, textColor=gris, spaceAfter=1,
    )
    registrar_estilo(
        "Valor", "BodyText", fontName="Helvetica-Bold", fontSize=11,
        leading=13, textColor=tinta,
    )
    registrar_estilo(
        "MapaTitulo", "BodyText", fontName="Helvetica-Bold", fontSize=9.2,
        leading=11, textColor=tinta, alignment=TA_CENTER, spaceAfter=3,
    )
    registrar_estilo(
        "MapaNota", "BodyText", fontName="Helvetica", fontSize=6.7,
        leading=8.2, textColor=gris, alignment=TA_CENTER,
    )
    registrar_estilo(
        "CabeceraTabla", "BodyText", fontName="Helvetica-Bold", fontSize=7.4,
        leading=9, textColor=tinta,
    )
    registrar_estilo(
        "Prioridad", "BodyText", fontName="Helvetica", fontSize=9,
        leading=12, textColor=tinta,
    )

    def parrafo(texto, estilo="CuerpoFicha"):
        return Paragraph(str(texto), estilos[estilo])

    def tabla_simple(filas, anchos, *, cabecera=False, fondo=None):
        contenido = [
            [parrafo(celda, "CabeceraTabla" if cabecera and i == 0 else "CuerpoPequeno") for celda in fila]
            for i, fila in enumerate(filas)
        ]
        tabla = Table(contenido, colWidths=anchos, repeatRows=1 if cabecera else 0)
        comandos = [
            ("GRID", (0, 0), (-1, -1), 0.35, borde),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if fondo:
            comandos.append(("BACKGROUND", (0, 0), (-1, -1), fondo))
        if cabecera:
            comandos.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), verde_claro),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.8, verde),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, superficie]),
                ]
            )
        tabla.setStyle(TableStyle(comandos))
        return tabla

    def tarjeta(texto, *, fondo=verde_claro, acento=verde, estilo="CuerpoFicha"):
        tabla = Table([[parrafo(texto, estilo)]], colWidths=[17.0 * cm])
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), fondo),
                    ("LINEBEFORE", (0, 0), (0, -1), 4, acento),
                    ("BOX", (0, 0), (-1, -1), 0.35, borde),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return tabla

    def tarjetas_metricas(items):
        celdas = []
        for etiqueta, valor in items:
            celdas.append([parrafo(etiqueta, "Etiqueta"), parrafo(valor, "Valor")])
        tabla = Table([celdas], colWidths=[4.25 * cm] * len(celdas))
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), superficie),
                    ("BOX", (0, 0), (-1, -1), 0.4, borde),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, borde),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return tabla

    def leyenda(items):
        filas = []
        for color, etiqueta, detalle in items:
            filas.append(["", parrafo(f"<b>{etiqueta}</b><br/>{detalle}", "CuerpoPequeno")])
        tabla = Table(filas, colWidths=[0.45 * cm, 7.95 * cm], hAlign="LEFT")
        comandos = [
            ("GRID", (0, 0), (-1, -1), 0.25, borde),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        for i, (color, _, _) in enumerate(items):
            comandos.append(("BACKGROUND", (0, i), (0, i), colors.HexColor(color)))
        tabla.setStyle(TableStyle(comandos))
        return tabla

    r = resultados
    aportes = r["aportes_indice"]
    area = r["area_ha"]
    pct_arbol = r["esri_arboles_final"] / area * 100 if area else 0
    pct_ganancia = r["esri_ganancia"] / area * 100 if area else 0
    visita = r.get("prioridad_visita")
    prioridad_pdf = visita["prioridad_visita"] if visita else r["prioridad"]
    puntaje_cambios = visita["puntaje_cambios"] if visita else r["puntaje"]
    aporte_corredor = visita["aporte_corredor"] if visita else 0.0
    puntaje_integrado = visita["puntaje_integrado"] if visita else r["puntaje"]
    maximo_integrado = PUNTAJE_MAXIMO_VISITA if visita else PUNTAJE_MAXIMO
    accion_pdf = (
        texto_recomendacion_visita(prioridad_pdf)
        if visita
        else texto_recomendacion(prioridad_pdf)
    )
    fuentes = sum(
        bool(valor)
        for valor in (
            r["senal_tmf"],
            r["senal_esri"],
            r["senal_hansen"],
            r["senal_gedi"],
            r["senal_ndvi"],
        )
    )
    resultado_general = (
        "varias señales de cambio que justifican una revisión prioritaria"
        if fuentes >= 2
        else "una señal localizada que conviene revisar"
        if fuentes == 1
        else "sin señales relevantes de deterioro reciente en las fuentes evaluadas"
    )
    coincidencia = f"{r['consistencia']['nivel']}: {r['consistencia']['detalle']}"
    contexto_corredores = r.get("corredores") or {}
    contexto_fragmentacion = r.get("fragmentacion") or {}
    conexion_corredor = contexto_fragmentacion.get("conexion_corredor") or {}

    historia = [
        Paragraph("FICHA EJECUTIVA DE PREEVALUACIÓN TERRITORIAL", estilos["TituloFicha"]),
        Paragraph(
            "Lectura rápida para orientar una visita. Los mapas y cálculos son indicativos y no sustituyen la verificación de campo.",
            estilos["SubtituloFicha"],
        ),
    ]

    identificacion = tabla_simple(
        [
            ["Área evaluada", nombre_area, "Superficie", f"{area:,.2f} ha"],
            ["Fecha", date.today().strftime("%d/%m/%Y"), "Método", METHODOLOGY_VERSION],
        ],
        [2.2 * cm, 6.2 * cm, 2.0 * cm, 6.6 * cm],
        fondo=superficie,
    )
    historia.extend([identificacion, Spacer(1, 7)])

    color_prioridad = {
        "Muy alta": "#9b1c1c",
        "Alta": "#b42318",
        "Media": "#c85d0a",
        "Preventiva": "#9a6a00",
        "Baja": "#2f6b4f",
    }[prioridad_pdf]
    historia.extend(
        [
            tarjeta(
                f"<b>Prioridad {prioridad_pdf.lower()} de visita</b> &nbsp;·&nbsp; "
                f"<b>{puntaje_integrado:.2f} de {maximo_integrado:.1f} puntos</b><br/>"
                f"{accion_pdf}",
                fondo=colors.HexColor("#fff7ed") if prioridad_pdf != "Baja" else verde_claro,
                acento=colors.HexColor(color_prioridad),
                estilo="Prioridad",
            ),
            Spacer(1, 7),
            Paragraph("Qué significa el puntaje", estilos["SeccionFicha"]),
            Paragraph(
                "El valor total es una suma de criterios. Mide prioridad operativa para revisar el área; "
                "no es una probabilidad de deforestación ni indica cuántas capas se superponen.",
                estilos["CuerpoFicha"],
            ),
        ]
    )

    filas_puntaje = [
        ["Fuente o criterio", "Qué observó", "Aporte"],
        [f"JRC TMF {anio_tmf_diagnostico}", "Señal" if r["senal_tmf"] else "Sin señal", f"{aportes['tmf']:.1f} / {PESOS_INDICE['tmf']:.1f}"],
        ["Hansen GFC", "Señal" if r["senal_hansen"] else "Sin señal", f"{aportes['hansen']:.1f} / {PESOS_INDICE['hansen']:.1f}"],
        [f"ESRI {anio_esri_inicial}-{anio_esri_final}", "Señal" if r["senal_esri"] else "Sin señal", f"{aportes['esri']:.1f} / {PESOS_INDICE['esri']:.1f}"],
        ["GEDI · altura del dosel", "Contexto" if r["senal_gedi"] else "Sin aporte", f"{aportes['gedi']:.1f} / {PESOS_INDICE['gedi']:.1f}"],
        [
            f"NDVI {anio_ndvi_inicial}-{ANO_NDVI_FINAL_ANALISIS}",
            "Disminución significativa" if r["senal_ndvi"] else "Sin señal",
            f"{aportes['ndvi']:.1f} / {PESOS_INDICE['ndvi']:.1f}",
        ],
    ]
    if visita:
        filas_puntaje.append(["Valor estratégico de corredores", "Aporta al total de visita", f"{aporte_corredor:.2f} / 1.5"])
    filas_puntaje.extend(
        [
            ["Subtotal de cambios", "Suma de JRC + Hansen + ESRI + GEDI + NDVI", f"{puntaje_cambios:.2f} / {PUNTAJE_MAXIMO:.1f}"],
            ["TOTAL INTEGRADO", "Cambios + valor del corredor" if visita else "Índice de cambios", f"{puntaje_integrado:.2f} / {maximo_integrado:.1f}"],
        ]
    )
    tabla_puntaje = tabla_simple(
        filas_puntaje,
        [5.2 * cm, 7.7 * cm, 4.1 * cm],
        cabecera=True,
    )
    tabla_puntaje.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), azul_claro),
                ("LINEABOVE", (0, -1), (-1, -1), 1, tinta),
            ]
        )
    )
    historia.extend([tabla_puntaje, Spacer(1, 7)])
    eri_pdf = r.get("eri") or {}
    if eri_pdf:
        historia.extend(
            [
                tarjeta(
                    "<b>ERI indicativo · lectura complementaria</b><br/>"
                    f"{float(eri_pdf.get('valor', 0) or 0):.2f} / 1.00 · "
                    f"clase {eri_pdf.get('clase', 'sin clasificar')}. "
                    "Se reporta por separado y no modifica la prioridad anterior.",
                    fondo=azul_claro,
                    acento=colors.HexColor(str(eri_pdf.get("color", "#0A4393"))),
                ),
                Spacer(1, 7),
            ]
        )

    historia.extend(
        [
            tarjetas_metricas(
                [
                    ("Árboles en ESRI", f"{r['esri_arboles_final']:.1f} ha"),
                    ("Pérdida Hansen posterior a 2020", f"{r['hansen_post']:.2f} ha"),
                    ("Deforestación señalada por JRC", f"{r['tmf_deforestacion']:.1f} ha"),
                    ("Señal en 2 o 3 fuentes", f"{r['coincidencia_varias_fuentes']:.2f} ha"),
                ]
            ),
            Spacer(1, 7),
            tarjeta(
                f"<b>Lectura rápida.</b> El análisis encontró {resultado_general}. "
                f"La coincidencia espacial más sólida ocupa {r['coincidencia_varias_fuentes']:.2f} ha "
                f"({r['pct_coincidencia_varias_fuentes']:.2f}% del área). "
                "Revise primero esos sectores y contraste el resultado con imágenes recientes, "
                "documentos del predio y observación de campo.",
                fondo=azul_claro,
                acento=tinta,
            ),
            Spacer(1, 5),
            Paragraph("Puntaje y coincidencia espacial son cosas distintas", estilos["SeccionFicha"]),
            tabla_simple(
                [
                    ["Señal de una fuente", f"{r['coincidencia_1_fuente']:.2f} ha", "Revisión inicial"],
                    ["Coincidencia de dos fuentes", f"{r['coincidencia_2_fuentes']:.2f} ha", "Mayor respaldo espacial"],
                    ["Coincidencia de tres fuentes", f"{r['coincidencia_3_fuentes']:.2f} ha", "Revisión prioritaria"],
                ],
                [6.0 * cm, 3.0 * cm, 8.0 * cm],
                fondo=superficie,
            ),
            Paragraph(
                "Estas hectáreas indican dónde coinciden las señales. No se suman al puntaje y no confirman por sí solas la causa del cambio.",
                estilos["CuerpoPequeno"],
            ),
        ]
    )

    if contexto_fragmentacion:
        clase = contexto_fragmentacion["metricas_clase"]
        red = contexto_fragmentacion["metricas_red"]

        historia.extend(
            [
                PageBreak(),
                Paragraph("1. Cómo está distribuido el bosque", estilos["TituloPagina"]),
                Paragraph(
                    f"Este mapa muestra únicamente los fragmentos de {FUENTE_BOSQUE_CORTA} dentro del área evaluada. "
                    "No utiliza fondo satelital para que la forma, el tamaño y la distribución se lean con claridad.",
                    estilos["BajadaPagina"],
                ),
                tarjetas_metricas(
                    [
                        ("Bosque dentro del área", f"{clase['area_total_bosque_ha']:.2f} ha"),
                        ("Fragmentos identificados", f"{clase['numero_parches']}"),
                        ("Mayor fragmento", f"{clase['indice_parche_mayor_pct']:.1f}% del área"),
                        ("Tamaño mediano", f"{clase['area_mediana_parche_ha']:.2f} ha"),
                    ]
                ),
                Spacer(1, 8),
                crear_mapa_fragmentacion(contexto_fragmentacion, ancho=17.0 * cm, alto=10.2 * cm),
                Spacer(1, 6),
                Table(
                    [[
                        leyenda(
                            [
                                ("#2f6b4f", "Valor alto", "Fragmentos relativamente importantes para mantener unido el bosque."),
                                ("#78a66a", "Valor intermedio", "Aportan a la continuidad, con menor influencia relativa."),
                            ]
                        ),
                        leyenda(
                            [
                                ("#c7dbc4", "Valor bajo", "Menor influencia relativa dentro de esta área; no significa que carezca de valor ecológico."),
                                ("#eef5f1", "Área evaluada", "La superficie reportada siempre queda dentro de este límite."),
                            ]
                        ),
                    ]],
                    colWidths=[8.5 * cm, 8.5 * cm],
                    style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]),
                ),
                Spacer(1, 6),
                tarjeta(
                    f"<b>Lectura sencilla.</b> Se identificaron {clase['numero_parches']} fragmentos que reúnen "
                    f"{clase['area_total_bosque_ha']:.2f} ha, equivalentes al "
                    f"{clase['porcentaje_paisaje_bosque']:.1f}% del área. "
                    "Los colores comparan los fragmentos entre sí dentro de este análisis; no son categorías oficiales de Almanaque Azul.",
                    fondo=verde_claro,
                ),
                Paragraph("Datos adicionales", estilos["SeccionFicha"]),
                tabla_simple(
                    [
                        ["Área media por fragmento", f"{clase['area_media_parche_ha']:.2f} ha", "Densidad de fragmentos", f"{clase['densidad_parches_por_100ha']:.2f} por 100 ha"],
                        ["Densidad de bordes", f"{clase['densidad_borde_m_ha']:.2f} m/ha", "Índice de forma medio", f"{clase['indice_forma_medio']:.2f}"],
                    ],
                    [4.1 * cm, 4.4 * cm, 4.1 * cm, 4.4 * cm],
                    fondo=superficie,
                ),
            ]
        )

        conecta = bool(conexion_corredor.get("conecta"))
        lectura_ruta = (
            f"La cadena potencial llega a <b>{conexion_corredor.get('corredor_nombre')}</b> "
            f"(categoría publicada {str(conexion_corredor.get('categoria_etiqueta') or 'no indicada').lower()}) "
            f"por medio de {conexion_corredor.get('numero_fragmentos_ruta', 0)} fragmentos. "
            f"El salto mayor es de {float(conexion_corredor.get('mayor_separacion_m') or 0):.1f} m."
            if conecta
            else "No se identificó una cadena completa hacia un corredor publicado dentro del entorno evaluado."
        )
        historia.extend(
            [
                PageBreak(),
                Paragraph("2. Cómo puede mantenerse la continuidad del bosque", estilos["TituloPagina"]),
                Paragraph(
                    "Este segundo mapa conserva los fragmentos como contexto y añade solo las relaciones esenciales, "
                    "las separaciones que conviene revisar y una ruta potencial hacia un corredor de referencia.",
                    estilos["BajadaPagina"],
                ),
                tarjetas_metricas(
                    [
                        ("Distancia evaluada", f"{red['umbral_m']:.0f} m"),
                        ("Fragmentos con vecino cercano", f"{red.get('numero_parches_conectados', 0)} de {red['numero_nodos']}"),
                        ("Fragmentos separados", f"{red.get('numero_parches_aislados', 0)}"),
                        ("Grupos de bosque", f"{red['numero_componentes']}"),
                    ]
                ),
                Spacer(1, 8),
                crear_mapa_conectividad(contexto_fragmentacion, ancho=17.0 * cm, alto=10.2 * cm),
                Spacer(1, 6),
                Table(
                    [[
                        leyenda(
                            [
                                ("#b8d1bd", "Fragmentos de bosque", "Cobertura 2021 usada para el análisis estructural."),
                                ("#176b61", "Estructura esencial", "Línea continua entre bordes próximos; el cálculo usa todas las relaciones válidas."),
                                ("#9a4a25", "Separación para revisar", "Línea discontinua desde un fragmento sin vecino dentro del umbral."),
                            ]
                        ),
                        leyenda(
                            [
                                ("#e97719", "Ruta potencial al corredor", "Una sola cadena de saltos; no demuestra movimiento de fauna."),
                                ("#dce8a5", "Corredor de referencia", "Polígono publicado por Almanaque Azul."),
                                ("#eef5f1", "Área evaluada", "El bosque exterior puede apoyar el cálculo sin aumentar las hectáreas reportadas."),
                            ]
                        ),
                    ]],
                    colWidths=[8.5 * cm, 8.5 * cm],
                    style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]),
                ),
                Spacer(1, 6),
                tarjeta(
                    f"<b>Lectura sencilla.</b> Con una distancia máxima de {red['umbral_m']:.0f} m, "
                    f"{red.get('numero_parches_conectados', 0)} fragmentos tienen al menos un vecino cercano y "
                    f"{red.get('numero_parches_aislados', 0)} quedan separados. {lectura_ruta}",
                    fondo=naranja_claro if conecta else azul_claro,
                    acento=colors.HexColor("#e97719") if conecta else tinta,
                ),
                Paragraph("Qué se calculó y qué se muestra", estilos["SeccionFicha"]),
                tabla_simple(
                    [
                        ["Relaciones usadas en el cálculo", f"{red['numero_aristas']}", "Relaciones esenciales dibujadas", f"{red.get('numero_relaciones_mostradas', 0)}"],
                        ["Fragmentos del entorno considerados", f"{red.get('numero_parches_contexto', red['numero_nodos'])}", "Con continuidad o conexión exterior", f"{red.get('numero_parches_continuidad_exterior', 0)}"],
                        ["Separaciones potenciales", f"{red.get('numero_brechas_potenciales', 0)}", "Distancia media de separaciones", f"{red.get('distancia_media_brechas_potenciales_m', 0):.1f} m"],
                    ],
                    [4.5 * cm, 2.2 * cm, 7.1 * cm, 3.2 * cm],
                    fondo=superficie,
                ),
                Paragraph(
                    "Importante: esta es conectividad estructural potencial basada en cobertura y distancia. "
                    "No demuestra conectividad funcional para una especie, calidad de hábitat ni uso real del corredor.",
                    estilos["CuerpoPequeno"],
                ),
            ]
        )

    historia.extend(
        [
            PageBreak(),
            Paragraph("Evidencia temática por fuente", estilos["TituloPagina"]),
            Paragraph(
                "Estas imágenes permiten revisar el detalle de cada fuente. Se presentan después de la conclusión y de los mapas explicativos para no sobrecargar la lectura inicial.",
                estilos["BajadaPagina"],
            ),
        ]
    )

    def tarjeta_mapa(mapa):
        titulo_mapa = mapa["titulo"].replace("ΔNDVI", "Variación NDVI")
        contenido = [parrafo(titulo_mapa, "MapaTitulo")]
        if mapa.get("imagen"):
            imagen = ReportLabImage(BytesIO(mapa["imagen"]))
            escala = min((15.8 * cm) / imagen.imageWidth, (6.5 * cm) / imagen.imageHeight)
            imagen.drawWidth = imagen.imageWidth * escala
            imagen.drawHeight = imagen.imageHeight * escala
            contenido.append(
                Table(
                    [[imagen]],
                    colWidths=[15.8 * cm],
                    style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]),
                )
            )
        else:
            contenido.append(
                Table(
                    [[parrafo("Imagen no disponible. Consulte el mapa interactivo.", "MapaNota")]],
                    colWidths=[15.8 * cm],
                    rowHeights=[5.5 * cm],
                    style=TableStyle([("BOX", (0, 0), (-1, -1), 0.35, borde), ("BACKGROUND", (0, 0), (-1, -1), superficie), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]),
                )
            )
        contenido.append(parrafo(mapa["leyenda"], "MapaNota"))
        tabla = Table([[contenido]], colWidths=[16.4 * cm], hAlign="CENTER")
        tabla.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.4, borde),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return KeepTogether([tabla, Spacer(1, 6)])

    for indice, mapa in enumerate(mapas or []):
        historia.append(tarjeta_mapa(mapa))
        if indice % 2 == 1 and indice < len(mapas or []) - 1:
            historia.append(PageBreak())

    historia.extend(
        [
            Paragraph("Detalle técnico y trazabilidad", estilos["TituloPagina"]),
            Paragraph(
                "Esta sección conserva la información completa para personal técnico. No es necesaria para comprender la conclusión ejecutiva.",
                estilos["BajadaPagina"],
            ),
        ]
    )
    filas_fuentes = [
        ["Fuente", "Resultado específico", "Aporte"],
        [f"JRC TMF {anio_tmf_diagnostico}", f"Bosque no perturbado {r['tmf_estable']:.1f}; degradación {r['tmf_degradacion']:.1f}; deforestación {r['tmf_deforestacion']:.1f}; regeneración forestal {r['tmf_recuperacion']:.1f}; agua {r['tmf_agua']:.1f}; otra cobertura {r['tmf_otra_cobertura']:.1f} ha", f"{aportes['tmf']:.1f}/{PESOS_INDICE['tmf']:.1f}"],
        ["Hansen GFC", f"Pérdida 2001-2020: {r['hansen_pre']:.2f} ha; posterior al {CUTOFF_LABEL}: {r['hansen_post']:.2f} ha", f"{aportes['hansen']:.1f}/{PESOS_INDICE['hansen']:.1f}"],
        [f"ESRI {anio_esri_inicial}-{anio_esri_final}", f"Árboles finales {r['esri_arboles_final']:.1f} ha; salida {r['esri_salida']:.1f} ha ({r['pct_esri_salida']:.1f}%); ganancia {r['esri_ganancia']:.1f} ha ({pct_ganancia:.1f}%)", f"{aportes['esri']:.1f}/{PESOS_INDICE['esri']:.1f}"],
        ["GEDI", f"Dosel {r['gedi_altura']:.1f} m; datos válidos en {r['gedi_cobertura_pct']:.0f}% del área" if r["gedi_disponible"] else "Datos insuficientes", f"{aportes['gedi']:.1f}/{PESOS_INDICE['gedi']:.1f}"],
        [
            f"NDVI {anio_ndvi_inicial}-{ANO_NDVI_FINAL_ANALISIS}",
            f"Media {r['ndvi_inicial_medio']:.3f} → {r['ndvi_final_medio']:.3f}; "
            f"Δ medio {r['ndvi_delta_medio']:+.3f}; disminución significativa "
            f"{r['ndvi_disminucion']:.2f} ha ({r['pct_ndvi_disminucion']:.1f}%); "
            f"datos válidos {r['ndvi_cobertura_pct']:.0f}%",
            f"{aportes['ndvi']:.1f}/{PESOS_INDICE['ndvi']:.1f}",
        ],
    ]
    historia.extend(
        [
            tabla_simple(filas_fuentes, [3.0 * cm, 10.8 * cm, 3.2 * cm], cabecera=True),
            Paragraph("Contexto de corredores", estilos["SeccionFicha"]),
        ]
    )
    if contexto_corredores:
        nombres = ", ".join(
            dict.fromkeys(detalle["nombre"] for detalle in contexto_corredores.get("corredores", []))
        ) or "ninguno"
        historia.append(
            Paragraph(
                f"El área intersecta {contexto_corredores['area_en_corredores_ha']:.2f} ha de corredores "
                f"({contexto_corredores['porcentaje_aoi_en_corredores']:.2f}% del área). "
                f"Corredores presentes: {nombres}. Intersección con el Corredor Biológico Mesoamericano: "
                f"{'sí' if contexto_corredores['intersecta_mesoamericano'] else 'no'}. "
                "Este valor aporta al puntaje integrado de visita; la estructura del bosque sirve para focalizar la revisión, pero no añade puntos.",
                estilos["CuerpoFicha"],
            )
        )
    else:
        historia.append(Paragraph("No se obtuvo contexto de corredores para esta área.", estilos["CuerpoFicha"]))

    texto_justificacion_pesos = " ".join(
        JUSTIFICACION_PESOS[fuente] for fuente in ("tmf", "hansen", "esri", "gedi", "ndvi")
    )
    texto_justificacion_umbrales = " ".join(
        JUSTIFICACION_UMBRALES[criterio]
        for criterio in (
            "hansen_post_2020_ha", "jrc_deforestacion", "jrc_degradacion",
            "esri_salida_arboles", "gedi_dosel_y_cobertura", "ndvi",
        )
    )
    texto_clases_ndvi = "; ".join(
        f"{clase['etiqueta']} ({clase['rango']})" for clase in CLASES_VIGOR_NDVI
    )
    historia.extend(
        [
            Paragraph("Cómo se interpreta", estilos["SeccionFicha"]),
            Paragraph(
                f"<b>Consistencia entre fuentes.</b> {coincidencia} La superposición espacial se calcula en una malla común de 30 m con JRC, Hansen y ESRI. GEDI y NDVI no se suman a ese mapa; NDVI aporta de forma separada al índice cuando supera sus umbrales.",
                estilos["CuerpoFicha"],
            ),
            Paragraph(
                f"<b>Justificación de los pesos.</b> {texto_justificacion_pesos}",
                estilos["CuerpoPequeno"],
            ),
            Paragraph(
                f"<b>Justificación de los umbrales.</b> {texto_justificacion_umbrales}",
                estilos["CuerpoPequeno"],
            ),
            Paragraph(
                f"<b>Escala visual NDVI.</b> {texto_clases_ndvi}. Describe vigor espectral, no identifica por sí sola bosque natural.",
                estilos["CuerpoPequeno"],
            ),
            tarjeta(
                "<b>Alcance.</b> Esta ficha orienta dónde revisar. No es una certificación, una determinación legal, una confirmación definitiva de deforestación ni una evaluación de conectividad funcional para fauna.",
                fondo=azul_claro,
                acento=tinta,
            ),
        ]
    )

    def pie_pagina(canvas_pdf, documento_pdf):
        canvas_pdf.saveState()
        ancho, _ = A4
        canvas_pdf.setStrokeColor(colors.HexColor("#9aab96"))
        canvas_pdf.setLineWidth(0.4)
        canvas_pdf.line(1.55 * cm, 1.2 * cm, ancho - 1.55 * cm, 1.2 * cm)
        canvas_pdf.setFont("Helvetica", 7.2)
        canvas_pdf.setFillColor(gris)
        canvas_pdf.drawString(1.45 * cm, 0.82 * cm, "Preevaluación territorial indicativa · requiere verificación")
        canvas_pdf.drawRightString(ancho - 1.45 * cm, 0.82 * cm, f"Página {documento_pdf.page}")
        canvas_pdf.restoreState()

    documento.build(historia, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
    memoria.seek(0)
    return memoria.getvalue()


# -----------------------------------------------------------------------------
# Capas de teselas para el visor del portal (las mismas del mapa Streamlit)
# -----------------------------------------------------------------------------
def capas_mapa(geometria_geojson, incluir_bosque=True):
    """Devuelve {clave: {nombre, url}} con URLs de teselas de Earth Engine para el área."""
    geometria = obtener_area(geometria_geojson=geometria_geojson).geometry(TOLERANCIA_RECORTE_M)
    perdida_post, perdida_pre, linea_base = imagenes_hansen(geometria)
    tmf = obtener_tmf(ANO_DIAG_TMF, geometria)
    esri_i = obtener_esri(ANO_ESRI_MIN, geometria)
    esri_f = obtener_esri(ANO_ESRI_MAX, geometria)
    coincidencia = imagen_coincidencia_revision(geometria, tmf=tmf, perdida_post=perdida_post,
                                                esri_inicial=esri_i, esri_final=esri_f)
    transicion = (ee.Image(0).where(esri_i.neq(2).And(esri_f.eq(2)), 1)
                  .where(esri_i.eq(2).And(esri_f.neq(2)), 2)
                  .where(esri_i.eq(2).And(esri_f.eq(2)), 3).selfMask())
    ndvi_i = obtener_ndvi(ANO_NDVI_INICIAL_ANALISIS, geometria)
    ndvi_f = obtener_ndvi(ANO_NDVI_FINAL_ANALISIS, geometria)
    definiciones = [
        ("coincidencia", "Sectores que requieren revisión · JRC + Hansen + ESRI",
         coincidencia.updateMask(coincidencia.gt(0)), VIS_COINCIDENCIA_REVISION),
        ("jrc", f"Estado forestal JRC {ANO_DIAG_TMF}", tmf, VIS_TMF),
        ("hansen_post", f"Pérdida Hansen 2021-{ANO_HANSEN_MAX}", perdida_post, VIS_HANSEN_POST),
        ("hansen_pre", "Pérdida Hansen 2001-2020", perdida_pre, VIS_HANSEN_PRE),
        ("linea_base", "Cobertura arbórea persistente a 2020", linea_base, VIS_LINEA_BASE),
        ("esri", f"Uso y cobertura ESRI {ANO_ESRI_MAX}", obtener_esri_visual(ANO_ESRI_MAX, geometria), VIS_ESRI),
        ("esri_transicion", f"Transiciones ESRI {ANO_ESRI_MIN}-{ANO_ESRI_MAX}", transicion, VIS_ESRI_CAMBIO),
        ("gedi", "Altura del dosel GEDI", imagen_gedi(geometria), VIS_GEDI),
        ("ndvi_delta", f"ΔNDVI {ANO_NDVI_INICIAL_ANALISIS}-{ANO_NDVI_FINAL_ANALISIS}", ndvi_f.subtract(ndvi_i), VIS_NDVI_DELTA),
        ("ndvi_clases", f"Vegetación NDVI {ANO_NDVI_FINAL_ANALISIS}", clasificar_ndvi(ndvi_f), VIS_NDVI_CLASES),
    ]
    if incluir_bosque and ASSET_BOSQUE_2021:
        definiciones.append(("bosque_2021", f"Bosque {ANO_BOSQUE_REFERENCIA} · {FUENTE_BOSQUE_ORGANIZACION}",
                             imagen_bosque_contexto(geometria), {"min": 1, "max": 1, "palette": ["2f6b45"]}))
    salida = {}
    for clave, nombre, imagen, vis in definiciones:
        try:
            salida[clave] = {"nombre": nombre, "url": ee.Image(imagen).getMapId(vis)["tile_fetcher"].url_format}
        except Exception as error:  # una capa no disponible no bloquea las demás
            salida[clave] = {"nombre": nombre, "error": str(error)}
    return salida
