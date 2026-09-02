"""Reglas auditables del índice operativo de prioridad territorial.

Este módulo no depende de Streamlit ni de Earth Engine. Mantiene en un único
lugar los umbrales, los pesos y la clasificación de prioridad usados por las
dos interfaces de la aplicación.
"""

PERIODOS_ANALISIS = {
    "referencia": 2025,
    "jrc_diagnostico": 2025,
    "hansen_diagnostico": 2025,
    "esri_inicial": 2017,
    "esri_final": 2024,
    "ndvi_final_visual": 2025,
}

PESOS_INDICE = {
    "tmf": 2.0,
    "hansen": 2.0,
    "esri": 1.5,
    "gedi": 0.5,
    "ndvi": 0.0,
}

PUNTAJE_MAXIMO = sum(PESOS_INDICE.values())

REGLAS_MAPA_COINCIDENCIA = {
    "nombre": "Sectores que requieren revisión",
    "malla_referencia_m": 30,
    "fuentes": {
        "jrc": "degradación o deforestación JRC TMF 2025",
        "hansen": "pérdida Hansen posterior al 31/12/2020",
        "esri": "transición de árboles a no árboles ESRI 2017-2024",
    },
    "clases": {
        1: {
            "color": "#F9A825",
            "etiqueta": "Señal de 1 fuente",
            "interpretacion": (
                "Evidencia espacial aislada. Revise el producto correspondiente "
                "antes de atribuir una causa."
            ),
        },
        2: {
            "color": "#E65100",
            "etiqueta": "Coincidencia de 2 fuentes",
            "interpretacion": (
                "Dos fuentes señalan el mismo sector en la malla común. Priorice "
                "su contraste con imágenes recientes y documentos."
            ),
        },
        3: {
            "color": "#8E1B16",
            "etiqueta": "Coincidencia de 3 fuentes",
            "interpretacion": (
                "JRC, Hansen y ESRI señalan el mismo sector. Es la clase de mayor "
                "prioridad cartográfica, sin que ello demuestre causalidad."
            ),
        },
    },
    "participa_indice": False,
    "limitacion": (
        "La superposición espacial es un apoyo cartográfico indicativo. Orienta "
        "dónde revisar, pero no demuestra la causa del cambio, no sustituye la "
        "verificación documental o de campo y no determina cumplimiento EUDR."
    ),
}

UMBRALES_INDICE = {
    "hansen_post_2020_ha": 0.18,
    "jrc_deforestacion_ha": 0.5,
    "jrc_deforestacion_pct": 1.0,
    "jrc_degradacion_ha": 2.0,
    "jrc_degradacion_pct": 5.0,
    "esri_salida_arboles_ha": 0.10,
    "esri_salida_arboles_pct": 5.0,
    "gedi_dosel_bajo_m": 8.0,
    "gedi_cobertura_minima_pct": 20.0,
    "gedi_linea_base_minima_pct": 10.0,
}

JUSTIFICACION_UMBRALES = {
    "hansen_post_2020_ha": (
        "0.18 ha equivale aproximadamente a dos píxeles de 30 m. Se evita que "
        "un único píxel aislado active la señal y se conserva sensibilidad a "
        "eventos pequeños posteriores al 31/12/2020."
    ),
    "jrc_deforestacion": (
        "La señal se activa con 0.5 ha o 1% del área. El criterio absoluto "
        "filtra parches mínimos y el relativo conserva sensibilidad en predios "
        "pequeños; cualquiera de los dos puede justificar revisión."
    ),
    "jrc_degradacion": (
        "La señal se activa con 2 ha o 5% del área. Se usa un criterio más "
        "conservador que para deforestación porque la degradación es gradual y "
        "puede presentar mayor ambigüedad espectral."
    ),
    "esri_salida_arboles": (
        "Se exigen simultáneamente 0.10 ha y 5% del área. A 10 m, 0.10 ha "
        "representa diez píxeles; combinar extensión mínima y proporción reduce "
        "transiciones aisladas por error de clasificación. ESRI corrobora, no "
        "domina, las fuentes forestales."
    ),
    "gedi_dosel_y_cobertura": (
        "GEDI solo aporta contexto cuando al menos 20% del área tiene datos "
        "válidos, la altura media es menor de 8 m y la línea base arbórea cubre "
        "al menos 10%. Así se evita interpretar dosel bajo en áreas sin "
        "cobertura arbórea previa o con muestreo insuficiente."
    ),
    "ndvi": (
        "NDVI se mantiene fuera del puntaje porque responde también a "
        "estacionalidad, humedad, cultivos, pastizales, nubes y sombras. Se usa "
        "como evidencia visual para orientar la interpretación."
    ),
}

