"""Fragmentacion y conectividad estructural desde cobertura bosque/no bosque.

La implementacion traslada a Python las decisiones principales de los scripts R
aportados por la usuaria: parches como nodos, aristas por distancia y un indice
compuesto de importancia como conector.

La cobertura puede llegar desde un ZIP durante pruebas locales o, en produccion,
como GeoJSON recortado desde un asset institucional de Earth Engine.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from io import BytesIO
from statistics import mean, median, pstdev
from typing import Any, Iterable
from zipfile import BadZipFile, ZipFile


def _dependencias():
    try:
        import networkx as nx
        import shapefile
        from pyproj import CRS, Transformer
        from shapely.geometry import (
            GeometryCollection,
            LineString,
            MultiPolygon,
            Polygon,
            mapping,
            shape,
        )
        from shapely.ops import transform, unary_union
        from shapely.strtree import STRtree
        from shapely.validation import make_valid
    except ImportError as exc:  # pragma: no cover - mensaje operativo
        raise RuntimeError(
            "Faltan pyshp, shapely, pyproj o networkx; instale requirements.txt."
        ) from exc
    return {
        "nx": nx,
        "shapefile": shapefile,
        "CRS": CRS,
        "Transformer": Transformer,
        "GeometryCollection": GeometryCollection,
        "LineString": LineString,
        "MultiPolygon": MultiPolygon,
        "Polygon": Polygon,
        "mapping": mapping,
        "shape": shape,
        "transform": transform,
        "unary_union": unary_union,
        "STRtree": STRtree,
        "make_valid": make_valid,
    }


def _archivos_shapefile(datos_zip: bytes):
    try:
        archivo = ZipFile(BytesIO(datos_zip))
    except BadZipFile as exc:
        raise ValueError("El archivo no es un ZIP valido.") from exc
    nombres = [nombre for nombre in archivo.namelist() if not nombre.endswith("/")]
    por_raiz: dict[str, dict[str, str]] = defaultdict(dict)
    for nombre in nombres:
        ruta_normalizada = nombre.replace("\\", "/")
        nombre_base = ruta_normalizada.rsplit("/", 1)[-1]
        if "." not in nombre_base:
            continue
        raiz, extension = nombre_base.rsplit(".", 1)
        extension = f".{extension.lower()}"
        if extension in {".shp", ".shx", ".dbf", ".prj", ".cpg"}:
            por_raiz[raiz.lower()][extension] = nombre

    candidatos = [
        (raiz, partes)
        for raiz, partes in por_raiz.items()
        if {".shp", ".shx", ".dbf"}.issubset(partes)
    ]
    if len(candidatos) != 1:
        raise ValueError(
            "El ZIP debe contener exactamente un conjunto .shp, .shx y .dbf con el mismo nombre."
        )
    _, partes = candidatos[0]
    return archivo, partes


def _lector(datos_zip: bytes):
    deps = _dependencias()
    archivo, partes = _archivos_shapefile(datos_zip)
    lector = deps["shapefile"].Reader(
        shp=BytesIO(archivo.read(partes[".shp"])),
        shx=BytesIO(archivo.read(partes[".shx"])),
        dbf=BytesIO(archivo.read(partes[".dbf"])),
        encoding="utf-8",
        encodingErrors="replace",
    )
    prj = archivo.read(partes[".prj"]).decode("utf-8", errors="replace") if ".prj" in partes else None
    return deps, lector, prj


def inspeccionar_shapefile(datos_zip: bytes, limite_valores: int = 200) -> dict[str, Any]:
    _, lector, prj = _lector(datos_zip)
    campos = [campo[0] for campo in lector.fields[1:]]
    valores: dict[str, set[Any]] = {campo: set() for campo in campos}
    for registro in lector.iterRecords():
        diccionario = registro.as_dict()
        for campo in campos:
            if len(valores[campo]) < limite_valores:
                valor = diccionario.get(campo)
                if valor is not None:
                    valores[campo].add(valor)
    return {
        "numero_features": len(lector),
        "campos": campos,
        "valores": {
            campo: sorted(conjunto, key=lambda valor: str(valor))
            for campo, conjunto in valores.items()
        },
        "tiene_prj": bool(prj),
    }


def _partes_poligonales(geometria, deps):
    if isinstance(geometria, deps["Polygon"]):
        return [geometria]
    if isinstance(geometria, deps["MultiPolygon"]):
        return list(geometria.geoms)
    if isinstance(geometria, deps["GeometryCollection"]):
        return [
            parte
            for geometria_interna in geometria.geoms
            for parte in _partes_poligonales(geometria_interna, deps)
        ]
    return []


def _percentil(valores: list[float], proporcion: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    posicion = (len(ordenados) - 1) * proporcion
    inferior = math.floor(posicion)
    superior = math.ceil(posicion)
    if inferior == superior:
        return ordenados[inferior]
    peso = posicion - inferior
    return ordenados[inferior] * (1 - peso) + ordenados[superior] * peso


def _escala01(valores: dict[int, float]) -> dict[int, float]:
    if not valores:
        return {}
    minimo, maximo = min(valores.values()), max(valores.values())
    if minimo == maximo:
        return {clave: 0.0 for clave in valores}
    return {
        clave: (valor - minimo) / (maximo - minimo)
        for clave, valor in valores.items()
    }


def _vecinos_mas_cercanos(parches: list[Any], arbol) -> dict[int, tuple[int | None, float | None]]:
    """Localiza el parche vecino más cercano sin construir una matriz O(n²)."""

    vecinos: dict[int, tuple[int | None, float | None]] = {}
    if len(parches) < 2:
        return {indice: (None, None) for indice in range(len(parches))}

    for indice, parche in enumerate(parches):
        indices, distancias = arbol.query_nearest(
            parche,
            exclusive=True,
            all_matches=False,
            return_distance=True,
        )
        if len(indices) == 0:
            vecinos[indice] = (None, None)
            continue
        vecinos[indice] = (int(indices[0]), float(distancias[0]))
    return vecinos


def _linea_entre_parches(parche_origen, parche_destino, deps):
    """Crea una línea esquemática entre puntos interiores de dos parches."""

    origen = parche_origen.representative_point()
    destino = parche_destino.representative_point()
    return deps["LineString"]([(origen.x, origen.y), (destino.x, destino.y)])


def _resultado_sin_parches(
    *,
    area_paisaje_ha: float,
    umbral_m: float,
    area_min_ha: float,
    campo_clase: str | None,
    valores_bosque: Iterable[Any],
    origen_datos: str,
) -> dict[str, Any]:
    """Devuelve un resultado valido cuando el recorte no contiene bosque."""

    return {
        "metricas_clase": {
            "numero_parches": 0,
            "area_total_bosque_ha": 0.0,
            "porcentaje_paisaje_bosque": 0.0,
            "densidad_parches_por_100ha": 0.0,
            "densidad_borde_m_ha": 0.0,
            "indice_parche_mayor_pct": 0.0,
            "area_media_parche_ha": 0.0,
            "area_mediana_parche_ha": 0.0,
            "desviacion_area_parche_ha": 0.0,
            "indice_forma_medio": 0.0,
        },
        "metricas_red": {
            "umbral_m": float(umbral_m),
            "numero_nodos": 0,
            "numero_aristas": 0,
            "numero_parches_conectados": 0,
            "numero_parches_aislados": 0,
            "porcentaje_parches_aislados": 0.0,
            "numero_componentes": 0,
            "tamano_componente_mayor": 0,
            "porcentaje_nodos_componente_mayor": 0.0,
            "densidad_red": 0.0,
            "distancia_media_conexiones_m": 0.0,
            "distancia_maxima_conexiones_m": 0.0,
            "numero_brechas_potenciales": 0,
            "distancia_media_brechas_potenciales_m": 0.0,
            "red_totalmente_conectada": False,
            "intermediacion_aproximada": False,
        },
        "top_conectores": [],
        "parches_geojson": {"type": "FeatureCollection", "features": []},
        "conexiones_geojson": {"type": "FeatureCollection", "features": []},
        "conexiones_potenciales_geojson": {
            "type": "FeatureCollection",
            "features": [],
        },
        "hay_parches_aislados": False,
        "campo_clase": campo_clase,
        "valores_bosque": sorted(str(valor) for valor in valores_bosque),
        "area_min_ha": float(area_min_ha),
        "area_paisaje_ha": round(float(area_paisaje_ha), 4),
        "origen_datos": origen_datos,
        "metodo": (
            "Parches de bosque como nodos; aristas por distancia; indice conector "
            "40% grado, 30% intermediacion, 20% area y 10% fuerza de conexion; "
            "brechas potenciales desde parches aislados hacia su vecino mas cercano."
        ),
        "participa_indice_prioridad": False,
    }


def _calcular_metricas_parches(
    *,
    parches: list[Any],
    deps: dict[str, Any],
    area_paisaje_ha: float,
    area_a_wgs,
    umbral_m: float,
    area_min_ha: float,
    campo_clase: str | None,
    valores_bosque: Iterable[Any],
    origen_datos: str,
) -> dict[str, Any]:
    if not parches:
        return _resultado_sin_parches(
            area_paisaje_ha=area_paisaje_ha,
            umbral_m=umbral_m,
            area_min_ha=area_min_ha,
            campo_clase=campo_clase,
            valores_bosque=valores_bosque,
            origen_datos=origen_datos,
        )

    nx = deps["nx"]
    grafo = nx.Graph()
    for indice, parche in enumerate(parches):
        grafo.add_node(indice, area_ha=parche.area / 10_000)

    arbol = deps["STRtree"](parches)
    for i, parche in enumerate(parches):
        candidatos = arbol.query(parche.buffer(umbral_m), predicate="intersects")
        for candidato in candidatos:
            j = int(candidato)
            if j <= i:
                continue
            distancia = parche.distance(parches[j])
            if distancia <= umbral_m:
                costo = max(1.0, float(distancia))
                peso = math.exp(-float(distancia) / umbral_m) if umbral_m else 1.0
                grafo.add_edge(i, j, distancia_m=float(distancia), costo=costo, peso=peso)

    grados = dict(grafo.degree())
    fuerza = dict(grafo.degree(weight="peso"))
    vecinos_mas_cercanos = _vecinos_mas_cercanos(parches, arbol)
    if grafo.number_of_nodes() > 400:
        intermediacion = nx.betweenness_centrality(
            grafo,
            k=min(200, grafo.number_of_nodes()),
            weight="costo",
            normalized=True,
            seed=123,
        )
        intermediacion_aproximada = True
    else:
        intermediacion = nx.betweenness_centrality(
            grafo, weight="costo", normalized=True
        )
        intermediacion_aproximada = False
    cercania = nx.closeness_centrality(grafo, distance="costo")
    componentes = list(nx.connected_components(grafo))
    componente_por_nodo = {
        nodo: indice + 1
        for indice, componente in enumerate(componentes)
        for nodo in componente
    }

    areas = {indice: parche.area / 10_000 for indice, parche in enumerate(parches)}
    grado_01 = _escala01({i: float(v) for i, v in grados.items()})
    fuerza_01 = _escala01({i: float(v) for i, v in fuerza.items()})
    intermediacion_01 = _escala01(intermediacion)
    area_01 = _escala01(areas)
    indices = {
        i: 0.40 * grado_01[i]
        + 0.30 * intermediacion_01[i]
        + 0.20 * area_01[i]
        + 0.10 * fuerza_01[i]
        for i in range(len(parches))
    }
    q75 = _percentil(list(indices.values()), 0.75)
    q50 = _percentil(list(indices.values()), 0.50)

    features = []
    nodos = []
    for i, parche in enumerate(parches):
        prioridad = "Alta" if indices[i] >= q75 else "Media" if indices[i] >= q50 else "Baja"
        indice_vecino, distancia_vecino = vecinos_mas_cercanos[i]
        propiedades = {
            "patch_id": i + 1,
            "area_ha": round(areas[i], 4),
            "grado": int(grados[i]),
            "grado_ponderado": round(float(fuerza[i]), 6),
            "intermediacion": round(float(intermediacion[i]), 6),
            "cercania": round(float(cercania[i]), 6),
            "componente": componente_por_nodo[i],
            "indice_conector": round(indices[i], 6),
            "prioridad_conectividad": prioridad,
            "esta_aislado": int(grados[i]) == 0,
            "distancia_vecino_mas_cercano_m": (
                round(distancia_vecino, 1) if distancia_vecino is not None else None
            ),
            "patch_id_vecino_mas_cercano": (
                indice_vecino + 1 if indice_vecino is not None else None
            ),
        }
        nodos.append(propiedades)
        geometria_wgs = deps["transform"](area_a_wgs.transform, parche)
        features.append(
            {
                "type": "Feature",
                "properties": propiedades,
                "geometry": deps["mapping"](geometria_wgs),
            }
        )

    conexiones = []
    distancias_conexiones = []
    for origen, destino, atributos in grafo.edges(data=True):
        distancia = float(atributos["distancia_m"])
        distancias_conexiones.append(distancia)
        linea_wgs = deps["transform"](
            area_a_wgs.transform,
            _linea_entre_parches(parches[origen], parches[destino], deps),
        )
        conexiones.append(
            {
                "type": "Feature",
                "properties": {
                    "tipo": "Conexion dentro del umbral",
                    "patch_id_origen": origen + 1,
                    "patch_id_destino": destino + 1,
                    "distancia_m": round(distancia, 1),
                    "umbral_m": float(umbral_m),
                },
                "geometry": deps["mapping"](linea_wgs),
            }
        )

    aislados = [indice for indice, grado in grados.items() if int(grado) == 0]
    conexiones_potenciales = []
    pares_potenciales = set()
    for origen in aislados:
        destino, distancia = vecinos_mas_cercanos[origen]
        if destino is None or distancia is None:
            continue
        par = tuple(sorted((origen, destino)))
        if par in pares_potenciales:
            continue
        pares_potenciales.add(par)
        linea_wgs = deps["transform"](
            area_a_wgs.transform,
            _linea_entre_parches(parches[origen], parches[destino], deps),
        )
        conexiones_potenciales.append(
            {
                "type": "Feature",
                "properties": {
                    "tipo": "Brecha potencial para revision",
                    "patch_id_origen": origen + 1,
                    "patch_id_destino": destino + 1,
                    "distancia_m": round(float(distancia), 1),
                    "umbral_m": float(umbral_m),
                },
                "geometry": deps["mapping"](linea_wgs),
            }
        )

    total_bosque_ha = sum(areas.values())
    perimetro_total_m = sum(parche.length for parche in parches)
    valores_area = list(areas.values())
    mayor_componente = max((len(componente) for componente in componentes), default=0)
    distancias_brechas = [
        float(feature["properties"]["distancia_m"])
        for feature in conexiones_potenciales
    ]
    metricas_clase = {
        "numero_parches": len(parches),
        "area_total_bosque_ha": round(total_bosque_ha, 4),
        "porcentaje_paisaje_bosque": round(total_bosque_ha / area_paisaje_ha * 100, 4)
        if area_paisaje_ha
        else 0.0,
        "densidad_parches_por_100ha": round(len(parches) / area_paisaje_ha * 100, 4)
        if area_paisaje_ha
        else 0.0,
        "densidad_borde_m_ha": round(perimetro_total_m / area_paisaje_ha, 4)
        if area_paisaje_ha
        else 0.0,
        "indice_parche_mayor_pct": round(max(valores_area) / area_paisaje_ha * 100, 4)
        if area_paisaje_ha
        else 0.0,
        "area_media_parche_ha": round(mean(valores_area), 4),
        "area_mediana_parche_ha": round(median(valores_area), 4),
        "desviacion_area_parche_ha": round(pstdev(valores_area), 4),
        "indice_forma_medio": round(
            mean(
                parche.length / (2 * math.sqrt(math.pi * parche.area))
                for parche in parches
            ),
            4,
        ),
    }
    metricas_red = {
        "umbral_m": float(umbral_m),
        "numero_nodos": grafo.number_of_nodes(),
        "numero_aristas": grafo.number_of_edges(),
        "numero_parches_conectados": grafo.number_of_nodes() - len(aislados),
        "numero_parches_aislados": len(aislados),
        "porcentaje_parches_aislados": round(
            len(aislados) / grafo.number_of_nodes() * 100, 4
        ),
        "numero_componentes": len(componentes),
        "tamano_componente_mayor": mayor_componente,
        "porcentaje_nodos_componente_mayor": round(
            mayor_componente / grafo.number_of_nodes() * 100, 4
        ),
        "densidad_red": round(nx.density(grafo), 8),
        "distancia_media_conexiones_m": round(mean(distancias_conexiones), 2)
        if distancias_conexiones
        else 0.0,
        "distancia_maxima_conexiones_m": round(max(distancias_conexiones), 2)
        if distancias_conexiones
        else 0.0,
        "numero_brechas_potenciales": len(conexiones_potenciales),
        "distancia_media_brechas_potenciales_m": round(mean(distancias_brechas), 2)
        if distancias_brechas
        else 0.0,
        "red_totalmente_conectada": nx.is_connected(grafo),
        "intermediacion_aproximada": intermediacion_aproximada,
    }
    nodos.sort(key=lambda item: item["indice_conector"], reverse=True)
    return {
        "metricas_clase": metricas_clase,
        "metricas_red": metricas_red,
        "top_conectores": nodos[:20],
        "parches_geojson": {"type": "FeatureCollection", "features": features},
        "conexiones_geojson": {
            "type": "FeatureCollection",
            "features": conexiones,
        },
        "conexiones_potenciales_geojson": {
            "type": "FeatureCollection",
            "features": conexiones_potenciales,
        },
        "hay_parches_aislados": bool(aislados),
        "campo_clase": campo_clase,
        "valores_bosque": sorted(str(valor) for valor in valores_bosque),
        "area_min_ha": float(area_min_ha),
        "area_paisaje_ha": round(float(area_paisaje_ha), 4),
        "origen_datos": origen_datos,
        "metodo": (
            "Parches de bosque como nodos; aristas por distancia; indice conector "
            "40% grado, 30% intermediacion, 20% area y 10% fuerza de conexion; "
            "brechas potenciales desde parches aislados hacia su vecino mas cercano."
        ),
        "participa_indice_prioridad": False,
    }


def analizar_fragmentacion_conectividad(
    datos_zip: bytes,
    campo_clase: str,
    valores_bosque: Iterable[Any],
    aoi_geojson: dict[str, Any],
    umbral_m: float = 500,
    area_min_ha: float = 0,
) -> dict[str, Any]:
    deps, lector, prj = _lector(datos_zip)
    if not prj:
        raise ValueError(
            "El ZIP debe incluir el archivo .prj para transformar las coordenadas correctamente."
        )
    campos = [campo[0] for campo in lector.fields[1:]]
    if campo_clase not in campos:
        raise ValueError(f"El campo {campo_clase!r} no existe en el shapefile.")

    crs_origen = deps["CRS"].from_wkt(prj)
    crs_area = deps["CRS"].from_epsg(8857)
    a_area = deps["Transformer"].from_crs(crs_origen, crs_area, always_xy=True)
    wgs_a_area = deps["Transformer"].from_crs("EPSG:4326", crs_area, always_xy=True)
    area_a_wgs = deps["Transformer"].from_crs(crs_area, "EPSG:4326", always_xy=True)

    aoi = deps["shape"](
        {"type": aoi_geojson["type"], "coordinates": aoi_geojson["coordinates"]}
    )
    if not aoi.is_valid:
        aoi = deps["make_valid"](aoi)
    aoi_m = deps["transform"](wgs_a_area.transform, aoi)
    area_paisaje_ha = aoi_m.area / 10_000
    valores_bosque = {str(valor) for valor in valores_bosque}

    parches = []
    for shape_record in lector.iterShapeRecords():
        registro = shape_record.record.as_dict()
        if str(registro.get(campo_clase)) not in valores_bosque:
            continue
        geometria = deps["shape"](shape_record.shape.__geo_interface__)
        if not geometria.is_valid:
            geometria = deps["make_valid"](geometria)
        geometria_m = deps["transform"](a_area.transform, geometria)
        if not geometria_m.intersects(aoi_m):
            continue
        recorte = deps["make_valid"](geometria_m.intersection(aoi_m))
        for parte in _partes_poligonales(recorte, deps):
            area_ha = parte.area / 10_000
            if area_ha >= area_min_ha and area_ha > 0:
                parches.append(parte)

    if not parches:
        raise ValueError(
            "No se encontraron parches de bosque dentro del area con los valores seleccionados."
        )

    nx = deps["nx"]
    grafo = nx.Graph()
    for indice, parche in enumerate(parches):
        grafo.add_node(indice, area_ha=parche.area / 10_000)

    arbol = deps["STRtree"](parches)
    for i, parche in enumerate(parches):
        candidatos = arbol.query(parche.buffer(umbral_m), predicate="intersects")
        for candidato in candidatos:
            j = int(candidato)
            if j <= i:
                continue
            distancia = parche.distance(parches[j])
            if distancia <= umbral_m:
                costo = max(1.0, float(distancia))
                peso = math.exp(-float(distancia) / umbral_m) if umbral_m else 1.0
                grafo.add_edge(i, j, distancia_m=float(distancia), costo=costo, peso=peso)

    grados = dict(grafo.degree())
    fuerza = dict(grafo.degree(weight="peso"))
    if grafo.number_of_nodes() > 400:
        intermediacion = nx.betweenness_centrality(
            grafo,
            k=min(200, grafo.number_of_nodes()),
            weight="costo",
            normalized=True,
            seed=123,
        )
        intermediacion_aproximada = True
    else:
        intermediacion = nx.betweenness_centrality(
            grafo, weight="costo", normalized=True
        )
        intermediacion_aproximada = False
    cercania = nx.closeness_centrality(grafo, distance="costo")
    componentes = list(nx.connected_components(grafo))
    componente_por_nodo = {
        nodo: indice + 1
        for indice, componente in enumerate(componentes)
        for nodo in componente
    }

    areas = {indice: parche.area / 10_000 for indice, parche in enumerate(parches)}
    grado_01 = _escala01({i: float(v) for i, v in grados.items()})
    fuerza_01 = _escala01({i: float(v) for i, v in fuerza.items()})
    intermediacion_01 = _escala01(intermediacion)
    area_01 = _escala01(areas)
    indices = {
        i: 0.40 * grado_01[i]
        + 0.30 * intermediacion_01[i]
        + 0.20 * area_01[i]
        + 0.10 * fuerza_01[i]
        for i in range(len(parches))
    }
    q75 = _percentil(list(indices.values()), 0.75)
    q50 = _percentil(list(indices.values()), 0.50)

    features = []
    nodos = []
    for i, parche in enumerate(parches):
        prioridad = "Alta" if indices[i] >= q75 else "Media" if indices[i] >= q50 else "Baja"
        propiedades = {
            "patch_id": i + 1,
            "area_ha": round(areas[i], 4),
            "grado": int(grados[i]),
            "grado_ponderado": round(float(fuerza[i]), 6),
            "intermediacion": round(float(intermediacion[i]), 6),
            "cercania": round(float(cercania[i]), 6),
            "componente": componente_por_nodo[i],
            "indice_conector": round(indices[i], 6),
            "prioridad_conectividad": prioridad,
        }
        nodos.append(propiedades)
        geometria_wgs = deps["transform"](area_a_wgs.transform, parche)
        features.append(
            {
                "type": "Feature",
                "properties": propiedades,
                "geometry": deps["mapping"](geometria_wgs),
            }
        )

    total_bosque_ha = sum(areas.values())
    perimetro_total_m = sum(parche.length for parche in parches)
    valores_area = list(areas.values())
    mayor_componente = max((len(componente) for componente in componentes), default=0)
    metricas_clase = {
        "numero_parches": len(parches),
        "area_total_bosque_ha": round(total_bosque_ha, 4),
        "porcentaje_paisaje_bosque": round(total_bosque_ha / area_paisaje_ha * 100, 4)
        if area_paisaje_ha
        else 0.0,
        "densidad_parches_por_100ha": round(len(parches) / area_paisaje_ha * 100, 4)
        if area_paisaje_ha
        else 0.0,
        "densidad_borde_m_ha": round(perimetro_total_m / area_paisaje_ha, 4)
        if area_paisaje_ha
        else 0.0,
        "indice_parche_mayor_pct": round(max(valores_area) / area_paisaje_ha * 100, 4)
        if area_paisaje_ha
        else 0.0,
        "area_media_parche_ha": round(mean(valores_area), 4),
        "area_mediana_parche_ha": round(median(valores_area), 4),
        "desviacion_area_parche_ha": round(pstdev(valores_area), 4),
        "indice_forma_medio": round(
            mean(
                parche.length / (2 * math.sqrt(math.pi * parche.area))
                for parche in parches
            ),
            4,
        ),
    }
    metricas_red = {
        "umbral_m": float(umbral_m),
        "numero_nodos": grafo.number_of_nodes(),
        "numero_aristas": grafo.number_of_edges(),
        "numero_componentes": len(componentes),
        "tamano_componente_mayor": mayor_componente,
        "porcentaje_nodos_componente_mayor": round(
            mayor_componente / grafo.number_of_nodes() * 100, 4
        ),
        "densidad_red": round(nx.density(grafo), 8),
        "red_totalmente_conectada": nx.is_connected(grafo),
        "intermediacion_aproximada": intermediacion_aproximada,
    }
    nodos.sort(key=lambda item: item["indice_conector"], reverse=True)
    return {
        "metricas_clase": metricas_clase,
        "metricas_red": metricas_red,
        "top_conectores": nodos[:20],
        "parches_geojson": {"type": "FeatureCollection", "features": features},
        "campo_clase": campo_clase,
        "valores_bosque": sorted(valores_bosque),
        "area_min_ha": float(area_min_ha),
        "metodo": (
            "Parches de bosque como nodos; aristas por distancia; indice conector "
            "40% grado, 30% intermediacion, 20% area y 10% fuerza de conexion."
        ),
        "participa_indice_prioridad": False,
    }


def _geometrias_desde_geojson(contenido: dict[str, Any]) -> list[dict[str, Any]]:
    tipo = contenido.get("type")
    if tipo == "FeatureCollection":
        return [
            feature["geometry"]
            for feature in contenido.get("features", [])
            if feature.get("geometry")
        ]
    if tipo == "Feature":
        return [contenido["geometry"]] if contenido.get("geometry") else []
    if tipo in {"Polygon", "MultiPolygon", "GeometryCollection"}:
        return [contenido]
    raise ValueError("La cobertura de bosque no contiene un GeoJSON compatible.")


def analizar_fragmentacion_geojson(
    bosque_geojson: dict[str, Any],
    aoi_geojson: dict[str, Any],
    umbral_m: float = 500,
    area_min_ha: float = 0,
) -> dict[str, Any]:
    """Analiza una cobertura preclasificada como bosque recibida desde Earth Engine.

    Todas las geometrias del asset representan bosque; por eso el usuario final no
    debe cargar archivos ni escoger un campo de clase.
    """

    deps = _dependencias()
    crs_area = deps["CRS"].from_epsg(8857)
    wgs_a_area = deps["Transformer"].from_crs(
        "EPSG:4326", crs_area, always_xy=True
    )
    area_a_wgs = deps["Transformer"].from_crs(
        crs_area, "EPSG:4326", always_xy=True
    )

    aoi = deps["shape"](
        {"type": aoi_geojson["type"], "coordinates": aoi_geojson["coordinates"]}
    )
    if not aoi.is_valid:
        aoi = deps["make_valid"](aoi)
    aoi_m = deps["transform"](wgs_a_area.transform, aoi)
    area_paisaje_ha = aoi_m.area / 10_000

    parches = []
    for geometria_geojson in _geometrias_desde_geojson(bosque_geojson):
        try:
            geometria = deps["shape"](geometria_geojson)
        except (TypeError, ValueError):
            continue
        if geometria.is_empty:
            continue
        if not geometria.is_valid:
            geometria = deps["make_valid"](geometria)
        geometria_m = deps["transform"](wgs_a_area.transform, geometria)
        if not geometria_m.intersects(aoi_m):
            continue
        recorte = deps["make_valid"](geometria_m.intersection(aoi_m))
        for parte in _partes_poligonales(recorte, deps):
            area_ha = parte.area / 10_000
            if area_ha >= area_min_ha and area_ha > 0:
                parches.append(parte)

    return _calcular_metricas_parches(
        parches=parches,
        deps=deps,
        area_paisaje_ha=area_paisaje_ha,
        area_a_wgs=area_a_wgs,
        umbral_m=umbral_m,
        area_min_ha=area_min_ha,
        campo_clase=None,
        valores_bosque=("bosque preclasificado",),
        origen_datos="asset_institucional_earth_engine",
    )


def agregar_resultados_fragmentacion(
    mapa,
    resultados: dict[str, Any],
    *,
    mostrar_parches: bool = True,
    mostrar_conexiones: bool = False,
    mostrar_brechas: bool = False,
):
    """Agrega una lectura cartográfica progresiva de la estructura del bosque.

    Los fragmentos son el resultado principal. Las relaciones de proximidad y las
    separaciones potenciales son evidencia técnica opcional y comienzan apagadas.
    """
    import folium

    if not resultados["parches_geojson"].get("features"):
        return []

    colores = {"Alta": "#a63f35", "Media": "#d58a24", "Baja": "#4f875f"}
    capas = []

    grupo_parches = folium.FeatureGroup(
        name="Bosque 2021 · fragmentos e importancia",
        overlay=True,
        control=False,
        show=mostrar_parches,
    )
    folium.GeoJson(
        resultados["parches_geojson"],
        style_function=lambda feature: {
            "color": "#0b3b36",
            "weight": 1.0,
            "fillColor": colores[
                feature["properties"]["prioridad_conectividad"]
            ],
            "fillOpacity": 0.48,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "patch_id",
                "area_ha",
                "prioridad_conectividad",
                "esta_aislado",
            ],
            aliases=[
                "Fragmento de bosque",
                "Área (ha)",
                "Valor para mantener unido el bosque",
                "Separado según la distancia elegida",
            ],
            localize=True,
            sticky=False,
        ),
        highlight_function=lambda feature: {
            "color": "#00544d",
            "weight": 4,
            "fillOpacity": 0.78,
        },
    ).add_to(grupo_parches)
    grupo_parches.add_to(mapa)
    capas.append(grupo_parches)

    if resultados.get("conexiones_geojson", {}).get("features"):
        grupo_conexiones = folium.FeatureGroup(
            name="Relaciones cercanas entre fragmentos · opcional",
            overlay=True,
            control=False,
            show=mostrar_conexiones,
        )
        folium.GeoJson(
            resultados["conexiones_geojson"],
            style_function=lambda _: {
                "color": "#2f6f68",
                "weight": 1.4,
                "opacity": 0.58,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[
                    "patch_id_origen",
                    "patch_id_destino",
                    "distancia_m",
                    "umbral_m",
                ],
                aliases=[
                    "Fragmento de origen",
                    "Fragmento de destino",
                    "Separación (m)",
                    "Distancia de referencia (m)",
                ],
                localize=True,
                sticky=False,
            ),
        ).add_to(grupo_conexiones)
        grupo_conexiones.add_to(mapa)
        capas.append(grupo_conexiones)

    if resultados.get("conexiones_potenciales_geojson", {}).get("features"):
        grupo_brechas = folium.FeatureGroup(
            name="Separaciones potenciales · revisar",
            overlay=True,
            control=False,
            show=mostrar_brechas,
        )
        folium.GeoJson(
            resultados["conexiones_potenciales_geojson"],
            style_function=lambda _: {
                "color": "#7c2d12",
                "weight": 2.0,
                "opacity": 0.78,
                "dashArray": "8 7",
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[
                    "patch_id_origen",
                    "patch_id_destino",
                    "distancia_m",
                    "umbral_m",
                ],
                aliases=[
                    "Fragmento separado",
                    "Vecino más cercano",
                    "Separación (m)",
                    "Distancia de referencia (m)",
                ],
                localize=True,
                sticky=False,
            ),
        ).add_to(grupo_brechas)
        grupo_brechas.add_to(mapa)
        capas.append(grupo_brechas)

    return capas
