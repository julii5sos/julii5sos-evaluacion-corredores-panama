"""Capas y analisis contextual de corredores ecologicos de Panama."""

from __future__ import annotations

import html
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


DIRECTORIO_DATOS = Path(__file__).with_name("data")
RUTA_CORREDORES = DIRECTORIO_DATOS / "corredores_almanaque_azul.geojson"
RUTA_OJOS = DIRECTORIO_DATOS / "puntos_criticos_almanaque_azul.geojson"
RUTA_CATALOGO = DIRECTORIO_DATOS / "catalogo_corredores.json"

CATEGORIAS = ("alta", "mediana", "mediabaja")
ETIQUETAS_CATEGORIA = {
    "alta": "Alta",
    "mediana": "Mediana",
    "mediabaja": "Media-baja",
}
# Colores exactos publicados por el visor de Almanaque Azul.
COLORES_CATEGORIA = {
    "alta": "#345a01",
    "mediana": "#a1d303",
    "mediabaja": "#e0c504",
}
FUENTE_CORTA = "Almanaque Azul · mapa de conectividad 2024.05"
URL_MAPA = "https://www.almanaqueazul.org/conectividad/mapa/"


@lru_cache(maxsize=4)
def _leer_json(ruta: str) -> dict[str, Any]:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def cargar_corredores() -> dict[str, Any]:
    return _leer_json(str(RUTA_CORREDORES))


def cargar_puntos_criticos() -> dict[str, Any]:
    return _leer_json(str(RUTA_OJOS))


def cargar_catalogo() -> dict[str, Any]:
    return _leer_json(str(RUTA_CATALOGO))


def _feature_collection(features: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


def _es_mesoamericano(feature: dict[str, Any]) -> bool:
    propiedades = feature.get("properties") or {}
    return bool(propiedades.get("es_mesoamericano")) or "mesoamericano" in str(
        propiedades.get("nombre", "")
    ).lower()


def agregar_capas_corredores(mapa, mostrar: bool = False):
    """Agrega capas Folium y devuelve los grupos para GroupedLayerControl."""

    import folium

    datos = cargar_corredores()
    capas = []
    for categoria in CATEGORIAS:
        etiqueta = ETIQUETAS_CATEGORIA[categoria]
        color = COLORES_CATEGORIA[categoria]
        grupo = folium.FeatureGroup(
            name=f"Conectividad {etiqueta.lower()} · Almanaque Azul",
            overlay=True,
            control=False,
            show=mostrar,
        )
        features = [
            feature
            for feature in datos["features"]
            if (feature.get("properties") or {}).get("cat") == categoria
        ]
        folium.GeoJson(
            _feature_collection(features),
            name=etiqueta,
            style_function=lambda _, color=color: {
                "color": color,
                "weight": 1.4,
                "fillColor": color,
                "fillOpacity": 0.26,
            },
            highlight_function=lambda _, color=color: {
                "color": "#00544d",
                "weight": 4,
                "fillColor": color,
                "fillOpacity": 0.42,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["nombre", "categoria_etiqueta", "cond_promedio", "area_ha"],
                aliases=["Corredor", "Conectividad", "Conductividad promedio", "Área (ha)"],
                localize=True,
                sticky=False,
            ),
            popup=folium.GeoJsonPopup(
                fields=["nombre", "categoria_etiqueta", "notas"],
                aliases=["Corredor", "Categoría original", "Lectura de Almanaque Azul"],
                localize=True,
                max_width=520,
            ),
            zoom_on_click=True,
        ).add_to(grupo)
        grupo.add_to(mapa)
        capas.append(grupo)

    meso = folium.FeatureGroup(
        name="Corredor Biológico Mesoamericano · tramos de Panamá",
        overlay=True,
        control=False,
        show=True,
    )
    folium.GeoJson(
        _feature_collection(filter(_es_mesoamericano, datos["features"])),
        name="Tramos mesoamericanos",
        style_function=lambda _: {
            "color": "#00544d",
            "weight": 5,
            "dashArray": "9 6",
            "fillColor": "#00544d",
            "fillOpacity": 0.04,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["nombre", "categoria_etiqueta", "cond_promedio"],
            aliases=["Tramo", "Conectividad", "Conductividad promedio"],
            sticky=False,
        ),
    ).add_to(meso)
    meso.add_to(mapa)
    capas.append(meso)

    ojos = folium.FeatureGroup(
        name="Puntos críticos de conectividad · Almanaque Azul",
        overlay=True,
        control=False,
        show=False,
    )
    for feature in cargar_puntos_criticos()["features"]:
        propiedades = feature.get("properties") or {}
        coordenadas = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordenadas) < 2:
            continue
        nota = html.escape(
            str(propiedades.get("notas") or "Punto crítico identificado")
        )
        folium.CircleMarker(
            location=[coordenadas[1], coordenadas[0]],
            radius=7,
            color="#ffffff",
            weight=2,
            fill=True,
            fill_color="#b42318",
            fill_opacity=0.92,
            tooltip="Punto crítico de conectividad",
            popup=folium.Popup(
                f"<strong>Punto crítico</strong><br>{nota}<br><small>{FUENTE_CORTA}</small>",
                max_width=430,
            ),
        ).add_to(ojos)
    ojos.add_to(mapa)
    capas.append(ojos)
    return capas


