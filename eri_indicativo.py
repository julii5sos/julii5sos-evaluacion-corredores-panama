"""Reglas transparentes para presentar el ERI como lectura complementaria.

El módulo no depende de Streamlit ni de Earth Engine. La aplicación construye
las cuatro imágenes componentes y este archivo conserva pesos, clases y textos
en un único lugar verificable. El ERI no modifica el índice de indicios ni la
prioridad de visita de la preevaluación vigente.
"""

from __future__ import annotations


PESOS_ERI = {
    "integridad_estructural": 0.35,
    "conectividad": 0.25,
    "estabilidad_topografica": 0.20,
    "proximidad_riparia": 0.20,
}

ETIQUETAS_COMPONENTES_ERI = {
    "integridad_estructural": "Integridad estructural",
    "conectividad": "Conectividad del bosque",
    "estabilidad_topografica": "Estabilidad topográfica",
    "proximidad_riparia": "Proximidad riparia",
}

COLORES_COMPONENTES_ERI = {
    "integridad_estructural": "#0A4393",
    "conectividad": "#2A9D8F",
    "estabilidad_topografica": "#FABC20",
    "proximidad_riparia": "#3A7CA5",
}

CLASES_ERI = (
    {
        "clave": "muy_baja",
        "etiqueta": "Muy baja",
        "minimo": 0.00,
        "maximo": 0.25,
        "color": "#B42318",
        "lectura": "Condición ecológica muy limitada; requiere revisión detallada.",
    },
    {
        "clave": "baja",
        "etiqueta": "Baja",
        "minimo": 0.25,
        "maximo": 0.40,
        "color": "#F79009",
        "lectura": "Persisten limitaciones importantes en uno o varios componentes.",
    },
    {
        "clave": "media",
        "etiqueta": "Media",
        "minimo": 0.40,
        "maximo": 0.60,
        "color": "#F2C94C",
        "lectura": "Condición intermedia; conviene revisar los componentes más débiles.",
    },
    {
        "clave": "alta",
        "etiqueta": "Alta",
        "minimo": 0.60,
        "maximo": 0.75,
        "color": "#76B72A",
        "lectura": "La mayoría de los componentes conserva una condición favorable.",
    },
    {
        "clave": "muy_alta",
        "etiqueta": "Muy alta",
        "minimo": 0.75,
        "maximo": 1.01,
        "color": "#00544D",
        "lectura": "Condición ecológica comparativamente favorable dentro del modelo.",
    },
)


def limitar_01(valor) -> float:
    """Convierte un valor numérico en una proporción entre cero y uno."""

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = 0.0
    return max(0.0, min(1.0, numero))


def calcular_valor_eri(componentes: dict) -> float:
    """Combina los cuatro componentes con los pesos documentados."""

    return sum(
        limitar_01(componentes.get(clave)) * peso
        for clave, peso in PESOS_ERI.items()
    )


def clasificar_eri(valor) -> dict:
    """Devuelve la clase visual e interpretación de un ERI entre cero y uno."""

    valor = limitar_01(valor)
    for clase in CLASES_ERI:
        if clase["minimo"] <= valor < clase["maximo"]:
            return dict(clase)
    return dict(CLASES_ERI[-1])


def construir_resultado_eri(resumen: dict) -> dict:
    """Normaliza la respuesta de Earth Engine para la interfaz y las descargas."""

    componentes = {
        clave: limitar_01(resumen.get(clave)) for clave in PESOS_ERI
    }
    valor = calcular_valor_eri(componentes)
    clase = clasificar_eri(valor)
    distribucion = []
    for item in CLASES_ERI:
        distribucion.append(
            {
                "clave": item["clave"],
                "clase": item["etiqueta"],
                "color": item["color"],
                "area_ha": max(
                    0.0,
                    float(resumen.get(f"eri_{item['clave']}_ha") or 0.0),
                ),
            }
        )
    componente_limitante = min(componentes, key=componentes.get)
    return {
        "nombre": "Índice de Resiliencia Ecológica indicativo",
        "valor": round(valor, 4),
        "clase": clase["etiqueta"],
        "color": clase["color"],
        "lectura": clase["lectura"],
        "componentes": componentes,
        "componente_limitante": componente_limitante,
        "componente_limitante_etiqueta": ETIQUETAS_COMPONENTES_ERI[
            componente_limitante
        ],
        "distribucion_clases": distribucion,
        "pesos": dict(PESOS_ERI),
        "participa_en_prioridad": False,
        "caracter": "Complementario e indicativo; requiere validación de campo.",
    }
