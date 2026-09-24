"""Punto de entrada ligero para Streamlit Community Cloud."""

import runpy
from pathlib import Path

import streamlit as st

from modos_app import MODO_INTEGRAL, MODOS_ANALISIS


st.set_page_config(
    page_title="Evaluación territorial y corredores | Panamá",
    page_icon=":material/map:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.session_state["_pagina_configurada"] = True


def elegir_modo(modo):
    st.session_state["modo_analisis"] = modo


modo_analisis = st.session_state.get("modo_analisis")
if modo_analisis not in MODOS_ANALISIS:
    st.session_state.pop("modo_analisis", None)
    modo_analisis = None

if modo_analisis is None:
    st.markdown(
        """
        <style>
        :root {--verde:#00544d;--suave:#356b61;--borde:#b6d1c8;--fondo:#f6faf8;}
        .stApp {background:var(--fondo);color:var(--verde);}
        .block-container {padding-top:4rem;max-width:1440px;}
        button, [role="button"] {min-height:44px;}
        .entrada {
            padding:1.45rem 1.6rem;border:1px solid var(--borde);
            border-left:6px solid var(--verde);background:#fff;margin-bottom:1.2rem;
        }
        .entrada h1 {margin:0;color:var(--verde);font-size:clamp(2rem,4vw,3.25rem);}
        .entrada p {color:var(--suave);max-width:850px;line-height:1.55;}
        .pregunta {margin:.1rem 0 1rem;color:var(--verde);}
        .tarjeta {min-height:205px;}
        .tarjeta small {display:block;color:var(--suave);font-weight:700;text-transform:uppercase;}
        .tarjeta h3 {margin:.45rem 0;color:var(--verde);}
        .tarjeta p {color:var(--suave);line-height:1.5;}
        .resultado {padding-top:.6rem;border-top:1px solid var(--borde);}
        @media(max-width:760px){.block-container{padding-top:3.5rem}.entrada{padding:1.1rem}}
        </style>
        <div class="entrada">
          <h1>Evaluación territorial y corredores</h1>
          <p>Elija qué necesita conocer. Las fuentes cartográficas se cargarán después,
          únicamente para el análisis seleccionado.</p>
          <small>Resultado indicativo · requiere interpretación y verificación de campo</small>
        </div>
        <h2 class="pregunta">¿Qué desea analizar?</h2>
        """,
        unsafe_allow_html=True,
    )
    columnas = st.columns(3)
    for columna, (modo, contenido) in zip(columnas, MODOS_ANALISIS.items()):
        with columna:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="tarjeta">
                      <small>{contenido['pregunta']}</small>
                      <h3>{contenido['titulo']}</h3>
                      <p>{contenido['descripcion']}</p>
                      <div class="resultado"><b>Recibirá:</b> {contenido['resultado']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.button(
                    f"Elegir {contenido['titulo'].lower()}",
                    key=f"elegir-modo-{modo}",
                    type="primary" if modo == MODO_INTEGRAL else "secondary",
                    use_container_width=True,
                    on_click=elegir_modo,
                    args=(modo,),
                )
    st.info("La aplicación cargará Earth Engine después de elegir una opción.")
    st.stop()


APLICACION_ACTIVA = Path(__file__).with_name("app_experiencia.py")
if not APLICACION_ACTIVA.is_file():
    raise FileNotFoundError(
        "No se encontró app_experiencia.py, la implementación activa del visor."
    )

runpy.run_path(str(APLICACION_ACTIVA), run_name="__main__")
