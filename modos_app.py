"""Definiciones ligeras de las rutas principales de la aplicación."""

MODO_TERRITORIAL = "territorial"
MODO_CORREDORES = "corredores"
MODO_INTEGRAL = "integral"

TIPO_AREA_SUBCUENCA = "Subcuenca"
TIPO_AREA_DIBUJADA = "Dibujar polígono en el mapa"
TOLERANCIA_RECORTE_M = 10


def area_debe_recortarse_a_cuenca(tipo_area):
    """Limita toda unidad menor al polígono institucional de la cuenca."""

    return tipo_area != "Toda la cuenca"


def aplicar_limite_cuenca(tipo_area, geometria, geometria_cuenca):
    """Devuelve únicamente la parte de la unidad ubicada dentro de la cuenca."""

    if area_debe_recortarse_a_cuenca(tipo_area):
        return geometria.intersection(geometria_cuenca, TOLERANCIA_RECORTE_M)
    return geometria

MODOS_ANALISIS = {
    MODO_TERRITORIAL: {
        "titulo": "Preevaluación territorial",
        "pregunta": "¿Qué señales justifican revisar el área?",
        "descripcion": (
            "Identifica indicios satelitales de cambio del bosque y propone un nivel "
            "inicial de atención, sin sumar el valor de los corredores."
        ),
        "resultado": "Atención sugerida, mapa de indicios y evidencia por fuente.",
    },
    MODO_CORREDORES: {
        "titulo": "Corredores y conectividad",
        "pregunta": "¿Qué elementos sostienen o limitan la conectividad?",
        "descripcion": (
            "Revisa corredores publicados, fragmentos de bosque, conexiones, "
            "separaciones y rutas estructurales potenciales, sin afirmar movimiento de fauna."
        ),
        "resultado": "Lectura de conectividad, mapa de fragmentos y descargas geográficas.",
    },
    MODO_INTEGRAL: {
        "titulo": "Preevaluación integral",
        "pregunta": "¿Dónde conviene enfocar una revisión considerando ambas lecturas?",
        "descripcion": (
            "Reúne indicios territoriales, corredores y estructura del bosque en una "
            "orientación inicial, con un mapa preparado automáticamente."
        ),
        "resultado": "Atención integrada sugerida, mapa resumido y siguiente paso.",
    },
}
