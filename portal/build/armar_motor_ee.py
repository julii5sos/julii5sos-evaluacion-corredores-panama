"""Arma evaluacion/motor_ee.py copiando las funciones de Earth Engine de app_experiencia.py.
Uso: python3 -I build/armar_motor_ee.py <repo_raiz> <carpeta_evaluacion>"""
import ast
import re
import sys

R, S = sys.argv[1], sys.argv[2]
src = open(R + '/app_experiencia.py', encoding='utf-8').read()
L = src.split('\n')
arbol = ast.parse(src)

QUIERO = ['convertir_imagen_byte', 'obtener_tmf', 'obtener_esri', 'obtener_esri_visual', 'mascara_sentinel_scl',
          'obtener_ndvi', 'clasificar_ndvi', 'imagenes_hansen', 'imagen_coincidencia_revision',
          'convertir_altura_gedi_float', 'imagen_gedi', 'imagen_bosque_contexto', 'numero', 'reducir_superficies',
          'normalizar_histograma_gedi', 'calcular_serie_fuente', 'analizar_bosque_asset',
          'ejecutar_analisis', 'texto_recomendacion',
          # informe: registro metodológico, mapas y PDF
          'construir_registro_metodologico', 'mascara_sentinel_rgb', 'obtener_rgb_sentinel', 'visualizar_con_borde',
          'crear_url_miniatura', 'descargar_url_miniatura', 'descargar_miniaturas', 'generar_mapas_reporte',
          'generar_pdf',
          # ERI indicativo
          'calcular_eri_indicativo', 'construir_imagenes_eri', 'clasificar_imagen_eri',
          'obtener_probabilidad_arboles', 'convertir_probabilidad_arboles_float']
partes, inicio_const, fin_const = [], None, None
for n in arbol.body:
    if isinstance(n, ast.FunctionDef) and n.name in QUIERO:
        assert all('st.' in ast.unparse(d) for d in n.decorator_list), n.name   # solo cachés de Streamlit
        bloque = '\n'.join(L[n.lineno - 1:n.end_lineno])                      # sin decoradores
        partes.append(bloque)
    if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'APP_VERSION' for t in n.targets):
        inicio_const = n.lineno - 1
    if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'VIS_RGB' for t in n.targets):
        fin_const = n.end_lineno
faltan = set(QUIERO) - {re.match(r'def (\w+)', p).group(1) for p in partes}
assert not faltan, faltan
ext = '\n\n\n'.join(partes)
# el portal no maneja fincas: se elimina esa rama del registro metodológico
ext, n_f = re.subn(r'    if tipo_area == "Finca de monitoreo":\n.*?    elif tipo_area == TIPO_AREA_SUBCUENCA:', '    if tipo_area == TIPO_AREA_SUBCUENCA:', ext, flags=re.S)
assert n_f == 1
assert not re.search(r'(^|[^a-zA-Z_])st\.', ext, re.M)

const = '\n'.join(L[inicio_const:fin_const])
const = const.replace('secreto_opcional("EE_PROJECT", "ee-julissaguevaravega")',
                      'os.environ.get("EE_PROJECT", "ee-julissaguevaravega")')
const = const.replace('ASSET_FINCAS = secreto_opcional("EE_ASSET_FINCAS")', 'ASSET_FINCAS = None  # el portal ya no usa fincas')
const += '\nASSET_SUBCUENCAS = os.environ.get("EE_ASSET_SubCuencas", "projects/ee-julissaguevaravega/assets/SubCuenca_CHCP")\n'
const = const.replace('ASSET_BOSQUE_2021 = secreto_opcional("EE_ASSET_BOSQUE_2021")',
                      'ASSET_BOSQUE_2021 = os.environ.get(\n    "EE_ASSET_BOSQUE_2021", "projects/ee-julissaguevaravega/assets/CBOTB_2021_BOSQUE"\n)')
assert 'secreto_opcional' not in const

CABECERA = '''"""Motor de preevaluación territorial y conectividad (Earth Engine).

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

'''
ADAPTADOR = '''


def obtener_area(tipo_area=None, finca_id=None, subcuenca_nombre=None, geometria_geojson=None):
    """Adaptador del portal: recibe la geometría GeoJSON (WGS 84) ya recortada al área de estudio."""
    datos = json.loads(geometria_geojson) if isinstance(geometria_geojson, str) else geometria_geojson
    return ee.FeatureCollection([ee.Feature(ee.Geometry(datos), {"Origen": tipo_area or "portal"})])

'''
CAPAS = '''


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
'''
destino = S + '/motor_ee.py'
open(destino, 'w', encoding='utf-8').write(CABECERA + const + ADAPTADOR + ext + CAPAS)
ast.parse(open(destino, encoding='utf-8').read())
print('escrito', destino, len(open(destino).read().splitlines()), 'líneas')

# ---- leyendas.py (sin Earth Engine) ----
for n in arbol.body:
    if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'LEYENDAS' for t in n.targets):
        bloque = '\n'.join(L[n.lineno - 1:n.end_lineno])
ley = ('"""Leyendas del mapa, copiadas de app_experiencia.py (generado por build/armar_motor_ee.py)."""\n'
       'from corredores import leyenda_corredores\n'
       'from metodologia_indice import CLASES_VIGOR_NDVI, REGLAS_MAPA_COINCIDENCIA\n'
       'from eri_indicativo import CLASES_ERI\n\n' + bloque + '\n')
open(S + '/leyendas.py', 'w', encoding='utf-8').write(ley)
print('escrito leyendas.py')
