"""Prepara las capas y estadísticas del portal.

Ejecutar una vez (o cada vez que cambien los insumos):
    python preparar_datos.py

Entradas (carpeta datos_entrada/):
    Cuencas_Hidrograficas_250k.zip   -> capa real de cuencas
    Subcuencas_Canal_Panama.zip      -> capa real de subcuencas del Canal
    paises_natural_earth.geojson     -> límites internacionales (contexto)

Salidas (carpeta static/data/):
    capas/*.png          rásters de demostración en Web Mercator
    datos.js             window.D con geometrías, estadísticas y rutas de capas
    estadisticas.json    estadísticas por unidad, para el motor de análisis

Las capas de cobertura, pérdida, conectividad, núcleos y corredores son
SINTÉTICAS (demostración) hasta reemplazarlas por los productos de Earth Engine.
"""
import json, base64, io, math, zipfile, tempfile
from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, mapping, box
from shapely.ops import unary_union
from shapely.validation import make_valid
from scipy import ndimage as ndi
from rasterio import features
from rasterio.transform import from_origin
from skimage.graph import route_through_array
from PIL import Image

import config as C

OUT = C.DATOS_SALIDA
(OUT / 'capas').mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)

def leer_shp_zip(nombre):
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(C.DATOS_ENTRADA / nombre) as z:
        z.extractall(tmp)
    shp = next(tmp.rglob('*.shp'))
    return gpd.read_file(shp)

# ---------- vectores reales ----------
cue = leer_shp_zip('Cuencas_Hidrograficas_250k.zip').to_crs(4326)
cue = cue[cue.Cod_Cuen_H > 0].copy()
cue['geometry'] = cue.geometry.buffer(0)
sub = leer_shp_zip('Subcuencas_Canal_Panama.zip').to_crs(4326)
sub['grupo'] = sub.NOMBRE.str.strip()
fix = {'Ro Piedras': 'Río Piedras', 'Rio Chagres': 'Río Chagres'}
sub['nombre'] = sub.SUBCUENC_2.str.strip().replace(fix)
sub['geometry'] = sub.geometry.buffer(0)
lakes = sub[sub.grupo == 'Lagos']
# disolver por nombre (Lago Miraflores aparece dos veces)
sub = sub.sort_values('HECTAREAS', ascending=False)
subd = sub.dissolve(by='nombre', aggfunc={'grupo': 'first', 'HECTAREAS': 'sum'}).reset_index()
subd = subd[subd.HECTAREAS >= 5].reset_index(drop=True)

countries = gpd.read_file(C.DATOS_ENTRADA / 'paises_natural_earth.geojson')
countries['geometry'] = countries.geometry.apply(make_valid).buffer(0)

# ---------- grilla ----------
W_, E_, S_, N_ = -83.1, -77.1, 7.15, 9.7
RES = 0.003
nx, ny = int(round((E_ - W_) / RES)), int(round((N_ - S_) / RES))
T = from_origin(W_, N_, RES, RES)
lons = W_ + (np.arange(nx) + .5) * RES
lats = N_ - (np.arange(ny) + .5) * RES
LON, LAT = np.meshgrid(lons, lats)

mask = features.rasterize([(g, 1) for g in cue.geometry], (ny, nx), transform=T).astype(bool)
water = features.rasterize([(g, 1) for g in lakes.geometry], (ny, nx), transform=T).astype(bool) & mask
land = mask & ~water

def nz(sig):
    a = ndi.gaussian_filter(rng.standard_normal((ny, nx)), sig)
    return (a - a.mean()) / a.std()

def g2(x0, y0, s):
    return np.exp(-(((LON - x0) / s) ** 2 + ((LAT - y0) / s) ** 2))

dist = ndi.distance_transform_edt(mask)
dn = np.clip(dist / 60, 0, 1)
spine_lat = np.interp(LON, [-83, -81.5, -80.6, -80, -79.6, -78.8, -78, -77.2], [8.75, 8.65, 8.6, 8.85, 9.1, 9.15, 8.6, 8.3])
carib = (LAT > spine_lat).astype(float)