def analizar_interseccion_corredores(aoi_geojson: dict[str, Any]) -> dict[str, Any]:
    """Calcula intersecciones en un CRS de area equivalente para Panama.

    Este resultado es contexto cartografico independiente. No modifica el indice
    de prioridad satelital de la aplicacion.
    """

    try:
        from pyproj import Transformer
        from shapely.geometry import shape
        from shapely.ops import transform, unary_union
        from shapely.validation import make_valid
    except ImportError as exc:  # pragma: no cover - mensaje operativo
        raise RuntimeError(
            "Faltan shapely o pyproj; instale las dependencias de requirements.txt."
        ) from exc

    geometria_aoi = shape(
        {"type": aoi_geojson["type"], "coordinates": aoi_geojson["coordinates"]}
    )
    if not geometria_aoi.is_valid:
        geometria_aoi = make_valid(geometria_aoi)

    # WGS 84 / Equal Earth Americas; evita medir areas en grados o Web Mercator.
    proyector = Transformer.from_crs("EPSG:4326", "EPSG:8857", always_xy=True)
    aoi_m = transform(proyector.transform, geometria_aoi)
    area_aoi_ha = aoi_m.area / 10_000

    detalles = []
    intersecciones = []
    por_categoria: dict[str, list[Any]] = {categoria: [] for categoria in CATEGORIAS}
    intersecciones_meso = []
    for feature in cargar_corredores()["features"]:
        geometria = shape(feature["geometry"])
        if not geometria.is_valid:
            geometria = make_valid(geometria)
        geometria_m = transform(proyector.transform, geometria)
        if not geometria_m.intersects(aoi_m):
            continue
        interseccion = geometria_m.intersection(aoi_m)
        area_ha = interseccion.area / 10_000
        if area_ha <= 0.0001:
            continue
        propiedades = feature.get("properties") or {}
        categoria = propiedades["cat"]
        detalle = {
            "nombre": propiedades.get("nombre"),
            "categoria": categoria,
            "categoria_etiqueta": ETIQUETAS_CATEGORIA[categoria],
            "interseccion_ha": round(area_ha, 4),
            "porcentaje_aoi": round(area_ha / area_aoi_ha * 100, 4)
            if area_aoi_ha
            else 0.0,
            "cond_promedio": propiedades.get("cond_promedio"),
            "es_mesoamericano": _es_mesoamericano(feature),
        }
        detalles.append(detalle)
        intersecciones.append(interseccion)
        por_categoria[categoria].append(interseccion)
        if detalle["es_mesoamericano"]:
            intersecciones_meso.append(interseccion)

    total_ha = unary_union(intersecciones).area / 10_000 if intersecciones else 0.0
    meso_ha = (
        unary_union(intersecciones_meso).area / 10_000
        if intersecciones_meso
        else 0.0
    )
    areas_categoria = {
        categoria: round(unary_union(geometrias).area / 10_000, 4)
        if geometrias
        else 0.0
        for categoria, geometrias in por_categoria.items()
    }
    detalles.sort(key=lambda item: item["interseccion_ha"], reverse=True)
    return {
        "intersecta": bool(detalles),
        "area_aoi_ha": round(area_aoi_ha, 4),
        "area_en_corredores_ha": round(total_ha, 4),
        "porcentaje_aoi_en_corredores": round(total_ha / area_aoi_ha * 100, 4)
        if area_aoi_ha
        else 0.0,
        "area_corredor_mesoamericano_ha": round(meso_ha, 4),
        "intersecta_mesoamericano": meso_ha > 0,
        "areas_categoria_ha": areas_categoria,
        "corredores": detalles,
        "fuente": FUENTE_CORTA,
        "url": URL_MAPA,
        "participa_indice_prioridad": False,
        "limitacion": (
            "La superposicion indica contexto territorial; no demuestra conectividad "
            "funcional para una especie ni modifica el indice de prioridad satelital."
        ),
    }


def leyenda_corredores():
    return [
        (COLORES_CATEGORIA[categoria], ETIQUETAS_CATEGORIA[categoria])
        for categoria in CATEGORIAS
    ]
