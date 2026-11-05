"""Descarga las Áreas Clave para la Biodiversidad (KBA) desde el servicio de ArcGIS
y las recorta al área de estudio (Cuenca del Canal + 10 km).

    python -m motor.kba

Servicio: KBAs_LATAM_June2024 (FeatureServer, capa 0). La consulta pide
geometrías en WGS 84 dentro del rectángulo del área de estudio, pagina de 2000
en 2000 y convierte el JSON de Esri a GeoJSON si el servicio no entrega GeoJSON.
"""
from __future__ import annotations

import json

import geopandas as gpd
import requests
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.geometry.polygon import orient

import config as C
from motor.area import geometria_area

URL = 'https://services1.arcgis.com/lDFzr3JyGEn5Eymu/arcgis/rest/services/KBAs_LATAM_June2024/FeatureServer/0/query'


def _esri_a_shapely(geom: dict):
    """Polígono Esri (rings) a shapely: anillos horarios = exteriores, antihorarios = huecos."""
    exteriores, huecos = [], []
    for ring in geom.get('rings', []):
        if len(ring) < 4:
            continue
        p = Polygon(ring)
        (huecos if p.exterior.is_ccw else exteriores).append(p)
    polys = []
    for e in exteriores:
        hs = [h.exterior.coords for h in huecos if e.contains(h.representative_point())]
        polys.append(orient(Polygon(e.exterior.coords, hs)))
    return MultiPolygon(polys).buffer(0) if len(polys) > 1 else (polys[0].buffer(0) if polys else None)


def descargar(timeout: int = 60) -> gpd.GeoDataFrame:
    area = shape(geometria_area('area_estudio'))
    xmin, ymin, xmax, ymax = area.bounds
    base = dict(where='1=1', outFields='*', returnGeometry='true', outSR=4326,
                geometry=f'{xmin},{ymin},{xmax},{ymax}', geometryType='esriGeometryEnvelope',
                inSR=4326, spatialRel='esriSpatialRelIntersects', resultRecordCount=2000)
    feats, offset = [], 0
    while True:
        r = requests.get(URL, params=base | dict(f='geojson', resultOffset=offset), timeout=timeout)
        datos = r.json()
        if 'error' in datos or datos.get('type') != 'FeatureCollection':   # sin soporte GeoJSON
            r = requests.get(URL, params=base | dict(f='json', resultOffset=offset), timeout=timeout)
            datos = r.json()
            if 'error' in datos:
                raise RuntimeError(f"ArcGIS respondió con error: {datos['error']}")
            lote = [dict(type='Feature', properties=f['attributes'], geometry=_esri_a_shapely(f['geometry']).__geo_interface__)
                    for f in datos.get('features', []) if f.get('geometry')]
            mas = datos.get('exceededTransferLimit', False)
        else:
            lote = datos['features']
            mas = datos.get('properties', {}).get('exceededTransferLimit', False) or datos.get('exceededTransferLimit', False)
        feats += lote
        if not mas or not lote:
            break
        offset += len(lote)
    if not feats:
        return gpd.GeoDataFrame(geometry=[], crs=4326)
    gdf = gpd.GeoDataFrame.from_features(feats, crs=4326)
    gdf['geometry'] = gdf.geometry.buffer(0)
    gdf = gdf[gdf.intersects(area)].copy()
    gdf['geometry'] = gdf.geometry.intersection(area)
    gdf['area_ha_en_estudio'] = gdf.to_crs(32617).area / 10_000
    return gdf


def guardar() -> int:
    gdf = descargar()
    destino = C.DATOS_SALIDA / 'kba_canal.geojson'
    gdf.to_file(destino, driver='GeoJSON')
    print(f'{len(gdf)} KBA en el área de estudio · campos: {list(gdf.columns)}')
    return len(gdf)


if __name__ == '__main__':
    guardar()
