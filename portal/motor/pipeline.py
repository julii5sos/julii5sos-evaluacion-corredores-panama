"""Cadena completa del motor para la Cuenca del Canal + 10 km.

    python ejecutar_motor.py            # con Earth Engine (EE_PROJECT definido)
    python ejecutar_motor.py --demo     # con las capas de demostración, sin Earth Engine

Pasos
  1. Área de estudio y subcuencas                       (motor.area)
  2. KBA desde ArcGIS                                   (motor.kba)
  3. Insumos en la rejilla UTM 30 m                     (Earth Engine o demo)
     bosque año base / año actual, integridad estructural, estabilidad topográfica,
     proximidad riparia, pérdida/ganancia, riesgo, alertas Sentinel-1
  4. CONNECT con ventana móvil (año base y actual)      (motor.fragstats)
  5. ERI = 0,35·E + 0,25·C + 0,20·T + 0,20·R            (config.ERI_PESOS)
  6. Pérdida de conectividad = caída de CONNECT; prioridades de intervención
  7. Estadísticas por subcuenca (LPI, CONNECT, ED, ENN, ERI, pérdida, ganancia, riesgo, KBA)
  8. Salidas: GeoTIFF + PNG para el visor + static/data/motor/motor.js
"""
from __future__ import annotations

import datetime as dt
import io
import json
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

import config as C
from motor import fragstats
from motor.area import construir as construir_area, geometria_area

SALIDA = C.DATOS_SALIDA / 'motor'
UTM = 'EPSG:32617'


# ------------------------------------------------------------------ utilidades
def _rasterizar(geojson_geom: dict, transform, shape) -> np.ndarray:
    import rasterio.features
    from rasterio.transform import Affine
    from pyproj import Transformer
    from shapely.geometry import shape as shp
    from shapely.ops import transform as tr
    t = Transformer.from_crs(4326, 32617, always_xy=True).transform
    g = tr(t, shp(geojson_geom))
    return rasterio.features.rasterize([(g, 1)], out_shape=shape, transform=Affine(*transform), dtype='uint8').astype(bool)


def _norm(a, lo=None, hi=None):
    lo = np.nanpercentile(a, 2) if lo is None else lo
    hi = np.nanpercentile(a, 98) if hi is None else hi
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)


# ------------------------------------------------------------------ insumos
def insumos_ee(anio0: int, anio1: int, escala: int = 30) -> dict:
    """Descarga los insumos desde Earth Engine a la rejilla UTM del área de estudio."""
    import ee
    from motor import gee as G
    G.iniciar()
    region = G.aoi()
    img = ee.Image.cat(
        G.bosque_anual(anio0).rename('bosque0'),
        G.bosque_anual(anio1).rename('bosque1'),
        G.estructura(anio1),
        G.topografia(anio1),
        G.riparia(),
        G.hansen().select('lossyear'),
        G.modelo_riesgo().unmask(0),
        G.alertas_s1().unmask(0),
        G.cobertura_anual(anio1).select('clase'),
    )
    d = G.descargar(img.clip(region), geometria_area('area_estudio'), escala)
    d['escala'] = escala
    return d


