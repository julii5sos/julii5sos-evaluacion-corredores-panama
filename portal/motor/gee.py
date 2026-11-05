"""Funciones de Google Earth Engine del motor de conectividad.

Requisitos: `pip install earthengine-api`, cuenta registrada para uso no
comercial y la variable EE_PROJECT con el id del proyecto de Google Cloud.

    import motor.gee as G
    G.iniciar()                      # usa EE_PROJECT
    bosque = G.bosque_anual(2024)    # ee.Image binaria

Todas las salidas se trabajan en la grilla del motor: UTM 17N (EPSG:32617),
30 m, recortadas al área de estudio (Cuenca del Canal + 10 km).

Nota: este módulo no se pudo ejecutar contra Earth Engine en el entorno donde
se escribió (sin credenciales). Los nombres de colecciones y bandas siguen el
catálogo público; los marcados con «VERIFICAR» conviene revisarlos al primer uso.
"""
from __future__ import annotations

import datetime as dt
import os

import numpy as np

try:
    import ee
except ImportError:  # el portal funciona sin Earth Engine
    ee = None

from motor.area import geometria_area

CRS = 'EPSG:32617'
ESCALA = 30

# ---------------------------------------------------------------- inicio
_listo = False


def disponible() -> bool:
    return ee is not None and bool(os.environ.get('EE_PROJECT'))


def iniciar(proyecto: str | None = None):
    """Inicia Earth Engine con el proyecto no comercial registrado."""
    global _listo
    if _listo:
        return
    if ee is None:
        raise RuntimeError('Falta la librería earthengine-api (pip install earthengine-api).')
    proyecto = proyecto or os.environ.get('EE_PROJECT')
    if not proyecto:
        raise RuntimeError('Define EE_PROJECT con el id de tu proyecto de Google Cloud registrado en Earth Engine.')
    # Igual que en la app de Streamlit: cuenta de servicio si está configurada
    # (EE_SERVICE_ACCOUNT_JSON = ruta al .json o su contenido); si no, la
    # credencial personal creada con `earthengine authenticate`.
    sa = os.environ.get('EE_SERVICE_ACCOUNT_JSON')
    if sa:
        import json
        from google.oauth2 import service_account
        info = json.loads(open(sa, encoding='utf-8').read() if os.path.exists(sa) else sa)
        cred = service_account.Credentials.from_service_account_info(
            info, scopes=['https://www.googleapis.com/auth/earthengine',
                          'https://www.googleapis.com/auth/cloud-platform'])
        ee.Initialize(credentials=cred, project=proyecto)
    else:
        ee.Initialize(project=proyecto)
    _listo = True


def aoi() -> 'ee.Geometry':
    return ee.Geometry(geometria_area('area_estudio'))


def cuenca() -> 'ee.Geometry':
    return ee.Geometry(geometria_area('cuenca'))


# ---------------------------------------------------------------- cobertura
def dynamic_world(inicio: str, fin: str, region=None) -> 'ee.ImageCollection':
    return (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
            .filterBounds(region or aoi()).filterDate(inicio, fin))


def cobertura_anual(anio: int, region=None) -> 'ee.Image':
    """Moda anual de la clase de Dynamic World (0 agua … 8 nieve) y probabilidad media de árboles."""
    dw = dynamic_world(f'{anio}-01-01', f'{anio + 1}-01-01', region)
    clase = dw.select('label').reduce(ee.Reducer.mode()).rename('clase')
    arboles = dw.select('trees').mean().rename('p_arboles')
    return clase.addBands(arboles).clip(region or aoi())


def bosque_anual(anio: int, region=None, umbral: float = 0.5) -> 'ee.Image':
    """Bosque = clase modal 'trees' (1) y probabilidad media de árboles ≥ umbral."""
    c = cobertura_anual(anio, region)
    return c.select('clase').eq(1).And(c.select('p_arboles').gte(umbral)).rename('bosque').unmask(0)


def bosque_reciente(dias: int = 365, region=None, umbral: float = 0.5) -> 'ee.Image':
    hoy = dt.date.today()
    dw = dynamic_world(str(hoy - dt.timedelta(days=dias)), str(hoy), region)
    return (dw.select('label').reduce(ee.Reducer.mode()).eq(1)
            .And(dw.select('trees').mean().gte(umbral)).rename('bosque').unmask(0).clip(region or aoi()))


def perdida_ganancia(anio0: int, anio1: int, region=None) -> 'ee.Image':
    """Transiciones de bosque entre dos años (Dynamic World).
    Bandas: perdida (bosque→no bosque), ganancia (no bosque→bosque), estable."""
    b0 = bosque_anual(anio0, region)
    b1 = bosque_anual(anio1, region)
    return ee.Image.cat(
        b0.And(b1.Not()).rename('perdida'),
        b0.Not().And(b1).rename('ganancia'),
        b0.And(b1).rename('estable'))


def hansen(region=None) -> 'ee.Image':
    """Pérdida anual 2001–2025 (lossyear 1–25) y cobertura arbórea 2000 (Hansen v1.13)."""
    return ee.Image('UMD/hansen/global_forest_change_2025_v1_13').select(
        ['treecover2000', 'lossyear']).clip(region or aoi())


