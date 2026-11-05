"""Exporta el portal como sitio estático (sin servidor) en la carpeta dist/.

    python exportar.py

Renderiza cada plantilla con Flask y copia static/. En el sitio exportado
el análisis de la Plataforma se calcula en el navegador con la misma lógica
de analisis.py, porque no hay servidor que responda a /api/analisis.
"""
import shutil

import config as C
from app import PAGINAS, app


def exportar():
    if C.DIST.exists():
        shutil.rmtree(C.DIST)
    C.DIST.mkdir(parents=True)
    app.config['ESTATICO'] = True
    with app.test_client() as cliente:
        for nombre in PAGINAS:
            r = cliente.get('/' if nombre == 'index' else f'/{nombre}.html')
            assert r.status_code == 200, (nombre, r.status_code)
            (C.DIST / f'{nombre}.html').write_bytes(r.data)
    shutil.copytree(C.STATIC, C.DIST / 'static',
                    ignore=shutil.ignore_patterns('estadisticas*.json', '*.tif', '*.npz', '*.geojson'))
    print('Sitio estático en', C.DIST)


if __name__ == '__main__':
    exportar()
