"""Definiciones ligeras de las rutas principales de la aplicación."""

MODO_TERRITORIAL = "territorial"
MODO_CORREDORES = "corredores"
MODO_INTEGRAL = "integral"

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
            "Combina cambios territoriales, valor estratégico de corredores y "
            "estructura del bosque en una lectura conjunta."
        ),
        "resultado": "Prioridad integrada, mapa completo e informe trazable.",
    },
}