# ---------------------------------------------------------------- alertas
def alertas_s1(dias: int = 60, caida_db: float = 3.0, region=None) -> 'ee.Image':
    """Detector propio con radar Sentinel-1 (ve a través de las nubes).

    Compara la mediana de VH de los últimos `dias` contra la mediana del mismo
    periodo del año anterior. Una caída ≥ `caida_db` dB dentro del bosque
    se marca como alerta. Funciona sin depender de la cobertura de terceros.
    """
    region = region or aoi()
    hoy = dt.date.today()
    ini = hoy - dt.timedelta(days=dias)

    def s1(a, b):
        return (ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(region).filterDate(str(a), str(b))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
                .select('VH').map(lambda i: i.focal_median(30, 'circle', 'meters')))
    reciente = s1(ini, hoy).median()
    base = s1(ini - dt.timedelta(days=365), hoy - dt.timedelta(days=365)).median()
    bosque = bosque_anual(hoy.year - 1, region)
    return base.subtract(reciente).gte(caida_db).And(bosque).rename('alerta_s1').selfMask().clip(region)


def alertas_radd(desde: str, region=None) -> 'ee.Image | None':
    """Alertas RADD (Sentinel-1, Wageningen). VERIFICAR que Panamá esté en la cobertura.
    Bandas: Alert (2 = baja confianza, 3 = alta), Date (formato yyDDD)."""
    region = region or aoi()
    col = (ee.ImageCollection('projects/radar-wur/raddalert/v1')
           .filterBounds(region).filter(ee.Filter.eq('layer', 'alert')))
    img = ee.Image(col.sort('system:time_start', False).first())
    d = dt.date.fromisoformat(desde)
    yyddd = (d.year % 100) * 1000 + d.timetuple().tm_yday
    return img.select('Alert').gte(2).And(img.select('Date').gte(yyddd)).selfMask().rename('alerta_radd').clip(region)


# ---------------------------------------------------------------- componentes del ERI
def estructura(anio: int, parcelas: 'ee.FeatureCollection | None' = None, campo_ab: str = 'ab_m2ha',
               region=None) -> 'ee.Image':
    """Componente 1 · Integridad estructural del bosque (0–1).

    = 0,5 × altura de dosel normalizada + 0,5 × área basal normalizada.
    Altura: ETH Global Canopy Height 2020, 10 m (VERIFICAR asset; alternativa: Meta 1 m).
    Área basal: si hay parcelas de campo (campo `campo_ab`, m²/ha), se modela con
    Random Forest a partir de Sentinel-2 + altura; si no, se usa como sustituto la
    probabilidad media de árboles de Dynamic World.
    """
    region = region or aoi()
    altura = ee.Image('users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1').select(0).rename('altura')
    h = altura.divide(35).clamp(0, 1)
    if parcelas is not None:
        s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(region)
              .filterDate(f'{anio}-01-01', f'{anio + 1}-01-01')
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60)).median()
              .select(['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B11', 'B12']))
        ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        X = s2.addBands(ndvi).addBands(altura)
        muestras = X.sampleRegions(parcelas, [campo_ab], scale=10)
        rf = ee.Classifier.smileRandomForest(200).setOutputMode('REGRESSION').train(muestras, campo_ab, X.bandNames())
        ab = X.classify(rf).rename('ab')
        p95 = ab.reduceRegion(ee.Reducer.percentile([95]), region, 30, maxPixels=1e9).values().get(0)
        ab_n = ab.divide(ee.Number(p95)).clamp(0, 1)
    else:
        ab_n = cobertura_anual(anio, region).select('p_arboles')
    return h.multiply(0.5).add(ab_n.multiply(0.5)).rename('estructura').clip(region)


def topografia(anio: int, region=None, pendiente_max: float = 45) -> 'ee.Image':
    """Componente 3 · Estabilidad topográfica (0–1) = 1 − riesgo de erosión ponderado por pendiente.
    Riesgo = pendiente normalizada × (1 − probabilidad de árboles)."""
    region = region or aoi()
    dem_col = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(region).select('DEM')
    dem = dem_col.mosaic().setDefaultProjection(dem_col.first().projection())
    pend = ee.Terrain.slope(dem).divide(pendiente_max).clamp(0, 1)
    cubierta = cobertura_anual(anio, region).select('p_arboles')
    riesgo = pend.multiply(ee.Image(1).subtract(cubierta))
    return ee.Image(1).subtract(riesgo).rename('topografia').clip(region)


def riparia(region=None, area_drenaje_km2: float = 1.0, dist_max_m: float = 1000) -> 'ee.Image':
    """Componente 4 · Proximidad riparia (0–1) = 1 − distancia a cauce perenne / dist_max.
    Cauces: MERIT Hydro con área de drenaje ≥ `area_drenaje_km2` (supuesto de perennidad
    en clima húmedo; si la ACP tiene una capa oficial de ríos perennes, sustituirla)."""
    region = region or aoi()
    upa = ee.Image('MERIT/Hydro/v1_0_1').select('upa')
    cauces = upa.gte(area_drenaje_km2).selfMask()
    d = (cauces.fastDistanceTransform(256, 'pixels', 'squared_euclidean').sqrt()
         .multiply(ESCALA).reproject(CRS, None, ESCALA))
    return ee.Image(1).subtract(d.divide(dist_max_m).clamp(0, 1)).rename('riparia').clip(region)