sbox = lambda m: ndi.gaussian_filter(m.astype(float), 22)
Sx = (0.55 * dn + 0.45 * nz(28) + 0.28 * nz(7) + 0.15 * nz(2) + 0.35 * carib
      + 0.55 * sbox((LON > -78.6) & (LAT < 8.9))                       # Darién
      + 0.45 * sbox((LON > -79.3) & (LAT > 9.15))                    # Guna Yala
      + 0.5 * g2(-79.6, 9.15, 0.18) + 0.4 * g2(-79.35, 9.32, 0.2)  # Soberanía / Chagres
      + 0.45 * g2(-82.5, 8.85, 0.35) + 0.35 * g2(-81.6, 8.75, 0.3)  # La Amistad / cordillera
      - 0.85 * sbox((LON > -80.95) & (LON < -80.0) & (LAT < 8.2) & (LAT > 7.45))  # Azuero
      - 0.55 * sbox((LON < -81.6) & (LAT < 8.45))                      # tierras bajas de Chiriquí
      - 0.45 * sbox((LON > -80.6) & (LON < -79.9) & (LAT < 8.65) & (LAT > 8.2))  # Coclé
      - 0.35 * g2(-79.1, 9.05, 0.25))                              # Chepo
urb = (g2(-79.52, 9.0, 0.09) * 1.2 + g2(-79.75, 8.9, 0.07) + g2(-79.9, 9.35, 0.05)
       + g2(-82.43, 8.43, 0.04) + g2(-80.45, 8.1, 0.03) + g2(-80.98, 8.1, 0.03) + g2(-80.43, 7.95, 0.03))
Sx = Sx - 1.4 * urb
vals = Sx[land]
q = lambda p: np.quantile(vals, p)

forest00 = land & (Sx > q(0.32))
# pérdida 2001-2025: borde del bosque con presión en la frontera agrícola
front = (0.08 + 1.8 * g2(-78.75, 9.0, 0.35) + 1.4 * g2(-78.0, 8.35, 0.35) + 1.0 * g2(-81.2, 8.6, 0.35)
         + 0.8 * g2(-79.95, 8.75, 0.25))
pl = np.clip((q(0.42) - Sx) / (q(0.42) - q(0.32)), 0, 1) * front * 0.55
pls = ndi.gaussian_filter(pl, 3)
loss = forest00 & (nz(1.8) > 2.4 - 2.6 * pls)
loss |= forest00 & (rng.random((ny, nx)) < pls * 0.12)
loss &= forest00
years = np.arange(2001, 2026)
w = np.exp(-((years - 2016) / 6.5) ** 2) + 0.35
ly = np.zeros((ny, nx), np.int16)
ly[loss] = rng.choice(years, loss.sum(), p=w / w.sum())
forest = forest00 & ~loss

# clases: 1 bosque maduro 2 bosque secundario 3 manglar 4 pastos 5 cultivos 6 urbano 7 agua
cls = np.zeros((ny, nx), np.uint8)
fv = Sx[forest]
cls[forest & (Sx > np.quantile(fv, 0.27))] = 1
cls[forest & (Sx <= np.quantile(fv, 0.27))] = 2
nf = land & ~forest
crop = nz(5) > 0.55
cls[nf] = 4
cls[nf & crop & (carib < 1)] = 5
coast = mask & (dist <= 3) & (carib < 1) & (nz(4) > 0.2) & ~(urb > .25)
cls[coast & land] = 3
cls[land & (urb * (1 + 0.9 * nz(1.5)) > 0.45)] = 6
cls[water] = 7
forest = np.isin(cls, [1, 2, 3])
forest00c = forest | loss

def conn(f):
    f = f.astype(float)
    return (0.15 * ndi.gaussian_filter(f, 3) + 0.5 * ndi.gaussian_filter(f, 9) + 0.35 * ndi.gaussian_filter(f, 25)) * mask
Cn = conn(forest); C0 = conn(forest00c)
ref = np.sort(C0[land])
def rank(a): return np.searchsorted(ref, a) / len(ref)
Cn = rank(Cn) ** 1.6; C0 = rank(C0) ** 1.6
Cn[~land] = 0; C0[~land] = 0

