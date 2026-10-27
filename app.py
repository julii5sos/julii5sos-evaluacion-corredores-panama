"""Punto de entrada ligero para Streamlit Community Cloud."""

import runpy
from pathlib import Path

import streamlit as st

from metodologia_indice import (
    PERIODOS_ANALISIS,
    PESOS_INDICE,
    PUNTAJE_MAXIMO,
    UMBRALES_INDICE,
)
from modos_app import MODO_INTEGRAL, MODOS_ANALISIS


st.set_page_config(
    page_title="Preevaluación territorial y corredores | Panamá",
    page_icon=":material/map:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.session_state["_pagina_configurada"] = True

VISTA_PREEVALUAR = "Preevaluar un área"
VISTA_OBJETIVO = "Objetivo y alcance"
VISTA_METODO = "Método y fuentes"
VISTAS_PRINCIPALES = (VISTA_PREEVALUAR, VISTA_OBJETIVO, VISTA_METODO)


st.markdown(
    """
    <style>
    :root {--verde:#00544d;--verde-oscuro:#00403a;--suave:#356b61;--borde:#b6d1c8;--fondo:#f6faf8;--claro:#eaf4f0;}
    .stApp {background:var(--fondo);color:var(--verde);}
    .block-container {padding-top:3.5rem;padding-bottom:2.5rem;max-width:1440px;}
    button, [role="button"] {min-height:44px;touch-action:manipulation;}
    button:focus-visible, [role="button"]:focus-visible, input:focus-visible {
        outline:3px solid var(--verde);outline-offset:2px;
    }
    [data-testid="stSegmentedControl"] {margin-bottom:1rem;}
    [data-testid="stSegmentedControl"] button {cursor:pointer;}
    .entrada {
        padding:1.45rem 1.6rem;border:1px solid var(--borde);
        border-left:6px solid var(--verde);background:#fff;margin-bottom:1.2rem;
    }
    .entrada h1 {margin:0;color:var(--verde);font-size:clamp(2rem,4vw,3.25rem);line-height:1.12;}
    .entrada .subtitulo {margin:.45rem 0 0;color:var(--verde);font-size:1.2rem;font-weight:650;line-height:1.4;}
    .entrada p {color:var(--suave);max-width:75ch;line-height:1.6;margin:.65rem 0 0;}
    .entrada small {display:block;margin-top:.65rem;color:var(--suave);line-height:1.5;}
    .pregunta {margin:.1rem 0 1rem;color:var(--verde);}
    .tarjeta {min-height:220px;}
    .tarjeta small {display:block;color:var(--suave);font-weight:700;text-transform:uppercase;line-height:1.4;}
    .tarjeta h3 {margin:.45rem 0;color:var(--verde);line-height:1.35;}
    .tarjeta p {color:var(--suave);line-height:1.55;}
    .resultado {padding-top:.6rem;border-top:1px solid var(--borde);line-height:1.5;}
    .ruta-simple, .metodo-pasos {
        display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin:.8rem 0 1.25rem;
    }
    .ruta-paso, .metodo-paso {
        position:relative;padding:1rem 1rem 1rem 3.7rem;border:1px solid var(--borde);
        background:#fff;min-height:130px;line-height:1.5;
    }
    .ruta-numero, .metodo-numero {
        position:absolute;top:1rem;left:1rem;display:grid;place-items:center;width:2rem;height:2rem;
        border-radius:50%;background:var(--verde);color:#fff;font-weight:750;
    }
    .ruta-paso b, .metodo-paso b {display:block;margin-bottom:.3rem;color:var(--verde);}
    .ruta-paso span, .metodo-paso span {color:var(--suave);font-size:.94rem;}
    .alcance-grid {display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin:.8rem 0 1.25rem;}
    .alcance-card {padding:1rem 1.1rem;border:1px solid var(--borde);background:#fff;line-height:1.6;}
    .alcance-card h3 {margin:0 0 .45rem;color:var(--verde);font-size:1.15rem;}
    .alcance-card ul {margin:.3rem 0 0;padding-left:1.25rem;color:var(--suave);}
    .alcance-card li {margin:.35rem 0;}
    .nota-alcance {
        padding:.9rem 1rem;border-left:5px solid var(--verde);background:var(--claro);
        color:var(--verde);line-height:1.6;margin:.75rem 0 1rem;
    }
    .texto-legible {max-width:75ch;color:var(--suave);line-height:1.65;}
    @media(max-width:760px){
        .block-container{padding-top:3rem}.entrada{padding:1.1rem}
        .ruta-simple,.metodo-pasos,.alcance-grid{grid-template-columns:1fr}
        .tarjeta{min-height:auto}
    }
    @media(prefers-reduced-motion:reduce){
        *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.01ms!important;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def elegir_modo(modo):
    st.session_state["modo_analisis"] = modo


def abrir_vista(vista):
    st.session_state["vista_principal"] = vista


def mostrar_cabecera(titulo, subtitulo, descripcion, alcance=None):
    alcance_html = f"<small>{alcance}</small>" if alcance else ""
    st.markdown(
        f"""
        <div class="entrada">
          <h1>{titulo}</h1>
          <div class="subtitulo">{subtitulo}</div>
          <p>{descripcion}</p>
          {alcance_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_objetivo():
    mostrar_cabecera(
        "¿Para qué sirve esta preevaluación?",
        "Convierte un área de interés en evidencia inicial para orientar una decisión.",
        "En pocos pasos, la aplicación ayuda a explicar por qué un territorio merece una "
        "revisión más detallada, dónde conviene mirar primero y qué información respalda esa orientación.",
        "Herramienta de orientación · no sustituye una visita de campo ni una decisión técnica o legal definitiva",
    )
    st.markdown("## Propósito y utilidad de la preevaluación")
    st.markdown(
        """
        <div class="ruta-simple" aria-label="Cómo ayuda la preevaluación">
          <div class="ruta-paso"><span class="ruta-numero">1</span><b>Seleccione el área</b><span>Use una finca, una subcuenca, un polígono dibujado o la cuenca completa.</span></div>
          <div class="ruta-paso"><span class="ruta-numero">2</span><b>Reúna indicios</b><span>La aplicación consulta señales satelitales, corredores publicados y estructura del bosque según el enfoque elegido.</span></div>
          <div class="ruta-paso"><span class="ruta-numero">3</span><b>Sustente el siguiente paso</b><span>Reciba una orientación, un mapa y evidencia trazable para decidir si conviene profundizar o visitar el área.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("## Qué puede concluir y qué debe confirmar")
    st.markdown(
        """
        <div class="alcance-grid">
          <section class="alcance-card">
            <h3>La aplicación sí permite</h3>
            <ul>
              <li>detectar indicios que justifican una revisión más detallada;</li>
              <li>comparar varias fuentes sin exigir experiencia previa en teledetección;</li>
              <li>ubicar sectores donde coinciden señales o donde la conectividad merece atención;</li>
              <li>documentar fuentes, períodos, reglas y parámetros para respaldar la conversación.</li>
            </ul>
          </section>
          <section class="alcance-card">
            <h3>La aplicación no pretende</h3>
            <ul>
              <li>confirmar en campo una pérdida, degradación o causa específica;</li>
              <li>demostrar conectividad funcional o movimiento de una especie;</li>
              <li>emitir una certificación, sanción o conclusión legal;</li>
              <li>determinar por sí sola cumplimiento de EUDR u otra norma.</li>
            </ul>
          </section>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="nota-alcance"><b>Resultado esperado:</b> una preevaluación reproducible
        que ayuda a justificar por qué un área debe tomarse en cuenta. La decisión final debe
        complementarse con conocimiento local, documentos, imágenes recientes y, cuando corresponda,
        verificación de campo.</div>
        """,
        unsafe_allow_html=True,
    )
    st.button(
        "Comenzar una preevaluación",
        type="primary",
        width="stretch",
        on_click=abrir_vista,
        args=(VISTA_PREEVALUAR,),
    )


def mostrar_metodo():
    mostrar_cabecera(
        "Cómo se construye la preevaluación",
        "Una explicación sencilla primero; las reglas técnicas permanecen disponibles después.",
        "Cada fuente responde una pregunta diferente. La aplicación conserva esas diferencias, "
        "aplica reglas documentadas y presenta una orientación que puede rastrearse hasta sus datos de origen.",
        "Los años del comparador cambian el mapa, pero no modifican las reglas del índice configurado",
    )
    st.markdown("## El proceso en cinco pasos")
    st.markdown(
        """
        <div class="metodo-pasos" aria-label="Pasos del método">
          <div class="metodo-paso"><span class="metodo-numero">1</span><b>Delimitar</b><span>El área elegida se recorta al límite institucional de la cuenca cuando corresponde.</span></div>
          <div class="metodo-paso"><span class="metodo-numero">2</span><b>Consultar</b><span>Se solicitan únicamente las fuentes necesarias para el enfoque seleccionado.</span></div>
          <div class="metodo-paso"><span class="metodo-numero">3</span><b>Medir</b><span>Las señales se expresan en hectáreas, porcentajes, cambios o métricas de conectividad.</span></div>
          <div class="metodo-paso"><span class="metodo-numero">4</span><b>Aplicar reglas</b><span>Los umbrales y pesos documentados convierten los indicios en una orientación comparable.</span></div>
          <div class="metodo-paso"><span class="metodo-numero">5</span><b>Explicar</b><span>El resumen, el mapa y el registro metodológico muestran qué influyó y qué no.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## Qué aporta cada fuente")
    st.caption("La tabla usa lenguaje cotidiano. La identificación técnica completa permanece en el registro metodológico descargable.")
    st.dataframe(
        [
            {
                "Fuente": "JRC Tropical Moist Forest",
                "Pregunta que ayuda a responder": "¿Hay indicios de degradación o deforestación en bosque tropical?",
                "Referencia": str(PERIODOS_ANALISIS["jrc_diagnostico"]),
                "Papel": "Señal forestal principal",
            },
            {
                "Fuente": "Hansen Global Forest Change",
                "Pregunta que ayuda a responder": "¿Se registró pérdida anual de cobertura arbórea después de 2020?",
                "Referencia": f"2021–{PERIODOS_ANALISIS['hansen_diagnostico']}",
                "Papel": "Señal forestal principal",
            },
            {
                "Fuente": "ESRI Land Use/Land Cover",
                "Pregunta que ayuda a responder": "¿Sectores clasificados como árboles pasaron a otra cobertura?",
                "Referencia": f"{PERIODOS_ANALISIS['esri_inicial']}–{PERIODOS_ANALISIS['esri_final']}",
                "Papel": "Señal corroborativa",
            },
            {
                "Fuente": "Sentinel-2 · NDVI",
                "Pregunta que ayuda a responder": "¿Disminuyó de forma importante el vigor de la vegetación?",
                "Referencia": f"{PERIODOS_ANALISIS['ndvi_inicial']}–{PERIODOS_ANALISIS['ndvi_final']}",
                "Papel": "Señal corroborativa",
            },
            {
                "Fuente": "GEDI / OpenForis",
                "Pregunta que ayuda a responder": "¿Qué contexto aporta la altura observada del dosel?",
                "Referencia": "Producto disponible",
                "Papel": "Contexto estructural",
            },
            {
                "Fuente": "Almanaque Azul",
                "Pregunta que ayuda a responder": "¿El área coincide con corredores naturales publicados?",
                "Referencia": "Versión publicada 2024.05",
                "Papel": "Valor estratégico",
            },
            {
                "Fuente": "SINIA–MiAMBIENTE · Bosque y otros usos",
                "Pregunta que ayuda a responder": "¿Cómo se distribuyen y relacionan los fragmentos de bosque?",
                "Referencia": "2021",
                "Papel": "Estructura y conectividad",
            },
        ],
        hide_index=True,
        width="stretch",
    )

    with st.expander("Para usuarios técnicos: pesos, umbrales y separación de resultados", expanded=False):
        st.markdown(
            f"""
            **Índice de indicios territoriales**

            - JRC: **{PESOS_INDICE['tmf']:.1f}** puntos.
            - Hansen: **{PESOS_INDICE['hansen']:.1f}** puntos.
            - ESRI: **{PESOS_INDICE['esri']:.1f}** puntos.
            - GEDI: **{PESOS_INDICE['gedi']:.1f}** puntos.
            - NDVI: **{PESOS_INDICE['ndvi']:.1f}** puntos.
            - Máximo configurado: **{PUNTAJE_MAXIMO:.1f}** puntos.

            La señal NDVI exige simultáneamente una disminución de
            **{abs(UMBRALES_INDICE['ndvi_delta_disminucion']):.2f}**, al menos
            **{UMBRALES_INDICE['ndvi_disminucion_ha']:.2f} ha** y
            **{UMBRALES_INDICE['ndvi_disminucion_pct']:.0f}% del área**, con una cobertura
            válida mínima de **{UMBRALES_INDICE['ndvi_cobertura_minima_pct']:.0f}%**.

            Los corredores publicados **no aumentan el índice satelital**. La opción integral
            los incorpora por separado para orientar la visita; un corredor sin indicios de
            cambio no produce por sí solo una prioridad alta. La estructura del bosque ayuda
            a decidir **dónde** revisar, pero no recibe un peso inventado.
            """
        )

    with st.expander("Alcance técnico y limitaciones", expanded=False):
        st.markdown(
            """
            - Cada producto tiene fecha, resolución, clasificación y cobertura propias.
            - Una coincidencia entre fuentes fortalece la necesidad de revisar, pero no demuestra causalidad.
            - NDVI puede responder a humedad, estacionalidad, cultivos, nubes o sombras y no identifica por sí solo bosque natural.
            - GEDI tiene cobertura espacial limitada y se interpreta como contexto, no como pérdida confirmada.
            - La red de fragmentos representa conectividad estructural potencial; no modela especies, conducta ni conectividad funcional.
            - Los resultados deben contrastarse con conocimiento local, imágenes recientes, documentos y campo.
            """
        )

    st.button(
        "Ir a la preevaluación",
        type="primary",
        width="stretch",
        on_click=abrir_vista,
        args=(VISTA_PREEVALUAR,),
    )


vista_principal = st.segmented_control(
    "Secciones principales",
    VISTAS_PRINCIPALES,
    default=VISTA_PREEVALUAR,
    key="vista_principal",
    label_visibility="collapsed",
    width="stretch",
)

if vista_principal == VISTA_OBJETIVO:
    mostrar_objetivo()
    st.stop()
if vista_principal == VISTA_METODO:
    mostrar_metodo()
    st.stop()


modo_analisis = st.session_state.get("modo_analisis")
if modo_analisis not in MODOS_ANALISIS:
    st.session_state.pop("modo_analisis", None)
    modo_analisis = None

if modo_analisis is None:
    mostrar_cabecera(
        "Preevaluación territorial y corredores",
        "Evidencia inicial para orientar dónde conviene revisar.",
        "Elija una pregunta y un área. Las fuentes cartográficas se cargarán después, "
        "únicamente para preparar la preevaluación seleccionada.",
        "Resultado indicativo · requiere interpretación y verificación de campo",
    )
    st.markdown('<h2 class="pregunta">¿Qué desea preevaluar?</h2>', unsafe_allow_html=True)
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
                    width="stretch",
                    on_click=elegir_modo,
                    args=(modo,),
                )
    st.info(
        "Puede consultar primero «Objetivo y alcance» o «Método y fuentes». "
        "Earth Engine se conectará solo después de elegir una preevaluación."
    )
    st.stop()


APLICACION_ACTIVA = Path(__file__).with_name("app_experiencia.py")
if not APLICACION_ACTIVA.is_file():
    raise FileNotFoundError(
        "No se encontró app_experiencia.py, la implementación activa del visor."
    )

runpy.run_path(str(APLICACION_ACTIVA), run_name="__main__")
