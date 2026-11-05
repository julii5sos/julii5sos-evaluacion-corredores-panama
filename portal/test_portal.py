"""Pruebas del portal Flask con resultados de ejemplo (sin Earth Engine). Ejecutar: pytest portal/test_portal.py"""
import json
import os
import sys
from pathlib import Path

os.environ['PREEVALUACION_EJEMPLO'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parent))
import app as A  # noqa: E402
import servicio as S  # noqa: E402

S.ee_disponible = lambda: False
GEO = json.load(open(Path(__file__).parent / 'static/data/subcuencas_canal.geojson'))['features'][0]['geometry']


def _post(tipo, modo='integral'):
    return A.app.test_client().post(f'/api/descargar/{tipo}', json={'geojson': GEO, 'modo': modo, 'nombre': 'prueba'})


def test_descargas_integral():
    for tipo, mime in (('registro', 'application/json'), ('fragmentos', 'application/geo+json'),
                       ('red', 'application/geo+json'), ('pdf', 'application/pdf')):
        r = _post(tipo)
        assert r.status_code == 200 and r.mimetype == mime, tipo
    assert _post('pdf').data[:4] == b'%PDF'


def test_red_no_disponible_en_territorial():
    assert _post('red', 'territorial').status_code == 400


def test_comparador_sin_ee_avisa():
    r = A.app.test_client().post('/api/comparar', json={'geojson': GEO, 'fuente': 'ESRI LULC', 'anio_inicial': 2019, 'anio_final': 2024})
    assert r.status_code == 400 and 'Earth Engine' in r.get_json()['error']
