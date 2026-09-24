"""Definiciones ligeras de las rutas principales de la aplicación."""

MODO_TERRITORIAL = "territorial"
MODO_CORREDORES = "corredores"
MODO_INTEGRAL = "integral"

TIPO_AREA_SUBCUENCA = "Subcuenca"
TIPO_AREA_DIBUJADA = "Dibujar polígono en el mapa"


def area_debe_recortarse_a_cuenca(tipo_area):
    """Solo limita los polígonos creados por el usuario a la cuenca principal."""

    return tipo_area == TIPO_AREA_DIBUJADA


def aplicar_limite_cuenca(tipo_area, geometria, geometria_cuenca):
    """Conserva áreas institucionales completas y recorta únicamente dibujos."""

    if area_debe_recortarse_a_cuenca(tipo_area):
        return geometria.intersection(geometria_cuenca, 1)
    return geometria

MODOS_ANALISIS = {
    MODO_TERRITORIAL: {
        "titulo": "Evaluación territorial",
        "pregunta": "¿Existen cambios que requieren revisión?",
        "descripcion": (
            "Examina señales satelitales de cambio del bosque y genera una prioridad "
            "territorial sin sumar el valor de los corredores."
        ),
        "resultado": "Prioridad territorial, mapa de cambios y evidencia por fuente.",
    },
    MODO_CORREDORES: {
        "titulo": "Corredores y conectividad",
        "pregunta": "¿Cómo está conectado o fragmentado el bosque?",
        "descripcion": (
            "Revisa corredores publicados, fragmentos de bosque, conexiones, "
            "separaciones y rutas estructurales potenciales."
        ),
        "resultado": "Lectura de conectividad, mapa de fragmentos y descargas geográficas.",
    },
    MODO_INTEGRAL: {
        "titulo": "Evaluación integral",
        "pregunta": "¿Dónde conviene priorizar una visita considerando todo?",
        "descripcion": (
            "Reúne cambios territoriales, corredores y estructura del bosque en una "
            "conclusión breve, con un mapa preparado automáticamente."
        ),
        "resultado": "Prioridad integrada, mapa resumido y acción recomendada.",
    },
}
