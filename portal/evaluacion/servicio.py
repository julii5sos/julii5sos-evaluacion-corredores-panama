"""Servicio de preevaluación para el portal (sin Streamlit).

Reproduce la orquestación de app_experiencia.py (líneas «solicitar_analisis»):

    territorial  → ejecutar_analisis (JRC, Hansen, ESRI, GEDI, NDVI) → índice 0–6,5
    corredores   → analizar_interseccion_corredores + fragmentación del bosque 2021
    integral     → ambos + calcular_prioridad_visita

La intersección con corredores de Almanaque Azul es local (no requiere Earth Engine).
Todo lo demás requiere Earth Engine y, para la fragmentación, el asset privado
del bosque 2021 (EE_ASSET_BOSQUE_2021).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from corredores import analizar_interseccion_corredores, calcular_radio_contexto
from metodologia_indice import (
    PESOS_INDICE,
    PUNTAJE_MAXIMO,
    PUNTAJE_MAXIMO_VISITA,
    calcular_prioridad_visita,
    evaluar_contexto_estructural,
    texto_recomendacion_visita,
)
from modos_app import MODO_CORREDORES, MODO_INTEGRAL, MODO_TERRITORIAL, MODOS_ANALISIS

MODOS = (MODO_TERRITORIAL, MODO_CORREDORES, MODO_INTEGRAL)
UMBRALES_DISTANCIA_M = (100, 200, 300, 500, 750, 1000, 1500, 2000)
# Copia de texto_recomendacion() de app_experiencia.py (sin importar Earth Engine).
TEXTO_RECOMENDACION = {
    "Alta": "Visita de campo prioritaria en los sectores con señales coincidentes.",
    "Media": "Revisar imágenes recientes y evaluar si se justifica una visita.",
    "Preventiva": "Mantener monitoreo periódico y revisar condiciones de riesgo.",
    "Baja": "Sin acción inmediata. Continuar el monitoreo anual normal.",
}


class ErrorPreevaluacion(ValueError):
    pass


def ee_disponible() -> bool:
    try:
        import ee  # noqa: F401
    except ImportError:
        return False
    return bool(os.environ.get('EE_PROJECT'))


def _iniciar_ee():
    from motor import gee  # reutiliza la inicialización del portal (cuenta de servicio o personal)
    gee.iniciar()


@lru_cache(maxsize=64)
def _analisis_cambios(geo_json: str) -> dict:
    import motor_ee as M
    _iniciar_ee()
    return M.ejecutar_analisis('portal', None, None, geo_json, M.ANO_DIAG_TMF, M.ANO_ESRI_MIN, M.ANO_ESRI_MAX)


@lru_cache(maxsize=64)
def _fragmentacion(geo_json: str, umbral_m: float, area_min_ha: float, radio_m: float = 5000.0) -> dict:
    import motor_ee as M
    _iniciar_ee()
    r = M.analizar_bosque_asset(M.ASSET_BOSQUE_2021, M.CAMPO_COBERTURA_BOSQUE_2021,
                                M.VALOR_COBERTURA_BOSQUE_2021, geo_json, umbral_m, area_min_ha, radio_m)
    r['radio_contexto_m'] = radio_m
    r['fuente_cobertura'] = M.FUENTE_BOSQUE_CORTA
    r['ano_referencia_cobertura'] = M.ANO_BOSQUE_REFERENCIA
    return r


@lru_cache(maxsize=64)
def _fragmentacion_local(geo_json: str, umbral_m: float, area_min_ha: float, radio_m: float = 5000.0) -> dict:
    """Alternativa sin el asset privado: vectoriza el bosque que dejó el motor del portal
    (Dynamic World si corrió con Earth Engine; capas sintéticas en modo demostración) y
    aplica exactamente el mismo análisis de fragmentación y red de parches."""
    import numpy as np
    import rasterio
    from rasterio.features import shapes
    from rasterio.mask import mask
    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform, unary_union
    from bosque_conectividad import analizar_fragmentacion_geojson
    from corredores import cargar_corredores
    import config as C
    ruta = C.DATOS_SALIDA / 'motor' / 'bosque_actual.tif'
    if not ruta.exists():
        raise ErrorPreevaluacion('Ejecuta primero python ejecutar_motor.py para disponer de una capa de bosque.')
    aoi = shape(json.loads(geo_json))
    a_utm = Transformer.from_crs(4326, 32617, always_xy=True).transform
    a_wgs = Transformer.from_crs(32617, 4326, always_xy=True).transform
    contexto = transform(a_utm, aoi).buffer(max(umbral_m, radio_m))
    with rasterio.open(ruta) as src:
        arr, t = mask(src, [mapping(contexto)], crop=True, filled=True, nodata=0)
        res = src.res[0]
    b = arr[0].astype(np.uint8)
    polis = [shape(g) for g, v in shapes(b, mask=b > 0, transform=t) if v == 1]
    bosque = unary_union(polis).simplify(res / 2) if polis else None
    geo_bosque = mapping(transform(a_wgs, bosque)) if bosque is not None and not bosque.is_empty else \
        {'type': 'FeatureCollection', 'features': []}
    r = analizar_fragmentacion_geojson(bosque_geojson=geo_bosque, aoi_geojson=json.loads(geo_json),
                                       umbral_m=umbral_m, area_min_ha=area_min_ha, incluir_contexto_exterior=True,
                                       corredores_geojson=cargar_corredores(), radio_busqueda_corredor_m=radio_m)
    meta = json.loads((C.DATOS_SALIDA / 'motor' / 'motor.js').read_text(encoding='utf-8')[len('window.MOTOR='):-1])
    r['fuente_cobertura'] = (f"Bosque {meta['anio1']} del motor del portal · "
                             + ('Dynamic World (Earth Engine)' if meta['modo'] != 'demo' else 'capas de demostración'))
    r['ano_referencia_cobertura'] = meta['anio1']
    r['cobertura_alternativa'] = True
    return r


@lru_cache(maxsize=64)
def _eri(geo_json: str) -> dict:
    import motor_ee as M
    _iniciar_ee()
    return M.calcular_eri_indicativo(M.TIPO_AREA_DIBUJADA, None, None, geo_json)


@lru_cache(maxsize=64)
def _capas(geo_json: str) -> dict:
    import motor_ee as M
    _iniciar_ee()
    return M.capas_mapa(json.loads(geo_json))


@lru_cache(maxsize=128)
def _serie(geo_json: str, fuente: str) -> dict:
    import motor_ee as M
    _iniciar_ee()
    return M.calcular_serie_fuente('portal', None, None, geo_json, fuente)


def _forma(geojson: dict):
    """Geometría shapely (WGS 84) de un Geometry, Feature o FeatureCollection, sin límite de superficie."""
    from shapely.geometry import shape
    from shapely.ops import unary_union
    if not isinstance(geojson, dict) or 'type' not in geojson:
        raise ErrorPreevaluacion('El área no es un GeoJSON válido.')
    t = geojson['type']
    if t == 'FeatureCollection':
        geoms = [shape(f['geometry']) for f in geojson.get('features', []) if f.get('geometry')]
    elif t == 'Feature':
        geoms = [shape(geojson['geometry'])]
    else:
        geoms = [shape(geojson)]
    geoms = [x.buffer(0) for x in geoms if x.geom_type in ('Polygon', 'MultiPolygon', 'GeometryCollection')]
    if not geoms:
        raise ErrorPreevaluacion('El archivo no contiene polígonos.')
    return unary_union(geoms)


def _area_ha(geojson: dict) -> float:
    from pyproj import Transformer
    from shapely.ops import transform
    return transform(Transformer.from_crs(4326, 32617, always_xy=True).transform, _forma(geojson)).area / 1e4


def recortar(geojson: dict) -> dict:
    """Recorta la geometría al área de estudio (Cuenca del Canal + 10 km), como la app
    original recorta los polígonos dibujados a la cuenca."""
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    from motor.area import geometria_area
    g = _forma(geojson)
    area = shape(geometria_area('area_estudio'))
    r = unary_union([g]).intersection(area).buffer(0)
    if r.is_empty or r.area == 0:
        raise ErrorPreevaluacion('El área está fuera de la Cuenca del Canal + 10 km.')
    return mapping(r)


def preevaluar(geojson: dict, modo: str, umbral_m: float = 500, area_min_ha: float = 0.0,
               con_capas: bool = True, ya_recortado: bool = False) -> dict:
    if modo not in MODOS:
        raise ErrorPreevaluacion('Modo de análisis no reconocido.')
    umbral_m = float(umbral_m)
    if umbral_m <= 0 or umbral_m > 5000:
        raise ErrorPreevaluacion('La distancia entre fragmentos debe estar entre 1 y 5000 m.')
    geo = geojson if ya_recortado else recortar(geojson)
    geo_json = json.dumps(geo, sort_keys=True, ensure_ascii=False)
    hay_ee = ee_disponible()
    analiza_cambios = modo in (MODO_TERRITORIAL, MODO_INTEGRAL)
    analiza_conectividad = modo in (MODO_CORREDORES, MODO_INTEGRAL)
    ejemplo = analiza_cambios and not hay_ee and os.environ.get('PREEVALUACION_EJEMPLO') == '1'
    if analiza_cambios and not hay_ee and not ejemplo:
        raise ErrorPreevaluacion(
            'La preevaluación territorial e integral necesita Earth Engine. Define EE_PROJECT '
            '(y EE_SERVICE_ACCOUNT_JSON si usas cuenta de servicio) y reinicia python app.py.')

    resultados: dict = {}
    if ejemplo:
        from ejemplo import resultado_cambios_ejemplo
        resultados.update(resultado_cambios_ejemplo(_area_ha(geo)))
    elif analiza_cambios:
        resultados.update(_analisis_cambios(geo_json))
    if analiza_conectividad:
        resultados['corredores'] = analizar_interseccion_corredores(geo)
        radio_m = calcular_radio_contexto(resultados['corredores'].get('distancia_corredor_mas_cercano_m'),
                                          umbral_m, 5000)
        resultados['radio_contexto_conectividad_m'] = radio_m
        error_asset = None
        if hay_ee:
            try:
                resultados['fragmentacion'] = _fragmentacion(geo_json, umbral_m, float(area_min_ha), radio_m)
            except Exception as error:
                error_asset = str(error)
        else:
            error_asset = ('El bosque 2021 de SINIA–MiAMBIENTE se lee desde el asset privado de Earth Engine '
                           '(EE_ASSET_BOSQUE_2021); sin Earth Engine se usa el bosque del motor del portal.')
        if 'fragmentacion' not in resultados:
            resultados['fragmentacion_aviso'] = error_asset
            try:
                resultados['fragmentacion'] = _fragmentacion_local(geo_json, umbral_m, float(area_min_ha), radio_m)
            except Exception as error:
                resultados['fragmentacion_error'] = f'{error_asset} · {error}'
        resultados['contexto_estructural'] = evaluar_contexto_estructural(resultados.get('fragmentacion'))
    if analiza_cambios and hay_ee and not ejemplo:
        try:
            resultados['eri'] = _eri(geo_json)
        except Exception as error:
            resultados['eri_error'] = str(error)
    if modo == MODO_INTEGRAL:
        resultados['prioridad_visita'] = calcular_prioridad_visita(
            puntaje_cambios=resultados['puntaje'], contexto_corredores=resultados['corredores'],
            contexto_fragmentacion=resultados.get('fragmentacion'))
        resultados['recomendacion_visita'] = texto_recomendacion_visita(resultados['prioridad_visita']['prioridad_visita'])
    if analiza_cambios:
        resultados['recomendacion'] = TEXTO_RECOMENDACION[resultados['prioridad']]
        if con_capas and not ejemplo:
            try:
                resultados['capas'] = _capas(geo_json)
            except Exception as error:
                resultados['capas_error'] = str(error)
    if 'area_ha' not in resultados:
        resultados['area_ha'] = round(_area_ha(geo), 2)
    resultados.update(modo_analisis=modo, modo_titulo=MODOS_ANALISIS[modo]['titulo'], umbral_m=umbral_m,
                      area_min_ha=float(area_min_ha), earth_engine=hay_ee, geometria=geo,
                      puntaje_maximo=PUNTAJE_MAXIMO, puntaje_maximo_visita=PUNTAJE_MAXIMO_VISITA,
                      pesos=PESOS_INDICE)
    return resultados


def serie_fuente(geojson: dict, fuente: str) -> dict:
    if not ee_disponible():
        raise ErrorPreevaluacion('Las series anuales se calculan con Earth Engine.')
    return _serie(json.dumps(recortar(geojson), sort_keys=True, ensure_ascii=False), fuente)


# ---------------------------------------------------------------- descargas ----
def _json(geo) -> str:
    return json.dumps(geo, sort_keys=True, ensure_ascii=False)


def registro_metodologico(resultados: dict) -> dict:
    """Registro JSON reproducible (fuentes, periodos, umbrales, pesos, reglas y resumen del resultado)."""
    import motor_ee as M
    return M.construir_registro_metodologico(
        M.TIPO_AREA_DIBUJADA, None, None, _json(resultados['geometria']),
        M.ANO_DIAG_TMF, M.ANO_DIAG_TMF, M.ANO_ESRI_MIN, M.ANO_ESRI_MAX,
        M.ANO_NDVI_INICIAL_ANALISIS, M.ANO_NDVI_FINAL_ANALISIS,
        M.ANO_DIAG_TMF, M.ANO_ESRI_MAX, M.ANO_NDVI_MAX,
        resultados['modo_analisis'], 'No aplica (portal)', [], resultados)


def geojson_fragmentos(resultados: dict) -> dict:
    fr = resultados.get('fragmentacion')
    if not fr or not fr.get('parches_geojson'):
        raise ErrorPreevaluacion('Este resultado no incluye fragmentos de bosque (usa el modo corredores o integral).')
    return fr['parches_geojson']


def geojson_red(resultados: dict) -> dict:
    fr = resultados.get('fragmentacion')
    if not fr:
        raise ErrorPreevaluacion('Este resultado no incluye la red de conectividad (usa el modo corredores o integral).')
    feats = []
    for k in ('conexiones_geojson', 'conexiones_potenciales_geojson', 'ruta_corredor_geojson'):
        feats += (fr.get(k) or {}).get('features', [])
    return {'type': 'FeatureCollection', 'features': feats}


def informe_pdf(resultados: dict, nombre_area: str = 'Área analizada') -> tuple[bytes, list[str]]:
    """Ficha PDF. Con Earth Engine incluye los siete mapas; sin él, la ficha va sin mapas (se avisa)."""
    import motor_ee as M
    if 'puntaje' not in resultados:
        raise ErrorPreevaluacion('El PDF corresponde a los modos territorial e integral.')
    avisos, mapas = [], None
    if ee_disponible() and not resultados.get('ejemplo'):
        try:
            _iniciar_ee()
            mapas = M.generar_mapas_reporte(M.TIPO_AREA_DIBUJADA, None, None, _json(resultados['geometria']),
                                            M.ANO_DIAG_TMF, M.ANO_ESRI_MIN, M.ANO_ESRI_MAX,
                                            M.ANO_NDVI_INICIAL_ANALISIS)
            if not all(m.get('imagen') for m in mapas):
                avisos.append('Earth Engine no entregó todos los mapas; el PDF incluye los disponibles.')
        except Exception as error:
            avisos.append(f'No se pudieron generar los mapas: {error}')
    else:
        avisos.append('Sin Earth Engine: la ficha se genera sin los mapas cartográficos.')
    pdf = M.generar_pdf(nombre_area, resultados, M.ANO_DIAG_TMF, M.ANO_ESRI_MIN, M.ANO_ESRI_MAX,
                        M.ANO_NDVI_INICIAL_ANALISIS, mapas)
    return pdf, avisos


# --------------------------------------------------------------- comparador ----
FUENTES_COMPARADOR = {
    'JRC TMF': {'min': 1990, 'max': 'ANO_TMF_MAX', 'ley': 'JRC TMF'},
    'ESRI LULC': {'min': 'ANO_ESRI_MIN', 'max': 'ANO_ESRI_MAX', 'ley': 'ESRI LULC'},
    'NDVI Sentinel-2': {'min': 2017, 'max': 'ANO_NDVI_MAX', 'ley': 'Vegetación NDVI'},
}


def opciones_comparador() -> dict:
    """Años disponibles por fuente (los mismos del comparador del repositorio)."""
    import motor_ee as M
    sal = {}
    for nombre, c in FUENTES_COMPARADOR.items():
        a0 = c['min'] if isinstance(c['min'], int) else getattr(M, c['min'])
        a1 = c['max'] if isinstance(c['max'], int) else getattr(M, c['max'])
        sal[nombre] = {'min': a0, 'max': a1, 'leyenda': c['ley']}
    return sal


@lru_cache(maxsize=64)
def _teselas_ano(geo_json: str, fuente: str, anio: int) -> str:
    import motor_ee as M
    _iniciar_ee()
    geometria = M.obtener_area(geometria_geojson=geo_json).geometry(M.TOLERANCIA_RECORTE_M)
    if fuente == 'JRC TMF':
        imagen, vis = M.obtener_tmf(anio, geometria), M.VIS_TMF
    elif fuente == 'ESRI LULC':
        imagen, vis = M.obtener_esri_visual(anio, geometria), M.VIS_ESRI
    else:
        imagen, vis = M.clasificar_ndvi(M.obtener_ndvi(anio, geometria)), M.VIS_NDVI_CLASES
    return M.ee.Image(imagen).getMapId(vis)['tile_fetcher'].url_format


def comparar_anios(geojson, fuente: str, anio_inicial: int, anio_final: int) -> dict:
    """URLs de teselas de Earth Engine para dos años de una misma fuente (divisor en el navegador)."""
    if fuente not in FUENTES_COMPARADOR:
        raise ErrorPreevaluacion('Elige JRC TMF, ESRI LULC o NDVI Sentinel-2.')
    op = opciones_comparador()[fuente]
    a0, a1 = int(anio_inicial), int(anio_final)
    if not (op['min'] <= a0 < a1 <= op['max']):
        raise ErrorPreevaluacion(f'Para {fuente} el año inicial debe ser menor que el final, entre {op["min"]} y {op["max"]}.')
    if not ee_disponible():
        raise ErrorPreevaluacion('El comparador necesita Earth Engine conectado en el servidor (define EE_PROJECT y autentica).')
    geo = _json(recortar(geojson))
    return {'fuente': fuente, 'leyenda': op['leyenda'],
            'izquierda': {'anio': a0, 'etiqueta': f'{fuente} {a0}', 'url': _teselas_ano(geo, fuente, a0)},
            'derecha': {'anio': a1, 'etiqueta': f'{fuente} {a1}', 'url': _teselas_ano(geo, fuente, a1)}}
