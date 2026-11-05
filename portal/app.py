"""Servidor del portal Conectividad Panamá (Flask + plantillas Jinja).

    python preparar_datos.py   # genera capas y estadísticas (una vez)
    python app.py              # abre http://127.0.0.1:5000

Rutas:
    /, /<pagina>.html      páginas del portal renderizadas desde templates/
    POST /api/analisis     motor de análisis (analisis.py)
    GET  /api/unidad/<id>  estadísticas de una cuenca o subcuenca
    GET  /api/capas        URLs de teselas de Earth Engine (si está configurado)
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'evaluacion'))   # motor_ee, servicio, leyendas
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))           # módulos del repositorio (corredores, metodologia_indice…)

from flask import Flask, abort, jsonify, render_template, request

import config as C
from analisis import Criterios, calcular, estadisticas
from ee_capas import urls_teselas

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['ESTATICO'] = False      # exportar.py lo cambia a True

PAGINAS = {
    'index': dict(usa_datos=True),
    'herramienta': dict(),
    'panel': dict(usa_mapa=True, app_page=True),
    'plataforma': dict(usa_mapa=True, app_page=True),
    'datos': dict(),
    'tutoriales': dict(),
    'faq': dict(),
}


@app.context_processor
def contexto_global():
    est = estadisticas()
    return dict(
        sitio=C.SITIO, menu=C.MENU, cfg=C, estatico=app.config['ESTATICO'],
        flujo=C.FLUJO, indicadores=C.INDICADORES, catalogo=C.CATALOGO,
        tutoriales=C.TUTORIALES, faq=C.FAQ, anio=date.today().year,
        n_cuencas=len(est['cuencas']), n_subcuencas=len(est['subcuencas']),
        periodo=f"{est['years'][0] - 1} – {est['years'][-1]}", motor_modo=_motor_modo(),
        mi=_mi(), modos_pre=_modos_pre(),
    )


def _mi():
    import metodologia_indice
    return metodologia_indice


def _modos_pre():
    from modos_app import MODOS_ANALISIS
    return MODOS_ANALISIS


def _motor_modo():
    js = C.DATOS_SALIDA / 'motor' / 'motor.js'
    if not js.exists():
        return None
    txt = js.read_text(encoding='utf-8')
    return 'demo' if '"modo": "demo"' in txt[:4000] or '"modo":"demo"' in txt[:4000] else 'earth-engine'


def render_pagina(nombre: str):
    if nombre not in PAGINAS:
        abort(404)
    opciones = dict(usa_mapa=False, usa_datos=False, app_page=False) | PAGINAS[nombre]
    return render_template(f'{nombre}.html', activo=nombre, **opciones)


@app.get('/')
def inicio():
    return render_pagina('index')


@app.get('/<nombre>.html')
def pagina(nombre):
    return render_pagina(nombre)


# ------------------------------ API ------------------------------
@app.post('/api/analisis')
def api_analisis():
    criterios = Criterios.desde_dict(request.get_json(force=True, silent=True) or {})
    error = criterios.validar(estadisticas()['unidades'])
    if error:
        return jsonify(error=error), 400
    return jsonify(calcular(criterios))


@app.get('/api/unidad/<uid>')
def api_unidad(uid):
    u = estadisticas()['unidades'].get(uid)
    return jsonify(u) if u else (jsonify(error='No existe esa unidad'), 404)


@app.get('/api/capas')
def api_capas():
    return jsonify(urls_teselas())


# ---------------------- Motor de la Cuenca del Canal ----------------------
@app.get('/api/motor/estado')
def api_motor_estado():
    from motor import gee
    js = C.DATOS_SALIDA / 'motor' / 'motor.js'
    meta = {}
    if js.exists():
        m = json.loads(js.read_text(encoding='utf-8')[len('window.MOTOR='):-1])
        meta = {k: m[k] for k in ('generado', 'modo', 'anio0', 'anio1', 'escala_m')}
    import motor_ee_estado
    return jsonify(earth_engine=gee.disponible(), motor=meta, preevaluacion=motor_ee_estado.estado())


@app.post('/api/verificar')
def api_verificar():
    from motor.verificar import ErrorVerificacion, verificar
    d = request.get_json(force=True, silent=True) or {}
    try:
        r = verificar(d.get('geojson'), d.get('anio0'), d.get('anio1'))
    except ErrorVerificacion as e:
        return jsonify(error=str(e)), 400
    except Exception as e:  # Earth Engine u otro fallo externo
        app.logger.exception('Fallo en la verificación')
        return jsonify(error=f'No se pudo completar la verificación: {e}'), 502
    return jsonify(r)


@app.post('/api/leer_poligono')
def api_leer_poligono():
    from motor.verificar import ErrorVerificacion, leer_archivo
    f = request.files.get('archivo')
    if not f:
        return jsonify(error='No se recibió ningún archivo.'), 400
    try:
        return jsonify(leer_archivo(f.filename, f.read()))
    except ErrorVerificacion as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=f'No se pudo leer el archivo: {e}'), 400


# ---------------- Preevaluación (método del repositorio de corredores) ----------------
def _geometria_unidad(uid):
    import geopandas as gpd
    from motor.area import geometria_area
    if uid == 'cuenca':
        return geometria_area('cuenca')
    if uid == 'area':
        return geometria_area('area_estudio')
    sub = gpd.read_file(C.DATOS_SALIDA / 'subcuencas_canal.geojson')
    fila = sub[sub['id'] == uid]
    if fila.empty:
        return None
    return json.loads(json.dumps(fila.geometry.iloc[0].__geo_interface__))


@app.post('/api/preevaluar')
def api_preevaluar():
    from servicio import ErrorPreevaluacion, preevaluar
    d = request.get_json(force=True, silent=True) or {}
    geo = d.get('geojson') or (_geometria_unidad(d['unidad']) if d.get('unidad') else None)
    if not geo:
        return jsonify(error='Elige un área o dibuja un polígono.'), 400
    try:
        return jsonify(preevaluar(geo, d.get('modo', 'territorial'), d.get('umbral_m', 500), d.get('area_min_ha', 0)))
    except ErrorPreevaluacion as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        app.logger.exception('Fallo en la preevaluación')
        return jsonify(error=f'No se pudo completar la preevaluación: {e}'), 502


@app.post('/api/descargar/<tipo>')
def api_descargar(tipo):
    """Recalcula (las partes de Earth Engine están en caché) y devuelve el archivo pedido."""
    import re
    from flask import Response
    import servicio as S
    d = request.get_json(force=True, silent=True) or {}
    geo = d.get('geojson') or (_geometria_unidad(d['unidad']) if d.get('unidad') else None)
    if not geo:
        return jsonify(error='Elige un área o dibuja un polígono.'), 400
    nombre = re.sub(r'[^A-Za-z0-9_-]+', '_', str(d.get('nombre') or 'area')).strip('_')[:40] or 'area'
    try:
        r = S.preevaluar(geo, d.get('modo', 'territorial'), d.get('umbral_m', 500), d.get('area_min_ha', 0),
                         con_capas=False)
        if tipo == 'registro':
            cuerpo, mime, arch = json.dumps(S.registro_metodologico(r), ensure_ascii=False, indent=2, sort_keys=True), \
                'application/json', f'metodologia_preevaluacion_{nombre}.json'
        elif tipo == 'fragmentos':
            cuerpo, mime, arch = json.dumps(S.geojson_fragmentos(r), ensure_ascii=False), 'application/geo+json', \
                f'parches_bosque_{nombre}.geojson'
        elif tipo == 'red':
            cuerpo, mime, arch = json.dumps(S.geojson_red(r), ensure_ascii=False), 'application/geo+json', \
                f'red_conectividad_{nombre}.geojson'
        elif tipo == 'pdf':
            cuerpo, avisos = S.informe_pdf(r, d.get('nombre') or 'Área analizada')
            mime, arch = 'application/pdf', f'ficha_preevaluacion_{nombre}.pdf'
        else:
            return jsonify(error='Tipo de descarga no reconocido.'), 404
    except S.ErrorPreevaluacion as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        app.logger.exception('Fallo en la descarga')
        return jsonify(error=f'No se pudo preparar la descarga: {e}'), 502
    resp = Response(cuerpo, mimetype=mime, headers={'Content-Disposition': f'attachment; filename="{arch}"'})
    if tipo == 'pdf' and avisos:
        from urllib.parse import quote
        resp.headers['X-Avisos'] = quote(' | '.join(avisos)[:300])
    return resp


@app.get('/api/comparar/opciones')
def api_comparar_opciones():
    import servicio as S
    return jsonify(S.opciones_comparador())


@app.post('/api/comparar')
def api_comparar():
    import servicio as S
    d = request.get_json(force=True, silent=True) or {}
    geo = d.get('geojson') or (_geometria_unidad(d['unidad']) if d.get('unidad') else None)
    if not geo:
        return jsonify(error='Elige un área o dibuja un polígono.'), 400
    try:
        return jsonify(S.comparar_anios(geo, d.get('fuente'), d.get('anio_inicial'), d.get('anio_final')))
    except (S.ErrorPreevaluacion, ValueError, TypeError) as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        app.logger.exception('Fallo en el comparador')
        return jsonify(error=f'No se pudo preparar el comparador: {e}'), 502


@app.post('/api/preevaluar/serie')
def api_serie():
    from servicio import ErrorPreevaluacion, serie_fuente
    d = request.get_json(force=True, silent=True) or {}
    geo = d.get('geojson') or (_geometria_unidad(d['unidad']) if d.get('unidad') else None)
    try:
        return jsonify(serie_fuente(geo, d.get('fuente')))
    except (ErrorPreevaluacion, ValueError) as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=f'No se pudo calcular la serie: {e}'), 502


if __name__ == '__main__':
    app.run(debug=True)