def insumos_demo(anio0: int, anio1: int, escala: int = 90) -> dict:
    """Construye insumos plausibles a partir de las capas de demostración (sin Earth Engine)."""
    from pyproj import Transformer
    from motor.gee import grilla
    z = np.load(C.DATOS_SALIDA / 'demo_rasters.npz')
    W, N, RES = float(z['W']), float(z['N']), float(z['RES'])
    x0, y1, ancho, alto = grilla(geometria_area('area_estudio'), escala)
    xs = x0 + (np.arange(ancho) + .5) * escala
    ys = y1 - (np.arange(alto) + .5) * escala
    X, Y = np.meshgrid(xs, ys)
    lon, lat = Transformer.from_crs(32617, 4326, always_xy=True).transform(X, Y)
    fi = np.clip(((N - lat) / RES).astype(int), 0, z['cls'].shape[0] - 1)
    co = np.clip(((lon - W) / RES).astype(int), 0, z['cls'].shape[1] - 1)
    cls = z['cls'][fi, co]
    b1 = np.isin(cls, [1, 2, 3])
    ly = z['ly'][fi, co]
    rng = np.random.default_rng(3)
    # bosque en el año base = bosque 2000 sin la pérdida previa a anio0
    b0 = z['f00'][fi, co].astype(bool) & ~((ly > 0) & (ly <= anio0 - 2000))
    # regeneración simulada: parte del bosque secundario actual no era bosque en el año base
    rg = ndi.gaussian_filter(rng.standard_normal(cls.shape), 2); regen = (cls == 2) & (rg > np.percentile(rg, 80))
    b0 = b0 & ~regen
    ruido = ndi.gaussian_filter(rng.standard_normal(cls.shape), 3)
    estructura = np.where(cls == 1, 0.8, np.where(cls == 2, 0.55, np.where(cls == 3, 0.5, 0.1))) + 0.08 * ruido
    relieve = ndi.gaussian_filter(rng.standard_normal(cls.shape), 18)
    pend = _norm(np.abs(np.gradient(relieve)[0]) + np.abs(np.gradient(relieve)[1]))
    topo = 1 - pend * (1 - b1 * 0.85)
    cauces = (ndi.gaussian_filter(rng.standard_normal(cls.shape), 2) > 2.1) | (cls == 7)
    dist = ndi.distance_transform_edt(~cauces) * escala
    rip = 1 - np.clip(dist / 1000, 0, 1)
    borde = ndi.distance_transform_edt(b1) * escala
    riesgo = np.where(b1, np.clip(1 - borde / 1500, 0, 1) * (0.4 + 0.6 * _norm(ruido)), 0)
    alerta = (ly >= (anio1 - 2000 - 1)) & z['f00'][fi, co].astype(bool)
    return dict(bosque0=b0.astype(np.float32), bosque1=b1.astype(np.float32),
                estructura=np.clip(estructura, 0, 1).astype(np.float32), topografia=topo.astype(np.float32),
                riparia=rip.astype(np.float32), lossyear=ly.astype(np.float32),
                riesgo=riesgo.astype(np.float32), alerta_s1=alerta.astype(np.float32),
                clase=np.select([cls == 1, cls == 2, cls == 3, cls == 4, cls == 5, cls == 6, cls == 7],
                                [1, 1, 1, 2, 4, 6, 0], 7).astype(np.float32),
                _transform=(escala, 0.0, float(x0), 0.0, -escala, float(y1)), escala=escala)