JUSTIFICACION_PESOS = {
    "tmf": (
        "Peso 2.0: producto forestal anual que distingue directamente "
        "degradación y deforestación en bosque tropical húmedo."
    ),
    "hansen": (
        "Peso 2.0: producto específico de pérdida anual de cobertura arbórea; "
        "aporta una señal independiente posterior al corte de referencia."
    ),
    "esri": (
        "Peso 1.5: producto general de uso y cobertura del suelo. La transición "
        "árbol a no árbol es corroborativa y recibe menos peso que los productos "
        "forestales especializados."
    ),
    "gedi": (
        "Peso 0.5: contexto estructural de altura del dosel con cobertura "
        "espacial limitada; no se interpreta como detección directa de pérdida."
    ),
    "ndvi": (
        "Peso 0.0: apoyo visual de vigor vegetal; no modifica el índice."
    ),
}

CLASES_VIGOR_NDVI = (
    {
        "color": "#B30000",
        "etiqueta": "Sin vegetación activa",
        "rango": "NDVI < 0",
        "interpretacion": (
            "No se observa una señal positiva de vegetación fotosintéticamente activa. "
            "Puede corresponder a agua, sombra, nubes residuales o superficies no vegetadas."
        ),
    },
    {
        "color": "#F4A582",
        "etiqueta": "Suelo o cobertura muy escasa",
        "rango": "0.0 ≤ NDVI < 0.2",
        "interpretacion": (
            "Respuesta espectral baja, común en suelo desnudo, áreas construidas o "
            "cobertura vegetal muy dispersa."
        ),
    },
    {
        "color": "#FFFFBF",
        "etiqueta": "Vegetación escasa",
        "rango": "0.2 ≤ NDVI < 0.4",
        "interpretacion": (
            "Cobertura vegetal poco densa o con vigor limitado. Puede incluir pastizales, "
            "cultivos en etapas tempranas o vegetación estacional."
        ),
    },
    {
        "color": "#78C679",
        "etiqueta": "Vegetación moderada",
        "rango": "0.4 ≤ NDVI < 0.6",
        "interpretacion": (
            "Señal intermedia de actividad vegetal y cobertura. Debe compararse con la "
            "época del año, el uso del suelo y las demás fuentes."
        ),
    },
    {
        "color": "#006837",
        "etiqueta": "Vegetación densa",
        "rango": "NDVI ≥ 0.6",
        "interpretacion": (
            "Señal alta de vegetación verde y densa. No demuestra por sí sola que la "
            "cobertura sea bosque natural ni determina su condición legal."
        ),
    },
)

REGLAS_PRIORIDAD = {
    "alta": "puntaje >= 3.0",
    "media": "puntaje >= 1.5 y < 3.0",
    "preventiva": "puntaje >= 0.5 y < 1.5",
    "baja": "puntaje < 0.5",
}

REGLAS_CONSISTENCIA = {
    "alta": "JRC TMF, Hansen y ESRI presentan señal de deterioro",
    "parcial": "exactamente dos de JRC TMF, Hansen y ESRI presentan señal",
    "mixta": "coexisten señales de deterioro y de recuperación/ganancia",
    "sin_senal": "menos de dos fuentes principales coinciden en deterioro",
}


def clasificar_prioridad(puntaje):
    """Clasifica un puntaje ya calculado sin alterar su valor."""
    if puntaje >= 3.0:
        return "Alta"
    if puntaje >= 1.5:
        return "Media"
    if puntaje >= 0.5:
        return "Preventiva"
    return "Baja"


