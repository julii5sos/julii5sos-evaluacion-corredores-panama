"""Área de estudio: Cuenca Hidrográfica del Canal de Panamá + zona de
amortiguamiento de 10 km. Todos los análisis del motor se recortan a esta área.

Salidas en static/data/:
    area_estudio.geojson   polígono (cuenca + 10 km) y polígono de la cuenca
    subcuencas_canal.geojson subcuencas en WGS 84 con id, nombre y grupo
"""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
from shapely.geometry import mapping

import config as C

UTM = 32617          # WGS 84 / UTM 17N, métrico, para buffers y áreas
BUFFER_M = 10_000


def _leer_zip(nombre: str) -> gpd.GeoDataFrame:
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(C.DATOS_ENTRADA / nombre) as z:
        z.extractall(tmp)
    return gpd.read_file(next(tmp.rglob('*.shp')))


def subcuencas() -> gpd.GeoDataFrame:
    sub = _leer_zip('Subcuencas_Canal_Panama.zip').to_crs(UTM)
    sub['geometry'] = sub.geometry.buffer(0)
    sub['grupo'] = sub['NOMBRE'].str.strip()
    sub['nombre'] = sub['SUBCUENC_2'].str.strip().replace({'Ro Piedras': 'Río Piedras', 'Rio Chagres': 'Río Chagres'})
    sub = sub.dissolve(by='nombre', aggfunc={'grupo': 'first'}).reset_index()
    sub['area_ha'] = sub.area / 10_000
    sub = sub[sub.area_ha >= 5].reset_index(drop=True)
    sub['id'] = [f's{i}' for i in range(len(sub))]
    return sub[['id', 'nombre', 'grupo', 'area_ha', 'geometry']]


def construir(guardar: bool = True) -> dict:
    sub = subcuencas()
    cuenca = sub.union_all().buffer(0)
    area = cuenca.buffer(BUFFER_M)
    g = gpd.GeoDataFrame({'nombre': ['Cuenca del Canal', 'Cuenca del Canal + 10 km']},
                         geometry=[cuenca, area], crs=UTM).to_crs(4326)
    res = dict(
        cuenca_ha=round(cuenca.area / 10_000), area_ha=round(area.area / 10_000),
        bbox=[round(float(v), 4) for v in g.total_bounds],
    )
    if guardar:
        C.DATOS_SALIDA.mkdir(parents=True, exist_ok=True)
        fc = {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'nombre': n, 'tipo': t},
             'geometry': mapping(geom.simplify(0.0003))}
            for n, t, geom in zip(g.nombre, ['cuenca', 'area_estudio'], g.geometry)]}
        (C.DATOS_SALIDA / 'area_estudio.geojson').write_text(json.dumps(fc), encoding='utf-8')
        s4 = sub.to_crs(4326)
        s4['geometry'] = s4.geometry.simplify(0.0002, preserve_topology=True)
        s4['area_ha'] = s4['area_ha'].round(1)
        s4.to_file(C.DATOS_SALIDA / 'subcuencas_canal.geojson', driver='GeoJSON', COORDINATE_PRECISION=5)
    return res


def geometria_area(tipo: str = 'area_estudio') -> dict:
    """GeoJSON (dict) del área de estudio o de la cuenca, para enviarlo a Earth Engine."""
    fc = json.loads((C.DATOS_SALIDA / 'area_estudio.geojson').read_text(encoding='utf-8'))
    return next(f['geometry'] for f in fc['features'] if f['properties']['tipo'] == tipo)


if __name__ == '__main__':
    print(construir())