# ------------------------------------------------------------------ cálculo
def calcular(ins: dict, anio0: int, anio1: int) -> dict:
    escala = ins['escala']
    shape = ins['bosque1'].shape
    valido = _rasterizar(geometria_area('area_estudio'), ins['_transform'], shape)
    cuenca = _rasterizar(geometria_area('cuenca'), ins['_transform'], shape)
    b0 = (ins['bosque0'] > 0.5) & valido
    b1 = (ins['bosque1'] > 0.5) & valido

    print('· CONNECT con ventana móvil (año base y actual)…')
    con0 = fragstats.connect_ventana(b0, valido, escala, C.CONNECT_VENTANA_M, max(300, escala * 4), C.CONNECT_UMBRAL_M)
    con1 = fragstats.connect_ventana(b1, valido, escala, C.CONNECT_VENTANA_M, max(300, escala * 4), C.CONNECT_UMBRAL_M)
    c0n, c1n = con0 / 100, con1 / 100

    P = C.ERI_PESOS
    E = np.nan_to_num(ins['estructura']); T = np.nan_to_num(ins['topografia']); R = np.nan_to_num(ins['riparia'])
    eri = P['estructura'] * E + P['conectividad'] * np.nan_to_num(c1n) + P['topografia'] * T + P['riparia'] * R
    eri[~valido] = np.nan
    lo, hi = C.ERI_CORTES
    eri_clase = np.where(eri > hi, 3, np.where(eri >= lo, 2, 1)).astype(np.uint8)
    eri_clase[~valido] = 0

    perdida_con = np.nan_to_num(c0n - c1n)                 # caída de CONNECT (0–1)
    perdida_bosque = b0 & ~b1
    ganancia_bosque = ~b0 & b1
    riesgo = np.nan_to_num(ins['riesgo'])
    alerta = np.nan_to_num(ins['alerta_s1']) > 0.5

    # Prioridades: 1 proteger · 2 restaurar · 3 vigilar · 4 mantener
    restaurable = valido & ~b1 & np.isin(np.nan_to_num(ins['clase']), [2, 4, 5])   # pasto, cultivo, arbusto (DW)
    puntaje_rest = 0.4 * R + 0.3 * (1 - T) + 0.3 * ndi.uniform_filter(b1.astype(float), size=max(3, int(500 / escala)))
    prioridad = np.full(shape, 4, np.uint8)
    prioridad[b1 & (eri >= 0.6) & (riesgo >= np.nanpercentile(riesgo[b1], 75) if b1.any() else False)] = 1
    prioridad[restaurable & (puntaje_rest >= np.nanpercentile(puntaje_rest[restaurable], 70) if restaurable.any() else False)] = 2
    prioridad[(alerta | (perdida_con > C.CAIDA_CONECTIVIDAD)) & valido] = 3
    prioridad[~valido] = 0

    return dict(valido=valido, cuenca=cuenca, b0=b0, b1=b1, con0=con0, con1=con1, eri=eri, eri_clase=eri_clase,
                estructura=E, topografia=T, riparia=R, perdida_con=perdida_con, perdida_bosque=perdida_bosque,
                ganancia_bosque=ganancia_bosque, riesgo=riesgo, alerta=alerta, prioridad=prioridad,
                lossyear=np.nan_to_num(ins['lossyear']), transform=ins['_transform'], escala=escala)


def estadisticas(res: dict, anio0: int, anio1: int) -> dict:
    import geopandas as gpd
    escala = res['escala']; ha = escala * escala / 1e4
    sub = gpd.read_file(C.DATOS_SALIDA / 'subcuencas_canal.geojson')
    unidades = [('cuenca', 'Cuenca del Canal', geometria_area('cuenca')),
                ('area', 'Cuenca + 10 km', geometria_area('area_estudio'))]
    unidades += [(r.id, r.nombre, r.geometry.__geo_interface__) for r in sub.itertuples()]
    kba = None
    if (C.DATOS_SALIDA / 'kba_canal.geojson').exists():
        kba_g = gpd.read_file(C.DATOS_SALIDA / 'kba_canal.geojson')
        if len(kba_g):
            kba = _rasterizar(kba_g.union_all().__geo_interface__, res['transform'], res['b1'].shape)
    out = {}
    for uid, nombre, geom in unidades:
        m = _rasterizar(geom, res['transform'], res['b1'].shape) & res['valido']
        if m.sum() < 4:
            continue
        f0 = fragstats.metricas(res['b0'], m, escala, C.CONNECT_UMBRAL_M)
        f1 = fragstats.metricas(res['b1'], m, escala, C.CONNECT_UMBRAL_M)
        e = res['eri'][m]
        d = dict(nombre=nombre, area_ha=round(float(m.sum() * ha)),
                 frag={str(anio0): {k: f0.get(k) for k in ('LPI', 'CONNECT', 'ED', 'ENN_MN', 'n_parches', 'bosque_pct')},
                       str(anio1): {k: f1.get(k) for k in ('LPI', 'CONNECT', 'ED', 'ENN_MN', 'n_parches', 'bosque_pct')}},
                 eri=round(float(np.nanmean(e)), 3),
                 eri_clases={k: round(float(np.mean(res['eri_clase'][m] == v) * 100), 1) for k, v in (('baja', 1), ('media', 2), ('alta', 3))},
                 perdida_ha=round(float((res['perdida_bosque'] & m).sum() * ha)),
                 ganancia_ha=round(float((res['ganancia_bosque'] & m).sum() * ha)),
                 alertas_ha=round(float((res['alerta'] & m).sum() * ha), 1),
                 riesgo_medio=round(float(np.mean(res['riesgo'][m & res['b1']])) if (m & res['b1']).any() else 0, 3),
                 perdida_conectividad_ha=round(float(((res['perdida_con'] > C.CAIDA_CONECTIVIDAD) & m).sum() * ha)),
                 prioridad_ha={C.PALETA_PRIORIDAD[k][0]: round(float(((res['prioridad'] == k) & m).sum() * ha)) for k in (1, 2, 3)},
                 hansen_perdida_anual={str(2000 + y): round(float(((res['lossyear'] == y) & m).sum() * ha), 1)
                                       for y in range(1, 26)})
        if kba is not None:
            d['kba_ha'] = round(float((kba & m).sum() * ha))
        out[uid] = d
    return out


