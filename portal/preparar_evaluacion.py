"""Prepara los datos de la preevaluación (método del repositorio de corredores) para el visor.

    python preparar_evaluacion.py

No requiere Earth Engine. Genera static/data/evaluacion.js con:
  · corredores y puntos críticos de Almanaque Azul (evaluacion/data/);
  · intersección con corredores para la cuenca, la cuenca + 10 km y cada subcuenca;
  · constantes del método (pesos, umbrales, reglas de prioridad y consistencia,
    clases NDVI, mapa de coincidencia) y leyendas, para mostrarlas sin duplicarlas.
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'evaluacion'))
sys.path.insert(0, str(BASE.parent))

import config as C  # noqa: E402
import metodologia_indice as MI  # noqa: E402
from corredores import (  # noqa: E402
    COLORES_CATEGORIA, ETIQUETAS_CATEGORIA, FUENTE_CORTA, URL_MAPA,
    analizar_interseccion_corredores, cargar_catalogo, cargar_corredores, cargar_puntos_criticos)
from leyendas import LEYENDAS  # noqa: E402
from modos_app import MODOS_ANALISIS  # noqa: E402
from motor.area import geometria_area  # noqa: E402


def main():
    import geopandas as gpd
    unidades = {'cuenca': ('Cuenca del Canal', geometria_area('cuenca')),
                'area': ('Cuenca del Canal + 10 km', geometria_area('area_estudio'))}
    sub = gpd.read_file(C.DATOS_SALIDA / 'subcuencas_canal.geojson')
    for r in sub.itertuples():
        unidades[r.id] = (r.nombre, r.geometry.__geo_interface__)
    inter = {}
    for uid, (nombre, geo) in unidades.items():
        res = analizar_interseccion_corredores(json.loads(json.dumps(geo)))
        res['nombre'] = nombre
        inter[uid] = res
    datos = dict(
        corredores=cargar_corredores(), puntos=cargar_puntos_criticos(), catalogo=cargar_catalogo(),
        colores=COLORES_CATEGORIA, etiquetas=ETIQUETAS_CATEGORIA, fuente=FUENTE_CORTA, url=URL_MAPA,
        interseccion=inter, modos=MODOS_ANALISIS,
        metodo=dict(
            periodos=MI.PERIODOS_ANALISIS, pesos=MI.PESOS_INDICE, puntaje_maximo=MI.PUNTAJE_MAXIMO,
            umbrales=MI.UMBRALES_INDICE, justificacion_umbrales=MI.JUSTIFICACION_UMBRALES,
            justificacion_pesos=MI.JUSTIFICACION_PESOS, reglas_prioridad=MI.REGLAS_PRIORIDAD,
            reglas_consistencia=MI.REGLAS_CONSISTENCIA, prioridad_visita=MI.REGLAS_PRIORIDAD_VISITA,
            contexto_estructural=MI.REGLAS_CONTEXTO_ESTRUCTURAL, coincidencia=MI.REGLAS_MAPA_COINCIDENCIA,
            ndvi=MI.CLASES_VIGOR_NDVI, puntaje_maximo_visita=MI.PUNTAJE_MAXIMO_VISITA),
        leyendas={k: [list(x) for x in v] for k, v in LEYENDAS.items()},
    )
    destino = C.DATOS_SALIDA / 'evaluacion.js'
    destino.write_text('window.EVAL=' + json.dumps(datos, ensure_ascii=False, default=str) + ';', encoding='utf-8')
    print(f'{len(inter)} unidades · {destino} ({destino.stat().st_size / 1e6:.2f} MB)')


if __name__ == '__main__':
    main()
