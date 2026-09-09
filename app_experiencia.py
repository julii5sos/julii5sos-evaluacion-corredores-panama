import html as html_lib
import hashlib
import hmac
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from io import BytesIO

import ee
import folium
import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from folium.plugins import Draw, Fullscreen, GroupedLayerControl, SideBySideLayers
from google.oauth2 import service_account
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as ReportLabImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from streamlit_folium import st_folium

from bosque_conectividad import (
    agregar_resultados_fragmentacion,
    analizar_fragmentacion_geojson,
)
from corredores import (
    FUENTE_CORTA as FUENTE_CORREDORES,
    URL_MAPA as URL_MAPA_CORREDORES,
    agregar_capas_corredores,
    analizar_interseccion_corredores,
    cargar_catalogo as cargar_catalogo_corredores,
    leyenda_corredores,
)
from metodologia_indice import (
    CLASES_VIGOR_NDVI,
    JUSTIFICACION_PESOS,
    JUSTIFICACION_UMBRALES,
    PERIODOS_ANALISIS,
    PESOS_INDICE,
    PUNTAJE_MAXIMO,
    PUNTAJE_MAXIMO_VISITA,
    REGLAS_CONSISTENCIA,
    REGLAS_CONTEXTO_ESTRUCTURAL,
    REGLAS_MAPA_COINCIDENCIA,
    REGLAS_PRIORIDAD,
    REGLAS_PRIORIDAD_VISITA,
    UMBRALES_INDICE,
    calcular_indice_prioridad,
    calcular_prioridad_visita,
    evaluar_consistencia,
    evaluar_senales,
    texto_recomendacion_visita,
)


