"""Punto de entrada estable para Streamlit Community Cloud.

La aplicación pública conserva ``app.py`` como archivo principal para no
invalidar el despliegue existente. La implementación activa vive en
``app_experiencia.py`` y se ejecuta explícitamente en cada recarga de
Streamlit.
"""

import runpy
from pathlib import Path


APLICACION_ACTIVA = Path(__file__).with_name("app_experiencia.py")

if not APLICACION_ACTIVA.is_file():
    raise FileNotFoundError(
        "No se encontró app_experiencia.py, la implementación activa del visor."
    )

runpy.run_path(str(APLICACION_ACTIVA), run_name="__main__")