def evaluar_senales(
    *,
    tmf_deforestacion_ha,
    tmf_deforestacion_pct,
    tmf_degradacion_ha,
    tmf_degradacion_pct,
    hansen_post_2020_ha,
    esri_salida_arboles_ha,
    esri_salida_arboles_pct,
    gedi_altura_media_m,
    gedi_cobertura_valida_pct,
    linea_base_arborea_pct,
):
    """Aplica los umbrales metodológicos sin asignar pesos todavía."""
    senal_tmf = (
        tmf_deforestacion_ha >= UMBRALES_INDICE["jrc_deforestacion_ha"]
        or tmf_deforestacion_pct >= UMBRALES_INDICE["jrc_deforestacion_pct"]
        or tmf_degradacion_ha >= UMBRALES_INDICE["jrc_degradacion_ha"]
        or tmf_degradacion_pct >= UMBRALES_INDICE["jrc_degradacion_pct"]
    )
    senal_hansen = (
        hansen_post_2020_ha >= UMBRALES_INDICE["hansen_post_2020_ha"]
    )
    # ESRI exige extensión y proporción simultáneamente. Esta conjunción evita
    # que el producto general de cobertura domine el índice por cambios aislados.
    senal_esri = (
        esri_salida_arboles_ha >= UMBRALES_INDICE["esri_salida_arboles_ha"]
        and esri_salida_arboles_pct >= UMBRALES_INDICE["esri_salida_arboles_pct"]
    )
    gedi_disponible = (
        gedi_cobertura_valida_pct
        >= UMBRALES_INDICE["gedi_cobertura_minima_pct"]
    )
    senal_gedi = (
        gedi_disponible
        and gedi_altura_media_m < UMBRALES_INDICE["gedi_dosel_bajo_m"]
        and linea_base_arborea_pct
        >= UMBRALES_INDICE["gedi_linea_base_minima_pct"]
    )
    return {
        "tmf": bool(senal_tmf),
        "hansen": bool(senal_hansen),
        "esri": bool(senal_esri),
        "gedi": bool(senal_gedi),
    }, bool(gedi_disponible)


def calcular_indice_prioridad(
    *,
    senal_tmf,
    senal_hansen,
    senal_esri,
    senal_gedi,
):
    """Suma una sola vez el peso de cada fuente cuya señal está activa."""
    senales = {
        "tmf": bool(senal_tmf),
        "hansen": bool(senal_hansen),
        "esri": bool(senal_esri),
        "gedi": bool(senal_gedi),
        "ndvi": False,
    }
    aportes = {
        fuente: PESOS_INDICE[fuente] if activa else 0.0
        for fuente, activa in senales.items()
    }
    puntaje = round(sum(aportes.values()), 1)
    return aportes, puntaje, clasificar_prioridad(puntaje)


def evaluar_consistencia(
    *,
    senal_tmf,
    senal_hansen,
    senal_esri,
    tmf_recuperacion_ha,
    tmf_recuperacion_pct,
    esri_ganancia_arboles_ha,
    esri_ganancia_arboles_pct,
):
    """Describe coincidencias entre fuentes sin modificar el índice.

    La consistencia es una lectura complementaria. Las ganancias se filtran con
    umbrales simétricos a los usados para deforestación JRC y transición ESRI,
    de modo que un píxel o una fracción mínima no produzcan una lectura mixta.
    """
    deterioro = [
        nombre
        for nombre, activa in (
            ("JRC TMF", bool(senal_tmf)),
            ("Hansen GFC", bool(senal_hansen)),
            ("ESRI LULC", bool(senal_esri)),
        )
        if activa
    ]
    recuperacion_tmf = (
        tmf_recuperacion_ha >= UMBRALES_INDICE["jrc_deforestacion_ha"]
        or tmf_recuperacion_pct >= UMBRALES_INDICE["jrc_deforestacion_pct"]
    )
    ganancia_esri = (
        esri_ganancia_arboles_ha
        >= UMBRALES_INDICE["esri_salida_arboles_ha"]
        and esri_ganancia_arboles_pct
        >= UMBRALES_INDICE["esri_salida_arboles_pct"]
    )
    recuperacion = [
        nombre
        for nombre, activa in (
            ("JRC TMF (recuperación)", recuperacion_tmf),
            ("ESRI LULC (ganancia de árboles)", ganancia_esri),
        )
        if activa
    ]

    if deterioro and recuperacion:
        nivel = "Lectura mixta"
        detalle = (
            "El área contiene señales de deterioro y de recuperación o ganancia "
            "arbórea. Revise su distribución espacial; no deben compensarse "
            "numéricamente ni interpretarse como ausencia de cambio."
        )
    elif len(deterioro) == 3:
        nivel = "Alta consistencia"
        detalle = (
            "JRC TMF, Hansen GFC y ESRI LULC presentan señales de deterioro. "
            "Las fuentes se refuerzan, aunque no se exige coincidencia píxel a píxel."
        )
    elif len(deterioro) == 2:
        nivel = "Consistencia parcial"
        detalle = (
            "Dos fuentes principales presentan señales de deterioro. La tercera "
            "puede responder a otra definición, resolución o período."
        )
    else:
        nivel = "Sin señal consistente"
        detalle = (
            "Menos de dos fuentes principales coinciden en deterioro. Mantenga "
            "el monitoreo y revise individualmente cualquier señal aislada."
        )

    return {
        "nivel": nivel,
        "detalle": detalle,
        "fuentes_deterioro": deterioro,
        "fuentes_recuperacion": recuperacion,
    }