core = (cls == 1) & (ndi.gaussian_filter((cls == 1).astype(float), 3) > 0.93) & (Cn > 0.55)
lab, n = ndi.label(core)
sizes = ndi.sum(core, lab, range(1, n + 1))
keep = np.zeros(n + 1, bool); keep[1:] = sizes >= 60
core = keep[lab]
lab, n = ndi.label(core)
sizes = ndi.sum(core, lab, range(1, n + 1))

# ---------- corredores (camino de menor costo entre núcleos) ----------
resist = np.full((ny, nx), 400.0)
for c, r in {1: 1, 2: 4, 3: 6, 4: 35, 5: 45, 6: 300, 7: 120}.items():
    resist[cls == c] = r
cs = 4
rs = resist[::cs, ::cs]
order = np.argsort(sizes)[::-1][:26]
cents = []
for i in order:
    yy, xx = np.nonzero(lab == i + 1)
    k = np.argmin((yy - yy.mean()) ** 2 + (xx - xx.mean()) ** 2)
    cents.append((yy[k], xx[k], sizes[i]))
pairs = set()
for a, (ya, xa, _) in enumerate(cents):
    d = [(math.hypot(ya - yb, xa - xb), b) for b, (yb, xb, _) in enumerate(cents) if b != a]
    for _, b in sorted(d)[:2]:
        pairs.add(tuple(sorted((a, b))))
