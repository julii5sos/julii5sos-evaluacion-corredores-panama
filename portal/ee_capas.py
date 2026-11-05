"""Conexión opcional con Google Earth Engine.

Si la variable de entorno EE_PROJECT está definida y la librería
`earthengine-api` está instalada y autenticada, `urls_teselas()` devuelve una
URL de teselas por capa. El visor las usa en lugar de las imágenes de
demostración. Sin Earth Engine, devuelve un diccionario vacío y el portal
sigue funcionando con las capas de static/data/capas/.
"""
import os
from functools import lru_cache

import config as C

# capa del visor -> (asset de Earth Engine, parámetros de visualización)
ASSETS = {
    'conectividad': ('projects/conectividad-panama/assets/indice_2025',
                     {'min': 0, 'max': 1, 'palette': [c.lstrip('#') for c in C.PALETA_CONECTIVIDAD]}),
    'conectividad2000': ('projects/conectividad-panama/assets/indice_2000',
                         {'min': 0, 'max': 1, 'palette': [c.lstrip('#') for c in C.PALETA_CONECTIVIDAD]}),
    'cobertura': ('projects/conectividad-panama/assets/cobertura_2025',
                  {'min': 1, 'max': 7, 'palette': [c.lstrip('#') for c in C.PALETA_COBERTURA]}),
}


@lru_cache(maxsize=1)
def urls_teselas() -> dict:
    proyecto = os.environ.get('EE_PROJECT')
    if not proyecto:
        return {}
    try:
        import ee
        ee.Initialize(project=proyecto)
    except Exception as e:  # sin credenciales o sin la librería
        print('Earth Engine no disponible:', e)
        return {}
    urls = {}
    for capa, (asset, vis) in ASSETS.items():
        try:
            urls[capa] = ee.Image(asset).getMapId(vis)['tile_fetcher'].url_format
        except Exception as e:
            print(f'No se pudo publicar {capa} ({asset}):', e)
    return urls
