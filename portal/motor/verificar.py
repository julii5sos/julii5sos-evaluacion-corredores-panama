"""Verificación bajo demanda de un polígono (área de interés dibujada o subida).

    from motor.verificar import verificar
    r = verificar(geojson_geometry, anio0=2019, anio1=2025)

Con Earth Engine (EE_PROJECT definido) el cálculo es en vivo:
  · bosque por año con Dynamic World (serie anual anio0…anio1)
  · pérdida y ganancia anio0→anio1
  · pérdida anual Hansen 2001–2025
  · alertas recientes de radar Sentinel-1 (últimos 60 días)
  · métricas de fragmentación (LPI, CONNECT, ED, ENN) y conectividad equivalente
Sin Earth Engine se usan los rásters que dejó el motor (static/data/motor/*.tif).
En ambos casos se agregan ERI, riesgo, prioridades y KBA que tocan el polígono.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import config as C
from motor import fragstats

MOTOR = C.DATOS_SALIDA / 'motor'


class ErrorVerificacion(ValueError):
    pass


# ------------------------------------------------------------------ geometría
def normalizar(geojson: dict):
    """Acepta Geometry, Feature o FeatureCollection; devuelve (shapely 4326, shapely UTM)."""
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform, unary_union
    if not isinstance(geojson, dict) or 'type' not in geojson:
        raise ErrorVerificacion('El polígono no es un GeoJSON válido.')
    t = geojson['type']
    if t == 'FeatureCollection':
        geoms = [shape(f['geometry']) for f in geojson.get('features', []) if f.get('geometry')]
    elif t == 'Feature':
        geoms = [shape(geojson['geometry'])]
    else:
        geoms = [shape(geojson)]
    geoms = [g.buffer(0) for g in geoms if g.geom_type in ('Polygon', 'MultiPolygon')]
    if not geoms:
        raise ErrorVerificacion('El archivo no contiene polígonos.')
    g = unary_union(geoms)
    utm = transform(Transformer.from_crs(4326, 32617, always_xy=True).transform, g)
    if utm.area < 900:
        raise ErrorVerificacion('El polígono es demasiado pequeño (menos de 0,1 ha).')
    if utm.area > 2_000_000_000:
        raise ErrorVerificacion('El polígono supera 200 000 ha. Para áreas grandes usa una subcuenca.')
    return g, utm


def leer_archivo(nombre: str, contenido: bytes) -> dict:
    """Convierte un archivo subido (GeoJSON, KML/KMZ o Shapefile en .zip) a GeoJSON en WGS 84."""
    import tempfile, zipfile
    import geopandas as gpd
    ext = Path(nombre).suffix.lower()
    tmp = Path(tempfile.mkdtemp())
    ruta = tmp / Path(nombre).name
    ruta.write_bytes(contenido)
    if ext in ('.geojson', '.json'):
        return json.loads(contenido.decode('utf-8'))
    if ext == '.zip':
        with zipfile.ZipFile(ruta) as z:
            z.extractall(tmp)
        shp = next(tmp.rglob('*.shp'), None)
        if shp is None:
            raise ErrorVerificacion('El .zip no contiene un archivo .shp.')
        gdf = gpd.read_file(shp)
    elif ext == '.kmz':
        with zipfile.ZipFile(ruta) as z:
            z.extractall(tmp)
        gdf = gpd.read_file(next(tmp.rglob('*.kml')))
    elif ext == '.kml':
        gdf = gpd.read_file(ruta)
    else:
        raise ErrorVerificacion('Formato no soportado. Usa GeoJSON, KML, KMZ o Shapefile comprimido en .zip.')
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return json.loads(gdf.to_crs(4326).to_json())


# ------------------------------------------------------------------ comunes
def _veredicto(perdida, ganancia, alertas, area):
    neto = ganancia - perdida
    if alertas > 0:
        return 'alerta', f'Hay {alertas:.1f} ha con alertas recientes de pérdida dentro del polígono. Conviene revisarlas en campo.'
    if neto > 0.01 * area:
        return 'mejora', f'La cobertura de bosque aumentó {neto:.1f} ha netas en el periodo.'
    if neto < -0.01 * area:
        return 'deterioro', f'La cobertura de bosque disminuyó {abs(neto):.1f} ha netas en el periodo.'
    return 'estable', 'La cobertura de bosque se mantuvo estable en el periodo.'


def _kba(g4326) -> list:
    p = C.DATOS_SALIDA / 'kba_canal.geojson'
    if not p.exists():
        return []
    import geopandas as gpd
    k = gpd.read_file(p)
    if not len(k):
        return []
    k = k[k.intersects(g4326)]
    campo = next((c for c in ('IntName', 'NatName', 'Name', 'name', 'NOMBRE', 'nombre', 'SitRecID') if c in k.columns), None)
    return sorted({str(v) for v in (k[campo] if campo else k.index)})


def _leer_tif(nombre: str, utm):
    import rasterio
    from rasterio.mask import mask
    ruta = MOTOR / f'{nombre}.tif'
    if not ruta.exists():
        raise ErrorVerificacion('Falta ejecutar el motor (python ejecutar_motor.py) para verificar sin Earth Engine.')
    with rasterio.open(ruta) as src:
        arr, _ = mask(src, [utm.__geo_interface__], crop=True, filled=True,
                      nodata=(np.nan if src.dtypes[0].startswith('float') else 0), all_touched=True)
        dentro, _ = mask(src, [utm.__geo_interface__], crop=True, filled=False, all_touched=True)
        return arr[0], ~np.ma.getmaskarray(dentro[0]), src.res[0]


def _contexto(utm) -> dict:
    """ERI, riesgo y prioridades desde los rásters del motor (si existen)."""
    out = {}
    try:
        eri, m, celda = _leer_tif('eri', utm)
        ha = celda * celda / 1e4
        e = eri[m & ~np.isnan(eri)]
        if e.size:
            lo, hi = C.ERI_CORTES
            out['eri'] = dict(medio=round(float(e.mean()), 3),
                              clases={'baja': round(float((e < lo).mean() * 100), 1),
                                      'media': round(float(((e >= lo) & (e <= hi)).mean() * 100), 1),
                                      'alta': round(float((e > hi).mean() * 100), 1)})
        r, m2, _ = _leer_tif('riesgo', utm)
        b, _, _ = _leer_tif('bosque_actual', utm)
        rv = r[m2 & (b > 0)]
        out['riesgo_medio'] = round(float(np.nanmean(rv)), 3) if rv.size else None
        pr, m3, _ = _leer_tif('prioridad', utm)
        out['prioridad_ha'] = {C.PALETA_PRIORIDAD[k][0]: round(float(((pr == k) & m3).sum() * ha), 1) for k in (1, 2, 3)}
        pc, m4, _ = _leer_tif('perdida_conectividad', utm)
        out['perdida_conectividad_ha'] = round(float(((np.nan_to_num(pc) > C.CAIDA_CONECTIVIDAD) & m4).sum() * ha), 1)
    except ErrorVerificacion:
        pass
    return out


def _frag(b0, b1, valido, celda):
    f = {}
    for clave, b in (('base', b0), ('actual', b1)):
        m = fragstats.metricas(b, valido, celda, C.CONNECT_UMBRAL_M)
        m['ECA_pct'] = round(fragstats.conectividad_equivalente(b, valido, celda, C.CONNECT_UMBRAL_M), 2)
        f[clave] = {k: m.get(k) for k in ('LPI', 'CONNECT', 'ED', 'ENN_MN', 'n_parches', 'bosque_pct', 'ECA_pct')}
    return f


# ------------------------------------------------------------------ modos
def _con_ee(g4326, utm, anio0, anio1) -> dict:
    import ee
    from motor import gee as G
    G.iniciar()
    region = ee.Geometry(g4326.__geo_interface__)
    pg = G.perdida_ganancia(anio0, anio1, region)
    area = utm.area / 1e4
    serie = {}
    for a in range(anio0, anio1 + 1):
        serie[str(a)] = round(G.area_ha(G.bosque_anual(a, region), region, 10), 1)
    han = G.hansen(region).select('lossyear')
    hist = han.updateMask(han.gt(0)).multiply(1).reduceRegion(
        ee.Reducer.frequencyHistogram(), region, 30, crs=G.CRS, maxPixels=1e9).get('lossyear').getInfo() or {}
    hansen = {str(2000 + int(k)): round(v * 0.09, 1) for k, v in sorted(hist.items(), key=lambda x: int(x[0]))}
    alertas = G.area_ha(G.alertas_s1(region=region), region, 10)
    try:
        radd = G.area_ha(G.alertas_radd(f'{anio1}-01-01', region), region, 10)
    except Exception:
        radd = None
    arr = G.descargar(ee.Image.cat(G.bosque_anual(anio0, region).rename('b0'), G.bosque_anual(anio1, region).rename('b1')),
                      g4326.__geo_interface__, 10)
    from motor.pipeline import _rasterizar
    valido = _rasterizar(g4326.__geo_interface__, arr['_transform'], arr['b0'].shape)
    return dict(modo='earth-engine', resolucion_m=10,
                perdida_ha=round(G.area_ha(pg.select('perdida'), region, 10), 1),
                ganancia_ha=round(G.area_ha(pg.select('ganancia'), region, 10), 1),
                serie_bosque_ha=serie, hansen_perdida_anual=hansen,
                alertas_ha=round(alertas, 1), alertas_radd_ha=None if radd is None else round(radd, 1),
                frag=_frag(arr['b0'] > 0.5, arr['b1'] > 0.5, valido, 10))


def _sin_ee(utm) -> dict:
    b0, m, celda = _leer_tif('bosque_base', utm)
    b1, _, _ = _leer_tif('bosque_actual', utm)
    al, _, _ = _leer_tif('alertas', utm)
    ly, _, _ = _leer_tif('lossyear', utm)
    if not m.any():
        raise ErrorVerificacion('El polígono está fuera del área de estudio (Cuenca del Canal + 10 km).')
    meta = json.loads((MOTOR / 'motor.js').read_text(encoding='utf-8')[len('window.MOTOR='):-1])
    ha = celda * celda / 1e4
    b0, b1 = (b0 > 0) & m, (b1 > 0) & m
    ys = np.unique(ly[m & (ly > 0)])
    return dict(modo=meta['modo'], resolucion_m=celda, anio0=meta['anio0'], anio1=meta['anio1'],
                perdida_ha=round(float((b0 & ~b1).sum() * ha), 1), ganancia_ha=round(float((~b0 & b1).sum() * ha), 1),
                serie_bosque_ha={str(meta['anio0']): round(float(b0.sum() * ha), 1), str(meta['anio1']): round(float(b1.sum() * ha), 1)},
                hansen_perdida_anual={str(2000 + int(y)): round(float(((ly == y) & m).sum() * ha), 1) for y in ys},
                alertas_ha=round(float(((al > 0) & m).sum() * ha), 1), alertas_radd_ha=None,
                frag=_frag(b0, b1, m, celda))


def verificar(geojson: dict, anio0: int | None = None, anio1: int | None = None, usar_ee: bool | None = None) -> dict:
    import datetime as dt
    from motor import gee as G
    from shapely.geometry import shape
    from motor.area import geometria_area
    g4326, utm = normalizar(geojson)
    area_estudio = shape(geometria_area('area_estudio'))
    if not g4326.intersects(area_estudio):
        raise ErrorVerificacion('El polígono está fuera del área de estudio (Cuenca del Canal + 10 km).')
    fuera = 1 - g4326.intersection(area_estudio).area / max(g4326.area, 1e-12)
    anio1 = anio1 or dt.date.today().year - 1
    anio0 = anio0 or max(C.ANIO_BASE, anio1 - 5)
    if anio1 <= anio0:
        raise ErrorVerificacion('El año final debe ser posterior al inicial.')
    usar_ee = G.disponible() if usar_ee is None else usar_ee
    r = _con_ee(g4326, utm, anio0, anio1) if usar_ee else _sin_ee(utm)
    r.setdefault('anio0', anio0); r.setdefault('anio1', anio1)
    area = utm.area / 1e4
    est, txt = _veredicto(r['perdida_ha'], r['ganancia_ha'], r['alertas_ha'], area)
    r.update(area_ha=round(area, 2), fuera_area_pct=round(fuera * 100, 1), neto_ha=round(r['ganancia_ha'] - r['perdida_ha'], 1),
             estado=est, veredicto=txt, kba=_kba(g4326), centroide=[round(g4326.centroid.y, 5), round(g4326.centroid.x, 5)],
             **_contexto(utm))
    return r