st.set_page_config(
    page_title="Evaluación territorial y corredores | Panamá",
    page_icon=":material/map:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --institucional-verde: #00544d;
        --institucional-verde-oscuro: #00403a;
        --institucional-verde-acento: #76b72a;
        --institucional-verde-claro: #eaf4f0;
        --institucional-tinta: #00544d;
        --institucional-suave: #356b61;
        --institucional-borde: #b6d1c8;
        --institucional-fondo: #f6faf8;
    }
    .stApp {background: var(--institucional-fondo); color: var(--institucional-tinta);}
    html {color-scheme: light;}
    .block-container {padding-top: 4rem; padding-bottom: 2.5rem; max-width: 1440px;}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp p, .stApp label, .stApp li, .stApp small, .stApp summary,
    .stApp legend, .stApp th, .stApp td,
    [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"],
    [data-testid="stExpander"] summary {
        color: var(--institucional-tinta);
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
        color: var(--institucional-suave) !important;
    }
    [data-testid="stMetricValue"] {font-size: 1.55rem;}
    .stApp a {
        color: var(--institucional-verde);
        text-decoration-color: var(--institucional-verde-acento);
        text-underline-offset: .16em;
    }
    .stApp a:hover {color: var(--institucional-verde-oscuro);}
    .stButton > button,
    .stDownloadButton > button {
        border-color: var(--institucional-verde);
        color: var(--institucional-verde);
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        border-color: var(--institucional-verde-oscuro);
        color: var(--institucional-verde-oscuro);
    }
    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"],
    .stButton button[data-testid="stBaseButton-primary"],
    .stDownloadButton button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primary"] {
        border-color: var(--institucional-verde) !important;
        background: var(--institucional-verde) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 700;
    }
    .stButton > button[kind="primary"] *,
    .stDownloadButton > button[kind="primary"] *,
    .stButton button[data-testid="stBaseButton-primary"] *,
    .stDownloadButton button[data-testid="stBaseButton-primary"] *,
    button[data-testid="stBaseButton-primary"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover,
    .stButton button[data-testid="stBaseButton-primary"]:hover,
    .stDownloadButton button[data-testid="stBaseButton-primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        border-color: var(--institucional-verde-oscuro) !important;
        background: var(--institucional-verde-oscuro) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    [data-testid="stSidebar"] {border-right: 1px solid var(--institucional-borde);}
    [data-testid="stSidebar"] > div:first-child {background: #ffffff;}
    [data-testid="stSidebar"] * {overflow-wrap: anywhere;}
    #MainMenu, footer {visibility: hidden;}
    iframe {max-width: 100% !important;}
    button, [role="button"] {min-height: 44px;}
    button:focus-visible, [role="button"]:focus-visible,
    input:focus-visible, select:focus-visible, textarea:focus-visible,
    .leyenda-info:focus-visible {
        outline: 3px solid var(--institucional-verde);
        outline-offset: 2px;
    }
    .cabecera-app {
        padding: 1.45rem 1.6rem 1.5rem;
        border: 1px solid var(--institucional-borde);
        border-left: 6px solid var(--institucional-verde);
        border-radius: .2rem;
        background: #ffffff;
        color: var(--institucional-tinta);
        margin-bottom: .8rem;
    }
    .cabecera-app h1 {
        margin: 0;
        font-size: clamp(2.15rem, 4vw, 3.35rem);
        line-height: 1.12;
        letter-spacing: -.025em;
        color: var(--institucional-verde);
        overflow-wrap: normal;
    }
    .cabecera-app .subtitulo-app {
        margin-top: .45rem;
        font-size: 1.2rem;
        line-height: 1.35;
        font-weight: 650;
        color: var(--institucional-tinta);
    }
    .cabecera-app p {margin: .65rem 0 0; color: var(--institucional-suave); max-width: 980px;}
    .alcance-app {margin-top: .65rem; font-size: .86rem; color: var(--institucional-suave);}
    .resumen-inicial {
        margin: .9rem 0 1rem;
        padding: 1rem 1.1rem 1.05rem;
        border: 1px solid var(--institucional-borde);
        border-radius: .35rem;
        background: #ffffff;
    }
    .resumen-inicial h2 {
        margin: 0 0 .35rem;
        color: var(--institucional-verde);
        font-size: 1.35rem;
        line-height: 1.3;
    }
    .resumen-inicial > p {
        max-width: 75ch;
        margin: 0;
        color: var(--institucional-suave);
        font-size: 1rem;
        line-height: 1.6;
    }
    .resumen-principiante {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .65rem;
        margin: .85rem 0;
    }
    .resumen-paso {
        position: relative;
        min-height: 136px;
        padding: .85rem .9rem .85rem 3.25rem;
        border: 1px solid var(--institucional-borde);
        border-radius: .35rem;
        background: var(--institucional-fondo);
    }
    .resumen-paso-numero {
        position: absolute;
        top: .85rem;
        left: .85rem;
        display: inline-grid;
        place-items: center;
        width: 1.8rem;
        height: 1.8rem;
        border-radius: 50%;
        background: var(--institucional-verde);
        color: #ffffff;
        font-weight: 750;
    }
    .resumen-paso h3 {
        margin: 0 0 .3rem;
        color: var(--institucional-verde);
        font-size: 1rem;
        line-height: 1.35;
    }
    .resumen-paso p {
        margin: 0;
        color: var(--institucional-suave);
        font-size: .92rem;
        line-height: 1.5;
    }
    .resumen-aclaracion {
        margin-top: .25rem;
        padding: .75rem .85rem;
        border-left: 4px solid var(--institucional-verde);
        border-radius: 0 .25rem .25rem 0;
        background: var(--institucional-verde-claro);
        color: var(--institucional-tinta);
        font-size: .93rem;
        line-height: 1.55;
    }
    .resumen-aclaracion strong {color: var(--institucional-verde);}
    .flujo-pasos {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .55rem;
        margin: .2rem 0 1.1rem;
    }
    .flujo-paso {
        position: relative;
        min-height: 92px;
        padding: .75rem .8rem .7rem 3.2rem;
        border: 1px solid var(--institucional-borde);
        border-radius: .35rem;
        background: #ffffff;
        color: var(--institucional-suave);
        font-size: .84rem;
        line-height: 1.4;
    }
    .flujo-paso b {
        display: block;
        margin-bottom: .12rem;
        color: var(--institucional-tinta);
        font-size: .94rem;
    }
    .flujo-numero {
        position: absolute;
        top: .72rem;
        left: .72rem;
        display: inline-grid;
        place-items: center;
        width: 1.9rem;
        height: 1.9rem;
        border: 1px solid var(--institucional-borde);
        border-radius: 50%;
        background: var(--institucional-fondo);
        color: var(--institucional-suave);
        font-weight: 750;
    }
    .flujo-paso.completado {
        border-color: #8dbeae;
        background: #f2f8f5;
    }
    .flujo-paso.completado .flujo-numero {
        border-color: var(--institucional-verde);
        background: var(--institucional-verde);
        color: #ffffff;
    }
    .flujo-paso.actual {
        border: 2px solid var(--institucional-verde);
        background: var(--institucional-verde-claro);
        box-shadow: 0 3px 10px rgba(0, 84, 77, .09);
    }
    .flujo-paso.actual .flujo-numero {
        border-color: var(--institucional-verde);
        background: #ffffff;
        color: var(--institucional-verde);
    }
    .flujo-paso.pendiente .flujo-estado {
        color: var(--institucional-suave);
    }
    .flujo-estado {
        display: block;
        margin-top: .3rem;
        color: var(--institucional-verde);
        font-size: .73rem;
        font-weight: 700;
        letter-spacing: .035em;
        text-transform: uppercase;
    }
    .paso-guia {
        padding: .75rem .9rem;
        border-left: 4px solid var(--institucional-verde);
        background: var(--institucional-verde-claro);
        border-radius: 0 .2rem .2rem 0;
        margin: .35rem 0 .85rem;
    }
    .tarjeta-resumen {
        border: 1px solid var(--institucional-borde);
        border-radius: .2rem;
        padding: .85rem 1rem;
        background: #ffffff;
        height: 100%;
    }
    .entregables {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .65rem;
        margin: .75rem 0 1rem;
    }
    .entregable {
        min-height: 92px;
        padding: .75rem .85rem;
        border: 1px solid var(--institucional-borde);
        border-radius: .35rem;
        background: #ffffff;
    }
    .entregable small {
        display: block;
        margin-bottom: .2rem;
        color: var(--institucional-verde);
        font-weight: 750;
        letter-spacing: .035em;
        text-transform: uppercase;
    }
    .entregable b {
        display: block;
        margin-bottom: .18rem;
        color: var(--institucional-tinta);
    }
    .entregable span {
        color: var(--institucional-suave);
        font-size: .84rem;
        line-height: 1.4;
    }
    .contexto-analisis {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1px;
        margin: .3rem 0 1rem;
        border: 1px solid var(--institucional-borde);
        background: var(--institucional-borde);
    }
    .contexto-item {background: #ffffff; padding: .75rem .85rem; min-height: 72px;}
    .contexto-item small {display: block; color: var(--institucional-suave); margin-bottom: .2rem;}
    .contexto-item strong {color: var(--institucional-tinta);}
    .lectura-rapida {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .7rem;
        margin: .65rem 0 1rem;
    }
    .lectura-tarjeta {
        min-height: 132px;
        padding: .85rem .95rem;
        border: 1px solid var(--institucional-borde);
        border-top: 4px solid var(--institucional-verde);
        border-radius: .3rem;
        background: #ffffff;
    }
    .lectura-tarjeta small {
        display: block;
        margin-bottom: .35rem;
        color: var(--institucional-suave);
        font-size: .75rem;
        font-weight: 750;
        letter-spacing: .045em;
        text-transform: uppercase;
    }
    .lectura-tarjeta b {
        display: block;
        margin-bottom: .28rem;
        color: var(--institucional-tinta);
        font-size: 1rem;
    }
    .lectura-tarjeta p {
        margin: 0;
        color: var(--institucional-suave);
        font-size: .86rem;
        line-height: 1.48;
    }
    .resultado-prioridad {
        padding: 1rem 1.1rem;
        border: 1px solid var(--institucional-borde);
        border-left: 6px solid var(--prioridad-color);
        border-radius: .3rem;
        background: #ffffff;
        margin: .5rem 0 1rem;
    }
    .resultado-prioridad small {
        display: block;
        margin-bottom: .2rem;
        color: var(--institucional-suave);
        font-size: .76rem;
        font-weight: 700;
        letter-spacing: .05em;
        text-transform: uppercase;
    }
    .resultado-prioridad strong {
        display: block;
        color: var(--prioridad-color);
        font-size: 1.35rem;
        line-height: 1.25;
    }
    .resultado-prioridad p {
        margin: .45rem 0 0;
        color: var(--institucional-tinta);
        line-height: 1.5;
    }
    .recuperacion-error {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .65rem;
        margin: .7rem 0 1rem;
    }
    .recuperacion-paso {
        padding: .8rem .9rem;
        border: 1px solid #dfb8b3;
        border-radius: .35rem;
        background: #fffafa;
    }
    .recuperacion-paso b {
        display: block;
        margin-bottom: .22rem;
        color: #8f2921;
    }
    .recuperacion-paso span {
        color: #5c4946;
        font-size: .85rem;
        line-height: 1.45;
    }
    .bloque-metodo {
        border: 1px solid var(--institucional-borde);
        border-radius: .2rem;
        background: #ffffff;
        padding: .8rem 1rem;
        margin: .5rem 0;
    }
    .leyenda-fila {
        display: grid;
        grid-template-columns: 1.05rem minmax(0, 1fr);
        align-items: start;
        gap: .55rem;
        margin: .22rem 0;
        font-size: .9rem;
    }
    .leyenda-color {
        width: 1.05rem;
        height: 1.05rem;
        border: 1px solid rgba(0,0,0,.35);
        flex: 0 0 1.05rem;
    }
    .leyenda-texto {
        align-self: center;
        line-height: 1.4;
    }
    .leyenda-detalle {
        min-width: 0;
        margin: 0;
    }
    .leyenda-detalle summary {
        display: flex;
        align-items: center;
        gap: .45rem;
        min-height: 2.75rem;
        margin: 0;
        padding: .35rem 0;
        cursor: pointer;
        list-style: none;
        touch-action: manipulation;
    }
    .leyenda-detalle summary::-webkit-details-marker {display: none;}
    .leyenda-detalle summary:focus-visible {
        outline: 3px solid rgba(0, 84, 77, .35);
        outline-offset: 2px;
        border-radius: .2rem;
    }
    .leyenda-info {
        display: inline-grid;
        place-items: center;
        width: 1.55rem;
        height: 1.55rem;
        border: 1.5px solid currentColor;
        border-radius: 50%;
        color: var(--institucional-verde);
        background: #ffffff;
        font-size: .88rem;
        font-weight: 700;
        line-height: 1;
        flex: 0 0 1.55rem;
        transition: background-color .18s ease, color .18s ease;
    }
    .leyenda-detalle summary:hover .leyenda-info,
    .leyenda-detalle[open] .leyenda-info {
        color: #ffffff;
        background: var(--institucional-verde);
    }
    .leyenda-ayuda {
        margin: .35rem 0 .55rem;
        padding: .5rem .65rem;
        border-left: 3px solid var(--institucional-verde);
        border-radius: 0 .2rem .2rem 0;
        background: var(--institucional-verde-claro);
        color: var(--institucional-verde);
        font-size: .84rem;
        line-height: 1.45;
    }
    .ndvi-metodo-fila {
        display: flex;
        align-items: center;
        gap: .75rem;
        min-height: 52px;
        padding: .55rem .7rem;
        border: 1px solid var(--institucional-borde);
        border-radius: .35rem;
        background: #ffffff;
    }
    .ndvi-metodo-color {
        width: 1.35rem;
        height: 1.35rem;
        border: 1px solid rgba(0,0,0,.42);
        border-radius: .15rem;
        flex: 0 0 1.35rem;
    }
    .ndvi-metodo-texto {
        display: flex;
        flex-wrap: wrap;
        align-items: baseline;
        gap: .25rem .6rem;
        min-width: 0;
    }
    .ndvi-metodo-rango {
        color: var(--institucional-suave);
        font-variant-numeric: tabular-nums;
    }
    @media (prefers-reduced-motion: reduce) {
        .leyenda-info {transition: none;}
    }
    .resultado-fuente {
        padding: .7rem .85rem;
        border: 1px solid var(--institucional-borde);
        border-radius: .2rem;
        background: #ffffff;
        margin-bottom: .45rem;
    }
    .comparador-anios {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: .65rem .85rem;
        margin: .25rem 0 .55rem;
        border: 1px solid rgba(0,84,77,.28);
        border-radius: .2rem;
        background: var(--institucional-verde-claro);
        color: var(--institucional-verde);
    }
    .comparador-anios span:last-child {text-align: right;}
    .corredor-aviso {
        margin: .75rem 0 1rem;
        padding: .9rem 1rem;
        border: 1px solid var(--institucional-borde);
        border-left: 5px solid var(--institucional-verde-acento);
        border-radius: .3rem;
        background: #ffffff;
        color: var(--institucional-tinta);
        line-height: 1.55;
    }
    .corredor-aviso strong {color: var(--institucional-verde);}
    .categoria-corredor {
        display: inline-flex;
        align-items: center;
        gap: .4rem;
        min-height: 32px;
        padding: .25rem .55rem;
        margin: .15rem .25rem .15rem 0;
        border: 1px solid var(--institucional-borde);
        border-radius: 999px;
        background: #ffffff;
        font-size: .86rem;
        font-weight: 700;
    }
    @media (max-width: 760px) {
        .flujo-pasos, .contexto-analisis, .entregables, .resumen-principiante,
        .lectura-rapida, .recuperacion-error {grid-template-columns: 1fr 1fr;}
        .block-container {padding-top: 3.5rem;}
        .cabecera-app {padding: 1.2rem;}
        .cabecera-app h1 {font-size: 2rem; line-height: 1.15;}
    }
    @media (max-width: 480px) {
        .flujo-pasos, .contexto-analisis, .entregables, .resumen-principiante,
        .lectura-rapida, .recuperacion-error {grid-template-columns: 1fr;}
        .flujo-paso {min-height: 82px;}
        .resumen-inicial {padding: .9rem;}
        .resumen-inicial > p {font-size: 1rem;}
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: .01ms !important;
            animation-iteration-count: 1 !important;
            scroll-behavior: auto !important;
            transition-duration: .01ms !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Configuración centralizada
# -----------------------------------------------------------------------------


def secreto_opcional(nombre, predeterminado=None):
    """Lee un secreto sin fallar cuando el archivo local todavía no existe."""

    try:
        return st.secrets.get(nombre, predeterminado)
    except StreamlitSecretNotFoundError:
        return predeterminado


APP_VERSION = "UX-0.6.0-BOSQUE-AUTOMATICO"
METHODOLOGY_VERSION = "MT-2026.8-BOSQUE-AUTOMATICO"
PROYECTO_EE = secreto_opcional("EE_PROJECT", "ee-julissaguevaravega")
FUENTE_BOSQUE_NOMBRE = "Bosque y otros usos"
FUENTE_BOSQUE_ORGANIZACION = "SINIA–MiAMBIENTE"
ANO_BOSQUE_REFERENCIA = 2021
FUENTE_BOSQUE_CORTA = (
    f"{FUENTE_BOSQUE_ORGANIZACION} · {FUENTE_BOSQUE_NOMBRE} · "
    f"{ANO_BOSQUE_REFERENCIA}"
)

ASSET_CUENCA = (
    "projects/ee-julissaguevaravega/assets/"
    "CuencasHidrograficadeInteres"
)
ASSET_FINCAS = secreto_opcional("EE_ASSET_FINCAS")
ASSET_BOSQUE_2021 = secreto_opcional("EE_ASSET_BOSQUE_2021")
ACCESO_FINCA_DURACION_SEG = 30 * 60
ACCESO_FINCA_MAX_INTENTOS = 5
ACCESO_FINCA_BLOQUEO_SEG = 60
HANSEN_ASSET = "UMD/hansen/global_forest_change_2025_v1_13"
TMF_ASSET = "projects/JRC/TMF/v1_2025/AnnualChanges"
ESRI_ASSET = (
    "projects/sat-io/open-datasets/landcover/"
    "ESRI_Global-LULC_10m_TS"
)
GEDI_ASSET = (
    "users/openforisearthmap/World_EarthMap/"
    "CanopyHeight_GEDI_V27"
)

ANO_REFERENCIA_ANALISIS = PERIODOS_ANALISIS["referencia"]
ANO_HANSEN_MAX = PERIODOS_ANALISIS["hansen_diagnostico"]
ANO_TMF_MAX = PERIODOS_ANALISIS["jrc_diagnostico"]
ANO_DIAG_TMF = PERIODOS_ANALISIS["jrc_diagnostico"]
ANO_ESRI_MIN = PERIODOS_ANALISIS["esri_inicial"]
ANO_ESRI_MAX = PERIODOS_ANALISIS["esri_final"]
ANO_NDVI_MAX = PERIODOS_ANALISIS["ndvi_final_visual"]
CUTOFF_YEAR = 20
CUTOFF_LABEL = "31/12/2020"

UMBRAL_ALERTA_HANSEN_HA = UMBRALES_INDICE["hansen_post_2020_ha"]
UMBRAL_REVISION_TMF_DEGRAD_HA = UMBRALES_INDICE["jrc_degradacion_ha"]
UMBRAL_REVISION_TMF_DEFOR_HA = UMBRALES_INDICE["jrc_deforestacion_ha"]
UMBRAL_PCT_TMF_DEFOR = UMBRALES_INDICE["jrc_deforestacion_pct"]
UMBRAL_PCT_TMF_DEGRAD = UMBRALES_INDICE["jrc_degradacion_pct"]
UMBRAL_PCT_ESRI_SALIDA = UMBRALES_INDICE["esri_salida_arboles_pct"]
UMBRAL_ESRI_SALIDA_HA = UMBRALES_INDICE["esri_salida_arboles_ha"]
UMBRAL_DOSEL_BAJO_M = UMBRALES_INDICE["gedi_dosel_bajo_m"]
UMBRAL_COBERTURA_GEDI_PCT = UMBRALES_INDICE["gedi_cobertura_minima_pct"]
UMBRAL_LINEA_BASE_GEDI_PCT = UMBRALES_INDICE["gedi_linea_base_minima_pct"]

ESRI_ORIG = [1, 2, 4, 5, 7, 8, 9, 10, 11]
ESRI_VIS = [1, 2, 3, 4, 5, 6, 7, 8, 9]
ESRI_COLORES = [
    "1A5BAB",
    "358221",
    "87D19E",
    "FFDB5C",
    "ED022A",
    "EDE9E4",
    "F2FAFF",
    "C8C8C8",
    "C6AD8D",
]

VIS_TMF = {
    "min": 1,
    "max": 6,
    "palette": ["006400", "FFCC00", "FF0000", "00FF00", "0000FF", "BDBDBD"],
}
VIS_ESRI = {"min": 1, "max": 9, "palette": ESRI_COLORES}
VIS_HANSEN_POST = {
    "min": 21,
    "max": 25,
    "palette": ["FF1744", "D50000", "B71C1C", "7F0000", "4A0000"],
}
VIS_HANSEN_PRE = {
    "min": 1,
    "max": 20,
    "palette": ["FFF9C4", "F9A825", "E65100", "C62828"],
}
VIS_HANSEN_TOTAL = {
    "min": 1,
    "max": 25,
    "palette": ["FFF9C4", "F9A825", "E65100", "FF1744", "7F0000"],
}
VIS_LINEA_BASE = {"min": 1, "max": 1, "palette": ["00C853"]}
VIS_TMF_DEFOR = {"min": 1, "max": 1, "palette": ["FF0000"]}
VIS_TMF_DEGRAD = {"min": 1, "max": 1, "palette": ["FFCC00"]}
VIS_ESRI_CAMBIO = {
    "min": 1,
    "max": 3,
    "palette": ["00FF00", "FF0000", "006400"],
}
VIS_GEDI = {
    "min": 0,
    "max": 35,
    "palette": ["FFFFCC", "C2E699", "78C679", "31A354", "006837"],
}
VIS_NDVI_DELTA = {
    "min": -0.3,
    "max": 0.3,
    "palette": ["7F0000", "D32F2F", "FF7043", "FFF9C4", "66BB6A", "2E7D32", "1B5E20"],
}
VIS_NDVI_CLASES = {
    "min": 0,
    "max": 4,
    "palette": ["B30000", "F4A582", "FFFFBF", "78C679", "006837"],
}
VIS_COINCIDENCIA_REVISION = {
    "min": 1,
    "max": 3,
    "palette": [
        REGLAS_MAPA_COINCIDENCIA["clases"][clase]["color"].lstrip("#")
        for clase in (1, 2, 3)
    ],
}
VIS_RGB = {"min": 150, "max": 3200, "gamma": 1.15, "bands": ["B4", "B3", "B2"]}

PERFILES_VISUALIZACION = {
    "Diagnóstico territorial integrado": {
        "descripcion": (
            "Conecta señales recientes, corredores y la estructura del bosque de 2021 "
            "para orientar la prioridad y el lugar de una visita."
        ),
        "modo": "Explorar capas",
        "comparador": "Sin comparador",
        "capas": [
            "Sectores para revisión",
        ],
    },
    "Consultar capas individuales": {
        "descripcion": (
            "Elija una o varias capas. Para JRC, ESRI y NDVI puede consultar un "
            "solo año, sin barrido temporal."
        ),
        "modo": "Explorar capas",
        "comparador": "Sin comparador",
        "capas": [
            "Sectores para revisión",
            "Pérdida Hansen post-2020",
            "Estado forestal JRC",
        ],
    },
    "Comparar estado forestal entre dos años (JRC TMF)": {
        "descripcion": "Compare visualmente el estado forestal de dos años mediante el swipe.",
        "modo": "Comparar años",
        "comparador": "JRC TMF",
        "capas": [],
    },
    "Comparar uso del suelo entre dos años (ESRI)": {
        "descripcion": "Compare visualmente las clases de uso y cobertura de dos años.",
        "modo": "Comparar años",
        "comparador": "ESRI LULC",
        "capas": [],
    },
    "Comparar vigor vegetal entre dos años (NDVI)": {
        "descripcion": "Compare clases de vigor vegetal de dos años; esta vista no modifica el índice.",
        "modo": "Comparar años",
        "comparador": "NDVI Sentinel-2",
        "capas": [],
    },
}

LEYENDAS = {
    "Corredores Almanaque Azul": leyenda_corredores(),
    "Importancia de parches": [
        ("#b42318", "Alta", "Cuartil superior del índice conector calculado"),
        ("#f79009", "Media", "Entre la mediana y el cuartil superior"),
        ("#157f3b", "Baja", "Por debajo de la mediana del área analizada"),
    ],
    "Sectores para revisión": [
        (
            REGLAS_MAPA_COINCIDENCIA["clases"][clase]["color"],
            REGLAS_MAPA_COINCIDENCIA["clases"][clase]["etiqueta"],
            REGLAS_MAPA_COINCIDENCIA["clases"][clase]["interpretacion"],
        )
        for clase in (1, 2, 3)
    ],
    "JRC TMF": [
        ("#006400", "Bosque no perturbado"),
        ("#FFCC00", "Degradación"),
        ("#FF0000", "Deforestación"),
        ("#00FF00", "Regeneración"),
        ("#0000FF", "Agua"),
        ("#BDBDBD", "Otra cobertura"),
    ],
    "ESRI LULC": [
        ("#1A5BAB", "Agua"),
        ("#358221", "Árboles"),
        ("#87D19E", "Vegetación inundada"),
        ("#FFDB5C", "Cultivos"),
        ("#ED022A", "Área construida"),
        ("#EDE9E4", "Suelo desnudo"),
        ("#F2FAFF", "Nieve/hielo"),
        ("#C8C8C8", "Nubes"),
        ("#C6AD8D", "Pastizal/matorral"),
    ],
    "Pérdida Hansen post-2020": [
        ("#FF1744", "2021"),
        ("#D50000", "2022"),
        ("#B71C1C", "2023"),
        ("#7F0000", "2024"),
        ("#4A0000", "2025"),
    ],
    "Pérdida Hansen 2001-2020": [
        ("#FFF9C4", "Pérdida más antigua"),
        ("#F9A825", "Pérdida intermedia"),
        ("#C62828", "Pérdida próxima a 2020"),
    ],
    "Cobertura arbórea persistente": [("#00C853", "Cobertura arbórea persistente hasta 2020")],
    "Deforestación JRC": [("#FF0000", "Deforestación")],
    "Degradación JRC": [("#FFCC00", "Degradación")],
    "Transiciones ESRI": [
        ("#00FF00", "No árbol → árboles"),
        ("#FF0000", "Árboles → no árbol"),
        ("#006400", "Árboles estables"),
    ],
    "Altura GEDI": [
        ("#FFFFCC", "Dosel bajo"),
        ("#78C679", "Dosel medio"),
        ("#006837", "Dosel alto"),
    ],
    "ΔNDVI": [
        ("#7F0000", "Pérdida fuerte de vigor"),
        ("#FF7043", "Pérdida moderada"),
        ("#FFF9C4", "Cambio pequeño"),
        ("#66BB6A", "Aumento de vigor"),
        ("#1B5E20", "Aumento fuerte"),
    ],
    "Vegetación NDVI": [
        (
            clase["color"],
            f"{clase['etiqueta']} · {clase['rango']}",
            clase["interpretacion"],
        )
        for clase in CLASES_VIGOR_NDVI
    ],
    "NDVI Sentinel-2": [
        (
            clase["color"],
            f"{clase['etiqueta']} · {clase['rango']}",
            clase["interpretacion"],
        )
        for clase in CLASES_VIGOR_NDVI
    ],
}


def construir_registro_metodologico(
    tipo_area,
    finca_id,
    geometria_geojson,
    anio_tmf_visual_inicial,
    anio_tmf_visual_final,
    anio_esri_visual_inicial,
    anio_esri_visual_final,
    anio_ndvi_visual_inicial,
    anio_ndvi_visual_final,
    anio_tmf_capa,
    anio_esri_capa,
    anio_ndvi_capa,
    modo_comparador,
    capas_activas,
    resultados=None,
):
    if tipo_area == "Finca de monitoreo":
        especificacion_area = {
            "tipo": "finca_privada",
            "identificador": str(finca_id),
            "geometria_vectorial_incluida": False,
            "fuente": "coleccion_privada_configurada_en_el_servidor",
        }
    elif tipo_area == "Dibujar polígono en el mapa":
        especificacion_area = {
            "tipo": "poligono_dibujado",
            "geojson": json.loads(geometria_geojson),
            "recorte": ASSET_CUENCA,
        }
    else:
        especificacion_area = {"tipo": "cuenca", "asset": ASSET_CUENCA}

    configuracion = {
        "metodologia": METHODOLOGY_VERSION,
        "area": especificacion_area,
        "periodos": {
            "referencia_metodologica": ANO_REFERENCIA_ANALISIS,
            "diagnostico_fijo": {
                "jrc": ANO_DIAG_TMF,
                "hansen": ANO_HANSEN_MAX,
                "esri_inicial": ANO_ESRI_MIN,
                "esri_final": ANO_ESRI_MAX,
            },
            "visualizacion": {
                "comparador": modo_comparador,
                "jrc_inicial": anio_tmf_visual_inicial,
                "jrc_final": anio_tmf_visual_final,
                "esri_inicial": anio_esri_visual_inicial,
                "esri_final": anio_esri_visual_final,
                "ndvi_inicial": anio_ndvi_visual_inicial,
                "ndvi_final": anio_ndvi_visual_final,
                "capas_un_ano": {
                    "jrc": anio_tmf_capa,
                    "esri": anio_esri_capa,
                    "ndvi": anio_ndvi_capa,
                },
                "capas_disponibles": list(capas_activas),
            },
            "corte_referencia": CUTOFF_LABEL,
        },
        "fuentes": [
            {
                "nombre": "JRC Tropical Moist Forest",
                "asset": TMF_ASSET,
                "banda": f"Dec{ANO_DIAG_TMF}",
                "escala_m": 30,
                "uso": "diagnostico",
            },
            {
                "nombre": "Hansen Global Forest Change",
                "asset": HANSEN_ASSET,
                "bandas": ["treecover2000", "loss", "lossyear"],
                "escala_m": 30,
                "uso": "diagnostico",
            },
            {
                "nombre": "ESRI Land Use Land Cover",
                "asset": ESRI_ASSET,
                "escala_m": 10,
                "uso": "diagnostico",
            },
            {
                "nombre": "GEDI Canopy Height",
                "asset": GEDI_ASSET,
                "escala_m": 100,
                "uso": "contexto",
            },
            {
                "nombre": "Sentinel-2 Surface Reflectance Harmonized",
                "asset": "COPERNICUS/S2_SR_HARMONIZED",
                "bandas": ["B8", "B4", "SCL"],
                "escala_m": 10,
                "uso": "visual; no participa en el indice",
            },
            {
                "nombre": "Mapa de conectividad ecologica de Panama",
                "organizacion": "Fundacion Almanaque Azul",
                "version": cargar_catalogo_corredores()["version_publicada"],
                "url": URL_MAPA_CORREDORES,
                "categorias": ["alta", "mediana", "media-baja"],
                "uso": (
                    "valor estrategico de la prioridad de visita; no modifica "
                    "el indice satelital de cambios"
                ),
            },
            {
                "nombre": FUENTE_BOSQUE_NOMBRE,
                "organizacion": FUENTE_BOSQUE_ORGANIZACION,
                "ano_referencia": ANO_BOSQUE_REFERENCIA,
                "formato": "asset vectorial institucional privado de Earth Engine",
                "configurado": bool(ASSET_BOSQUE_2021),
                "uso": (
                    "fragmentacion y conectividad estructural para focalizar "
                    "la visita; no participa en el puntaje ni constituye una serie anual"
                ),
            },
        ],
        "umbrales": dict(UMBRALES_INDICE),
        "justificacion_umbrales": dict(JUSTIFICACION_UMBRALES),
        "pesos": dict(PESOS_INDICE),
        "justificacion_pesos": dict(JUSTIFICACION_PESOS),
        "reglas_prioridad": dict(REGLAS_PRIORIDAD),
        "reglas_prioridad_visita": dict(REGLAS_PRIORIDAD_VISITA),
        "reglas_contexto_estructural": dict(REGLAS_CONTEXTO_ESTRUCTURAL),
        "reglas_consistencia": dict(REGLAS_CONSISTENCIA),
        "mapa_coincidencia_espacial": {
            "nombre": REGLAS_MAPA_COINCIDENCIA["nombre"],
            "malla_referencia_m": REGLAS_MAPA_COINCIDENCIA[
                "malla_referencia_m"
            ],
            "fuentes": dict(REGLAS_MAPA_COINCIDENCIA["fuentes"]),
            "clases": {
                str(clase): dict(especificacion)
                for clase, especificacion in REGLAS_MAPA_COINCIDENCIA[
                    "clases"
                ].items()
            },
            "participa_indice": REGLAS_MAPA_COINCIDENCIA["participa_indice"],
            "limitacion": REGLAS_MAPA_COINCIDENCIA["limitacion"],
        },
        "clases_vigor_ndvi": [dict(clase) for clase in CLASES_VIGOR_NDVI],
        "procesamiento": {
            "unidad_area": "hectareas",
            "reduccion": "suma de area por clase en la proyeccion de cada fuente",
            "respuesta_earth_engine": "reducciones agrupadas en una sola respuesta",
            "ndvi": "mediana anual con mascara SCL y respaldo del ano anterior",
            "formula_ndvi": "(B8 - B4) / (B8 + B4)",
            "coincidencia_espacial": (
                "JRC conserva su malla de 30 m; Hansen se reproyecta por vecino "
                "más cercano y ESRI se agrega desde 10 m por presencia máxima "
                "antes de sumar las tres señales binarias."
            ),
            "corredores": (
                "Interseccion vectorial en Equal Earth Americas (EPSG:8857); "
                "conserva las categorias originales de Almanaque Azul. El "
                "solapamiento y la pertenencia al Corredor Biologico "
                "Mesoamericano aportan a la prioridad separada de visita."
            ),
            "estructura_bosque": (
                "Los parches de Bosque y otros usos 2021 forman una red según el "
                "umbral seleccionado. Su condición orienta la focalización de la "
                "visita sin añadir un peso ecológico no calibrado."
            ),
        },
    }
    huella = hashlib.sha256(
        json.dumps(configuracion, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    registro = {
        "aplicacion": APP_VERSION,
        "fecha_generacion": date.today().isoformat(),
        "codigo_reproducibilidad": huella,
        "explicacion_codigo": (
            "Identificador técnico generado a partir del área, las fuentes, los períodos, "
            "los umbrales, los pesos y las reglas de esta configuración."
        ),
        **configuracion,
        "alcance": (
            "Preevaluacion indicativa para priorizar revisiones. No constituye validacion "
            "de campo ni determina cumplimiento EUDR."
        ),
    }
    if resultados:
        registro["resultados_resumen"] = {
            "area_ha": resultados["area_ha"],
            "puntaje": resultados["puntaje"],
            "prioridad": resultados["prioridad"],
            "senal_jrc": resultados["senal_tmf"],
            "senal_hansen": resultados["senal_hansen"],
            "senal_esri": resultados["senal_esri"],
            "senal_gedi": resultados["senal_gedi"],
            "aportes_indice": resultados["aportes_indice"],
            "consistencia": resultados["consistencia"],
            "corredores": resultados.get("corredores"),
            "prioridad_visita": resultados.get("prioridad_visita"),
            "estadisticas": {
                "cobertura_arborea_persistente_2020_ha": resultados["linea_base"],
                "hansen_pre_2021_ha": resultados["hansen_pre"],
                "hansen_post_2020_ha": resultados["hansen_post"],
                "tmf_clases_ha": {
                    "bosque_estable": resultados["tmf_estable"],
                    "degradacion": resultados["tmf_degradacion"],
                    "deforestacion": resultados["tmf_deforestacion"],
                    "recuperacion": resultados["tmf_recuperacion"],
                    "agua": resultados["tmf_agua"],
                    "otra_cobertura": resultados["tmf_otra_cobertura"],
                },
                "esri_arboles_final_ha": resultados["esri_arboles_final"],
                "esri_salida_arboles_ha": resultados["esri_salida"],
                "esri_ganancia_arboles_ha": resultados["esri_ganancia"],
                "gedi_altura_media_m": resultados["gedi_altura"],
                "gedi_cobertura_valida_pct": resultados["gedi_cobertura_pct"],
                "coincidencia_espacial_ha": {
                    "una_fuente": resultados["coincidencia_1_fuente"],
                    "dos_fuentes": resultados["coincidencia_2_fuentes"],
                    "tres_fuentes": resultados["coincidencia_3_fuentes"],
                    "dos_o_tres_fuentes": resultados[
                        "coincidencia_varias_fuentes"
                    ],
                },
            },
        }
        if resultados.get("fragmentacion"):
            registro["resultados_resumen"]["fragmentacion_conectividad"] = {
                "metricas_clase": resultados["fragmentacion"]["metricas_clase"],
                "metricas_red": resultados["fragmentacion"]["metricas_red"],
                "top_conectores": resultados["fragmentacion"]["top_conectores"],
                "campo_clase": resultados["fragmentacion"]["campo_clase"],
                "valores_bosque": resultados["fragmentacion"]["valores_bosque"],
                "fuente_cobertura": resultados["fragmentacion"].get(
                    "fuente_cobertura", FUENTE_BOSQUE_CORTA
                ),
                "ano_referencia_cobertura": resultados["fragmentacion"].get(
                    "ano_referencia_cobertura", ANO_BOSQUE_REFERENCIA
                ),
                "metodo": resultados["fragmentacion"]["metodo"],
                "participa_indice_prioridad": False,
                "papel_diagnostico": (
                    "orienta la focalizacion espacial de la visita y permite "
                    "identificar conectores y componentes aislados"
                ),
            }
    return registro


# -----------------------------------------------------------------------------
# Earth Engine y datos
# -----------------------------------------------------------------------------

@st.cache_resource
def iniciar_earth_engine():
    secreto = secreto_opcional("EE_SERVICE_ACCOUNT_JSON")
    if secreto is None:
        raise RuntimeError(
            "Falta EE_SERVICE_ACCOUNT_JSON en los secretos de esta aplicación."
        )
    if isinstance(secreto, str):
        informacion = json.loads(secreto)
    else:
        informacion = dict(secreto)
    credenciales = service_account.Credentials.from_service_account_info(
        informacion,
        scopes=[
            "https://www.googleapis.com/auth/earthengine",
            "https://www.googleapis.com/auth/cloud-platform",
        ],
    )
    ee.Initialize(credentials=credenciales, project=PROYECTO_EE)
    return True


def acceso_fincas_vigente():
    return time.time() < float(st.session_state.get("fincas_acceso_hasta", 0))


def cerrar_acceso_fincas():
    st.session_state.pop("fincas_acceso_hasta", None)
    st.session_state.pop("codigo_acceso_fincas", None)
    st.session_state.pop("mensaje_acceso_fincas", None)


def procesar_codigo_acceso_fincas():
    ahora = time.time()
    codigo_configurado = str(secreto_opcional("FINCAS_ACCESS_CODE", ""))
    codigo_ingresado = str(st.session_state.get("codigo_acceso_fincas", ""))
    bloqueo_hasta = float(st.session_state.get("fincas_bloqueo_hasta", 0))

    if ahora < bloqueo_hasta:
        st.session_state["mensaje_acceso_fincas"] = (
            "warning",
            "Acceso temporalmente bloqueado. Espere un minuto antes de volver a intentarlo.",
        )
    elif hmac.compare_digest(codigo_ingresado, codigo_configurado):
        st.session_state["fincas_acceso_hasta"] = ahora + ACCESO_FINCA_DURACION_SEG
        st.session_state["fincas_intentos_acceso"] = 0
        st.session_state["mensaje_acceso_fincas"] = (
            "success",
            "Acceso autorizado para esta sesión.",
        )
    else:
        intentos = int(st.session_state.get("fincas_intentos_acceso", 0)) + 1
        if intentos >= ACCESO_FINCA_MAX_INTENTOS:
            st.session_state["fincas_bloqueo_hasta"] = ahora + ACCESO_FINCA_BLOQUEO_SEG
            st.session_state["fincas_intentos_acceso"] = 0
            mensaje = (
                "warning",
                "Demasiados intentos. El acceso quedó bloqueado durante un minuto.",
            )
        else:
            st.session_state["fincas_intentos_acceso"] = intentos
            restantes = ACCESO_FINCA_MAX_INTENTOS - intentos
            mensaje = (
                "error",
                f"Código incorrecto. Quedan {restantes} intentos antes del bloqueo temporal.",
            )
        st.session_state["mensaje_acceso_fincas"] = mensaje

    # El código digitado no permanece almacenado en la sesión.
    st.session_state["codigo_acceso_fincas"] = ""


def solicitar_acceso_fincas():
    codigo_configurado = str(secreto_opcional("FINCAS_ACCESS_CODE", ""))
    if not ASSET_FINCAS or len(codigo_configurado) < 8:
        st.sidebar.error(
            "El acceso privado a las fincas no está configurado. El administrador debe "
            "definir EE_ASSET_FINCAS y FINCAS_ACCESS_CODE en los secretos de Streamlit."
        )
        return False

    mensaje = st.session_state.pop("mensaje_acceso_fincas", None)
    if acceso_fincas_vigente():
        st.sidebar.success("Acceso privado a fincas activo")
        st.sidebar.caption("La autorización caduca automáticamente después de 30 minutos.")
        st.sidebar.button(
            "Cerrar acceso a fincas",
            on_click=cerrar_acceso_fincas,
            use_container_width=True,
        )
        if mensaje and mensaje[0] == "success":
            st.sidebar.success(mensaje[1])
        return True

    bloqueo_hasta = float(st.session_state.get("fincas_bloqueo_hasta", 0))
    if time.time() < bloqueo_hasta:
        st.sidebar.warning(
            "Acceso temporalmente bloqueado. Espere un minuto antes de volver a intentarlo."
        )
        return False

    st.sidebar.info(
        "Esta opción contiene información privada. Ingrese el código autorizado para "
        "consultar la lista de fincas."
    )
    st.sidebar.text_input(
        "Código de acceso",
        type="password",
        key="codigo_acceso_fincas",
        help="El código no se guarda en GitHub ni se incluye en los informes.",
    )
    st.sidebar.button(
        "Acceder a las fincas",
        type="primary",
        on_click=procesar_codigo_acceso_fincas,
        use_container_width=True,
    )
    if mensaje:
        getattr(st.sidebar, mensaje[0])(mensaje[1])
    return False


def nombre_area_legible(tipo_area, finca_id=None):
    if tipo_area == "Toda la cuenca":
        return "Cuenca hidrográfica de interés"
    if tipo_area == "Dibujar polígono en el mapa":
        return "Polígono dibujado por el usuario"
    nombre = str(finca_id).strip()
    return nombre if nombre.casefold().startswith("finca") else f"Finca {nombre}"


def clave_orden_natural(valor):
    partes = re.split(r"(\d+)", str(valor).strip())
    return tuple(
        (0, int(parte)) if parte.isdigit() else (1, parte.casefold())
        for parte in partes
        if parte
    )


@st.cache_data(ttl=3600)
def obtener_ids_fincas():
    if not ASSET_FINCAS or not acceso_fincas_vigente():
        raise PermissionError("La colección privada requiere un acceso autorizado.")
    valores = (
        ee.FeatureCollection(ASSET_FINCAS)
        .aggregate_array("FincaID")
        .distinct()
        .getInfo()
    )
    return sorted(
        [valor for valor in valores if valor is not None],
        key=clave_orden_natural,
    )


def obtener_area(tipo_area, finca_id=None, geometria_geojson=None):
    if tipo_area == "Finca de monitoreo":
        if not ASSET_FINCAS or not acceso_fincas_vigente():
            raise PermissionError("La finca privada requiere un acceso autorizado.")
        return ee.FeatureCollection(ASSET_FINCAS).filter(
            ee.Filter.eq("FincaID", finca_id)
        )
    if tipo_area == "Dibujar polígono en el mapa":
        if not geometria_geojson:
            raise ValueError("Debe dibujar un polígono antes de ejecutar el análisis.")
        datos_geometria = (
            json.loads(geometria_geojson)
            if isinstance(geometria_geojson, str)
            else geometria_geojson
        )
        geometria = ee.Geometry(datos_geometria)
        geometria_cuenca = ee.FeatureCollection(ASSET_CUENCA).geometry()
        geometria_recortada = geometria.intersection(geometria_cuenca, 1)
        return ee.FeatureCollection(
            [ee.Feature(geometria_recortada, {"Origen": "Dibujo del usuario"})]
        )
    return ee.FeatureCollection(ASSET_CUENCA)


def serializar_poligono_dibujado(dibujo):
    geometria = dibujo.get("geometry", dibujo) if dibujo else None
    if not isinstance(geometria, dict):
        raise ValueError("No fue posible interpretar la geometría dibujada.")
    if geometria.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("La figura debe ser un polígono cerrado.")
    return json.dumps(geometria, sort_keys=True, separators=(",", ":"))


def obtener_limites(objeto):
    coordenadas = objeto.geometry().bounds(1).coordinates().getInfo()[0]
    longitudes = [punto[0] for punto in coordenadas]
    latitudes = [punto[1] for punto in coordenadas]
    return [
        [min(latitudes), min(longitudes)],
        [max(latitudes), max(longitudes)],
    ]


def obtener_tmf(anio, geometria):
    coleccion_tmf = ee.ImageCollection(TMF_ASSET).filterBounds(geometria)
    proyeccion_tmf = (
        ee.Image(coleccion_tmf.first())
        .select(f"Dec{anio}")
        .projection()
    )
    return (
        coleccion_tmf
        .mosaic()
        .select(f"Dec{anio}")
        .setDefaultProjection(proyeccion_tmf)
        .rename(f"tmf_{anio}")
        .clip(geometria)
    )


def obtener_esri(anio, geometria):
    anio_seguro = max(ANO_ESRI_MIN, min(ANO_ESRI_MAX, anio))
    coleccion_esri = (
        ee.ImageCollection(ESRI_ASSET)
        .filterBounds(geometria)
        .filterDate(f"{anio_seguro}-01-01", f"{anio_seguro}-12-31")
    )
    proyeccion_esri = ee.Image(coleccion_esri.first()).select(0).projection()
    return (
        coleccion_esri
        .mosaic()
        .select(0)
        .setDefaultProjection(proyeccion_esri)
        .rename(f"esri_{anio_seguro}")
        .clip(geometria)
    )


def obtener_esri_visual(anio, geometria):
    return (
        obtener_esri(anio, geometria)
        .remap(ESRI_ORIG, ESRI_VIS)
        .rename(f"esri_visual_{anio}")
        .selfMask()
    )


def mascara_sentinel_scl(imagen):
    scl = imagen.select("SCL")
    mascara = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(11))
    return imagen.updateMask(mascara).select(["B8", "B4"]).toFloat()


def mascara_sentinel_rgb(imagen):
    scl = imagen.select("SCL")
    mascara = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(11))
    return imagen.updateMask(mascara).select(["B4", "B3", "B2"]).toFloat()


def obtener_rgb_sentinel(anio, geometria):
    coleccion = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometria)
        .filterDate(f"{anio}-01-01", f"{anio}-12-31")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .map(mascara_sentinel_rgb)
    )
    respaldo = (
        ee.Image.constant([0, 0, 0])
        .rename(["B4", "B3", "B2"])
        .updateMask(ee.Image(0))
        .toFloat()
    )
    return (
        coleccion.merge(ee.ImageCollection.fromImages([respaldo]))
        .median()
        .clip(geometria)
    )


def obtener_ndvi(anio, geometria):
    anio_respaldo = max(anio - 1, 2017)

    def coleccion(anio_consulta):
        return (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(geometria)
            .filterDate(f"{anio_consulta}-01-01", f"{anio_consulta}-12-31")
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
            .map(mascara_sentinel_scl)
        )

    fallback = (
        ee.Image.constant([0, 0])
        .rename(["B8", "B4"])
        .updateMask(ee.Image(0))
        .toFloat()
    )

    def mediana_con_fallback(coleccion_s2):
        return coleccion_s2.merge(
            ee.ImageCollection.fromImages([fallback])
        ).median()

    actual = mediana_con_fallback(coleccion(anio))
    anterior = mediana_con_fallback(coleccion(anio_respaldo))
    compuesto = ee.ImageCollection.fromImages(
        [fallback, anterior, actual]
    ).mosaic()

    return (
        compuesto.normalizedDifference(["B8", "B4"])
        .rename(f"ndvi_{anio}")
        .toFloat()
        .clip(geometria)
    )


def clasificar_ndvi(ndvi):
    clases = (
        ee.Image(0)
        .where(ndvi.lt(0.0), 0)
        .where(ndvi.gte(0.0).And(ndvi.lt(0.2)), 1)
        .where(ndvi.gte(0.2).And(ndvi.lt(0.4)), 2)
        .where(ndvi.gte(0.4).And(ndvi.lt(0.6)), 3)
        .where(ndvi.gte(0.6), 4)
    )
    return clases.updateMask(ndvi.mask()).rename("ndvi_clases").toInt()


def imagenes_hansen(geometria):
    hansen = ee.Image(HANSEN_ASSET)
    cobertura_2000 = hansen.select("treecover2000").unmask(0).gte(30)
    perdida = hansen.select("loss").unmask(0)
    anio_perdida = hansen.select("lossyear")

    perdida_post = (
        anio_perdida.updateMask(anio_perdida.gt(CUTOFF_YEAR))
        .rename("perdida_post")
        .clip(geometria)
    )
    perdida_pre = (
        anio_perdida.updateMask(
            anio_perdida.gt(0).And(anio_perdida.lte(CUTOFF_YEAR))
        )
        .rename("perdida_pre")
        .clip(geometria)
    )
    linea_base = (
        cobertura_2000.And(
            perdida.eq(0).Or(anio_perdida.unmask(0).gt(CUTOFF_YEAR))
        )
        .selfMask()
        .rename("linea_base_2020")
        .clip(geometria)
    )
    return perdida_post, perdida_pre, linea_base


def imagen_coincidencia_revision(
    geometria,
    tmf=None,
    perdida_post=None,
    esri_inicial=None,
    esri_final=None,
):
    """Estandariza tres señales de deterioro en la malla JRC de 30 m."""
    if tmf is None:
        tmf = obtener_tmf(ANO_DIAG_TMF, geometria)
    if perdida_post is None:
        perdida_post, _, _ = imagenes_hansen(geometria)
    if esri_inicial is None:
        esri_inicial = obtener_esri(ANO_ESRI_MIN, geometria)
    if esri_final is None:
        esri_final = obtener_esri(ANO_ESRI_MAX, geometria)

    proyeccion_referencia = ee.Image(tmf).projection()
    proyeccion_esri = ee.Image(esri_inicial).projection()
    senal_jrc = (
        ee.Image(tmf)
        .eq(2)
        .Or(ee.Image(tmf).eq(3))
        .unmask(0)
        .rename("senal_jrc")
    )
    senal_hansen = (
        ee.Image(perdida_post)
        .gt(0)
        .unmask(0)
        .reproject(crs=proyeccion_referencia)
        .rename("senal_hansen")
    )
    senal_esri_10m = (
        ee.Image(esri_inicial)
        .eq(2)
        .And(ee.Image(esri_final).neq(2))
        .unmask(0)
        .setDefaultProjection(proyeccion_esri)
    )
    senal_esri = (
        senal_esri_10m.reduceResolution(
            reducer=ee.Reducer.max(),
            bestEffort=True,
            maxPixels=1024,
        )
        .reproject(crs=proyeccion_referencia)
        .gt(0)
        .rename("senal_esri")
    )
    return (
        senal_jrc.add(senal_hansen)
        .add(senal_esri)
        .rename("fuentes_coincidentes")
        .toByte()
        .clip(geometria)
    )


def imagen_gedi(geometria):
    return (
        ee.ImageCollection(GEDI_ASSET)
        .filterBounds(geometria)
        .mosaic()
        .select(0)
        .rename("altura_dosel")
        .clip(geometria)
    )


def capa_gee(
    mapa,
    imagen,
    visualizacion,
    nombre,
    mostrar=True,
    opacidad=1.0,
    control=True,
    z_index=None,
):
    datos = ee.Image(imagen).getMapId(visualizacion)
    opciones_capa = {}
    if z_index is not None:
        opciones_capa["z_index"] = int(z_index)
    capa = folium.TileLayer(
        tiles=datos["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=nombre,
        overlay=True,
        control=control,
        show=mostrar,
        opacity=opacidad,
        **opciones_capa,
    )
    capa.add_to(mapa)
    return capa


def agregar_rotulos_comparador(mapa, limites, etiqueta_inicial, etiqueta_final):
    (sur, oeste), (norte, este) = limites
    margen_latitud = (norte - sur) * 0.045
    margen_longitud = (este - oeste) * 0.035
    latitud = norte - margen_latitud
    estilo = (
        "background:rgba(17,50,74,.92);color:white;padding:7px 10px;"
        "border:2px solid white;border-radius:6px;box-shadow:0 2px 7px rgba(0,0,0,.35);"
        "font:12px Arial,sans-serif;line-height:1.25;white-space:nowrap;"
    )
    folium.Marker(
        location=[latitud, oeste + margen_longitud],
        icon=folium.DivIcon(
            class_name="rotulo-comparador-mapa",
            icon_size=(185, 48),
            icon_anchor=(0, 0),
            html=(
                f'<div style="{estilo}"><span style="font-size:10px;">◀ AÑO INICIAL</span>'
                f'<br><b>{etiqueta_inicial}</b></div>'
            ),
        ),
        z_index_offset=1000,
    ).add_to(mapa)
    folium.Marker(
        location=[latitud, este - margen_longitud],
        icon=folium.DivIcon(
            class_name="rotulo-comparador-mapa",
            icon_size=(185, 48),
            icon_anchor=(185, 0),
            html=(
                f'<div style="{estilo}text-align:right;"><span style="font-size:10px;">'
                f'AÑO FINAL ▶</span><br><b>{etiqueta_final}</b></div>'
            ),
        ),
        z_index_offset=1000,
    ).add_to(mapa)


# -----------------------------------------------------------------------------
# Análisis bajo demanda
# -----------------------------------------------------------------------------

def numero(diccionario, clave):
    valor = diccionario.get(clave)
    return float(valor) if valor is not None else 0.0


def reducir_superficies(imagen, geometria, escala, proyeccion=None):
    parametros = {
        "reducer": ee.Reducer.sum(),
        "geometry": geometria,
        "scale": escala,
        "bestEffort": True,
        "maxPixels": 1e9,
        "tileScale": 4,
    }
    if proyeccion is not None:
        parametros["crs"] = proyeccion
    return ee.Dictionary(imagen.reduceRegion(**parametros))


@st.cache_data(ttl=3600, show_spinner=False)
def analizar_corredores_cache(aoi_geojson_serializado):
    return analizar_interseccion_corredores(json.loads(aoi_geojson_serializado))


@st.cache_data(ttl=3600, show_spinner=False)
def analizar_bosque_asset_cache(
    asset_id,
    aoi_geojson_serializado,
    umbral_m,
    area_min_ha,
):
    aoi_geojson = json.loads(aoi_geojson_serializado)
    aoi_ee = ee.Geometry(aoi_geojson)
    bosque_en_area = ee.FeatureCollection(asset_id).filterBounds(aoi_ee)
    if int(bosque_en_area.size().getInfo()) == 0:
        geometria_bosque = {"type": "FeatureCollection", "features": []}
    else:
        geometria_bosque = (
            bosque_en_area.geometry(1).intersection(aoi_ee, 1).getInfo()
        )
    return analizar_fragmentacion_geojson(
        bosque_geojson=geometria_bosque,
        aoi_geojson=aoi_geojson,
        umbral_m=umbral_m,
        area_min_ha=area_min_ha,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def ejecutar_analisis(
    tipo_area,
    finca_id,
    anio_tmf_diagnostico,
    anio_esri_inicial,
    anio_esri_final,
    geometria_geojson=None,
):
    area_fc = obtener_area(tipo_area, finca_id, geometria_geojson)
    geometria = area_fc.geometry()

    tmf = obtener_tmf(anio_tmf_diagnostico, geometria)
    esri_inicial = obtener_esri(anio_esri_inicial, geometria)
    esri_final = obtener_esri(anio_esri_final, geometria)
    perdida_post, perdida_pre, linea_base = imagenes_hansen(geometria)
    coincidencia_revision = imagen_coincidencia_revision(
        geometria,
        tmf=tmf,
        perdida_post=perdida_post,
        esri_inicial=esri_inicial,
        esri_final=esri_final,
    )
    gedi = imagen_gedi(geometria)
    pixel_ha = ee.Image.pixelArea().divide(10000)

    # Cada fuente se reduce en su propia resolución y proyección. Esto evita
    # forzar los datos ESRI de 10 m a la malla de los productos de 30 m.
    areas_tmf = ee.Image.cat(
        [
            tmf.eq(1).unmask(0).multiply(pixel_ha).rename("tmf_estable"),
            tmf.eq(2).unmask(0).multiply(pixel_ha).rename("tmf_degradacion"),
            tmf.eq(3).unmask(0).multiply(pixel_ha).rename("tmf_deforestacion"),
            tmf.eq(4).unmask(0).multiply(pixel_ha).rename("tmf_recuperacion"),
            tmf.eq(5).unmask(0).multiply(pixel_ha).rename("tmf_agua"),
            tmf.eq(6).unmask(0).multiply(pixel_ha).rename("tmf_otra_cobertura"),
            coincidencia_revision.eq(1).unmask(0).multiply(pixel_ha).rename(
                "coincidencia_1_fuente"
            ),
            coincidencia_revision.eq(2).unmask(0).multiply(pixel_ha).rename(
                "coincidencia_2_fuentes"
            ),
            coincidencia_revision.eq(3).unmask(0).multiply(pixel_ha).rename(
                "coincidencia_3_fuentes"
            ),
        ]
    )
    areas_hansen = ee.Image.cat(
        [
            perdida_post.gt(0).unmask(0).multiply(pixel_ha).rename("hansen_post"),
            perdida_pre.gt(0).unmask(0).multiply(pixel_ha).rename("hansen_pre"),
            linea_base.unmask(0).multiply(pixel_ha).rename("linea_base"),
        ]
    )
    areas_esri = ee.Image.cat(
        [
            esri_final.eq(2).unmask(0).multiply(pixel_ha).rename("esri_arboles_final"),
            esri_inicial.eq(2).And(esri_final.neq(2)).unmask(0).multiply(pixel_ha).rename("esri_salida"),
            esri_inicial.neq(2).And(esri_final.eq(2)).unmask(0).multiply(pixel_ha).rename("esri_ganancia"),
            esri_inicial.eq(2).And(esri_final.eq(2)).unmask(0).multiply(pixel_ha).rename("esri_estable"),
        ]
    )

    # Las reducciones conservan la escala y proyección de cada fuente, pero se
    # agrupan en una sola respuesta para evitar varios viajes de red consecutivos.
    resumen = (
        reducir_superficies(areas_tmf, geometria, 30, tmf.projection())
        .combine(
            reducir_superficies(
                areas_hansen,
                geometria,
                30,
                ee.Image(HANSEN_ASSET).projection(),
            ),
            True,
        )
        .combine(
            reducir_superficies(
                areas_esri,
                geometria,
                10,
                esri_final.projection(),
            ),
            True,
        )
        .combine(
            ee.Dictionary(
                {
                    "area_ha": geometria.area(1).divide(10000),
                    "gedi_altura": gedi.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geometria,
                        scale=100,
                        bestEffort=True,
                        maxPixels=1e9,
                        tileScale=4,
                    ).get("altura_dosel"),
                    "gedi_area_datos": gedi.mask()
                    .multiply(pixel_ha)
                    .reduceRegion(
                        reducer=ee.Reducer.sum(),
                        geometry=geometria,
                        scale=100,
                        bestEffort=True,
                        maxPixels=1e9,
                        tileScale=4,
                    )
                    .get("altura_dosel"),
                }
            ),
            True,
        )
        .getInfo()
    )

    claves_areas = [
        "tmf_estable",
        "tmf_degradacion",
        "tmf_deforestacion",
        "tmf_recuperacion",
        "tmf_agua",
        "tmf_otra_cobertura",
        "coincidencia_1_fuente",
        "coincidencia_2_fuentes",
        "coincidencia_3_fuentes",
        "hansen_post",
        "hansen_pre",
        "linea_base",
        "esri_arboles_final",
        "esri_salida",
        "esri_ganancia",
        "esri_estable",
    ]
    resultados = {clave: numero(resumen, clave) for clave in claves_areas}
    area_ha = numero(resumen, "area_ha")
    resultados["area_ha"] = area_ha
    resultados["gedi_altura"] = numero(resumen, "gedi_altura")
    resultados["gedi_area_datos"] = numero(resumen, "gedi_area_datos")
    resultados["gedi_cobertura_pct"] = (
        resultados["gedi_area_datos"] / area_ha * 100 if area_ha else 0
    )
    resultados["coincidencia_varias_fuentes"] = (
        resultados["coincidencia_2_fuentes"]
        + resultados["coincidencia_3_fuentes"]
    )
    resultados["pct_coincidencia_varias_fuentes"] = (
        resultados["coincidencia_varias_fuentes"] / area_ha * 100
        if area_ha
        else 0
    )

    pct_tmf_defor = resultados["tmf_deforestacion"] / area_ha * 100 if area_ha else 0
    pct_tmf_degrad = resultados["tmf_degradacion"] / area_ha * 100 if area_ha else 0
    pct_tmf_recuperacion = (
        resultados["tmf_recuperacion"] / area_ha * 100 if area_ha else 0
    )
    pct_esri_salida = resultados["esri_salida"] / area_ha * 100 if area_ha else 0
    pct_esri_ganancia = (
        resultados["esri_ganancia"] / area_ha * 100 if area_ha else 0
    )
    pct_linea_base = resultados["linea_base"] / area_ha * 100 if area_ha else 0

    senales, gedi_disponible = evaluar_senales(
        tmf_deforestacion_ha=resultados["tmf_deforestacion"],
        tmf_deforestacion_pct=pct_tmf_defor,
        tmf_degradacion_ha=resultados["tmf_degradacion"],
        tmf_degradacion_pct=pct_tmf_degrad,
        hansen_post_2020_ha=resultados["hansen_post"],
        esri_salida_arboles_ha=resultados["esri_salida"],
        esri_salida_arboles_pct=pct_esri_salida,
        gedi_altura_media_m=resultados["gedi_altura"],
        gedi_cobertura_valida_pct=resultados["gedi_cobertura_pct"],
        linea_base_arborea_pct=pct_linea_base,
    )
    senal_tmf = senales["tmf"]
    senal_hansen = senales["hansen"]
    senal_esri = senales["esri"]
    senal_gedi = senales["gedi"]

    aportes_indice, puntaje, prioridad = calcular_indice_prioridad(
        senal_tmf=senal_tmf,
        senal_hansen=senal_hansen,
        senal_esri=senal_esri,
        senal_gedi=senal_gedi,
    )
    consistencia = evaluar_consistencia(
        senal_tmf=senal_tmf,
        senal_hansen=senal_hansen,
        senal_esri=senal_esri,
        tmf_recuperacion_ha=resultados["tmf_recuperacion"],
        tmf_recuperacion_pct=pct_tmf_recuperacion,
        esri_ganancia_arboles_ha=resultados["esri_ganancia"],
        esri_ganancia_arboles_pct=pct_esri_ganancia,
    )

    resultados.update(
        {
            "pct_tmf_defor": pct_tmf_defor,
            "pct_tmf_degrad": pct_tmf_degrad,
            "pct_tmf_recuperacion": pct_tmf_recuperacion,
            "pct_esri_salida": pct_esri_salida,
            "pct_esri_ganancia": pct_esri_ganancia,
            "pct_linea_base": pct_linea_base,
            "senal_tmf": senal_tmf,
            "senal_hansen": senal_hansen,
            "senal_esri": senal_esri,
            "senal_gedi": senal_gedi,
            "gedi_disponible": gedi_disponible,
            "aportes_indice": aportes_indice,
            "puntaje": puntaje,
            "prioridad": prioridad,
            "consistencia": consistencia,
        }
    )
    return resultados


def texto_recomendacion(prioridad):
    return {
        "Alta": "Visita de campo prioritaria en los sectores con señales coincidentes.",
        "Media": "Revisar imágenes recientes y evaluar si se justifica una visita.",
        "Preventiva": "Mantener monitoreo periódico y revisar condiciones de riesgo.",
        "Baja": "Sin acción inmediata. Continuar el monitoreo anual normal.",
    }[prioridad]


def visualizar_con_borde(imagen, visualizacion, area_fc, fondo=None):
    visual = ee.Image(imagen).visualize(**visualizacion)
    if fondo is not None:
        visual = ee.Image(fondo).visualize(**VIS_RGB).blend(visual)
    borde = (
        ee.Image()
        .byte()
        .paint(featureCollection=area_fc, color=1, width=4)
        .selfMask()
        .visualize(min=1, max=1, palette=["00E5FF"])
    )
    return visual.blend(borde)


def crear_url_miniatura(imagen, region, dimension):
    """Solicita a Earth Engine una URL temporal sin descargar todavía el PNG."""
    return ee.Image(imagen).getThumbURL(
        {
            "region": region,
            # Una dimensión conserva la proporción original del territorio.
            "dimensions": dimension,
            "format": "png",
        }
    )


def descargar_url_miniatura(url):
    """Descarga y valida una miniatura ya preparada por Earth Engine."""
    respuesta = requests.get(
        url,
        timeout=(10, 60),
        headers={"User-Agent": "visor-preevaluacion-territorial/1.0"},
    )
    respuesta.raise_for_status()
    if len(respuesta.content) < 1000 or not respuesta.content.startswith(b"\x89PNG"):
        raise RuntimeError("respuesta PNG no válida")
    return respuesta.content


def descargar_miniaturas(especificaciones, geometria, mapas_existentes=None):
    """Descarga los mapas en paralelo y reintenta únicamente los que fallan."""
    # Antes se consultaban estos límites una vez por cada mapa. Una sola consulta
    # reduce siete viajes innecesarios a Earth Engine.
    region = geometria.bounds(1).coordinates().getInfo()
    existentes_por_titulo = {
        mapa["titulo"]: mapa
        for mapa in (mapas_existentes or [])
        if mapa.get("imagen")
    }
    resultados = [
        existentes_por_titulo.get(titulo)
        for titulo, _, _ in especificaciones
    ]
    pendientes = {
        indice for indice, resultado in enumerate(resultados) if resultado is None
    }
    fallos = {indice: [] for indice in pendientes}

    # 1200 px conserva buena definición para el PDF. El segundo intento a 800 px
    # reduce el costo solo cuando Earth Engine no logra servir el mapa principal.
    for dimension in (1200, 800):
        if not pendientes:
            break

        urls = {}
        for indice in list(pendientes):
            titulo, imagen, _ = especificaciones[indice]
            try:
                urls[indice] = crear_url_miniatura(imagen, region, dimension)
            except Exception as error:
                fallos[indice].append(
                    f"{dimension}px al solicitar: {type(error).__name__}"
                )

        if not urls:
            continue

        # Tres solicitudes simultáneas acortan la espera sin saturar la cuota de
        # Earth Engine ni la memoria limitada de Streamlit Community Cloud.
        trabajadores = min(3, len(urls))
        with ThreadPoolExecutor(max_workers=trabajadores) as ejecutor:
            futuros = {
                ejecutor.submit(descargar_url_miniatura, url): indice
                for indice, url in urls.items()
            }
            for futuro in as_completed(futuros):
                indice = futuros[futuro]
                titulo, _, leyenda = especificaciones[indice]
                try:
                    resultados[indice] = {
                        "titulo": titulo,
                        "imagen": futuro.result(),
                        "leyenda": leyenda,
                    }
                    pendientes.discard(indice)
                except Exception as error:
                    # No se registran la URL ni sus tokens temporales.
                    fallos[indice].append(f"{dimension}px: {type(error).__name__}")

    errores = []
    for indice in sorted(pendientes):
        titulo, _, leyenda = especificaciones[indice]
        resultados[indice] = {"titulo": titulo, "imagen": None, "leyenda": leyenda}
        errores.append(
            f"{titulo}: Miniatura no disponible después de reintentos "
            f"({', '.join(fallos[indice]) or 'sin respuesta'})."
        )
    return resultados, errores


@st.cache_data(ttl=3600, show_spinner=False)
def generar_mapas_reporte(
    tipo_area,
    finca_id,
    anio_tmf_diagnostico,
    anio_esri_inicial,
    anio_esri_final,
    anio_ndvi_inicial,
    geometria_geojson=None,
    intento_cache=0,
    _mapas_existentes=None,
):
    # El número de intento forma parte de la clave de caché y permite reintentar
    # si Earth Engine no entrega alguna miniatura temporalmente.
    _ = intento_cache
    area_fc = obtener_area(tipo_area, finca_id, geometria_geojson)
    geometria = area_fc.geometry()
    tmf = obtener_tmf(anio_tmf_diagnostico, geometria)
    gedi = imagen_gedi(geometria)
    ndvi_final = obtener_ndvi(ANO_NDVI_MAX, geometria)
    ndvi_inicial = obtener_ndvi(anio_ndvi_inicial, geometria)
    delta_ndvi = ndvi_final.subtract(ndvi_inicial).rename("delta_ndvi")

    hansen = ee.Image(HANSEN_ASSET).select("lossyear")
    rgb = obtener_rgb_sentinel(ANO_NDVI_MAX, geometria)
    perdida_post, _, _ = imagenes_hansen(geometria)
    coincidencia_revision = imagen_coincidencia_revision(
        geometria,
        tmf=tmf,
        perdida_post=perdida_post,
        esri_inicial=obtener_esri(ANO_ESRI_MIN, geometria),
        esri_final=obtener_esri(ANO_ESRI_MAX, geometria),
    )

    especificaciones = [
        (
            f"ESRI - Uso y cobertura {anio_esri_final}",
            visualizar_con_borde(
                obtener_esri_visual(anio_esri_final, geometria),
                VIS_ESRI,
                area_fc,
            ),
            "Azul: agua | Verde: árboles | Amarillo: cultivos | Rojo: construido | Beige: pastizal",
        ),
        (
            f"JRC TMF - Estado forestal {anio_tmf_diagnostico}",
            visualizar_con_borde(tmf, VIS_TMF, area_fc),
            "Verde oscuro: bosque estable | Amarillo: degradación | Rojo: deforestación | Verde claro: recuperación",
        ),
        (
            f"Hansen - Pérdida arbórea 2001-{ANO_HANSEN_MAX}",
            visualizar_con_borde(
                hansen.updateMask(hansen.gt(0)).clip(geometria),
                VIS_HANSEN_TOTAL,
                area_fc,
                fondo=rgb,
            ),
            "Amarillo: pérdida antigua | Naranja: intermedia | Rojo oscuro: pérdida más reciente",
        ),
        (
            "GEDI - Altura del dosel",
            visualizar_con_borde(gedi, VIS_GEDI, area_fc),
            "Amarillo claro: dosel bajo | Verde medio: dosel intermedio | Verde oscuro: dosel alto",
        ),
        (
            f"ΔNDVI - Cambio de vigor {anio_ndvi_inicial}-{ANO_NDVI_MAX}",
            visualizar_con_borde(delta_ndvi, VIS_NDVI_DELTA, area_fc),
            "Rojo: disminución de vigor | Crema: cambio pequeño | Verde: aumento de vigor",
        ),
        (
            f"Vigor vegetal NDVI - {ANO_NDVI_MAX}",
            visualizar_con_borde(
                clasificar_ndvi(ndvi_final),
                VIS_NDVI_CLASES,
                area_fc,
            ),
            "Rojo: NDVI inferior a 0, sin vegetación activa | Rosado: NDVI 0.0 a menos de 0.2, suelo o cobertura muy escasa | Amarillo: NDVI 0.2 a menos de 0.4, vegetación escasa | Verde claro: NDVI 0.4 a menos de 0.6, vegetación moderada | Verde oscuro: NDVI mayor o igual a 0.6, vegetación densa",
        ),
        (
            "Sectores que requieren revisión - Coincidencia espacial",
            visualizar_con_borde(
                coincidencia_revision.updateMask(coincidencia_revision.gt(0)),
                VIS_COINCIDENCIA_REVISION,
                area_fc,
                fondo=rgb,
            ),
            (
                "Amarillo: señal de 1 fuente | Naranja: coincidencia de 2 fuentes | "
                "Rojo oscuro: coincidencia de 3 fuentes. Integra JRC TMF 2025, "
                "Hansen posterior a 2020 y ESRI 2017-2024 en una malla común de "
                "30 m. GEDI y NDVI no participan; el mapa no modifica el índice."
            ),
        ),
    ]

    return descargar_miniaturas(especificaciones, geometria, _mapas_existentes)


# -----------------------------------------------------------------------------
# PDF institucional
# -----------------------------------------------------------------------------

def generar_pdf(
    nombre_area,
    resultados,
    anio_tmf_diagnostico,
    anio_esri_inicial,
    anio_esri_final,
    anio_ndvi_inicial,
    mapas=None,
):
    memoria = BytesIO()
    documento = SimpleDocTemplate(
        memoria,
        pagesize=A4,
        rightMargin=1.55 * cm,
        leftMargin=1.55 * cm,
        topMargin=1.55 * cm,
        bottomMargin=1.6 * cm,
        title="Ficha de evaluación territorial y corredores",
        author="Aplicación de evaluación territorial y corredores",
    )

    verde = colors.HexColor("#244d23")
    verde_claro = colors.HexColor("#e8f0e3")
    borde = colors.HexColor("#8aa684")
    estilos = getSampleStyleSheet()
    estilos.add(
        ParagraphStyle(
            name="TituloFicha",
            parent=estilos["Title"],
            fontName="Times-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_CENTER,
            textColor=verde,
            spaceAfter=8,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="SubtituloFicha",
            parent=estilos["BodyText"],
            fontName="Times-Italic",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4d5f4c"),
            spaceAfter=10,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="SeccionFicha",
            parent=estilos["Heading2"],
            fontName="Times-Bold",
            fontSize=10.5,
            leading=13,
            textColor=verde,
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="CuerpoFicha",
            parent=estilos["BodyText"],
            fontName="Times-Roman",
            fontSize=9.2,
            leading=12.2,
            alignment=4,
            spaceAfter=5,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="MapaTitulo",
            parent=estilos["BodyText"],
            fontName="Times-Bold",
            fontSize=8.6,
            leading=10,
            alignment=TA_CENTER,
            textColor=verde,
            spaceAfter=3,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="MapaNota",
            parent=estilos["BodyText"],
            fontName="Times-Roman",
            fontSize=6.8,
            leading=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4d4d4d"),
        )
    )
    estilos.add(
        ParagraphStyle(
            name="CabeceraTabla",
            parent=estilos["BodyText"],
            fontName="Times-Bold",
            fontSize=8.8,
            leading=10,
            textColor=colors.white,
        )
    )

    r = resultados
    aportes = r["aportes_indice"]
    texto_justificacion_pesos = " ".join(
        JUSTIFICACION_PESOS[fuente]
        for fuente in ("tmf", "hansen", "esri", "gedi", "ndvi")
    )
    texto_justificacion_umbrales = " ".join(
        JUSTIFICACION_UMBRALES[criterio]
        for criterio in (
            "hansen_post_2020_ha",
            "jrc_deforestacion",
            "jrc_degradacion",
            "esri_salida_arboles",
            "gedi_dosel_y_cobertura",
            "ndvi",
        )
    )
    texto_clases_ndvi = "; ".join(
        f"{clase['etiqueta']} ({clase['rango']})"
        for clase in CLASES_VIGOR_NDVI
    )
    area = r["area_ha"]
    pct_arbol = r["esri_arboles_final"] / area * 100 if area else 0
    pct_ganancia = r["esri_ganancia"] / area * 100 if area else 0
    fuentes = sum(
        [r["senal_tmf"], r["senal_esri"], r["senal_hansen"], r["senal_gedi"]]
    )
    descripcion_cobertura = (
        "mantiene una cobertura arbórea importante"
        if pct_arbol >= 50
        else "presenta una cobertura arbórea limitada"
        if pct_arbol < 20
        else "combina áreas arboladas y áreas productivas"
    )
    resultado_general = (
        "señales de pérdida o deterioro"
        if fuentes >= 2
        else "una señal localizada de cambio"
        if fuentes == 1
        else "ninguna señal relevante de deterioro reciente"
    )
    coincidencia = (
        f"{r['consistencia']['nivel']}: {r['consistencia']['detalle']}"
    )
    texto_coincidencia_espacial = (
        f"El mapa 7 ubica {r['coincidencia_1_fuente']:.2f} ha con señal de una "
        f"fuente, {r['coincidencia_2_fuentes']:.2f} ha con coincidencia de dos "
        f"fuentes y {r['coincidencia_3_fuentes']:.2f} ha con coincidencia de tres. "
        f"Priorice las {r['coincidencia_varias_fuentes']:.2f} ha señaladas por dos "
        "o tres fuentes. Esta superposición no modifica el índice y no demuestra "
        "por sí sola la causa del cambio."
    )
    texto_dosel = (
        f"La altura promedio del dosel fue de {r['gedi_altura']:.1f} m. "
        f"El {r['gedi_cobertura_pct']:.0f}% del área presentó datos válidos en el producto de altura."
        if r["gedi_disponible"]
        else "El producto de altura del dosel no presenta información suficiente para interpretar esta área."
    )

    historia = [
        Paragraph("FICHA DE EVALUACIÓN TERRITORIAL Y CORREDORES", estilos["TituloFicha"]),
        Paragraph(
            "Documento indicativo para orientar revisiones territoriales. No determina cumplimiento EUDR.",
            estilos["SubtituloFicha"],
        ),
    ]
    datos = [
        [Paragraph("Área evaluada", estilos["CuerpoFicha"]), Paragraph(nombre_area, estilos["CuerpoFicha"])],
        [Paragraph("Superficie total", estilos["CuerpoFicha"]), Paragraph(f"{area:,.2f} ha", estilos["CuerpoFicha"])],
        [Paragraph("Fecha del análisis", estilos["CuerpoFicha"]), Paragraph(date.today().strftime("%d/%m/%Y"), estilos["CuerpoFicha"])],
        [
            Paragraph("Referencia metodológica", estilos["CuerpoFicha"]),
            Paragraph(
                f"JRC: estado {ANO_DIAG_TMF}; Hansen: pérdida 2021-{ANO_HANSEN_MAX} "
                f"posterior al corte {CUTOFF_LABEL}; ESRI: {ANO_ESRI_MIN}-{ANO_ESRI_MAX}",
                estilos["CuerpoFicha"],
            ),
        ],
        [
            Paragraph("Apoyo visual", estilos["CuerpoFicha"]),
            Paragraph(
                f"NDVI {anio_ndvi_inicial}-{ANO_NDVI_MAX}; no modifica el índice",
                estilos["CuerpoFicha"],
            ),
        ],
        [
            Paragraph("Metodología aplicada", estilos["CuerpoFicha"]),
            Paragraph(
                METHODOLOGY_VERSION,
                estilos["CuerpoFicha"],
            ),
        ],
    ]
    tabla = Table(datos, colWidths=[4.0 * cm, 12.5 * cm])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), verde_claro),
                ("FONTNAME", (0, 0), (0, -1), "Times-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Times-Roman"),
                ("GRID", (0, 0), (-1, -1), 0.4, borde),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    historia.extend([tabla, Spacer(1, 7)])

    visita = r.get("prioridad_visita")
    prioridad_pdf = visita["prioridad_visita"] if visita else r["prioridad"]
    accion_pdf = (
        texto_recomendacion_visita(prioridad_pdf)
        if visita
        else texto_recomendacion(prioridad_pdf)
    )
    detalle_puntaje_pdf = (
        f"Cambios: {visita['puntaje_cambios']:.1f}/{PUNTAJE_MAXIMO:.1f}; "
        f"corredor: +{visita['aporte_corredor']:.2f}; "
        f"estructura 2021: {visita['contexto_estructural']['estado']} (sin puntos); "
        f"total: {visita['puntaje_integrado']:.2f}/{PUNTAJE_MAXIMO_VISITA:.1f}"
        if visita
        else f"Índice operativo: {r['puntaje']:.1f}/{PUNTAJE_MAXIMO:.1f}"
    )
    color_prioridad = {
        "Muy alta": "#7f0000",
        "Alta": "#b71c1c",
        "Media": "#e65100",
        "Preventiva": "#b8860b",
        "Baja": "#2e7d32",
    }[prioridad_pdf]
    tarjeta_prioridad = Table(
        [[Paragraph(
            f"<b>PRIORIDAD {prioridad_pdf.upper()} DE VISITA</b><br/>"
            f"{detalle_puntaje_pdf} - {accion_pdf}",
            ParagraphStyle(
                "Prioridad",
                fontName="Times-Roman",
                fontSize=9.5,
                leading=12,
                textColor=colors.white,
            ),
        )]],
        colWidths=[16.5 * cm],
    )
    tarjeta_prioridad.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color_prioridad)),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(color_prioridad)),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    metricas = Table(
        [
            [
                Paragraph("Cobertura clasificada como árboles", estilos["CuerpoFicha"]),
                Paragraph(f"<b>{r['esri_arboles_final']:.1f} ha ({pct_arbol:.1f}%)</b>", estilos["CuerpoFicha"]),
                Paragraph("Pérdida posterior a 2020", estilos["CuerpoFicha"]),
                Paragraph(f"<b>{r['hansen_post']:.2f} ha</b>", estilos["CuerpoFicha"]),
            ],
            [
                Paragraph("Deforestación señalada por JRC", estilos["CuerpoFicha"]),
                Paragraph(f"<b>{r['tmf_deforestacion']:.1f} ha</b>", estilos["CuerpoFicha"]),
                Paragraph("Altura promedio del dosel", estilos["CuerpoFicha"]),
                Paragraph(
                    f"<b>{r['gedi_altura']:.1f} m</b>" if r["gedi_disponible"] else "Datos insuficientes",
                    estilos["CuerpoFicha"],
                ),
            ],
            [
                Paragraph("Cobertura arbórea persistente a 2020", estilos["CuerpoFicha"]),
                Paragraph(
                    f"<b>{r['linea_base']:.1f} ha ({r['pct_linea_base']:.1f}%)</b>",
                    estilos["CuerpoFicha"],
                ),
                Paragraph("Pérdida Hansen 2001-2020", estilos["CuerpoFicha"]),
                Paragraph(f"<b>{r['hansen_pre']:.2f} ha</b>", estilos["CuerpoFicha"]),
            ],
            [
                Paragraph("Señal espacial de una fuente", estilos["CuerpoFicha"]),
                Paragraph(
                    f"<b>{r['coincidencia_1_fuente']:.2f} ha</b>",
                    estilos["CuerpoFicha"],
                ),
                Paragraph("Coincidencia de dos o tres fuentes", estilos["CuerpoFicha"]),
                Paragraph(
                    f"<b>{r['coincidencia_varias_fuentes']:.2f} ha "
                    f"({r['pct_coincidencia_varias_fuentes']:.2f}%)</b>",
                    estilos["CuerpoFicha"],
                ),
            ],
        ],
        colWidths=[4.6 * cm, 3.0 * cm, 4.6 * cm, 3.0 * cm],
    )
    metricas.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, borde),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7faf6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    historia.extend([tarjeta_prioridad, Spacer(1, 5), metricas, Spacer(1, 3)])

    secciones = [
        (
            "RESULTADO GENERAL",
            f"El área {descripcion_cobertura}. El análisis identificó {resultado_general}. "
            "Este resultado no confirma por sí solo que haya ocurrido deforestación. "
            "Su función es señalar sectores que requieren una revisión más detallada.",
        ),
        (
            "¿QUÉ SE ENCONTRÓ?",
            f"<b>1. Estado actual de la cobertura.</b> En {anio_esri_final} se identificaron "
            f"{r['esri_arboles_final']:.1f} ha con cobertura clasificada como árboles, "
            f"aproximadamente {pct_arbol:.1f}% del área.<br/><br/>"
            f"<b>2. Cambios que requieren atención.</b> Entre {anio_esri_inicial} y "
            f"{anio_esri_final}, {r['esri_salida']:.1f} ha pasaron de árboles a otra "
            f"cobertura ({r['pct_esri_salida']:.1f}% del área), mientras "
            f"{r['esri_ganancia']:.1f} ha pasaron a árboles ({pct_ganancia:.1f}%). "
            f"Hansen registró {r['hansen_post']:.2f} ha de pérdida después del "
            f"{CUTOFF_LABEL}. {coincidencia}<br/><br/>"
            f"<b>3. Condición del bosque y la vegetación.</b> JRC TMF {anio_tmf_diagnostico} registró "
            f"{r['tmf_estable']:.1f} ha de bosque estable, {r['tmf_degradacion']:.1f} ha "
            f"de degradación, {r['tmf_deforestacion']:.1f} ha de deforestación y "
            f"{r['tmf_recuperacion']:.1f} ha de recuperación, {r['tmf_agua']:.1f} ha "
            f"de agua y {r['tmf_otra_cobertura']:.1f} ha de otra cobertura. {texto_dosel}",
        ),
        (
            "¿QUÉ SIGNIFICAN ESTOS RESULTADOS?",
            "Las imágenes satelitales permiten reconocer dónde pudo ocurrir un cambio, "
            "pero no establecen automáticamente su causa. El patrón observado puede "
            "corresponder a manejo productivo, cosecha de plantaciones, regeneración, "
            "nubosidad residual o una modificación real de la cobertura forestal.",
        ),
        (
            "CONSISTENCIA ENTRE FUENTES",
            coincidencia,
        ),
        (
            "¿DÓNDE SE DEBE REVISAR?",
            f"{texto_coincidencia_espacial} Deben contrastarse con imágenes recientes, "
            "registros de manejo, información del predio y verificación de campo "
            "cuando corresponda.",
        ),
        ("ACCIÓN RECOMENDADA", accion_pdf),
        (
            "CONCLUSIÓN DE LA PREEVALUACIÓN",
            f"El área presenta prioridad {prioridad_pdf.lower()} de visita. La decisión "
            "final debe complementarse con información del productor, documentación del "
            "predio, imágenes recientes y verificación de campo cuando corresponda.",
        ),
    ]
    if visita:
        secciones.insert(
            1,
            (
                "DIAGNÓSTICO TERRITORIAL INTEGRADO",
                f"{visita['lectura_integrada']} "
                f"La combinación territorial es <b>{visita['combinacion_territorial']}</b>. "
                f"Orientación operativa: {visita['foco_visita']} La condición estructural "
                "sirve para ubicar la revisión, pero no añade puntos porque requiere "
                "calibración ecológica para el territorio y las especies objetivo.",
            ),
        )
    contexto_corredores = r.get("corredores")
    if contexto_corredores:
        nombres_corredores = ", ".join(
            dict.fromkeys(
                detalle["nombre"]
                for detalle in contexto_corredores["corredores"]
            )
        ) or "ninguno"
        secciones.insert(
            4,
            (
                "CONTEXTO DE CORREDORES ECOLÓGICOS",
                f"El área intersecta {contexto_corredores['area_en_corredores_ha']:.2f} ha "
                f"de los corredores interpretados por Almanaque Azul "
                f"({contexto_corredores['porcentaje_aoi_en_corredores']:.2f}% del área). "
                f"Corredores presentes: {nombres_corredores}. "
                f"Intersección con el Corredor Biológico Mesoamericano: "
                f"{'sí' if contexto_corredores['intersecta_mesoamericano'] else 'no'}. "
                "Las categorías originales son alta, mediana y media-baja. Este contexto "
                "no modifica el índice satelital de cambios; aporta únicamente al valor "
                "estratégico de la prioridad integrada de visita.",
            ),
        )
    contexto_fragmentacion = r.get("fragmentacion")
    if contexto_fragmentacion:
        clase_fragmentacion = contexto_fragmentacion["metricas_clase"]
        red_fragmentacion = contexto_fragmentacion["metricas_red"]
        secciones.insert(
            5,
            (
                "FRAGMENTACIÓN Y RED DE PARCHES",
                f"El recorte de {FUENTE_BOSQUE_CORTA} produjo "
                f"{clase_fragmentacion['numero_parches']} "
                f"parches y {clase_fragmentacion['area_total_bosque_ha']:.2f} ha de bosque. "
                f"La red, calculada con un umbral de {red_fragmentacion['umbral_m']:.0f} m, "
                f"contiene {red_fragmentacion['numero_componentes']} componentes y "
                f"{red_fragmentacion['numero_aristas']} conexiones. La importancia "
                "Alta/Media/Baja de los parches es relativa al área evaluada, no equivale "
                "a las categorías de Almanaque Azul. Esta red se conecta con la decisión "
                "para focalizar la visita en parches conectores y componentes aislados, "
                "sin modificar el puntaje integrado.",
            ),
        )
    for titulo, cuerpo in secciones:
        historia.append(Paragraph(titulo, estilos["SeccionFicha"]))
        historia.append(Paragraph(cuerpo, estilos["CuerpoFicha"]))

    historia.extend([PageBreak(), Paragraph("MAPAS TEMÁTICOS DEL ÁREA EVALUADA", estilos["TituloFicha"])])
    for mapa in mapas or []:
        contenido = [Paragraph(mapa["titulo"], estilos["MapaTitulo"])]
        if mapa.get("imagen"):
            imagen = ReportLabImage(BytesIO(mapa["imagen"]))
            # Se conserva la proporción original y solo se limita el tamaño
            # máximo. La celda aumenta su altura según el mapa.
            escala = min(
                (15.75 * cm) / imagen.imageWidth,
                (9.8 * cm) / imagen.imageHeight,
            )
            imagen.drawWidth = imagen.imageWidth * escala
            imagen.drawHeight = imagen.imageHeight * escala
            tabla_imagen = Table([[imagen]], colWidths=[15.75 * cm])
            tabla_imagen.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            contenido.extend([tabla_imagen, Spacer(1, 2)])
        else:
            contenido.append(
                Table(
                    [[Paragraph("Imagen no disponible. Consulte el mapa interactivo.", estilos["MapaNota"])]],
                    colWidths=[15.4 * cm],
                    rowHeights=[7.0 * cm],
                    style=TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f4f4")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    ),
                )
            )
        contenido.append(Paragraph(mapa["leyenda"], estilos["MapaNota"]))
        tabla_mapa = Table([[contenido]], colWidths=[16.3 * cm], hAlign="CENTER")
        tabla_mapa.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.45, borde),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        historia.extend([tabla_mapa, Spacer(1, 7)])
    historia.append(
        Paragraph(
            "Nota cartográfica: el contorno celeste identifica el área evaluada. Las imágenes "
            "se generan automáticamente a partir de las fuentes indicadas y deben interpretarse "
            "junto con las leyendas y las limitaciones metodológicas. El mapa 7 estandariza "
            "JRC, Hansen y ESRI en una malla común de 30 m solo para orientar la ubicación; "
            "GEDI y NDVI no participan en esa superposición.",
            estilos["CuerpoFicha"],
        )
    )

    historia.extend([PageBreak(), Paragraph("DIAGNÓSTICO POR FUENTE", estilos["TituloFicha"])])
    filas_fuentes = [
        ["Fuente", "Resultado específico", "Señal", "Aporte"],
        [f"JRC TMF {anio_tmf_diagnostico}", f"Estable {r['tmf_estable']:.1f}; degradación {r['tmf_degradacion']:.1f}; deforestación {r['tmf_deforestacion']:.1f}; recuperación {r['tmf_recuperacion']:.1f}; agua {r['tmf_agua']:.1f}; otra cobertura {r['tmf_otra_cobertura']:.1f} ha", "Sí" if r["senal_tmf"] else "No", f"{aportes['tmf']:.1f}/{PESOS_INDICE['tmf']:.1f}"],
        ["Hansen GFC", f"Pérdida posterior al {CUTOFF_LABEL}: {r['hansen_post']:.2f} ha", "Sí" if r["senal_hansen"] else "No", f"{aportes['hansen']:.1f}/{PESOS_INDICE['hansen']:.1f}"],
        [f"ESRI {anio_esri_inicial}-{anio_esri_final}", f"Salida de árboles {r['esri_salida']:.1f} ha ({r['pct_esri_salida']:.1f}%)", "Sí" if r["senal_esri"] else "No", f"{aportes['esri']:.1f}/{PESOS_INDICE['esri']:.1f}"],
        ["GEDI", f"Dosel {r['gedi_altura']:.1f} m; área con datos válidos {r['gedi_cobertura_pct']:.0f}%" if r["gedi_disponible"] else "Datos insuficientes", "Contexto" if r["senal_gedi"] else "No", f"{aportes['gedi']:.1f}/{PESOS_INDICE['gedi']:.1f}"],
        [f"NDVI {anio_ndvi_inicial}-{ANO_NDVI_MAX}", "Apoyo visual; no participa en el índice operativo", "No aplica", "0.0"],
    ]
    filas_fuentes = [
        [
            Paragraph(str(c), estilos["CabeceraTabla"] if i == 0 else estilos["CuerpoFicha"])
            for c in fila
        ]
        for i, fila in enumerate(filas_fuentes)
    ]
    tabla_fuentes = Table(
        filas_fuentes,
        colWidths=[3.3 * cm, 8.0 * cm, 2.2 * cm, 2.8 * cm],
        repeatRows=1,
    )
    tabla_fuentes.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), verde),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, borde),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7f2")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    historia.extend(
        [
            tabla_fuentes,
            Paragraph("INFORMACIÓN TÉCNICA DE RESPALDO", estilos["SeccionFicha"]),
            Paragraph(
                "La preevaluación integró JRC Tropical Moist Forest, Hansen Global Forest "
                "Change, ESRI Land Use/Land Cover, altura del dosel basada en GEDI y NDVI "
                "derivado de Sentinel-2. Los cálculos se realizan por fuente en su resolución "
                "de trabajo. Únicamente el mapa 7 realiza una superposición espacial "
                "estandarizada en 30 m para orientar la revisión; no modifica el índice.",
                estilos["CuerpoFicha"],
            ),
            Paragraph(
                "Los pesos del índice son criterios operativos preliminares: JRC TMF 2.0, "
                "Hansen 2.0, ESRI 1.5, GEDI 0.5 y NDVI 0.0. Cada fuente se suma una sola vez. "
                "El índice no representa una probabilidad, "
                "una certificación, una determinación legal ni una confirmación definitiva "
                "de deforestación o de cumplimiento EUDR.",
                estilos["CuerpoFicha"],
            ),
            Paragraph(
                f"<b>Justificación de los pesos.</b> {texto_justificacion_pesos}",
                estilos["CuerpoFicha"],
            ),
            Paragraph(
                f"<b>Justificación de los umbrales.</b> {texto_justificacion_umbrales}",
                estilos["CuerpoFicha"],
            ),
            Paragraph(
                f"<b>Escala visual de vigor NDVI.</b> {texto_clases_ndvi}. "
                "Los intervalos describen vigor espectral y no identifican por sí solos "
                "el tipo de cobertura ni la presencia de bosque natural.",
                estilos["CuerpoFicha"],
            ),
            Paragraph(
                "<b>Consistencia entre fuentes.</b> Alta: JRC, Hansen y ESRI presentan "
                "señal; parcial: dos fuentes presentan señal; mixta: coexisten deterioro "
                "y recuperación o ganancia; sin señal consistente: menos de dos fuentes "
                "coinciden. Esta lectura no modifica el puntaje.",
                estilos["CuerpoFicha"],
            ),
        ]
    )

    def pie_pagina(canvas_pdf, documento_pdf):
        canvas_pdf.saveState()
        ancho, _ = A4
        canvas_pdf.setStrokeColor(colors.HexColor("#9aab96"))
        canvas_pdf.setLineWidth(0.4)
        canvas_pdf.line(1.55 * cm, 1.2 * cm, ancho - 1.55 * cm, 1.2 * cm)
        canvas_pdf.setFont("Times-Roman", 7.5)
        canvas_pdf.setFillColor(colors.HexColor("#555555"))
        canvas_pdf.drawString(1.55 * cm, 0.82 * cm, "Preevaluación territorial indicativa - requiere verificación")
        canvas_pdf.drawRightString(ancho - 1.55 * cm, 0.82 * cm, f"Página {documento_pdf.page}")
        canvas_pdf.restoreState()

    documento.build(historia, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
    memoria.seek(0)
    return memoria.getvalue()


# -----------------------------------------------------------------------------
# Presentación de leyendas y resultados
# -----------------------------------------------------------------------------

def mostrar_flujo(paso_actual, contenedor=None):
    pasos = [
        ("Área", "Seleccione la unidad territorial."),
        ("Vista", "Elija qué mapas ver primero."),
        ("Resultados", "Ejecute y lea las señales."),
        ("Evidencia", "Explore mapas y descargue."),
    ]
    tarjetas = []
    for numero, (titulo, descripcion) in enumerate(pasos, start=1):
        if numero < paso_actual:
            estado = "completado"
            texto_estado = "Completado"
        elif numero == paso_actual:
            estado = "actual"
            texto_estado = "Paso actual"
        else:
            estado = "pendiente"
            texto_estado = "Pendiente"
        aria_actual = ' aria-current="step"' if numero == paso_actual else ""
        tarjetas.append(
            f'<div class="flujo-paso {estado}"{aria_actual}>'
            f'<span class="flujo-numero">{numero}</span>'
            f"<b>{html_lib.escape(titulo)}</b>"
            f"{html_lib.escape(descripcion)}"
            f'<span class="flujo-estado">{texto_estado}</span>'
            f"</div>"
        )
    destino = contenedor if contenedor is not None else st
    destino.markdown(
        '<div class="flujo-pasos" aria-label="Progreso del análisis">'
        + "".join(tarjetas)
        + "</div>",
        unsafe_allow_html=True,
    )


def mostrar_entregables(contenedor=None):
    destino = contenedor if contenedor is not None else st
    destino.markdown(
        """
        <div class="entregables" aria-label="Contenido que entregará el análisis">
          <div class="entregable">
            <small>Primero</small>
            <b>Una conclusión resumida</b>
            <span>Indica la prioridad de revisión y explica qué significa en lenguaje sencillo.</span>
          </div>
          <div class="entregable">
            <small>Después</small>
            <b>La evidencia en el mapa</b>
            <span>Permite ubicar visualmente las señales y comparar los períodos disponibles.</span>
          </div>
          <div class="entregable">
            <small>Al finalizar</small>
            <b>Un informe trazable</b>
            <span>Reúne resultados, mapas, fuentes y parámetros para documentar la revisión.</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_error_amigable(error):
    if isinstance(error, json.JSONDecodeError):
        explicacion = (
            "La conexión segura con los datos necesita ser corregida por el administrador. "
            "El problema no está relacionado con el área que intentó analizar."
        )
    elif "permission" in str(error).lower():
        explicacion = (
            "La aplicación no tiene autorización para consultar una de las fuentes de datos. "
            "El administrador debe revisar los permisos de Earth Engine."
        )
    else:
        explicacion = (
            "La aplicación no pudo completar la conexión inicial con las fuentes territoriales. "
            "Sus datos y selecciones no causaron este problema."
        )
    st.error("El visor no pudo iniciar el análisis territorial.")
    st.markdown(f"**Qué ocurrió:** {explicacion}")
    st.markdown(
        """
        <div class="recuperacion-error" aria-label="Cómo continuar">
          <div class="recuperacion-paso">
            <b>1. Intente nuevamente</b>
            <span>Recargue la página una vez para descartar una interrupción temporal.</span>
          </div>
          <div class="recuperacion-paso">
            <b>2. Avise al administrador</b>
            <span>Si continúa, indique que el visor no logró conectarse con Earth Engine.</span>
          </div>
          <div class="recuperacion-paso">
            <b>3. Comparta el detalle</b>
            <span>Abra el detalle técnico inferior y envíe únicamente el mensaje de error.</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_leyenda(titulo, elementos):
    st.markdown(f"**{titulo}**")
    filas = []
    for elemento in elementos:
        color, texto = elemento[:2]
        explicacion = elemento[2] if len(elemento) > 2 else None
        texto_seguro = html_lib.escape(texto)
        if explicacion:
            ayuda = html_lib.escape(explicacion)
            etiqueta = html_lib.escape(
                f"{texto}: pulse para ver la explicación",
                quote=True,
            )
            contenido = (
                f'<details class="leyenda-detalle">'
                f'<summary aria-label="{etiqueta}">'
                f'<span class="leyenda-texto">{texto_seguro}</span>'
                f'<span class="leyenda-info" aria-hidden="true">i</span>'
                f'</summary>'
                f'<div class="leyenda-ayuda">{ayuda}</div>'
                f'</details>'
            )
        else:
            contenido = f'<span class="leyenda-texto">{texto_seguro}</span>'
        filas.append(
            f'<div class="leyenda-fila"><span class="leyenda-color" '
            f'style="background:{color};"></span>'
            f'{contenido}</div>'
        )
    st.markdown("".join(filas), unsafe_allow_html=True)


def mostrar_escala_ndvi_metodologia():
    st.markdown("**Escala visual del vigor vegetal (NDVI)**")
    st.caption(
        "Los intervalos se muestran siempre. Pulse el botón de información de "
        "cada clase para conocer su interpretación y sus precauciones."
    )
    for clase in CLASES_VIGOR_NDVI:
        contenido, ayuda = st.columns(
            [5, 1.35],
            gap="small",
            vertical_alignment="center",
        )
        with contenido:
            etiqueta = html_lib.escape(clase["etiqueta"])
            rango = html_lib.escape(clase["rango"])
            st.markdown(
                f"""
                <div class="ndvi-metodo-fila">
                  <span class="ndvi-metodo-color" style="background:{clase['color']};"></span>
                  <span class="ndvi-metodo-texto">
                    <strong>{etiqueta}</strong>
                    <span class="ndvi-metodo-rango">{rango}</span>
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with ayuda:
            with st.popover(
                "Información",
                icon=":material/info:",
                help=f"Cómo interpretar: {clase['etiqueta']}",
                use_container_width=True,
            ):
                st.markdown(f"**{clase['etiqueta']}**")
                st.code(clase["rango"], language=None)
                st.write(clase["interpretacion"])
    st.caption(
        "Esta escala describe vigor espectral, no tipo de cobertura. Un NDVI alto "
        "no confirma por sí solo la presencia de bosque natural."
    )


def mostrar_resultados(
    resultados,
    anio_tmf_diagnostico,
    anio_esri_inicial,
    anio_esri_final,
):
    prioridad_cambios = resultados["prioridad"]
    visita = resultados.get("prioridad_visita")
    prioridad = (
        visita["prioridad_visita"] if visita else prioridad_cambios
    )
    recomendacion_resultado = (
        texto_recomendacion_visita(prioridad)
        if visita
        else texto_recomendacion(prioridad)
    )
    color = {
        "Muy alta": "#7f0000",
        "Alta": "#b71c1c",
        "Media": "#a33a00",
        "Preventiva": "#8a5b00",
        "Baja": "#2e7d32",
    }[prioridad]
    fuentes_principales = sum(
        bool(resultados[clave])
        for clave in ("senal_tmf", "senal_hansen", "senal_esri")
    )
    if fuentes_principales == 0:
        titulo_hallazgo = "Sin señales principales que eleven la prioridad"
        detalle_hallazgo = (
            "JRC, ESRI y Hansen no superaron los umbrales operativos definidos para esta área."
        )
        titulo_ubicacion = "No hay un sector prioritario confirmado"
        detalle_ubicacion = (
            "Aun así, revise el mapa si necesita documentar la condición actual del predio."
        )
    elif fuentes_principales == 1:
        titulo_hallazgo = "Una fuente principal presenta una señal"
        detalle_hallazgo = (
            "Conviene contrastarla con los demás mapas y con información del predio antes de interpretarla."
        )
        titulo_ubicacion = "Revise primero las zonas resaltadas"
        detalle_ubicacion = (
            "El mapa permite ubicar la señal; su color no establece automáticamente la causa del cambio."
        )
    else:
        titulo_hallazgo = f"{fuentes_principales} fuentes principales presentan señales"
        detalle_hallazgo = (
            "La necesidad de revisión aumenta. El mapa de coincidencia permite comprobar "
            "si las señales también se superponen espacialmente."
        )
        titulo_ubicacion = "Priorice los sectores señalados en varios mapas"
        detalle_ubicacion = (
            "Compare la ubicación visual y luego confróntela con imágenes recientes y documentos del predio."
        )
    if resultados["coincidencia_varias_fuentes"] > 0:
        titulo_ubicacion = (
            f"Revise primero {resultados['coincidencia_varias_fuentes']:.2f} ha "
            "con coincidencia espacial"
        )
        detalle_ubicacion = (
            "Active «Sectores que requieren revisión»: naranja indica dos fuentes "
            "y rojo oscuro tres. Después confronte esos lugares con imágenes "
            "recientes y documentos del predio."
        )
    elif resultados["coincidencia_1_fuente"] > 0:
        titulo_ubicacion = "Hay señales localizadas, pero ninguna coincide espacialmente"
        detalle_ubicacion = (
            "El séptimo mapa las muestra en amarillo como señales de una sola "
            "fuente. Revise cada producto y mantenga una interpretación cautelosa."
        )
    else:
        titulo_ubicacion = "No se delimitaron sectores en el mapa de coincidencia"
        detalle_ubicacion = (
            "No se detectaron píxeles con las tres señales espaciales definidas. "
            "Consulte los mapas individuales si necesita documentar el área."
        )
    if visita:
        estructura = visita["contexto_estructural"]
        detalle_resultado = (
            f"Resultado integrado · cambios {visita['puntaje_cambios']:.1f}/"
            f"{PUNTAJE_MAXIMO:.1f} + corredor {visita['aporte_corredor']:.2f}/"
            f"{REGLAS_PRIORIDAD_VISITA['aporte_maximo_corredor']:.1f} · "
            f"estructura: {estructura['estado']}"
        )
        titulo_ubicacion = visita["combinacion_territorial"]
        detalle_ubicacion = f"{visita['foco_visita']} {detalle_ubicacion}"
    else:
        detalle_resultado = (
            f"Índice operativo {resultados['puntaje']:.1f}/{PUNTAJE_MAXIMO:.1f}"
        )
    st.markdown(
        f"""
        <div class="resultado-prioridad" style="--prioridad-color:{color};">
          <small>{html_lib.escape(detalle_resultado)}</small>
          <strong>Prioridad {prioridad.lower()} de visita</strong>
          <p>{html_lib.escape(recomendacion_resultado)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if visita:
        col_cambios, col_corredor, col_estructura, col_final = st.columns(4)
        col_cambios.metric(
            "Urgencia por cambios",
            prioridad_cambios,
            f"{visita['puntaje_cambios']:.1f} de {PUNTAJE_MAXIMO:.1f}",
            delta_color="off",
        )
        col_corredor.metric(
            "Valor estratégico del corredor",
            visita["valor_corredor"],
            f"+{visita['aporte_corredor']:.2f} puntos",
            delta_color="off",
        )
        detalle_estructura = (
            f"{estructura['numero_componentes']} componentes · "
            f"{estructura['porcentaje_componente_mayor']:.1f}% en la red mayor"
            if estructura["disponible"]
            else "Cargue la cobertura 2021"
        )
        col_estructura.metric(
            "Condición estructural 2021",
            estructura["estado"],
            detalle_estructura,
            delta_color="off",
        )
        col_final.metric(
            "Prioridad integrada",
            prioridad,
            f"{visita['puntaje_integrado']:.2f} de {PUNTAJE_MAXIMO_VISITA:.1f}",
            delta_color="off",
        )
        st.caption(
            "Las señales recientes determinan la urgencia; el corredor aumenta el "
            "valor estratégico; y la estructura del bosque 2021 orienta dónde "
            "concentrar la visita. La estructura no suma puntos hasta contar con "
            "umbrales ecológicos calibrados."
        )
        st.markdown(
            f"""
            <div class="resultado-fuente">
              <b>{html_lib.escape(visita['combinacion_territorial'])}</b><br/>
              {html_lib.escape(visita['foco_visita'])}<br/>
              <small>{html_lib.escape(estructura['interpretacion'])}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )
    aportes = resultados["aportes_indice"]
    st.markdown("#### Evidencia de cambio territorial")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("JRC TMF", f"{aportes['tmf']:.1f} / {PESOS_INDICE['tmf']:.1f}")
    c2.metric("Hansen GFC", f"{aportes['hansen']:.1f} / {PESOS_INDICE['hansen']:.1f}")
    c3.metric("ESRI LULC", f"{aportes['esri']:.1f} / {PESOS_INDICE['esri']:.1f}")
    c4.metric("GEDI", f"{aportes['gedi']:.1f} / {PESOS_INDICE['gedi']:.1f}")
    st.caption(
        "Cada fuente puede sumar una sola vez. JRC y Hansen tienen el mayor peso "
        "(2.0 cada uno); ESRI aporta como máximo 1.5, GEDI 0.5 y NDVI 0.0."
    )
    consistencia = resultados["consistencia"]
    fuentes_deterioro = ", ".join(consistencia["fuentes_deterioro"]) or "ninguna"
    fuentes_recuperacion = (
        ", ".join(consistencia["fuentes_recuperacion"]) or "ninguna"
    )
    st.markdown(
        f"""
        <div class="resultado-fuente">
          <b>Consistencia entre fuentes: {html_lib.escape(consistencia['nivel'])}</b><br/>
          {html_lib.escape(consistencia['detalle'])}<br/>
          <small>Señales de deterioro: {html_lib.escape(fuentes_deterioro)} ·
          Recuperación o ganancia: {html_lib.escape(fuentes_recuperacion)}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### Lectura rápida")
    st.markdown(
        f"""
        <div class="lectura-rapida" aria-label="Interpretación resumida del resultado">
          <div class="lectura-tarjeta">
            <small>Qué se detectó</small>
            <b>{html_lib.escape(titulo_hallazgo)}</b>
            <p>{html_lib.escape(detalle_hallazgo)}</p>
          </div>
          <div class="lectura-tarjeta">
            <small>Dónde mirar</small>
            <b>{html_lib.escape(titulo_ubicacion)}</b>
            <p>{html_lib.escape(detalle_ubicacion)}</p>
          </div>
          <div class="lectura-tarjeta">
            <small>Qué hacer después</small>
            <b>Documente la revisión</b>
            <p>{html_lib.escape(recomendacion_resultado)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    area = resultados["area_ha"]
    resumen, detalle = st.tabs(["Resumen para decidir", "Evidencia por fuente"])
    with resumen:
        st.markdown(
            "**¿Qué significa?** La prioridad sirve para decidir dónde conviene revisar "
            "imágenes, documentos o realizar una visita. No demuestra por sí sola la causa del cambio."
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Deforestación JRC", f"{resultados['tmf_deforestacion']:.1f} ha")
        c2.metric("Pérdida Hansen post-2020", f"{resultados['hansen_post']:.2f} ha")
        c3.metric(
            "Salida de árboles ESRI",
            f"{resultados['esri_salida']:.1f} ha",
            f"{resultados['pct_esri_salida']:.1f}% del área",
            delta_color="off",
        )
        c4.metric(
            "Altura media GEDI",
            (
                f"{resultados['gedi_altura']:.1f} m"
                if resultados["gedi_disponible"]
                else "Datos insuficientes"
            ),
        )
        st.info(
            f"Mapa «Sectores que requieren revisión»: "
            f"{resultados['coincidencia_1_fuente']:.2f} ha con señal de una fuente; "
            f"{resultados['coincidencia_2_fuentes']:.2f} ha con dos fuentes; "
            f"{resultados['coincidencia_3_fuentes']:.2f} ha con tres fuentes. "
            "Priorice las coincidencias de dos o tres fuentes. Este mapa no modifica "
            "el índice y no confirma por sí solo la causa del cambio."
        )
        st.markdown(f"**Acción sugerida:** {recomendacion_resultado}")

    filas = [
        (
            f"Mapa forestal JRC {anio_tmf_diagnostico}",
            f"Deforestación {resultados['tmf_deforestacion']:.1f} ha; "
            f"degradación {resultados['tmf_degradacion']:.1f} ha · "
            f"aporte {aportes['tmf']:.1f}/{PESOS_INDICE['tmf']:.1f}",
            resultados["senal_tmf"],
        ),
        (
            "Pérdida arbórea Hansen",
            f"Pérdida post-{CUTOFF_LABEL}: {resultados['hansen_post']:.2f} ha · "
            f"aporte {aportes['hansen']:.1f}/{PESOS_INDICE['hansen']:.1f}",
            resultados["senal_hansen"],
        ),
        (
            f"Transiciones ESRI {anio_esri_inicial} → {anio_esri_final}",
            f"Árboles → no árbol: {resultados['esri_salida']:.1f} ha "
            f"({resultados['pct_esri_salida']:.1f}%) · "
            f"aporte {aportes['esri']:.1f}/{PESOS_INDICE['esri']:.1f}",
            resultados["senal_esri"],
        ),
        (
            "Altura del dosel GEDI",
            (
                f"Dosel {resultados['gedi_altura']:.1f} m; "
                f"{resultados['gedi_cobertura_pct']:.0f}% del área con datos válidos · "
                f"aporte {aportes['gedi']:.1f}/{PESOS_INDICE['gedi']:.1f}"
                if resultados["gedi_disponible"]
                else "Sin datos válidos suficientes; aporte 0.0/0.5"
            ),
            resultados["senal_gedi"],
        ),
        (
            "ΔNDVI Sentinel-2",
            "Solo visualización; aporte 0.0 al índice",
            False,
        ),
    ]
    with detalle:
        st.markdown("**Estadísticas territoriales y forestales**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Área evaluada", f"{resultados['area_ha']:.1f} ha")
        c2.metric(
            "Cobertura arbórea persistente a 2020",
            f"{resultados['linea_base']:.1f} ha",
            f"{resultados['pct_linea_base']:.1f}% del área",
            delta_color="off",
        )
        c3.metric("Pérdida Hansen 2001-2020", f"{resultados['hansen_pre']:.2f} ha")
        c4.metric("Pérdida Hansen post-2020", f"{resultados['hansen_post']:.2f} ha")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Bosque estable JRC", f"{resultados['tmf_estable']:.1f} ha")
        c2.metric("Degradación JRC", f"{resultados['tmf_degradacion']:.1f} ha")
        c3.metric("Deforestación JRC", f"{resultados['tmf_deforestacion']:.1f} ha")
        c4.metric("Recuperación JRC", f"{resultados['tmf_recuperacion']:.1f} ha")
        for titulo, texto_detalle, alerta in filas:
            estado = "SEÑAL" if alerta else "SIN SEÑAL OPERATIVA"
            color_texto = "#c62828" if alerta else "#2e7d32"
            st.markdown(
                f'<div class="resultado-fuente"><b style="color:{color_texto};">'
                f"{estado} · {titulo}</b><br/>{texto_detalle}</div>",
                unsafe_allow_html=True,
            )
        st.caption("Use el menú de cada gráfico para guardarlo como imagen o descargar sus datos.")
        grafico_jrc, grafico_esri = st.columns(2)
        with grafico_jrc:
            st.markdown("**Distribución del estado forestal JRC**")
            st.bar_chart(
                {
                    "Clase": [
                        "Bosque estable",
                        "Degradación",
                        "Deforestación",
                        "Recuperación",
                        "Agua",
                        "Otra cobertura",
                    ],
                    "Hectáreas": [
                        resultados["tmf_estable"],
                        resultados["tmf_degradacion"],
                        resultados["tmf_deforestacion"],
                        resultados["tmf_recuperacion"],
                        resultados["tmf_agua"],
                        resultados["tmf_otra_cobertura"],
                    ],
                },
                x="Clase",
                y="Hectáreas",
                height=280,
            )
        with grafico_esri:
            st.markdown("**Cambios de la clase árboles ESRI**")
            st.bar_chart(
                {
                    "Clase": ["Árboles estables", "Salida de árboles", "Ganancia de árboles"],
                    "Hectáreas": [
                        resultados["esri_estable"],
                        resultados["esri_salida"],
                        resultados["esri_ganancia"],
                    ],
                },
                x="Clase",
                y="Hectáreas",
                height=280,
            )
        st.markdown("**Comparación del aporte de las fuentes al índice**")
        st.bar_chart(
            {
                "Fuente": ["JRC TMF", "Hansen GFC", "ESRI LULC", "GEDI", "NDVI"],
                "Aporte": [
                    aportes["tmf"],
                    aportes["hansen"],
                    aportes["esri"],
                    aportes["gedi"],
                    aportes["ndvi"],
                ],
            },
            x="Fuente",
            y="Aporte",
            height=280,
        )
        st.caption(
            "El gráfico representa aportes ponderados, no superficies comparables "
            "píxel a píxel. NDVI permanece en 0 porque es exclusivamente visual."
        )


def mostrar_resultados_corredores(resultados):
    st.subheader("Contexto de corredores ecológicos")
    columna_estado, columna_area, columna_meso = st.columns(3)
    columna_estado.metric(
        "Intersección con corredores",
        "Sí" if resultados["intersecta"] else "No",
    )
    columna_area.metric(
        "Área dentro de corredores",
        f"{resultados['area_en_corredores_ha']:,.2f} ha",
        f"{resultados['porcentaje_aoi_en_corredores']:.1f}% del área",
    )
    columna_meso.metric(
        "Corredor Mesoamericano",
        "Sí" if resultados["intersecta_mesoamericano"] else "No",
        f"{resultados['area_corredor_mesoamericano_ha']:,.2f} ha",
    )
    st.markdown(
        """
        <div class="corredor-aviso"><strong>Valor estratégico:</strong> esta superposición
        describe el contexto territorial publicado por Almanaque Azul. No modifica el índice
        satelital de cambios; aporta únicamente a la prioridad integrada de visita y no demuestra
        por sí sola conectividad funcional para una especie.</div>
        """,
        unsafe_allow_html=True,
    )
    areas = resultados["areas_categoria_ha"]
    st.markdown(
        " ".join(
            [
                (
                    '<span class="categoria-corredor">'
                    f'{etiqueta}: {areas[clave]:,.2f} ha</span>'
                )
                for clave, etiqueta in (
                    ("alta", "Alta"),
                    ("mediana", "Mediana"),
                    ("mediabaja", "Media-baja"),
                )
            ]
        ),
        unsafe_allow_html=True,
    )
    if resultados["corredores"]:
        tabla = [
            {
                "Corredor": fila["nombre"],
                "Categoría original": fila["categoria_etiqueta"],
                "Intersección (ha)": fila["interseccion_ha"],
                "% del área": fila["porcentaje_aoi"],
                "Mesoamericano": "Sí" if fila["es_mesoamericano"] else "No",
            }
            for fila in resultados["corredores"]
        ]
        st.dataframe(tabla, hide_index=True, use_container_width=True)
    else:
        st.info("El área evaluada no intersecta los polígonos de corredores publicados.")
    st.caption(
        f"Fuente: {resultados['fuente']}. Categorías originales: alta, mediana y media-baja."
    )


def mostrar_resultados_fragmentacion(resultados):
    st.subheader(f"Fragmentación y conectividad del bosque de {ANO_BOSQUE_REFERENCIA}")
    st.caption(
        f"Fuente de cobertura: {resultados.get('fuente_cobertura', FUENTE_BOSQUE_CORTA)}. "
        "Es un corte de cobertura; no representa una serie anual de deforestación."
    )
    clase = resultados["metricas_clase"]
    red = resultados["metricas_red"]
    col_parches, col_bosque, col_componentes, col_mayor = st.columns(4)
    col_parches.metric("Parches", f"{clase['numero_parches']:,}")
    col_bosque.metric("Bosque en el área", f"{clase['area_total_bosque_ha']:,.2f} ha")
    col_componentes.metric("Componentes de red", f"{red['numero_componentes']:,}")
    col_mayor.metric(
        "Mayor componente",
        f"{red['porcentaje_nodos_componente_mayor']:.1f}% de parches",
    )
    resumen, conectores = st.tabs(["Métricas del paisaje", "Parches conectores"])
    with resumen:
        st.dataframe(
            [
                {"Métrica": "Bosque en el paisaje", "Valor": f"{clase['porcentaje_paisaje_bosque']:.2f}%"},
                {"Métrica": "Densidad de parches", "Valor": f"{clase['densidad_parches_por_100ha']:.3f} por 100 ha"},
                {"Métrica": "Densidad de borde", "Valor": f"{clase['densidad_borde_m_ha']:.2f} m/ha"},
                {"Métrica": "Área media de parche", "Valor": f"{clase['area_media_parche_ha']:.2f} ha"},
                {"Métrica": "Área mediana de parche", "Valor": f"{clase['area_mediana_parche_ha']:.2f} ha"},
                {"Métrica": "Índice del parche mayor", "Valor": f"{clase['indice_parche_mayor_pct']:.2f}%"},
                {"Métrica": "Densidad de la red", "Valor": f"{red['densidad_red']:.6f}"},
                {"Métrica": "Umbral de conexión", "Valor": f"{red['umbral_m']:.0f} m"},
            ],
            hide_index=True,
            use_container_width=True,
        )
    with conectores:
        if resultados["top_conectores"]:
            st.dataframe(
                resultados["top_conectores"],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "patch_id": "Parche",
                    "area_ha": st.column_config.NumberColumn("Área (ha)", format="%.2f"),
                    "indice_conector": st.column_config.NumberColumn("Índice conector", format="%.3f"),
                    "prioridad_conectividad": "Importancia",
                },
            )
        else:
            st.info(
                "La cobertura institucional de 2021 no identifica parches de bosque "
                "dentro del área seleccionada."
            )
    st.caption(
        "La importancia Alta/Media/Baja se calcula dentro del área analizada mediante los "
        "cuantiles del índice conector; no corresponde a las categorías de Almanaque Azul "
        "y no añade puntos. Sí orienta la focalización de la visita hacia conectores y "
        "componentes aislados."
    )


# -----------------------------------------------------------------------------
# Aplicación
# -----------------------------------------------------------------------------

st.markdown(
    """
    <div class="cabecera-app">
      <h1>EVALUACIÓN TERRITORIAL Y CORREDORES</h1>
      <div class="subtitulo-app">Bosque, fragmentación y conectividad ecológica en Panamá</div>
      <p>Integra evidencia satelital, los corredores interpretados por Almanaque Azul y
      el recorte institucional de Bosque y otros usos 2021 de SINIA–MiAMBIENTE para
      definir la urgencia, el valor estratégico y el lugar donde conviene revisar.</p>
      <div class="alcance-app">Resultado indicativo · requiere interpretación documental y
      verificación de campo · no determina cumplimiento EUDR</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="resumen-inicial" aria-labelledby="resumen-aplicacion">
      <h2 id="resumen-aplicacion">¿Qué hace esta aplicación? En palabras sencillas</h2>
      <p>
        Imagine que revisa varias fotografías y mapas del mismo terreno, pero cada uno observa
        algo distinto. Esta aplicación reúne esas miradas para ayudarle a encontrar lugares que
        conviene revisar con más atención. No necesita conocimientos de mapas digitales.
      </p>
      <div class="resumen-principiante" role="list" aria-label="Cómo funciona la aplicación">
        <article class="resumen-paso" role="listitem">
          <span class="resumen-paso-numero" aria-hidden="true">1</span>
          <h3>Usted elige el lugar</h3>
          <p>Puede seleccionar una finca registrada, dibujar su propia área o revisar toda la cuenca.</p>
        </article>
        <article class="resumen-paso" role="listitem">
          <span class="resumen-paso-numero" aria-hidden="true">2</span>
          <h3>La aplicación busca señales</h3>
          <p>Revisa cambios del bosque, corredores publicados y, si carga su archivo, la red de parches.</p>
        </article>
        <article class="resumen-paso" role="listitem">
          <span class="resumen-paso-numero" aria-hidden="true">3</span>
          <h3>Usted recibe una guía</h3>
          <p>Obtiene una prioridad y un foco de visita: cambios, corredor y estructura del bosque se leen juntos.</p>
        </article>
      </div>
      <div class="resumen-aclaracion">
        <strong>Cómo interpretar el resultado:</strong> una prioridad alta no confirma deforestación,
        una causa específica ni incumplimiento. Indica que varias señales justifican revisar imágenes
        recientes, documentos del predio y, cuando corresponda, realizar una visita de campo.
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.expander("Ver qué información revisa la aplicación", expanded=False):
    st.markdown(
        """
        - **Estado y cambios del bosque (JRC TMF):** muestra cómo se ha clasificado el bosque tropical a través del tiempo.
        - **Pérdida anual de cobertura arbórea (Hansen):** señala los años en que se detectó pérdida de árboles.
        - **Uso y cobertura del suelo (ESRI):** ayuda a reconocer cambios entre árboles, cultivos, pastizales, agua y áreas construidas.
        - **Altura del dosel (GEDI):** aporta información sobre la estructura vertical de la vegetación.
        - **Vigor vegetal (NDVI de Sentinel-2):** permite observar qué tan activa o densa parece la vegetación; se usa como apoyo visual y no aumenta la prioridad.
        - **Corredores de Almanaque Azul:** muestra categorías originales alta, mediana y media-baja, incluidos los tramos mesoamericanos oeste, San Lorenzo y este.
        - **Bosque y otros usos 2021:** el recorte institucional de SINIA–MiAMBIENTE se carga automáticamente y permite calcular fragmentación, componentes de red y parches importantes como conectores.

        Los tres componentes se conectan en una recomendación operativa. Los corredores
        aportan valor estratégico y la red de parches orienta el lugar de la revisión;
        ninguno se confunde con evidencia satelital de pérdida.
        La configuración se mantiene igual entre análisis para que los resultados puedan compararse.
        Al finalizar podrá descargar el informe PDF y el registro metodológico JSON con las fuentes,
        períodos, umbrales, pesos y reglas utilizados.
        """
    )

try:
    iniciar_earth_engine()

    st.sidebar.markdown("## Configurar análisis")
    st.sidebar.caption("Paso 1 de 3 · Seleccione la unidad territorial")
    etiquetas_area = {
        "Finca de monitoreo": "Finca registrada (recomendado)",
        "Dibujar polígono en el mapa": "Dibujar un área en el mapa",
        "Toda la cuenca": "Toda la cuenca (análisis regional)",
    }
    descripciones_area = {
        "Finca de monitoreo": (
            "Opción más rápida. Seleccione una finca disponible después de autorizar el acceso."
        ),
        "Dibujar polígono en el mapa": (
            "Úsela cuando el área no aparece en la lista. El dibujo se limita automáticamente a la cuenca."
        ),
        "Toda la cuenca": (
            "Evalúa la región completa. Requiere más tiempo y es menos detallada para decisiones prediales."
        ),
    }
    tipo_area = st.sidebar.radio(
        "¿Qué área desea analizar?",
        ["Finca de monitoreo", "Dibujar polígono en el mapa", "Toda la cuenca"],
        format_func=lambda valor: etiquetas_area[valor],
        help="Se recomienda iniciar con una finca. El análisis de toda la cuenca puede tardar varios minutos.",
    )
    st.sidebar.caption(descripciones_area[tipo_area])
    finca_seleccionada = None
    geometria_dibujada_json = st.session_state.get("geometria_dibujada_json")
    version_mapa_dibujo = st.session_state.get("version_mapa_dibujo", 0)
    if tipo_area == "Finca de monitoreo":
        if not solicitar_acceso_fincas():
            st.info(
                "El acceso a las fincas está protegido. Ingrese el código en el panel lateral "
                "o seleccione otra unidad territorial."
            )
            st.stop()
        finca_seleccionada = st.sidebar.selectbox(
            "Finca:",
            obtener_ids_fincas(),
            format_func=str,
            help="Las fincas están ordenadas de forma natural: 1, 2, 3...",
        )
    elif tipo_area == "Dibujar polígono en el mapa":
        st.subheader("1. Dibuje el área que desea evaluar")
        st.markdown(
            "Seleccione la herramienta de polígono en el mapa, marque los vértices y "
            "haga clic en el primer punto para cerrar la figura. El área se limitará "
            "automáticamente a la cuenca hidrográfica."
        )
        if geometria_dibujada_json and st.button("Borrar polígono y dibujar otro"):
            st.session_state.pop("geometria_dibujada_json", None)
            st.session_state.pop("resultados_analisis", None)
            st.session_state.pop("pdf_analisis", None)
            st.session_state.pop("firma_analisis", None)
            st.session_state.pop("errores_mapas", None)
            st.session_state["version_mapa_dibujo"] = version_mapa_dibujo + 1
            st.rerun()

        mapa_dibujo = folium.Map(
            location=[8.7, -80.0],
            zoom_start=8,
            tiles=None,
            control_scale=True,
        )
        folium.TileLayer(
            tiles=(
                "https://server.arcgisonline.com/ArcGIS/rest/services/"
                "World_Imagery/MapServer/tile/{z}/{y}/{x}"
            ),
            attr="Esri",
            name="Imagen satelital",
            overlay=False,
            control=False,
            max_zoom=20,
        ).add_to(mapa_dibujo)
        cuenca_dibujo = ee.FeatureCollection(ASSET_CUENCA)
        capa_gee(
            mapa_dibujo,
            cuenca_dibujo.style(color="FF4444", fillColor="00000000", width=3),
            {},
            "Límite de la cuenca",
            control=False,
        )
        if geometria_dibujada_json:
            folium.GeoJson(
                json.loads(geometria_dibujada_json),
                name="Polígono dibujado",
                style_function=lambda _: {
                    "color": "#00E5FF",
                    "weight": 4,
                    "fillColor": "#00E5FF",
                    "fillOpacity": 0.12,
                },
            ).add_to(mapa_dibujo)
        Draw(
            export=False,
            position="topleft",
            draw_options={
                "polyline": False,
                "rectangle": False,
                "circle": False,
                "marker": False,
                "circlemarker": False,
                "polygon": {
                    "allowIntersection": False,
                    "showArea": True,
                    "shapeOptions": {"color": "#00E5FF", "weight": 4},
                },
            },
            edit_options={"edit": True, "remove": True},
        ).add_to(mapa_dibujo)
        mapa_dibujo.fit_bounds(obtener_limites(cuenca_dibujo))
        resultado_dibujo = st_folium(
            mapa_dibujo,
            height=520,
            use_container_width=True,
            returned_objects=["all_drawings"],
            key=f"mapa-seleccion-poligono-{version_mapa_dibujo}",
        )
        dibujos = (resultado_dibujo or {}).get("all_drawings") or []
        if dibujos:
            nuevo_poligono = serializar_poligono_dibujado(dibujos[-1])
            if nuevo_poligono != geometria_dibujada_json:
                st.session_state["geometria_dibujada_json"] = nuevo_poligono
                st.rerun()
        geometria_dibujada_json = st.session_state.get("geometria_dibujada_json")
        if not geometria_dibujada_json:
            st.info("Dibuje un polígono para continuar con la preevaluación.")
            st.stop()
        st.success(
            "Polígono listo. Puede continuar con el tipo de revisión y ejecutar la preevaluación."
        )
    nombre_area = nombre_area_legible(tipo_area, finca_seleccionada)

    area_seleccionada = obtener_area(
        tipo_area,
        finca_seleccionada,
        geometria_dibujada_json,
    )
    geometria = area_seleccionada.geometry()
    superficie_ha = float(geometria.area(1).divide(10000).getInfo())
    if tipo_area == "Dibujar polígono en el mapa":
        superficie_original_ha = float(
            ee.Geometry(json.loads(geometria_dibujada_json))
            .area(1)
            .divide(10000)
            .getInfo()
        )
        if superficie_ha <= 0:
            st.error("El polígono no intersecta la cuenca. Bórrelo y dibuje uno dentro del límite rojo.")
            st.stop()
        if superficie_ha + 0.01 < superficie_original_ha:
            st.warning(
                "Una parte del polígono estaba fuera de la cuenca y fue excluida del análisis."
            )

    bosque_automatico_disponible = bool(ASSET_BOSQUE_2021)
    umbral_conectividad_m = 500
    area_min_parche_ha = 0.0
    huella_bosque = (
        hashlib.sha256(ASSET_BOSQUE_2021.encode("utf-8")).hexdigest()[:16]
        if bosque_automatico_disponible
        else "sin-asset-bosque"
    )
    catalogo_corredores = cargar_catalogo_corredores()

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Paso 2 de 3 · Cobertura institucional de {ANO_BOSQUE_REFERENCIA}")
    st.sidebar.caption(
        f"Corredores públicos listos: {catalogo_corredores['corredores_poligonos']} "
        f"polígonos y {catalogo_corredores['puntos_criticos']} puntos críticos."
    )
    with st.sidebar.expander("Cobertura de bosque y opciones de red", expanded=False):
        if bosque_automatico_disponible:
            st.success(
                "Cobertura lista. La aplicación la recortará automáticamente al área elegida."
            )
        else:
            st.warning(
                "La cobertura institucional todavía no fue configurada por la administración. "
                "El resto del diagnóstico puede ejecutarse, pero no mostrará la red de parches."
            )
        st.caption(
            f"Fuente: {FUENTE_BOSQUE_CORTA}. La persona usuaria no necesita cargar archivos."
        )
        umbral_conectividad_m = st.select_slider(
            "Distancia máxima entre parches",
            options=[100, 250, 500, 1000, 1500, 3000, 6000],
            value=500,
            format_func=lambda valor: f"{valor:,} m",
        )
        area_min_parche_ha = st.number_input(
            "Área mínima de parche (ha)",
            min_value=0.0,
            value=0.0,
            step=0.1,
            help="Permite excluir fragmentos demasiado pequeños del análisis estructural.",
        )

    st.sidebar.markdown("---")
    st.sidebar.caption("Paso 3 de 3 · Elija cómo explorar el mapa")
    objetivo = st.sidebar.selectbox(
        "¿Qué desea ver en el mapa?",
        list(PERFILES_VISUALIZACION),
        help=(
            "Puede consultar capas de un solo año o comparar dos años. "
            "El cálculo científico es el mismo en todas las opciones."
        ),
    )
    perfil = PERFILES_VISUALIZACION[objetivo]
    st.sidebar.caption(perfil["descripcion"])
    st.sidebar.info(
        "Esta selección solo cambia el mapa. El análisis siempre usa períodos "
        f"fijos y documentados: JRC {ANO_DIAG_TMF}, Hansen 2021-{ANO_HANSEN_MAX} "
        f"y ESRI {ANO_ESRI_MIN}-{ANO_ESRI_MAX}."
    )

    opciones_capas = [
        "Sectores para revisión",
        "Pérdida Hansen post-2020",
        "Pérdida Hansen 2001-2020",
        "Cobertura arbórea persistente",
        "Estado forestal JRC",
        "Deforestación JRC",
        "Degradación JRC",
        "Uso y cobertura ESRI",
        "Transiciones ESRI",
        "Altura GEDI",
        "ΔNDVI",
        "Vegetación NDVI",
    ]
    nombres_capas = {
        "Sectores para revisión": "Sectores que requieren revisión (3 fuentes)",
        "Pérdida Hansen post-2020": "Pérdida de árboles posterior a 2020",
        "Pérdida Hansen 2001-2020": "Pérdida histórica de árboles (2001-2020)",
        "Cobertura arbórea persistente": "Cobertura arbórea persistente hasta 2020",
        "Estado forestal JRC": "Estado forestal de un año (JRC)",
        "Deforestación JRC": "Señales de deforestación (JRC)",
        "Degradación JRC": "Señales de degradación (JRC)",
        "Uso y cobertura ESRI": "Uso y cobertura del suelo (ESRI)",
        "Transiciones ESRI": "Cambios de la clase árboles (ESRI)",
        "Altura GEDI": "Altura del dosel (GEDI)",
        "ΔNDVI": "Cambio del vigor vegetal (ΔNDVI)",
        "Vegetación NDVI": "Vigor vegetal de un año (NDVI)",
    }

    modo_comparador = perfil["comparador"]
    capas_activas = list(perfil["capas"])
    modo_mapa = (
        "Comparar años" if modo_comparador != "Sin comparador" else "Explorar capas"
    )
    orden_capas_mapa = list(capas_activas)
    capa_visible_inicial = capas_activas[0] if capas_activas else None
    anio_tmf_inicial, anio_tmf_final = 2020, ANO_TMF_MAX
    anio_esri_inicial, anio_esri_final = ANO_ESRI_MIN, ANO_ESRI_MAX
    anio_ndvi_inicial, anio_ndvi_final = 2022, ANO_NDVI_MAX
    anio_tmf_capa = ANO_TMF_MAX
    anio_esri_capa = ANO_ESRI_MAX
    anio_ndvi_capa = ANO_NDVI_MAX

    if modo_mapa == "Comparar años":
        capas_activas = []
        orden_capas_mapa = []
        capa_visible_inicial = None
        if modo_comparador == "JRC TMF":
            opciones_inicio_tmf = list(range(1990, ANO_TMF_MAX))
            anio_tmf_inicial = st.sidebar.selectbox(
                "Año inicial (JRC):",
                opciones_inicio_tmf,
                index=opciones_inicio_tmf.index(2020),
            )
            opciones_final_tmf = list(range(anio_tmf_inicial + 1, ANO_TMF_MAX + 1))
            anio_tmf_final = st.sidebar.selectbox(
                "Año final (JRC):",
                opciones_final_tmf,
                index=len(opciones_final_tmf) - 1,
            )
            st.sidebar.caption(
                f"Comparación visual. El análisis no resta estos años: clasifica el "
                f"estado JRC de {ANO_DIAG_TMF}."
            )
        elif modo_comparador == "ESRI LULC":
            opciones_inicio_esri = list(range(ANO_ESRI_MIN, ANO_ESRI_MAX))
            anio_esri_inicial = st.sidebar.selectbox(
                "Año inicial (ESRI):",
                opciones_inicio_esri,
            )
            opciones_final_esri = list(range(anio_esri_inicial + 1, ANO_ESRI_MAX + 1))
            anio_esri_final = st.sidebar.selectbox(
                "Año final (ESRI):",
                opciones_final_esri,
                index=len(opciones_final_esri) - 1,
            )
            st.sidebar.caption(
                f"El análisis usa los extremos disponibles {ANO_ESRI_MIN} y "
                f"{ANO_ESRI_MAX}; esta selección solo cambia el comparador."
            )
        else:
            opciones_inicio_ndvi = list(range(2017, ANO_NDVI_MAX))
            anio_ndvi_inicial = st.sidebar.selectbox(
                "Año inicial (NDVI):",
                opciones_inicio_ndvi,
                index=opciones_inicio_ndvi.index(2022),
            )
            opciones_final_ndvi = list(range(anio_ndvi_inicial + 1, ANO_NDVI_MAX + 1))
            anio_ndvi_final = st.sidebar.selectbox(
                "Año final (NDVI):",
                opciones_final_ndvi,
                index=len(opciones_final_ndvi) - 1,
            )
            st.sidebar.caption(
                "Comparación visual de vigor vegetal. NDVI no suma puntos al índice de prioridad."
            )
    else:
        modo_comparador = "Sin comparador"
        st.sidebar.markdown("**Capas disponibles en el mapa**")
        capas_seleccionadas = st.sidebar.multiselect(
            "Seleccione una o varias capas:",
            opciones_capas,
            default=capas_activas,
            format_func=lambda valor: nombres_capas[valor],
            help=(
                "Las capas seleccionadas permanecen en el control del mapa. Puede "
                "encenderlas o apagarlas sin volver a agregarlas."
            ),
        )
        orden_guardado = st.session_state.get("orden_capas_personalizado", [])
        orden_capas_mapa = [
            nombre for nombre in orden_guardado if nombre in capas_seleccionadas
        ]
        orden_capas_mapa.extend(
            nombre for nombre in capas_seleccionadas if nombre not in orden_capas_mapa
        )
        st.session_state["orden_capas_personalizado"] = orden_capas_mapa
        capas_activas = list(orden_capas_mapa)

        if any(
            nombre in capas_activas
            for nombre in ("Estado forestal JRC", "Deforestación JRC", "Degradación JRC")
        ):
            anio_tmf_capa = st.sidebar.selectbox(
                "Año de la capa JRC:",
                list(range(1990, ANO_TMF_MAX + 1)),
                index=ANO_TMF_MAX - 1990,
                help="Muestra un solo año; no activa el comparador.",
            )
        if "Uso y cobertura ESRI" in capas_activas:
            anio_esri_capa = st.sidebar.selectbox(
                "Año de la capa ESRI:",
                list(range(ANO_ESRI_MIN, ANO_ESRI_MAX + 1)),
                index=ANO_ESRI_MAX - ANO_ESRI_MIN,
                help="Muestra un solo año; no activa el comparador.",
            )
        if "Vegetación NDVI" in capas_activas:
            anio_ndvi_capa = st.sidebar.selectbox(
                "Año de la capa NDVI:",
                list(range(2017, ANO_NDVI_MAX + 1)),
                index=ANO_NDVI_MAX - 2017,
                help="Muestra un solo año; no activa el comparador.",
            )
        if "ΔNDVI" in capas_activas:
            anio_ndvi_inicial = st.sidebar.selectbox(
                f"Año inicial del cambio NDVI (final {ANO_NDVI_MAX}):",
                list(range(2017, ANO_NDVI_MAX)),
                index=list(range(2017, ANO_NDVI_MAX)).index(2023),
            )

        if orden_capas_mapa:
            with st.sidebar.expander("Orden y capa inicial", expanded=False):
                st.caption(
                    "La primera capa queda arriba. Las demás continúan disponibles en el mapa."
                )
                for posicion, nombre in enumerate(orden_capas_mapa, start=1):
                    st.caption(f"{posicion}. {nombres_capas[nombre]}")

                clave_capa_mover = "capa_a_reordenar"
                if st.session_state.get(clave_capa_mover) not in orden_capas_mapa:
                    st.session_state[clave_capa_mover] = orden_capas_mapa[0]
                capa_a_mover = st.selectbox(
                    "Capa que desea mover:",
                    orden_capas_mapa,
                    format_func=lambda valor: nombres_capas[valor],
                    key=clave_capa_mover,
                )
                columna_subir, columna_bajar = st.columns(2)
                if columna_subir.button(
                    "Subir",
                    use_container_width=True,
                    disabled=orden_capas_mapa.index(capa_a_mover) == 0,
                ):
                    indice = orden_capas_mapa.index(capa_a_mover)
                    orden_capas_mapa[indice - 1], orden_capas_mapa[indice] = (
                        orden_capas_mapa[indice],
                        orden_capas_mapa[indice - 1],
                    )
                    st.session_state["orden_capas_personalizado"] = orden_capas_mapa
                    st.rerun()
                if columna_bajar.button(
                    "Bajar",
                    use_container_width=True,
                    disabled=orden_capas_mapa.index(capa_a_mover) == len(orden_capas_mapa) - 1,
                ):
                    indice = orden_capas_mapa.index(capa_a_mover)
                    orden_capas_mapa[indice + 1], orden_capas_mapa[indice] = (
                        orden_capas_mapa[indice],
                        orden_capas_mapa[indice + 1],
                    )
                    st.session_state["orden_capas_personalizado"] = orden_capas_mapa
                    st.rerun()

                clave_capa_inicial = "capa_visible_inicial_personalizada"
                if st.session_state.get(clave_capa_inicial) not in orden_capas_mapa:
                    st.session_state[clave_capa_inicial] = orden_capas_mapa[0]
                capa_visible_inicial = st.selectbox(
                    "Capa visible al abrir:",
                    orden_capas_mapa,
                    format_func=lambda valor: nombres_capas[valor],
                    key=clave_capa_inicial,
                )
        else:
            capa_visible_inicial = None
            st.sidebar.warning("Seleccione al menos una capa temática.")

    firma_analisis_actual = (
        METHODOLOGY_VERSION,
        tipo_area,
        finca_seleccionada,
        ANO_DIAG_TMF,
        ANO_ESRI_MIN,
        ANO_ESRI_MAX,
        geometria_dibujada_json,
        catalogo_corredores["version_publicada"],
        huella_bosque,
        umbral_conectividad_m,
        area_min_parche_ha,
    )
    firma_visual_actual = (
        firma_analisis_actual,
        modo_mapa,
        modo_comparador,
        anio_tmf_inicial,
        anio_tmf_final,
        anio_esri_inicial,
        anio_esri_final,
        anio_ndvi_inicial,
        anio_ndvi_final,
        anio_tmf_capa,
        anio_esri_capa,
        anio_ndvi_capa,
        tuple(orden_capas_mapa),
        capa_visible_inicial,
    )
    analisis_actual = (
        st.session_state.get("firma_analisis") == firma_analisis_actual
    )
    flujo_contenedor = st.empty()

    st.markdown("### Selección actual")
    st.markdown(
        f"""
        <div class="contexto-analisis">
          <div class="contexto-item"><small>Área</small><strong>{html_lib.escape(nombre_area)}</strong></div>
          <div class="contexto-item"><small>Superficie</small><strong>{superficie_ha:,.1f} ha</strong></div>
          <div class="contexto-item"><small>Modo de mapa</small><strong>{html_lib.escape(modo_mapa)}</strong></div>
          <div class="contexto-item"><small>Vista</small><strong>{html_lib.escape(objetivo)}</strong></div>
          <div class="contexto-item"><small>Corredores</small><strong>Almanaque Azul {catalogo_corredores['version_publicada']}</strong></div>
          <div class="contexto-item"><small>Bosque y otros usos {ANO_BOSQUE_REFERENCIA}</small><strong>{'Disponible automáticamente' if bosque_automatico_disponible else 'Pendiente de configuración'}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if tipo_area == "Toda la cuenca":
        st.warning(
            "El análisis regional puede tardar varios minutos. Para una revisión rápida y "
            "más detallada se recomienda seleccionar una finca."
        )

    st.markdown(
        f"""
        <div class="paso-guia"><b>Configuración lista.</b> La vista elegida solo organiza
        los mapas. El cálculo utilizará siempre el mismo método <b>{METHODOLOGY_VERSION}</b>
        y sus períodos fijos. Pulse <b>Ejecutar análisis</b> y revise
        después la evidencia cartográfica.</div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("¿Qué diferencia hay entre cambio vegetal y vigor vegetal?", expanded=False):
        st.markdown(
            f"""
            - **ΔNDVI {anio_ndvi_inicial} → {ANO_NDVI_MAX}:** muestra cuánto cambió el vigor
              vegetal entre ambos años. Rojo indica disminución y verde indica aumento.
            - **Vegetación {anio_ndvi_capa}:** muestra la condición del vigor vegetal únicamente
              en {anio_ndvi_capa}. No representa un cambio y no distingue por sí sola entre bosque,
              cultivo o pastizal denso.

            GEDI aporta el componente estructural —altura del dosel— que NDVI no puede determinar.
            """
        )

    with st.expander("¿Por qué aparecen los períodos 2020-2025 y 2017-2024?", expanded=False):
        st.markdown(
            f"""
            - **JRC 2020-2025 en el comparador:** es una lectura visual desde el año del
              corte de referencia EUDR ({CUTOFF_LABEL}) hasta el estado forestal más
              reciente disponible ({ANO_DIAG_TMF}). **No es la operación que calcula la
              señal JRC.** El análisis lee la banda `Dec{ANO_DIAG_TMF}` y mide los píxeles
              clasificados por JRC como degradación o deforestación.
            - **Hansen 2021-{ANO_HANSEN_MAX}:** identifica pérdidas arbóreas posteriores
              al 31/12/2020. Es la fuente que aplica explícitamente el corte temporal post-2020.
            - **ESRI {ANO_ESRI_MIN}-{ANO_ESRI_MAX}:** el análisis compara los extremos de
              la serie configurada y mide dónde la clase árboles de {ANO_ESRI_MIN} cambió
              a otra clase en {ANO_ESRI_MAX}. El año {ANO_ESRI_MAX} es el último disponible
              en esta configuración.

            Los años elegidos por el usuario en el mapa son solo para exploración visual;
            no alteran esos períodos del análisis.
            """
        )

    st.subheader("Ejecutar y revisar resultados")
    st.caption(
        "Primero se calcularán únicamente las señales y el resumen. El informe con siete mapas "
        "se preparará después, solo si usted lo solicita. "
        f"Períodos fijos: estado JRC {ANO_DIAG_TMF}, Hansen 2021-{ANO_HANSEN_MAX} "
        f"posterior al corte {CUTOFF_LABEL} y ESRI {ANO_ESRI_MIN}-{ANO_ESRI_MAX}. "
        "Los años elegidos en el mapa solo modifican la visualización."
    )
    entregables_contenedor = st.empty()
    if not analisis_actual:
        mostrar_entregables(entregables_contenedor)
    if st.button(
        "Ejecutar análisis",
        type="primary",
        use_container_width=True,
        help="Calcula las señales territoriales. El PDF se prepara por separado para reducir la espera.",
    ):
        firma_anterior = st.session_state.get("firma_analisis")
        with st.spinner("Calculando las señales territoriales..."):
            resultados_nuevos = ejecutar_analisis(
                tipo_area,
                finca_seleccionada,
                ANO_DIAG_TMF,
                ANO_ESRI_MIN,
                ANO_ESRI_MAX,
                geometria_dibujada_json,
            )
            aoi_geojson_serializado = json.dumps(
                geometria.getInfo(),
                ensure_ascii=False,
                sort_keys=True,
            )
            resultados_nuevos["corredores"] = analizar_corredores_cache(
                aoi_geojson_serializado
            )
            if bosque_automatico_disponible:
                try:
                    resultados_nuevos["fragmentacion"] = analizar_bosque_asset_cache(
                        ASSET_BOSQUE_2021,
                        aoi_geojson_serializado,
                        umbral_conectividad_m,
                        area_min_parche_ha,
                    )
                    resultados_nuevos["fragmentacion"][
                        "fuente_cobertura"
                    ] = FUENTE_BOSQUE_CORTA
                    resultados_nuevos["fragmentacion"][
                        "ano_referencia_cobertura"
                    ] = ANO_BOSQUE_REFERENCIA
                except Exception as error:
                    resultados_nuevos["fragmentacion_error"] = str(error)
            resultados_nuevos["prioridad_visita"] = calcular_prioridad_visita(
                puntaje_cambios=resultados_nuevos["puntaje"],
                contexto_corredores=resultados_nuevos["corredores"],
                contexto_fragmentacion=resultados_nuevos.get("fragmentacion"),
            )
            st.session_state["resultados_analisis"] = resultados_nuevos
            st.session_state["firma_analisis"] = firma_analisis_actual
            if firma_anterior != firma_analisis_actual:
                st.session_state.pop("pdf_analisis", None)
                st.session_state.pop("firma_informe", None)
                st.session_state.pop("errores_mapas", None)
                st.session_state.pop("intento_informe", None)
                st.session_state.pop("mapas_reporte", None)

    analisis_actual = (
        st.session_state.get("firma_analisis") == firma_analisis_actual
    )
    mostrar_flujo(4 if analisis_actual else 3, flujo_contenedor)
    if analisis_actual:
        entregables_contenedor.empty()

    if st.session_state.get("firma_analisis") == firma_analisis_actual:
        resultados = st.session_state["resultados_analisis"]
        mostrar_resultados(
            resultados,
            ANO_DIAG_TMF,
            ANO_ESRI_MIN,
            ANO_ESRI_MAX,
        )
        mostrar_resultados_corredores(resultados["corredores"])
        if resultados.get("fragmentacion"):
            mostrar_resultados_fragmentacion(resultados["fragmentacion"])
        elif resultados.get("fragmentacion_error"):
            st.warning(
                "La cobertura institucional de bosque no pudo incorporarse en esta ejecución. "
                "La administración debe revisar el secreto EE_ASSET_BOSQUE_2021 y el permiso "
                f"de lectura del asset. Detalle técnico: {resultados['fragmentacion_error']}"
            )
        registro_resultados = construir_registro_metodologico(
            tipo_area=tipo_area,
            finca_id=finca_seleccionada,
            geometria_geojson=geometria_dibujada_json,
            anio_tmf_visual_inicial=anio_tmf_inicial,
            anio_tmf_visual_final=anio_tmf_final,
            anio_esri_visual_inicial=anio_esri_inicial,
            anio_esri_visual_final=anio_esri_final,
            anio_ndvi_visual_inicial=anio_ndvi_inicial,
            anio_ndvi_visual_final=anio_ndvi_final,
            anio_tmf_capa=anio_tmf_capa,
            anio_esri_capa=anio_esri_capa,
            anio_ndvi_capa=anio_ndvi_capa,
            modo_comparador=modo_comparador,
            capas_activas=capas_activas,
            resultados=resultados,
        )
        nombre_archivo = re.sub(r"[^A-Za-z0-9_-]+", "_", nombre_area).strip("_").lower()
        columna_pdf, columna_metodo = st.columns(2)
        informe_actual = (
            st.session_state.get("firma_informe") == firma_visual_actual
            and st.session_state.get("pdf_analisis")
        )
        errores_informe = (
            st.session_state.get("errores_mapas", [])
            if st.session_state.get("firma_informe") == firma_visual_actual
            else []
        )
        if not informe_actual or errores_informe:
            etiqueta_informe = (
                "Reintentar mapas faltantes"
                if informe_actual and errores_informe
                else "Preparar informe PDF"
            )
            preparar_informe = columna_pdf.button(
                etiqueta_informe,
                use_container_width=True,
                key="preparar-informe-pdf",
                help=(
                    "Solicita en paralelo las siete imágenes temáticas a Earth Engine y arma "
                    "el documento. Si ya existe un informe parcial, vuelve a intentar los mapas."
                ),
            )
            if preparar_informe:
                # El primer intento conserva una clave de caché estable. Solo se
                # crea una clave nueva cuando el usuario reintenta mapas faltantes.
                intento_informe = (
                    st.session_state.get("intento_informe", 0) + 1
                    if errores_informe
                    else 0
                )
                st.session_state["intento_informe"] = intento_informe
                with st.status(
                    "Preparando el informe cartográfico...",
                    expanded=True,
                ) as estado_informe:
                    try:
                        estado_informe.write(
                            "Solicitando siete mapas a Earth Engine en grupos de tres."
                        )
                        mapas_reporte, errores_mapas = generar_mapas_reporte(
                            tipo_area,
                            finca_seleccionada,
                            ANO_DIAG_TMF,
                            anio_esri_inicial,
                            anio_esri_final,
                            anio_ndvi_inicial,
                            geometria_dibujada_json,
                            intento_informe,
                            st.session_state.get("mapas_reporte")
                            if errores_informe
                            else None,
                        )
                        disponibles = sum(
                            1 for mapa_reporte in mapas_reporte if mapa_reporte.get("imagen")
                        )
                        estado_informe.write(
                            f"Earth Engine entregó {disponibles} de 7 mapas. Armando el PDF."
                        )
                        st.session_state["errores_mapas"] = errores_mapas
                        st.session_state["mapas_reporte"] = mapas_reporte
                        st.session_state["firma_informe"] = firma_visual_actual
                        if disponibles:
                            st.session_state["pdf_analisis"] = generar_pdf(
                                nombre_area,
                                resultados,
                                ANO_DIAG_TMF,
                                ANO_ESRI_MIN,
                                ANO_ESRI_MAX,
                                anio_ndvi_inicial,
                                mapas_reporte,
                            )
                            estado_informe.update(
                                label="Informe listo para descargar",
                                state="complete",
                                expanded=False,
                            )
                        else:
                            st.session_state.pop("pdf_analisis", None)
                            estado_informe.update(
                                label="Earth Engine no entregó los mapas",
                                state="error",
                                expanded=True,
                            )
                    except Exception as error:
                        st.session_state.pop("pdf_analisis", None)
                        st.session_state.pop("firma_informe", None)
                        st.session_state["errores_mapas"] = [
                            f"Preparación del informe: {type(error).__name__}"
                        ]
                        estado_informe.update(
                            label="No fue posible preparar el informe",
                            state="error",
                            expanded=True,
                        )
                        st.error(
                            "La solicitud cartográfica no finalizó. Puede intentarlo nuevamente; "
                            "los resultados del análisis permanecen disponibles."
                        )
                informe_actual = st.session_state.get("pdf_analisis")

        if informe_actual:
            columna_pdf.download_button(
                "Descargar informe PDF",
                data=informe_actual,
                file_name=f"ficha_preevaluacion_{nombre_archivo}.pdf",
                mime="application/pdf",
                on_click="ignore",
                type="primary",
                use_container_width=True,
            )
        else:
            columna_pdf.caption(
                "El PDF se prepara por separado. Los siete mapas se solicitan en paralelo para reducir la espera."
            )
        columna_metodo.download_button(
            "Descargar registro metodológico",
            data=json.dumps(
                registro_resultados,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            file_name=f"metodologia_preevaluacion_{nombre_archivo}.json",
            mime="application/json",
            on_click="ignore",
            use_container_width=True,
            help="Contiene fuentes, períodos, umbrales, pesos, reglas y el resumen del resultado.",
        )

        if st.session_state.get("firma_informe") == firma_visual_actual:
            errores_mapas = st.session_state.get("errores_mapas", [])
            if errores_mapas:
                disponibles = 7 - len(errores_mapas)
                if disponibles:
                    st.warning(
                        f"El informe contiene {disponibles} de 7 mapas. Algunas imágenes no "
                        "estuvieron disponibles temporalmente; puede volver a preparar el PDF."
                    )
                else:
                    st.error(
                        "Earth Engine no entregó las imágenes cartográficas. No se generó un PDF "
                        "incompleto. Vuelva a preparar el informe y, si continúa, envíe el detalle "
                        "técnico mostrado abajo."
                    )
                with st.expander("Detalle de los mapas no disponibles", expanded=False):
                    st.code("\n".join(errores_mapas))
    elif "resultados_analisis" in st.session_state:
        st.warning(
            "Cambió el área o el período. Ejecute nuevamente la preevaluación para "
            "actualizar los resultados y el informe."
        )
    else:
        st.info(
            "Cuando ejecute el análisis aparecerán el resumen, el detalle por fuente y los archivos de respaldo."
        )

    st.divider()
    st.subheader("Evidencia cartográfica")

    mapa = folium.Map(
        location=[8.7, -80.0],
        zoom_start=8,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        attr="Esri",
        name="Imagen satelital",
        overlay=False,
        control=True,
        max_zoom=20,
    ).add_to(mapa)
    Fullscreen(position="topleft", title="Pantalla completa").add_to(mapa)

    capa_izquierda = None
    capa_derecha = None
    etiqueta_inicial = None
    etiqueta_final = None
    if modo_comparador == "JRC TMF":
        etiqueta_inicial = f"JRC TMF {anio_tmf_inicial}"
        etiqueta_final = f"JRC TMF {anio_tmf_final}"
        capa_izquierda = capa_gee(
            mapa,
            obtener_tmf(anio_tmf_inicial, geometria),
            VIS_TMF,
            etiqueta_inicial,
            control=False,
            z_index=200,
        )
        capa_derecha = capa_gee(
            mapa,
            obtener_tmf(anio_tmf_final, geometria),
            VIS_TMF,
            etiqueta_final,
            control=False,
            z_index=200,
        )
    elif modo_comparador == "ESRI LULC":
        etiqueta_inicial = f"ESRI {anio_esri_inicial}"
        etiqueta_final = f"ESRI {anio_esri_final}"
        capa_izquierda = capa_gee(
            mapa,
            obtener_esri_visual(anio_esri_inicial, geometria),
            VIS_ESRI,
            etiqueta_inicial,
            control=False,
            z_index=200,
        )
        capa_derecha = capa_gee(
            mapa,
            obtener_esri_visual(anio_esri_final, geometria),
            VIS_ESRI,
            etiqueta_final,
            control=False,
            z_index=200,
        )
    elif modo_comparador == "NDVI Sentinel-2":
        etiqueta_inicial = f"NDVI {anio_ndvi_inicial}"
        etiqueta_final = f"NDVI {anio_ndvi_final}"
        capa_izquierda = capa_gee(
            mapa,
            clasificar_ndvi(obtener_ndvi(anio_ndvi_inicial, geometria)),
            VIS_NDVI_CLASES,
            etiqueta_inicial,
            control=False,
            z_index=200,
        )
        capa_derecha = capa_gee(
            mapa,
            clasificar_ndvi(obtener_ndvi(anio_ndvi_final, geometria)),
            VIS_NDVI_CLASES,
            etiqueta_final,
            control=False,
            z_index=200,
        )
    if capa_izquierda is not None and capa_derecha is not None:
        SideBySideLayers(
            layer_left=capa_izquierda,
            layer_right=capa_derecha,
        ).add_to(mapa)

    # En el modo de capas, el z-index conserva el orden configurado aunque una
    # capa se apague y se vuelva a encender desde el control del mapa.
    prioridades_capas = {
        nombre: 400 + (len(orden_capas_mapa) - indice) * 10
        for indice, nombre in enumerate(orden_capas_mapa)
    }
    capas_tematicas_mapa = []

    def agregar_tematica(clave, imagen, visualizacion, nombre):
        capa = capa_gee(
            mapa,
            imagen,
            visualizacion,
            nombre,
            mostrar=(
                modo_comparador == "Sin comparador"
                and clave == capa_visible_inicial
            ),
            z_index=prioridades_capas.get(clave, 400),
        )
        capas_tematicas_mapa.append((clave, capa))
        return capa

    perdida_post = perdida_pre = linea_base = None
    if any(
        nombre in capas_activas
        for nombre in [
            "Sectores para revisión",
            "Pérdida Hansen post-2020",
            "Pérdida Hansen 2001-2020",
            "Cobertura arbórea persistente",
        ]
    ):
        perdida_post, perdida_pre, linea_base = imagenes_hansen(geometria)

    if "Sectores para revisión" in capas_activas:
        coincidencia_revision = imagen_coincidencia_revision(
            geometria,
            tmf=obtener_tmf(ANO_DIAG_TMF, geometria),
            perdida_post=perdida_post,
            esri_inicial=obtener_esri(ANO_ESRI_MIN, geometria),
            esri_final=obtener_esri(ANO_ESRI_MAX, geometria),
        )
        agregar_tematica(
            "Sectores para revisión",
            coincidencia_revision.updateMask(coincidencia_revision.gt(0)),
            VIS_COINCIDENCIA_REVISION,
            "Sectores que requieren revisión · JRC + Hansen + ESRI",
        )

    if "Pérdida Hansen post-2020" in capas_activas:
        agregar_tematica(
            "Pérdida Hansen post-2020",
            perdida_post,
            VIS_HANSEN_POST,
            f"Hansen 2021-{ANO_HANSEN_MAX}",
        )
    if "Pérdida Hansen 2001-2020" in capas_activas:
        agregar_tematica(
            "Pérdida Hansen 2001-2020",
            perdida_pre,
            VIS_HANSEN_PRE,
            "Hansen 2001-2020",
        )
    if "Cobertura arbórea persistente" in capas_activas:
        agregar_tematica(
            "Cobertura arbórea persistente",
            linea_base,
            VIS_LINEA_BASE,
            "Cobertura arbórea persistente",
        )

    if "Estado forestal JRC" in capas_activas:
        agregar_tematica(
            "Estado forestal JRC",
            obtener_tmf(anio_tmf_capa, geometria),
            VIS_TMF,
            f"Estado forestal JRC {anio_tmf_capa}",
        )
    if "Deforestación JRC" in capas_activas:
        agregar_tematica(
            "Deforestación JRC",
            obtener_tmf(anio_tmf_capa, geometria).eq(3).selfMask(),
            VIS_TMF_DEFOR,
            f"Deforestación JRC {anio_tmf_capa}",
        )
    if "Degradación JRC" in capas_activas:
        agregar_tematica(
            "Degradación JRC",
            obtener_tmf(anio_tmf_capa, geometria).eq(2).selfMask(),
            VIS_TMF_DEGRAD,
            f"Degradación JRC {anio_tmf_capa}",
        )
    if "Uso y cobertura ESRI" in capas_activas:
        agregar_tematica(
            "Uso y cobertura ESRI",
            obtener_esri_visual(anio_esri_capa, geometria),
            VIS_ESRI,
            f"Uso y cobertura ESRI {anio_esri_capa}",
        )
    if "Transiciones ESRI" in capas_activas:
        esri_i = obtener_esri(anio_esri_inicial, geometria)
        esri_f = obtener_esri(anio_esri_final, geometria)
        transicion = (
            ee.Image(0)
            .where(esri_i.neq(2).And(esri_f.eq(2)), 1)
            .where(esri_i.eq(2).And(esri_f.neq(2)), 2)
            .where(esri_i.eq(2).And(esri_f.eq(2)), 3)
            .selfMask()
        )
        agregar_tematica(
            "Transiciones ESRI",
            transicion,
            VIS_ESRI_CAMBIO,
            f"Transiciones ESRI {anio_esri_inicial}-{anio_esri_final}",
        )
    if "Altura GEDI" in capas_activas:
        gedi = imagen_gedi(geometria)
        agregar_tematica(
            "Altura GEDI",
            gedi,
            VIS_GEDI,
            "Altura del dosel GEDI",
        )
    ndvi_final = None
    if "ΔNDVI" in capas_activas:
        ndvi_final = obtener_ndvi(ANO_NDVI_MAX, geometria)
    if "ΔNDVI" in capas_activas:
        ndvi_inicial = obtener_ndvi(anio_ndvi_inicial, geometria)
        delta_ndvi = ndvi_final.subtract(ndvi_inicial).rename("delta_ndvi")
        agregar_tematica(
            "ΔNDVI",
            delta_ndvi,
            VIS_NDVI_DELTA,
            f"ΔNDVI {anio_ndvi_inicial}-{ANO_NDVI_MAX}",
        )
    if "Vegetación NDVI" in capas_activas:
        agregar_tematica(
            "Vegetación NDVI",
            clasificar_ndvi(obtener_ndvi(anio_ndvi_capa, geometria)),
            VIS_NDVI_CLASES,
            f"Vegetación NDVI {anio_ndvi_capa}",
        )

    capas_corredores_mapa = agregar_capas_corredores(
        mapa,
        mostrar=objetivo == "Diagnóstico territorial integrado",
    )
    capa_fragmentacion_mapa = None
    if st.session_state.get("firma_analisis") == firma_analisis_actual:
        resultados_mapa = st.session_state.get("resultados_analisis", {})
        if resultados_mapa.get("fragmentacion"):
            capa_fragmentacion_mapa = agregar_resultados_fragmentacion(
                mapa,
                resultados_mapa["fragmentacion"],
            )

    cuenca = ee.FeatureCollection(ASSET_CUENCA)
    capa_limite_cuenca = capa_gee(
        mapa,
        cuenca.style(color="FF4444", fillColor="00000000", width=3),
        {},
        "Límite de la cuenca",
        z_index=1000,
    )
    capa_area_seleccionada = capa_gee(
        mapa,
        area_seleccionada.style(color="00E5FF", fillColor="00E5FF18", width=4),
        {},
        "Área seleccionada",
        z_index=1010,
    )
    limites_area = obtener_limites(area_seleccionada)
    if etiqueta_inicial and etiqueta_final:
        agregar_rotulos_comparador(
            mapa,
            limites_area,
            etiqueta_inicial,
            etiqueta_final,
        )
    mapa.fit_bounds(limites_area)
    if capas_tematicas_mapa:
        capas_por_clave = dict(capas_tematicas_mapa)
        capas_control = [
            capas_por_clave[nombre]
            for nombre in orden_capas_mapa
            if nombre in capas_por_clave
        ]
        GroupedLayerControl(
            groups={
                "Capas temáticas · puede combinar varias": capas_control
            },
            exclusive_groups=False,
            collapsed=False,
        ).add_to(mapa)
    GroupedLayerControl(
        groups={
            "Corredores ecológicos · fuente externa": capas_corredores_mapa,
        },
        exclusive_groups=False,
        collapsed=True,
    ).add_to(mapa)
    if capa_fragmentacion_mapa is not None:
        GroupedLayerControl(
            groups={
                f"Conectividad calculada · bosque {ANO_BOSQUE_REFERENCIA}": [
                    capa_fragmentacion_mapa
                ],
            },
            exclusive_groups=False,
            collapsed=True,
        ).add_to(mapa)
    GroupedLayerControl(
        groups={
            "Referencias · se mantienen visibles": [
                capa_limite_cuenca,
                capa_area_seleccionada,
            ]
        },
        exclusive_groups=False,
        collapsed=True,
    ).add_to(mapa)

    st.markdown("#### Mapa interactivo del área evaluada")
    if etiqueta_inicial and etiqueta_final:
        st.markdown(
            f"""
            <div class="comparador-anios">
              <span>◀ <b>Año inicial</b><br>{etiqueta_inicial}</span>
              <span><b>Año final</b> ▶<br>{etiqueta_final}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "Arrastre el control circular del divisor vertical. El lado izquierdo muestra el "
            "año inicial y el derecho el año final. Este modo muestra únicamente la comparación "
            "temporal para que ninguna capa temática la cubra."
        )
    else:
        st.caption(
            "Use «Capas temáticas» dentro del mapa para encender o apagar una o varias capas. "
            "Su orden se controla en el panel lateral; los límites permanecen arriba y se "
            "administran por separado en «Referencias». Los corredores se controlan en el "
            "grupo «Corredores ecológicos»: no modifican el índice satelital, pero sí "
            "aportan al valor estratégico. La red de parches 2021 se controla en "
            "«Conectividad calculada» y orienta dónde focalizar la visita."
        )
    st_folium(
        mapa,
        height=650,
        use_container_width=True,
        returned_objects=[],
        key=(
            f"mapa-{APP_VERSION}-{tipo_area}-{finca_seleccionada}-{modo_mapa}-{modo_comparador}-"
            f"{anio_tmf_inicial}-{anio_tmf_final}-{anio_esri_inicial}-"
            f"{anio_esri_final}-{anio_ndvi_inicial}-{anio_ndvi_final}-"
            f"{anio_tmf_capa}-{anio_esri_capa}-{anio_ndvi_capa}-"
            f"{'-'.join(orden_capas_mapa)}-"
            f"{capa_visible_inicial}-"
            f"{catalogo_corredores['version_publicada']}-{huella_bosque}-"
            f"{umbral_conectividad_m}-{area_min_parche_ha}-"
            f"{hash(geometria_dibujada_json or '')}"
        ),
    )

    with st.expander("Ver leyendas de colores", expanded=True):
        columnas_leyenda = st.columns(2)
        leyendas_activas = [
            ("Corredores · Almanaque Azul", LEYENDAS["Corredores Almanaque Azul"])
        ]
        if capa_fragmentacion_mapa is not None:
            leyendas_activas.append(
                ("Importancia calculada de parches", LEYENDAS["Importancia de parches"])
            )
        if modo_comparador in ("JRC TMF", "ESRI LULC", "NDVI Sentinel-2"):
            leyendas_activas.append((modo_comparador, LEYENDAS[modo_comparador]))
        for nombre in capas_activas:
            if nombre in LEYENDAS:
                leyendas_activas.append((nombres_capas.get(nombre, nombre), LEYENDAS[nombre]))
            elif nombre == "Estado forestal JRC":
                leyendas_activas.append((nombres_capas[nombre], LEYENDAS["JRC TMF"]))
            elif nombre == "Uso y cobertura ESRI":
                leyendas_activas.append((nombres_capas[nombre], LEYENDAS["ESRI LULC"]))
        for indice, (titulo, elementos) in enumerate(leyendas_activas):
            with columnas_leyenda[indice % 2]:
                mostrar_leyenda(titulo, elementos)

    if modo_comparador == "NDVI Sentinel-2":
        periodo_ndvi_visual = f"{anio_ndvi_inicial}-{anio_ndvi_final}"
    elif "ΔNDVI" in capas_activas:
        periodo_ndvi_visual = f"{anio_ndvi_inicial}-{ANO_NDVI_MAX}"
    elif "Vegetación NDVI" in capas_activas:
        periodo_ndvi_visual = str(anio_ndvi_capa)
    else:
        periodo_ndvi_visual = f"hasta {ANO_NDVI_MAX}"

    with st.expander("Metodología y reproducibilidad", expanded=False):
        st.markdown(f"**Metodología aplicada:** {METHODOLOGY_VERSION}")
        tab_fuentes, tab_reglas, tab_limites = st.tabs(
            ["Fuentes y períodos", "Reglas del análisis", "Alcance y limitaciones"]
        )
        with tab_fuentes:
            st.markdown(
                f"""
                | Fuente | Período o referencia | Resolución de trabajo | Función |
                |---|---:|---:|---|
                | JRC Tropical Moist Forest | Estado {ANO_DIAG_TMF} | 30 m | Señales de degradación y deforestación |
                | Hansen Global Forest Change | 2001-{ANO_HANSEN_MAX}; corte {CUTOFF_LABEL} | 30 m | Pérdida de cobertura arbórea |
                | ESRI Land Use/Land Cover | Diagnóstico {ANO_ESRI_MIN}-{ANO_ESRI_MAX} | 10 m | Transiciones de la clase árboles |
                | GEDI / OpenForis | Producto disponible | 100 m | Altura y cobertura válida del dosel |
                | Sentinel-2 SR Harmonized | {periodo_ndvi_visual} | 10 m | Vigor vegetal; apoyo visual |
                | Almanaque Azul | {catalogo_corredores['version_publicada']} | Vector interpretado | Valor estratégico para planificar visitas |
                | SINIA–MiAMBIENTE · Bosque y otros usos | {ANO_BOSQUE_REFERENCIA if bosque_automatico_disponible else 'Pendiente de configuración'} | Vector institucional en Earth Engine | Fragmentación y red de parches; contexto |
                """
            )
            st.markdown(
                f"""
                **Cómo se interpretan los períodos**

                - JRC aporta el **estado forestal de {ANO_DIAG_TMF}**. La señal se obtiene
                  de sus clases de degradación y deforestación; no de una resta 2020-2025.
                - Hansen aporta la pérdida anual **posterior al 31/12/2020**, es decir,
                  2021-{ANO_HANSEN_MAX}.
                - ESRI compara la clase árboles entre **{ANO_ESRI_MIN} y {ANO_ESRI_MAX}**,
                  los extremos de la serie utilizada por el análisis.
                - Los años seleccionables del mapa son parámetros de visualización y no
                  cambian el índice de prioridad.
                """
            )
            with st.expander("Identificadores técnicos de los datos", expanded=False):
                st.code(
                    "\n".join(
                        [TMF_ASSET, HANSEN_ASSET, ESRI_ASSET, GEDI_ASSET, "COPERNICUS/S2_SR_HARMONIZED"]
                    )
                )
        with tab_reglas:
            st.markdown(
                f"""
                1. Cada fuente se procesa en su propia resolución y proyección.
                2. Las superficies se expresan en hectáreas dentro del área seleccionada.
                3. Las señales se activan con umbrales documentados: JRC, Hansen, ESRI y GEDI.
                4. El índice suma cada fuente una sola vez: **JRC 2.0**, **Hansen 2.0**,
                   **ESRI 1.5**, **GEDI 0.5** y **NDVI 0.0**.
                5. La prioridad es **alta desde 3.0**, **media desde 1.5**, **preventiva desde 0.5** y **baja por debajo de 0.5**.
                6. El mapa **Sectores que requieren revisión** suma, en una malla común
                   de 30 m, las señales binarias de JRC, Hansen y ESRI. Muestra una,
                   dos o tres fuentes coincidentes, pero **no modifica el índice**.
                7. Los corredores de Almanaque Azul conservan sus categorías publicadas:
                   **alta, mediana y media-baja**. Su intersección se mide en un sistema
                   equivalente en área y **no modifica el índice satelital**. Para la prioridad
                   de visita, el solapamiento aporta proporcionalmente hasta **1.0 punto al
                   alcanzar 25% del área** y el Corredor Biológico Mesoamericano aporta **0.5**.
                8. El corredor por sí solo nunca genera una prioridad alta: sin señales de
                   cambio, el resultado integrado queda limitado a **preventiva**.
                9. El recorte institucional de **Bosque y otros usos 2021** de
                   SINIA–MiAMBIENTE se carga automáticamente. Cada parche de bosque es un nodo y se conecta con
                   otros dentro del umbral elegido. El índice conector usa 40% grado,
                   30% intermediación, 20% área y 10% fuerza; sus categorías son relativas
                   al área evaluada y no deben confundirse con las de Almanaque Azul.
                10. La estructura 2021 se conecta con el diagnóstico para indicar **dónde**
                    focalizar la visita —conectores y componentes aislados—, pero no suma
                    puntos hasta contar con umbrales calibrados para el territorio y las
                    especies objetivo.

                El NDVI se calcula como `(B8 - B4) / (B8 + B4)` y se utiliza únicamente
                como apoyo visual. No modifica el índice de prioridad.
                """
            )
            mostrar_escala_ndvi_metodologia()
            st.markdown("**Justificación de los pesos**")
            st.markdown(
                "\n".join(
                    [
                        f"- **JRC TMF · 2.0:** {JUSTIFICACION_PESOS['tmf']}",
                        f"- **Hansen GFC · 2.0:** {JUSTIFICACION_PESOS['hansen']}",
                        f"- **ESRI LULC · 1.5:** {JUSTIFICACION_PESOS['esri']}",
                        f"- **GEDI · 0.5:** {JUSTIFICACION_PESOS['gedi']}",
                        f"- **NDVI · 0.0:** {JUSTIFICACION_PESOS['ndvi']}",
                    ]
                )
            )
            st.markdown("**Justificación de los umbrales**")
            st.markdown(
                "\n".join(
                    [
                        f"- **Hansen ≥ {UMBRAL_ALERTA_HANSEN_HA:.2f} ha:** {JUSTIFICACION_UMBRALES['hansen_post_2020_ha']}",
                        f"- **JRC deforestación ≥ {UMBRAL_REVISION_TMF_DEFOR_HA:.1f} ha o {UMBRAL_PCT_TMF_DEFOR:.0f}%:** {JUSTIFICACION_UMBRALES['jrc_deforestacion']}",
                        f"- **JRC degradación ≥ {UMBRAL_REVISION_TMF_DEGRAD_HA:.1f} ha o {UMBRAL_PCT_TMF_DEGRAD:.0f}%:** {JUSTIFICACION_UMBRALES['jrc_degradacion']}",
                        f"- **ESRI ≥ {UMBRAL_ESRI_SALIDA_HA:.2f} ha y {UMBRAL_PCT_ESRI_SALIDA:.0f}%:** {JUSTIFICACION_UMBRALES['esri_salida_arboles']}",
                        f"- **GEDI < {UMBRAL_DOSEL_BAJO_M:.0f} m, cobertura válida ≥ {UMBRAL_COBERTURA_GEDI_PCT:.0f}% y línea base ≥ {UMBRAL_LINEA_BASE_GEDI_PCT:.0f}%:** {JUSTIFICACION_UMBRALES['gedi_dosel_y_cobertura']}",
                        f"- **NDVI:** {JUSTIFICACION_UMBRALES['ndvi']}",
                    ]
                )
            )
            st.caption(
                "Todos los años seleccionables cambian únicamente la visualización. "
                f"El diagnóstico conserva JRC {ANO_DIAG_TMF}, Hansen 2021-{ANO_HANSEN_MAX} "
                f"posterior al corte {CUTOFF_LABEL} y ESRI {ANO_ESRI_MIN}-{ANO_ESRI_MAX}."
            )
            st.markdown("**Lectura de consistencia entre fuentes**")
            st.markdown(
                "\n".join(
                    [
                        f"- **Alta consistencia:** {REGLAS_CONSISTENCIA['alta']}.",
                        f"- **Consistencia parcial:** {REGLAS_CONSISTENCIA['parcial']}.",
                        f"- **Lectura mixta:** {REGLAS_CONSISTENCIA['mixta']}.",
                        f"- **Sin señal consistente:** {REGLAS_CONSISTENCIA['sin_senal']}.",
                    ]
                )
            )
            st.caption(
                "La consistencia complementa la interpretación y nunca suma, resta ni "
                "compensa puntos del índice."
            )
            st.markdown("**Mapa de coincidencia espacial**")
            st.markdown(
                "\n".join(
                    [
                        "- **1 fuente · amarillo:** señal aislada; revise el producto correspondiente.",
                        "- **2 fuentes · naranja:** coincidencia espacial que merece revisión prioritaria.",
                        "- **3 fuentes · rojo oscuro:** coincidencia espacial de las tres fuentes principales.",
                        f"- **Limitación:** {REGLAS_MAPA_COINCIDENCIA['limitacion']}",
                    ]
                )
            )
        with tab_limites:
            st.markdown(
                """
                - Una señal satelital no confirma por sí sola la causa de un cambio.
                - Las fuentes tienen fechas, resoluciones y metodologías diferentes.
                - La altura GEDI depende de la disponibilidad espacial del producto.
                - El NDVI puede responder a estacionalidad, humedad, nubes, cultivos o pastizales.
                - Los resultados deben contrastarse con documentos, imágenes recientes y campo.
                - Los corredores publicados representan conectividad estructural a escala de paisaje;
                  no garantizan movimiento efectivo de una especie concreta.
                - La cobertura SINIA–MiAMBIENTE representa bosque y otros usos en 2021; no indica por sí sola el año de una pérdida.
                - La calidad del análisis de fragmentación depende de la escala, topología y clasificación del asset institucional configurado.

                **Esta herramienta orienta revisiones. No es una certificación, una validación de
                campo ni una determinación de cumplimiento EUDR.**
                """
            )

except Exception as error:
    mostrar_flujo(1)
    mostrar_error_amigable(error)
    with st.expander("Detalle técnico para soporte", expanded=False):
        st.code(f"{type(error).__name__}: {error}")
