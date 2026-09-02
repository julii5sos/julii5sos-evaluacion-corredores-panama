"""Prepara los datos publicos de Almanaque Azul para uso web.

Los GeoJSON publicados por el visor estan en Web Mercator (EPSG:3857).
Folium y el analisis local de la aplicacion trabajan con GeoJSON RFC 7946 en
longitud/latitud (EPSG:4326), por lo que esta conversion se realiza una sola
vez y deja un artefacto reproducible dentro del repositorio.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path


RADIO_TIERRA_M = 6_378_137.0
ETIQUETAS = {
    "alta": "Alta",
    "mediana": "Mediana",
    "mediabaja": "Media-baja",
}


def web_mercator_a_lon_lat(coordenada: list[float]) -> list[float]:
    """Convierte un punto EPSG:3857 a EPSG:4326 preservando dimensiones extra."""

    x, y, *resto = coordenada
    lon = math.degrees(x / RADIO_TIERRA_M)
    lat = math.degrees(2 * math.atan(math.exp(y / RADIO_TIERRA_M)) - math.pi / 2)
    return [round(lon, 7), round(lat, 7), *resto]


def transformar_coordenadas(valor):
    """Transforma recursivamente cualquier arreglo de coordenadas GeoJSON."""

    if not isinstance(valor, list):
        return valor
    if valor and isinstance(valor[0], (int, float)):
        return web_mercator_a_lon_lat(valor)
    return [transformar_coordenadas(elemento) for elemento in valor]


def preparar_geojson(origen: Path, destino: Path, es_corredor: bool) -> dict:
    datos = json.loads(origen.read_text(encoding="utf-8"))
    for feature in datos.get("features", []):
        geometria = feature.get("geometry") or {}
        geometria["coordinates"] = transformar_coordenadas(
            geometria.get("coordinates", [])
        )
        propiedades = feature.setdefault("properties", {})
        if es_corredor:
            categoria = str(propiedades.get("cat", "")).strip().lower()
            if categoria not in ETIQUETAS:
                raise ValueError(f"Categoria de corredor no reconocida: {categoria!r}")
            propiedades["categoria_etiqueta"] = ETIQUETAS[categoria]
            propiedades["es_mesoamericano"] = "mesoamericano" in str(
                propiedades.get("nombre", "")
            ).lower()
            if propiedades.get("cond_promedio") is not None:
                propiedades["cond_promedio"] = round(
                    float(propiedades["cond_promedio"]), 2
                )

    # RFC 7946 usa WGS84 y desaconseja el miembro crs.
    datos.pop("crs", None)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return datos


def construir_catalogo(corredores: dict, ojos: dict) -> dict:
    categorias = Counter(
        feature["properties"]["cat"] for feature in corredores["features"]
    )
    mesoamericanos = sorted(
        {
            feature["properties"]["nombre"]
            for feature in corredores["features"]
            if feature["properties"]["es_mesoamericano"]
        }
    )
    return {
        "fuente": "Fundacion Almanaque Azul",
        "proyecto": "Mapa de conectividad ecologica de Panama",
        "version_publicada": "2024.05",
        "modelo": "Omniscape; ventana de conectividad de 6 km",
        "url_mapa": "https://www.almanaqueazul.org/conectividad/mapa/",
        "url_proyecto": "https://www.almanaqueazul.org/proyectos/",
        "fecha_consulta": "2026-09-01",
        "crs_salida": "EPSG:4326",
        "corredores_poligonos": len(corredores["features"]),
        "puntos_criticos": len(ojos["features"]),
        "categorias_originales": dict(sorted(categorias.items())),
        "etiquetas": ETIQUETAS,
        "tramos_mesoamericanos": mesoamericanos,
        "nota": (
            "Las categorias originales son alta, mediana y media-baja. "
            "La aplicacion no las sustituye por cuantiles propios."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corredores", type=Path, required=True)
    parser.add_argument("--ojos", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()

    corredores = preparar_geojson(
        args.corredores,
        args.salida / "corredores_almanaque_azul.geojson",
        es_corredor=True,
    )
    ojos = preparar_geojson(
        args.ojos,
        args.salida / "puntos_criticos_almanaque_azul.geojson",
        es_corredor=False,
    )
    catalogo = construir_catalogo(corredores, ojos)
    (args.salida / "catalogo_corredores.json").write_text(
        json.dumps(catalogo, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