# ------------------------------------------------------------------ salidas
def _png(arr: np.ndarray, colores, transform, nombre: str, alpha=None) -> list:
    """Reproyecta a Web Mercator, colorea y guarda PNG. Devuelve los límites [[S,W],[N,E]]."""
    import rasterio
    from rasterio.transform import Affine
    from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
    from PIL import Image
    src_t = Affine(*transform)
    h, w = arr.shape
    dst_t, dw, dh = calculate_default_transform(UTM, 'EPSG:3857', w, h, *rasterio.transform.array_bounds(h, w, src_t))
    dst = np.full((dh, dw), np.nan, np.float32)
    reproject(arr.astype(np.float32), dst, src_transform=src_t, src_crs=UTM, dst_transform=dst_t,
              dst_crs='EPSG:3857', resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    rgba = colores(dst)
    if alpha is not None:
        rgba[..., 3] = np.where(np.isnan(dst), 0, rgba[..., 3])
    Image.fromarray(rgba, 'RGBA').save(SALIDA / f'{nombre}.png', optimize=True)
    l, b, r, t = rasterio.transform.array_bounds(dh, dw, dst_t)
    W, S, E, N = transform_bounds('EPSG:3857', 'EPSG:4326', l, b, r, t)
    return [[S, W], [N, E]]


def _hex(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _rampa(paleta):
    st = np.array([_hex(c) for c in paleta], float)

    def f(a):   # clases sólidas (sin degradado), una por color de la paleta
        i = np.clip(np.floor(np.clip(np.nan_to_num(a), 0, 1) * len(paleta)).astype(int), 0, len(paleta) - 1)
        rgb = st[i]
        out = np.zeros(a.shape + (4,), np.uint8)
        out[..., :3] = rgb.astype(np.uint8)
        out[..., 3] = np.where(np.isnan(a), 0, 235)
        return out
    return f


def _eri_clases(a):
    """ERI en 5 clases sólidas con cortes en 0,25 · 0,40 · 0,60 · 0,75."""
    st = np.array([_hex(c) for c in C.PALETA_ERI], np.uint8)
    i = np.digitize(np.nan_to_num(a), [0.25, C.ERI_CORTES[0], 0.60, C.ERI_CORTES[1]])
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., :3] = st[i]
    out[..., 3] = np.where(np.isnan(a), 0, 235)
    return out


def _categorias(mapa: dict):
    def f(a):
        out = np.zeros(a.shape + (4,), np.uint8)
        for v, (col, al) in mapa.items():
            out[np.nan_to_num(a, nan=-1) == v] = _hex(col) + [al]
        return out
    return f


def guardar(res: dict, stats: dict, anio0: int, anio1: int, modo: str):
    import rasterio
    from rasterio.transform import Affine
    SALIDA.mkdir(parents=True, exist_ok=True)
    perfil = dict(driver='GTiff', height=res['b1'].shape[0], width=res['b1'].shape[1], count=1,
                  crs=UTM, transform=Affine(*res['transform']), compress='deflate')
    for nombre, arr, dtype in [('eri', res['eri'], 'float32'), ('connect_actual', res['con1'], 'float32'),
                               ('connect_base', res['con0'], 'float32'), ('perdida_conectividad', res['perdida_con'], 'float32'),
                               ('prioridad', res['prioridad'], 'uint8'), ('riesgo', res['riesgo'], 'float32'),
                               ('bosque_base', res['b0'], 'uint8'), ('bosque_actual', res['b1'], 'uint8'),
                               ('alertas', res['alerta'], 'uint8'), ('lossyear', res['lossyear'], 'uint8'),
                               ('valido', res['valido'], 'uint8')]:
        with rasterio.open(SALIDA / f'{nombre}.tif', 'w', dtype=dtype, nodata=(np.nan if dtype == 'float32' else None), **perfil) as dst:
            dst.write(arr.astype(dtype), 1)

    v = res['valido']
    def m(a):
        a = a.astype(np.float32).copy(); a[~v] = np.nan; return a
    capas = {}
    capas['eri'] = dict(nombre='Índice de Resiliencia Ecológica (ERI)', tipo='rampa', paleta=C.PALETA_ERI, rango=[0, 1], cortes=[0, 0.25, C.ERI_CORTES[0], 0.60, C.ERI_CORTES[1], 1],
                        bounds=_png(m(res['eri']), _eri_clases, res['transform'], 'eri'))
    capas['connect'] = dict(nombre=f'Conectividad de parches (CONNECT {anio1})', tipo='rampa', paleta=C.PALETA_CONECTIVIDAD, rango=[0, 100],
                            bounds=_png(m(res['con1'] / 100), _rampa(C.PALETA_CONECTIVIDAD), res['transform'], 'connect'))
    capas['perdida_conectividad'] = dict(nombre=f'Pérdida de conectividad {anio0}–{anio1}', tipo='rampa', paleta=['#fff3cf', '#fabc20', '#d0442c'], rango=[0, 0.5],
                                         bounds=_png(np.where(res['perdida_con'] > 0.02, np.clip(res['perdida_con'] / 0.5, 0, 1), np.nan), _rampa(['#fff3cf', '#fabc20', '#d0442c']), res['transform'], 'perdida_conectividad'))
    capas['riesgo'] = dict(nombre='Riesgo de pérdida de bosque', tipo='rampa', paleta=['#fff3cf', '#f2a541', '#d0442c'], rango=[0, 1],
                           bounds=_png(np.where(res['b1'] & v, res['riesgo'], np.nan), _rampa(['#fff3cf', '#f2a541', '#d0442c']), res['transform'], 'riesgo'))
    capas['prioridad'] = dict(nombre='Prioridad de intervención', tipo='categorias',
                              clases=[[C.PALETA_PRIORIDAD[k][0], C.PALETA_PRIORIDAD[k][1]] for k in (1, 2, 3)],
                              bounds=_png(m(res['prioridad']), _categorias({k: (C.PALETA_PRIORIDAD[k][1], 220) for k in (1, 2, 3)}), res['transform'], 'prioridad'))
    cambio = np.where(res['perdida_bosque'], 1, np.where(res['ganancia_bosque'], 2, np.nan))
    capas['cambio'] = dict(nombre=f'Pérdida y ganancia de bosque {anio0}–{anio1}', tipo='categorias',
                           clases=[['Pérdida', '#d0442c'], ['Ganancia', '#77cc09']],
                           bounds=_png(cambio, _categorias({1: ('#d0442c', 255), 2: ('#77cc09', 255)}), res['transform'], 'cambio'))
    capas['alertas'] = dict(nombre='Alertas recientes (Sentinel-1)', tipo='categorias', clases=[['Alerta', '#d0442c']],
                            bounds=_png(np.where(res['alerta'] & v, 1, np.nan), _categorias({1: ('#d0442c', 255)}), res['transform'], 'alertas'))
    for k, nombre in (('estructura', 'ERI · Integridad estructural'), ('topografia', 'ERI · Estabilidad topográfica'), ('riparia', 'ERI · Proximidad riparia')):
        capas[k] = dict(nombre=nombre, tipo='rampa', paleta=C.PALETA_ERI, rango=[0, 1],
                        bounds=_png(m(res[k]), _rampa(C.PALETA_ERI), res['transform'], k))

    vector = {}
    for n in ('area_estudio', 'subcuencas_canal', 'kba_canal'):
        p = C.DATOS_SALIDA / f'{n}.geojson'
        if p.exists():
            vector[n] = json.loads(p.read_text(encoding='utf-8'))
    meta = dict(generado=dt.datetime.now().isoformat(timespec='minutes'), modo=modo, anio0=anio0, anio1=anio1,
                escala_m=res['escala'], pesos=C.ERI_PESOS, cortes=C.ERI_CORTES, connect_umbral_m=C.CONNECT_UMBRAL_M,
                capas={k: dict(v, url=f'static/data/motor/{k}.png') for k, v in capas.items()}, vector=vector, stats=stats)
    (SALIDA / 'motor.js').write_text('window.MOTOR=' + json.dumps(meta, ensure_ascii=False) + ';', encoding='utf-8')
    (SALIDA / 'estadisticas_motor.json').write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')
    _rejilla_navegador(res, anio0, anio1)
    print('· Salidas en', SALIDA)


def _rejilla_navegador(res: dict, anio0: int, anio1: int, celda_obj: int = 180):
    """Rejilla compacta (UTM 17N) para verificar polígonos en el navegador cuando no hay servidor.
    Banderas por celda: 1 válido · 2 bosque base · 4 bosque actual · 8 alerta · 16 pérdida de conectividad."""
    import base64
    f = max(1, int(round(celda_obj / res['escala'])))
    def red(a, modo='max'):
        h, w = a.shape[0] // f * f, a.shape[1] // f * f
        b = a[:h, :w].reshape(h // f, f, w // f, f)
        return b.max(axis=(1, 3)) if modo == 'max' else np.nanmean(b, axis=(1, 3))
    def frac(a):
        return red(a.astype(np.float32), 'mean') >= 0.5
    flags = (frac(res['valido']) * 1 | frac(res['b0']) * 2 | frac(res['b1']) * 4
             | red(res['alerta'].astype(np.uint8)) * 8 | frac(res['perdida_con'] > C.CAIDA_CONECTIVIDAD) * 16).astype(np.uint8)
    eri = np.nan_to_num(red(res['eri'], 'mean'), nan=0)
    eri8 = np.where(flags & 1, np.clip(eri * 254, 0, 254) + 1, 0).astype(np.uint8)
    pri = res['prioridad']; h, w = pri.shape[0] // f * f, pri.shape[1] // f * f
    pri_r = pri[:h, :w].reshape(h // f, f, w // f, f).transpose(0, 2, 1, 3).reshape(h // f, w // f, f * f)
    moda = np.apply_along_axis(lambda v: np.bincount(v, minlength=5)[1:4].argmax() + 1 if (v > 0).any() and np.isin(v, [1, 2, 3]).any() else 4, 2, pri_r).astype(np.uint8)
    b64 = lambda a: base64.b64encode(a.tobytes()).decode()
    t = res['transform']
    datos = dict(x0=t[2], y1=t[5], celda=res['escala'] * f, w=int(flags.shape[1]), h=int(flags.shape[0]),
                 anio0=anio0, anio1=anio1, flags=b64(flags), eri=b64(eri8), prioridad=b64(moda),
                 cortes=C.ERI_CORTES)
    (SALIDA / 'motor_rejilla.js').write_text('window.MOTOR_REJILLA=' + json.dumps(datos) + ';', encoding='utf-8')


def ejecutar(demo: bool = False, anio0: int | None = None, anio1: int | None = None, escala: int | None = None):
    anio0 = anio0 or C.ANIO_BASE
    anio1 = anio1 or dt.date.today().year - 1
    print('1. Área de estudio…', construir_area())
    try:
        from motor import kba
        print('2. KBA…'); kba.guardar()
    except Exception as e:
        print('2. KBA no descargadas:', e)
    print('3. Insumos', 'de demostración' if demo else 'desde Earth Engine', '…')
    ins = insumos_demo(anio0, anio1, escala or 90) if demo else insumos_ee(anio0, anio1, escala or 30)
    print('4–6. Conectividad, ERI, pérdida de conectividad y prioridades…')
    res = calcular(ins, anio0, anio1)
    print('7. Estadísticas por subcuenca…')
    stats = estadisticas(res, anio0, anio1)
    guardar(res, stats, anio0, anio1, 'demo' if demo else 'earth-engine')
    return stats
