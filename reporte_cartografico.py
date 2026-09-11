"""Mapas vectoriales limpios para la ficha PDF.

Estos mapas no usan una imagen satelital de fondo. Su propósito es explicar la
fragmentación y la conectividad estructural sin el ruido visual del visor web.
Las geometrías llegan en WGS84 desde ``bosque_conectividad`` y se representan
con una proyección local únicamente para ajustar su extensión al papel.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

from reportlab.graphics.shapes import Circle, Drawing, Path, Rect
from reportlab.lib import colors


FONDO_MAPA = colors.HexColor("#f7faf8")
AREA_RELLENO = colors.HexColor("#eef5f1")
AREA_BORDE = colors.HexColor("#00544d")
PARCHE_COLORES = {
    "Alta": colors.HexColor("#2f6b4f"),
    "Media": colors.HexColor("#78a66a"),
    "Baja": colors.HexColor("#c7dbc4"),
}
PARCHE_BORDE = colors.HexColor("#234c43")
ENLACE = colors.HexColor("#176b61")
SEPARACION = colors.HexColor("#9a4a25")
RUTA = colors.HexColor("#e97719")
CORREDOR = colors.HexColor("#dce8a5")
CORREDOR_BORDE = colors.HexColor("#73950f")


def _features(contenido: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not contenido:
        return []
    if contenido.get("type") == "FeatureCollection":
        return [f for f in contenido.get("features", []) if f.get("geometry")]
    if contenido.get("type") == "Feature":
        return [contenido] if contenido.get("geometry") else []
    if contenido.get("type"):
        return [{"type": "Feature", "properties": {}, "geometry": contenido}]
    return []


def _iter_coords(geometria: dict[str, Any]) -> Iterable[tuple[float, float]]:
    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates") or []
    if tipo == "Point":
        if len(coordenadas) >= 2:
            yield float(coordenadas[0]), float(coordenadas[1])
    elif tipo in {"LineString", "MultiPoint"}:
        for punto in coordenadas:
            if len(punto) >= 2:
                yield float(punto[0]), float(punto[1])
    elif tipo in {"Polygon", "MultiLineString"}:
        for linea in coordenadas:
            for punto in linea:
                if len(punto) >= 2:
                    yield float(punto[0]), float(punto[1])
    elif tipo == "MultiPolygon":
        for poligono in coordenadas:
            for linea in poligono:
                for punto in linea:
                    if len(punto) >= 2:
                        yield float(punto[0]), float(punto[1])
    elif tipo == "GeometryCollection":
        for parte in geometria.get("geometries", []):
            yield from _iter_coords(parte)


def _geometrias_poligonales(geometria: dict[str, Any]) -> Iterable[list[list[list[float]]]]:
    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates") or []
    if tipo == "Polygon":
        yield coordenadas
    elif tipo == "MultiPolygon":
        yield from coordenadas
    elif tipo == "GeometryCollection":
        for parte in geometria.get("geometries", []):
            yield from _geometrias_poligonales(parte)


def _geometrias_lineales(geometria: dict[str, Any]) -> Iterable[list[list[float]]]:
    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates") or []
    if tipo == "LineString":
        yield coordenadas
    elif tipo == "MultiLineString":
        yield from coordenadas
    elif tipo == "GeometryCollection":
        for parte in geometria.get("geometries", []):
            yield from _geometrias_lineales(parte)


def _transformador(
    colecciones: Iterable[dict[str, Any] | None],
    ancho: float,
    alto: float,
    margen: float = 18,
):
    puntos = [
        punto
        for coleccion in colecciones
        for feature in _features(coleccion)
        for punto in _iter_coords(feature["geometry"])
    ]
    if not puntos:
        return lambda x, y: (ancho / 2, alto / 2)
    xs, ys = zip(*puntos)
    minimo_x, maximo_x = min(xs), max(xs)
    minimo_y, maximo_y = min(ys), max(ys)
    rango_x = max(maximo_x - minimo_x, 1e-9)
    rango_y = max(maximo_y - minimo_y, 1e-9)
    escala = min((ancho - 2 * margen) / rango_x, (alto - 2 * margen) / rango_y)
    usado_x = rango_x * escala
    usado_y = rango_y * escala
    origen_x = (ancho - usado_x) / 2
    origen_y = (alto - usado_y) / 2

    def convertir(x: float, y: float) -> tuple[float, float]:
        return (
            origen_x + (float(x) - minimo_x) * escala,
            origen_y + (float(y) - minimo_y) * escala,
        )

    return convertir


def _ruta(linea: list[list[float]], convertir) -> Path | None:
    if len(linea) < 2:
        return None
    if len(linea) > 1500:
        paso = max(1, math.ceil(len(linea) / 1500))
        reducida = linea[::paso]
        if reducida[-1] != linea[-1]:
            reducida.append(linea[-1])
        linea = reducida
    camino = Path()
    x0, y0 = convertir(linea[0][0], linea[0][1])
    camino.moveTo(x0, y0)
    for x, y, *_ in linea[1:]:
        xp, yp = convertir(x, y)
        camino.lineTo(xp, yp)
    return camino


def _dibujar_poligonos(
    dibujo: Drawing,
    coleccion: dict[str, Any] | None,
    convertir,
    *,
    relleno,
    borde,
    grosor: float,
    color_por_propiedad: tuple[str, dict[str, Any]] | None = None,
) -> None:
    for feature in _features(coleccion):
        color_relleno = relleno
        if color_por_propiedad:
            campo, paleta = color_por_propiedad
            color_relleno = paleta.get(
                feature.get("properties", {}).get(campo), relleno
            )
        for poligono in _geometrias_poligonales(feature["geometry"]):
            if not poligono:
                continue
            exterior = _ruta(poligono[0], convertir)
            if exterior is None:
                continue
            exterior.closePath()
            exterior.fillColor = color_relleno
            exterior.strokeColor = borde
            exterior.strokeWidth = grosor
            dibujo.add(exterior)
            # Los huecos se vuelven a pintar con el fondo del área para evitar
            # que lagos o claros internos aparezcan como bosque.
            for interior in poligono[1:]:
                hueco = _ruta(interior, convertir)
                if hueco is None:
                    continue
                hueco.closePath()
                hueco.fillColor = AREA_RELLENO
                hueco.strokeColor = borde
                hueco.strokeWidth = max(0.25, grosor * 0.5)
                dibujo.add(hueco)


def _dibujar_lineas(
    dibujo: Drawing,
    coleccion: dict[str, Any] | None,
    convertir,
    *,
    color,
    grosor: float,
    guiones: list[float] | None = None,
    halo: bool = False,
) -> None:
    for feature in _features(coleccion):
        for linea in _geometrias_lineales(feature["geometry"]):
            if halo:
                camino_halo = _ruta(linea, convertir)
                if camino_halo:
                    camino_halo.fillColor = None
                    camino_halo.strokeColor = colors.white
                    camino_halo.strokeWidth = grosor + 2.2
                    if guiones:
                        camino_halo.strokeDashArray = guiones
                    dibujo.add(camino_halo)
            camino = _ruta(linea, convertir)
            if camino is None:
                continue
            camino.fillColor = None
            camino.strokeColor = color
            camino.strokeWidth = grosor
            if guiones:
                camino.strokeDashArray = guiones
            dibujo.add(camino)
            if linea:
                for punto in (linea[0], linea[-1]):
                    x, y = convertir(punto[0], punto[1])
                    dibujo.add(Circle(x, y, 1.7, fillColor=color, strokeColor=colors.white, strokeWidth=0.6))


def crear_mapa_fragmentacion(fragmentacion: dict[str, Any], ancho=470, alto=285) -> Drawing:
    """Mapa A: distribución de fragmentos e importancia relativa."""

    area = fragmentacion.get("area_objetivo_geojson")
    parches = fragmentacion.get("parches_geojson")
    convertir = _transformador([area, parches], ancho, alto)
    dibujo = Drawing(ancho, alto)
    dibujo.add(Rect(0, 0, ancho, alto, fillColor=FONDO_MAPA, strokeColor=colors.HexColor("#c5d7d0"), strokeWidth=0.8))
    _dibujar_poligonos(
        dibujo,
        area,
        convertir,
        relleno=AREA_RELLENO,
        borde=AREA_BORDE,
        grosor=1.4,
    )
    _dibujar_poligonos(
        dibujo,
        parches,
        convertir,
        relleno=PARCHE_COLORES["Baja"],
        borde=PARCHE_BORDE,
        grosor=0.55,
        color_por_propiedad=("prioridad_conectividad", PARCHE_COLORES),
    )
    # Repite el límite encima de los fragmentos para conservar la referencia.
    _dibujar_poligonos(
        dibujo,
        area,
        convertir,
        relleno=None,
        borde=AREA_BORDE,
        grosor=1.45,
    )
    return dibujo


def crear_mapa_conectividad(fragmentacion: dict[str, Any], ancho=470, alto=285) -> Drawing:
    """Mapa B: estructura esencial, separaciones y ruta al corredor."""

    area = fragmentacion.get("area_objetivo_geojson")
    parches = fragmentacion.get("parches_geojson")
    enlaces = fragmentacion.get("conexiones_geojson")
    separaciones = fragmentacion.get("conexiones_potenciales_geojson")
    ruta = fragmentacion.get("ruta_corredor_geojson")
    corredor = fragmentacion.get("corredor_referencia_geojson")
    convertir = _transformador(
        [area, parches, enlaces, separaciones, ruta, corredor], ancho, alto
    )
    dibujo = Drawing(ancho, alto)
    dibujo.add(Rect(0, 0, ancho, alto, fillColor=FONDO_MAPA, strokeColor=colors.HexColor("#c5d7d0"), strokeWidth=0.8))
    _dibujar_poligonos(
        dibujo,
        area,
        convertir,
        relleno=AREA_RELLENO,
        borde=AREA_BORDE,
        grosor=1.3,
    )
    _dibujar_poligonos(
        dibujo,
        corredor,
        convertir,
        relleno=CORREDOR,
        borde=CORREDOR_BORDE,
        grosor=1.2,
    )
    _dibujar_poligonos(
        dibujo,
        parches,
        convertir,
        relleno=colors.HexColor("#b8d1bd"),
        borde=PARCHE_BORDE,
        grosor=0.5,
    )
    _dibujar_lineas(dibujo, enlaces, convertir, color=ENLACE, grosor=1.65, halo=True)
    _dibujar_lineas(
        dibujo,
        separaciones,
        convertir,
        color=SEPARACION,
        grosor=1.8,
        guiones=[5, 3],
        halo=True,
    )
    _dibujar_lineas(
        dibujo,
        ruta,
        convertir,
        color=RUTA,
        grosor=2.35,
        guiones=[7, 3],
        halo=True,
    )
    _dibujar_poligonos(
        dibujo,
        area,
        convertir,
        relleno=None,
        borde=AREA_BORDE,
        grosor=1.4,
    )
    return dibujo