lines = []
for a, b in sorted(pairs):
    ya, xa, _ = cents[a]; yb, xb, _ = cents[b]
    path, cost = route_through_array(rs, (ya // cs, xa // cs), (yb // cs, xb // cs), fully_connected=True, geometric=True)
    p = np.array(path) * cs + cs / 2
    pi = np.clip(p.astype(int), 0, [ny - 1, nx - 1])
    out = ~core[pi[:, 0], pi[:, 1]]
    if out.sum() < 3: continue
    idx = np.nonzero(out)[0]; lo, hi = max(idx[0] - 3, 0), min(idx[-1] + 4, len(p))
    p = p[lo:hi]; path = path[lo:hi]
    coords = [(W_ + (x + .5) * RES, N_ - (y + .5) * RES) for y, x in p]
    ls = LineString(coords).simplify(0.004)
    pyx = np.array(path) * cs
    cv = Cn[np.clip(pyx[:, 0], 0, ny - 1), np.clip(pyx[:, 1], 0, nx - 1)]
    nonf = 1 - np.isin(cls[np.clip(pyx[:, 0], 0, ny - 1), np.clip(pyx[:, 1], 0, nx - 1)], [1, 2, 3]).mean()
    km = gpd.GeoSeries([ls], crs=4326).to_crs(32617).length.iloc[0] / 1000
    if km < 4: continue
    q_ = 'Alta' if nonf < .2 else ('Media' if nonf < .5 else 'Baja')
    lines.append(dict(geometry=ls, km=round(km, 1), calidad=q_, conectividad=round(float(cv.mean()), 2), brecha=round(float(nonf * 100), 1)))
cor = gpd.GeoDataFrame(lines, crs=4326)
qq = cor.conectividad.rank(pct=True)
cor['calidad'] = np.where(qq > .6, 'Alta', np.where(qq > .25, 'Media', 'Baja'))
cor['id'] = [f'C-{i+1:02d}' for i in range(len(cor))]
print('corredores', len(cor), cor.calidad.value_counts().to_dict())

# ---------- estadísticas ----------
pix_ha = (RES * 111.32 * np.cos(np.radians(LAT))) * (RES * 110.57) * 100
CLS = C.CLASES

def stats(geom, area_ha):
    m = features.rasterize([(geom, 1)], (ny, nx), transform=T, all_touched=True).astype(bool) & mask
    if m.sum() < 3:
        m = ndi.binary_dilation(m, iterations=2) & mask
    pw = pix_ha * m
    tot = pw.sum()
    f = lambda arr: float((pw * arr).sum() / tot)
    fr = [f(cls == i + 1) for i in range(7)]
    lossy = [f(ly == y) * area_ha for y in years]
    w_ = pw[m]
    cn = Cn[m]; c0 = C0[m]
    hist = np.histogram(cn, bins=10, range=(0, 1), weights=w_)[0] / tot * area_ha
    dens = ndi.gaussian_filter(forest.astype(float), 1.5)[m]
    dh = np.histogram(dens, bins=10, range=(0, 1.0001), weights=w_)[0] / tot * area_ha
    labs = np.unique(lab[m & core])
    return dict(
        area=round(area_ha), clases=[round(x * area_ha) for x in fr],
        bosque=round(sum(fr[:3]) * 100, 1), bosque2000=round(f(forest00c) * 100, 1),
        perdida=[round(x) for x in lossy], conn=round(float((cn * w_).sum() / w_.sum()), 3),
        conn2000=round(float((c0 * w_).sum() / w_.sum()), 3), hist=[round(x) for x in hist],
        dens=[round(x) for x in dh], nucleo=round(f(core) * area_ha), nnuc=int((labs > 0).sum()),
        corr=round(float(cor.clip(geom).to_crs(32617).length.sum() / 1000), 1) if len(cor) else 0,
        corrq=[round(float(cor[cor.calidad == k].clip(geom).to_crs(32617).length.sum() / 1000), 1) for k in ('Alta', 'Media', 'Baja')],
        corrids=sorted(cor[cor.intersects(geom)].id.tolist()),
    )

def odd(c): return 'Caribe' if c % 2 else 'Pacífico'
basins = []
for _, r in cue.sort_values('Cod_Cuen_H').iterrows():
    st = stats(r.geometry, r.Area_km2 * 100)
    st.update(id=f'c{int(r.Cod_Cuen_H)}', cod=int(r.Cod_Cuen_H), nombre=r.Nom_Cuen_H.strip(),
              rio=(r.Nom_Rio_Pr or '').strip(), vertiente=odd(int(r.Cod_Cuen_H)))
    basins.append(st)
subs = []
for i, r in subd.iterrows():
    st = stats(r.geometry, r.HECTAREAS)
    st.update(id=f's{i}', nombre=r.nombre, grupo=r.grupo, cuenca='c115')
    subs.append(st)
nat = stats(unary_union(cue.geometry), float(cue.Area_km2.sum() * 100))
nat.update(id='pa', nombre='Panamá')
print('nacional bosque %', nat['bosque'], 'conn', nat['conn'])

# ---------- GeoJSON ----------
def gj(gdf, props, tol):
    g = gdf.copy(); g['geometry'] = g.geometry.simplify(tol, preserve_topology=True)
    feats = []
    for _, r in g.iterrows():
        geo = json.loads(json.dumps(mapping(r.geometry)), parse_float=lambda x: round(float(x), 4))
        feats.append(dict(type='Feature', properties={k: r[k] for k in props}, geometry=geo))
    return dict(type='FeatureCollection', features=feats)
cue['id'] = [f'c{int(c)}' for c in cue.Cod_Cuen_H]
cue['nombre'] = cue.Nom_Cuen_H.str.strip()
subd['id'] = [f's{i}' for i in range(len(subd))]
geo = dict(
    cuencas=gj(cue, ['id', 'nombre'], 0.004),
    subcuencas=gj(subd, ['id', 'nombre', 'grupo'], 0.0012),
    paises=gj(countries.clip(box(-86, 5.5, -75, 11.5)), ['name'], 0.01),
    corredores=gj(cor, ['id', 'km', 'calidad', 'conectividad', 'brecha'], 0.002),
)

# ---------- PNG (remuestreo a Mercator) ----------
def merc(lat): return np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
H = int(ny * 1.0)
my = np.linspace(merc(N_), merc(S_), H)
srcrow = np.clip(((N_ - np.degrees(2 * np.arctan(np.exp(my)) - np.pi / 2)) / RES).astype(int), 0, ny - 1)
def png(rgba, name, scale=1, inline=False):
    a = rgba[srcrow]
    if scale != 1: a = a[::scale, ::scale]
    im = Image.fromarray(a, 'RGBA')
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True)
    (OUT / 'capas' / f'{name}.png').write_bytes(b.getvalue())
    if inline:   # se incrusta para poder leer sus píxeles en el navegador
        return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()
    return f'static/data/capas/{name}.png'

def hexrgb(h): return [int(h[i:i + 2], 16) for i in (1, 3, 5)]
PAL = C.PALETA_COBERTURA
# clases suavizadas para una lectura cartográfica limpia (sin moteado)
def smooth_cls(c, size=5):
    out = c.copy()
    m = ndi.median_filter(c, size=size)
    out[land] = m[land]; out[water] = 7; out[~mask] = 0
    out[land & (out == 0)] = 4; out[land & (out == 7)] = c[land & (out == 7)]
    return out
clsv = smooth_cls(cls)
rgba = np.zeros((ny, nx, 4), np.uint8)
for i, h in enumerate(PAL):
    rgba[clsv == i + 1] = hexrgb(h) + [255]
imgs = {}
imgs['cobertura'] = png(rgba, 'cobertura')

CONN = C.PALETA_CONECTIVIDAD
def connimg(C):
    Cs = ndi.gaussian_filter(C, 2.2)
    k = np.digitize(Cs, [0.2, 0.4, 0.6, 0.8])
    k = ndi.median_filter(k, size=7)
    r = np.zeros((ny, nx, 4), np.uint8)
    for q, h in enumerate(CONN):
        r[(k == q) & land] = hexrgb(h) + [255]
    return r
imgs['conectividad'] = png(connimg(Cn), 'conectividad')
imgs['conectividad2000'] = png(connimg(C0), 'conectividad2000')
cv = ndi.binary_fill_holes(ndi.binary_closing(ndi.binary_opening(core, iterations=2), iterations=3)) & land
r = np.zeros((ny, nx, 4), np.uint8); r[cv] = hexrgb(C.COLOR_NUCLEOS) + [200]
edge = cv & ~ndi.binary_erosion(cv)
r[edge] = hexrgb(C.COLOR_NUCLEOS) + [255]
imgs['nucleos'] = png(r, 'nucleos')
r = np.zeros((ny, nx, 4), np.uint8)
t = np.clip((ly - 2001) / 24, 0, 1)
lc = np.stack([np.interp(t, [0, 1], [hexrgb(C.PERDIDA_RAMPA[0])[k], hexrgb(C.PERDIDA_RAMPA[1])[k]]) for k in range(3)], -1)
r[..., :3] = lc.astype(np.uint8); r[..., 3] = (loss * 255).astype(np.uint8)
imgs['perdida'] = png(r, 'perdida')
r = np.zeros((ny, nx, 4), np.uint8); r[..., 0] = np.where(loss, ly - 2000, 0); r[..., 3] = (loss * 255).astype(np.uint8)
imgs['perdidaidx'] = png(r, 'perdidaidx', inline=True)
f0 = ndi.median_filter(forest00c.astype(np.uint8), size=5).astype(bool) & land
r = np.zeros((ny, nx, 4), np.uint8); r[f0] = hexrgb(C.COLOR_BOSQUE_2000) + [235]
imgs['bosque2000'] = png(r, 'bosque2000')

# rásters de demostración para el motor (modo --demo) y la verificación sin Earth Engine
np.savez_compressed(OUT / 'demo_rasters.npz', cls=cls.astype(np.uint8),
                    ly=np.where(loss, ly - 2000, 0).astype(np.uint8), f00=forest00c,
                    conn=(Cn * 255).astype(np.uint8), W=W_, N=N_, RES=RES)
data = dict(bounds=[[S_, W_], [N_, E_]], geo=geo, imgs=imgs, years=years.tolist(), clases=CLS, pal=PAL,
            nat=nat, cuencas=basins, subcuencas=subs, ramp=CONN, ramp_clases=C.CLASES_CONECTIVIDAD,
            corredores_col=C.CORREDORES, perdida_rampa=C.PERDIDA_RAMPA, nucleos_col=C.COLOR_NUCLEOS)
js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
(OUT / 'datos.js').write_text('window.D=' + js + ';', encoding='utf-8')
est = dict(years=years.tolist(), nat=nat, cuencas=basins, subcuencas=subs,
           corredores=[f['properties'] for f in geo['corredores']['features']])
(OUT / 'estadisticas.json').write_text(json.dumps(est, ensure_ascii=False), encoding='utf-8')
print('datos.js MB', round(len(js) / 1e6, 2), '· capas en', OUT / 'capas')
