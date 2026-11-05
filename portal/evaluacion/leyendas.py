"""Leyendas del mapa, copiadas de app_experiencia.py (generado por build/armar_motor_ee.py)."""
from corredores import leyenda_corredores
from metodologia_indice import CLASES_VIGOR_NDVI, REGLAS_MAPA_COINCIDENCIA
from eri_indicativo import CLASES_ERI

LEYENDAS = {
    "Corredores Almanaque Azul": leyenda_corredores(),
    "Bosque 2021 de contexto": [
        (
            "#2f6b45",
            "Bosque 2021 dentro y alrededor del área",
            "Cobertura institucional visible en el contexto adaptativo; solo el bosque dentro del polígono se suma a las hectáreas",
        ),
    ],
    "Importancia de parches": [
        (
            "#a63f35",
            "Valor alto para mantener unido el bosque",
            "Fragmento ubicado en el grupo superior del cálculo; conviene conservarlo y revisarlo con atención",
        ),
        (
            "#d58a24",
            "Valor intermedio",
            "Fragmento con una contribución intermedia dentro del área analizada",
        ),
        (
            "#4f875f",
            "Valor menor",
            "Fragmento con menor contribución relativa dentro de esta área; no significa que carezca de valor ecológico",
        ),
    ],
    "Estructura esencial": [
        (
            "#00544d",
            "Enlaces estructurales esenciales",
            "Cada grupo se muestra con el mínimo de líneas necesario; el cálculo sí conserva todas las relaciones",
        ),
    ],
    "Ruta potencial al corredor": [
        (
            "#d97904",
            "Conexión estructural potencial",
            "Cadena de fragmentos cuyos saltos no superan la distancia elegida hasta un corredor publicado",
        ),
    ],
    "Separaciones potenciales": [
        (
            "#f6c7b8",
            "Fragmento separado",
            "No tiene otro fragmento dentro de la distancia elegida, incluso al considerar el entorno exterior",
        ),
        (
            "#7c2d12",
            "Distancia al vecino más próximo",
            "Línea discontinua desde un fragmento separado hacia su vecino más próximo; no confirma un corredor",
        ),
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
        ("#43AA8B", "Regeneración forestal (Forest regrowth)"),
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
    "Regeneración forestal JRC": [
        (
            "#43AA8B",
            "Regeneración forestal",
            "Área antes deforestada que JRC TMF clasifica actualmente como bosque en regeneración",
        )
    ],
    "ERI indicativo": [
        (
            clase["color"],
            f"{clase['etiqueta']} · {clase['minimo']:.2f}–{min(clase['maximo'], 1):.2f}",
            clase["lectura"],
        )
        for clase in CLASES_ERI
    ],
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