# ---------------------------------------------------------------- riesgo de pérdida
def modelo_riesgo(anio_base: int = 2019, horizonte: int = 3, region=None, n: int = 4000) -> 'ee.Image':
    """Probabilidad de pérdida de bosque (0–1) con Random Forest.

    Entrena con la pérdida Hansen de (anio_base+1 … anio_base+horizonte) sobre el
    bosque de anio_base, y predice sobre el bosque actual con predictores actualizados.
    Predictores: distancia a pérdida reciente, a borde de bosque, a zona construida,
    a cauces, pendiente y elevación.
    """
    region = region or aoi()
    han = hansen(region)
    dem_col = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(region).select('DEM')
    dem = dem_col.mosaic().setDefaultProjection(dem_col.first().projection())
    pend = ee.Terrain.slope(dem)

    def dist(mask):
        return (mask.selfMask().fastDistanceTransform(256, 'pixels', 'squared_euclidean').sqrt()
                .multiply(ESCALA).reproject(CRS, None, ESCALA))

    def predictores(anio):
        ly = han.select('lossyear')
        y = anio - 2000
        reciente = ly.gt(y - 5).And(ly.lte(y))
        cob = cobertura_anual(anio, region)
        bosque = cob.select('clase').eq(1)
        return ee.Image.cat(
            dist(reciente).rename('d_perdida'), dist(bosque.Not()).rename('d_borde'),
            dist(cob.select('clase').eq(6)).rename('d_construido'),
            dist(ee.Image('MERIT/Hydro/v1_0_1').select('upa').gte(1)).rename('d_cauce'),
            pend.rename('pendiente'), dem.rename('elevacion')), bosque

    X0, bosque0 = predictores(anio_base)
    ly = han.select('lossyear')
    y = ly.gt(anio_base - 2000).And(ly.lte(anio_base - 2000 + horizonte)).rename('perdio')
    muestras = X0.addBands(y).updateMask(bosque0).stratifiedSample(
        numPoints=n, classBand='perdio', region=region, scale=ESCALA, seed=7, geometries=False)
    rf = ee.Classifier.smileRandomForest(200).setOutputMode('PROBABILITY').train(muestras, 'perdio', X0.bandNames())
    X1, bosque1 = predictores(dt.date.today().year - 1)
    return X1.classify(rf).updateMask(bosque1).rename('riesgo').clip(region)


# ---------------------------------------------------------------- estadísticas y descarga
def area_ha(mascara: 'ee.Image', region, escala: int = ESCALA) -> float:
    v = mascara.selfMask().multiply(ee.Image.pixelArea()).reduceRegion(
        ee.Reducer.sum(), region, escala, crs=CRS, maxPixels=1e10).values().get(0)
    return float(ee.Number(ee.Algorithms.If(v, v, 0)).divide(1e4).getInfo())


def grilla(region_geojson: dict, escala: int = ESCALA):
    """Rejilla UTM que cubre la geometría: (x0, y1, ancho, alto)."""
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform
    t = Transformer.from_crs(4326, 32617, always_xy=True).transform
    xmin, ymin, xmax, ymax = transform(t, shape(region_geojson)).bounds
    x0 = np.floor(xmin / escala) * escala
    y1 = np.ceil(ymax / escala) * escala
    return x0, y1, int(np.ceil((xmax - x0) / escala)), int(np.ceil((y1 - ymin) / escala))


def descargar(img: 'ee.Image', region_geojson: dict, escala: int = ESCALA, tile: int = 1024) -> dict:
    """Descarga una imagen como arreglos numpy (por banda) en la rejilla UTM, por mosaicos."""
    x0, y1, ancho, alto = grilla(region_geojson, escala)
    bandas = img.bandNames().getInfo()
    salida = {b: np.full((alto, ancho), np.nan, dtype=np.float32) for b in bandas}
    for fy in range(0, alto, tile):
        for fx in range(0, ancho, tile):
            h, w = min(tile, alto - fy), min(tile, ancho - fx)
            arr = ee.data.computePixels({
                'expression': img.unmask(-9999).toFloat(), 'fileFormat': 'NUMPY_NDARRAY',
                'grid': {'dimensions': {'width': w, 'height': h},
                         'affineTransform': {'scaleX': escala, 'shearX': 0, 'translateX': x0 + fx * escala,
                                             'shearY': 0, 'scaleY': -escala, 'translateY': y1 - fy * escala},
                         'crsCode': CRS}})
            for b in bandas:
                v = arr[b].astype(np.float32)
                v[v == -9999] = np.nan
                salida[b][fy:fy + h, fx:fx + w] = v
    salida['_transform'] = (escala, 0.0, float(x0), 0.0, -escala, float(y1))
    return salida
