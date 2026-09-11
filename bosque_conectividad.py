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
        from shapely.ops import nearest_points, transform, unary_union
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
        "nearest_points": nearest_points,
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
    """Crea el segmento más corto entre los bordes de dos geometrías."""

    origen, destino = deps["nearest_points"](parche_origen, parche_destino)
    return deps["LineString"]([(origen.x, origen.y), (destino.x, destino.y)])


def _conexion_hacia_corredor(
    *,
    grafo,
    parches,
    arbol,
    indices_objetivo,
    corredores_contexto,
    umbral_m,
    deps,
    area_a_wgs,
    radio_busqueda_m,
):
    """Selecciona una ruta estructural reproducible hacia un corredor publicado."""

    vacio = {"type": "FeatureCollection", "features": []}
    resumen_vacio = {
        "evaluada": bool(corredores_contexto),
        "conecta": False,
        "tipo": "Sin conexión estructural al umbral",
        "corredor_nombre": None,
        "categoria": None,
        "categoria_etiqueta": None,
        "distancia_acumulada_m": None,
        "mayor_separacion_m": None,
        "numero_fragmentos_ruta": 0,
        "cruza_fuera_area": False,
        "radio_busqueda_m": float(radio_busqueda_m),
        "umbral_m": float(umbral_m),
        "participa_puntaje": False,
        "limitacion": (
            "Es una conexión estructural potencial basada en cobertura 2021 y "
            "distancias entre bordes; no demuestra movimiento de fauna ni "
            "conectividad funcional para una especie."
        ),
    }
    if not corredores_contexto or not indices_objetivo or not parches:
        return resumen_vacio, vacio, vacio

    prioridad_categoria = {"alta": 0, "mediana": 1, "mediabaja": 2}
    candidatos_ruta = []
    nx = deps["nx"]
    for indice_corredor, corredor in enumerate(corredores_contexto):
        geometria = corredor["geometria"]
        propiedades = corredor.get("propiedades") or {}
        indices_ancla = [
            int(indice)
            for indice in arbol.query(
                geometria.buffer(float(umbral_m)), predicate="intersects"
            )
            if parches[int(indice)].distance(geometria) <= float(umbral_m)
        ]
        if not indices_ancla:
            continue

        fuente_virtual = ("corredor", indice_corredor)
        grafo.add_node(fuente_virtual)
        for indice_ancla in indices_ancla:
            separacion_final = float(parches[indice_ancla].distance(geometria))
            grafo.add_edge(
                fuente_virtual,
                indice_ancla,
                costo=max(1.0, separacion_final),
                distancia_m=separacion_final,
            )
        try:
            distancias, rutas = nx.single_source_dijkstra(
                grafo, fuente_virtual, weight="costo"
            )
        finally:
            grafo.remove_node(fuente_virtual)
        destinos = [indice for indice in indices_objetivo if indice in distancias]
        if not destinos:
            continue
        destino = min(destinos, key=lambda indice: distancias[indice])
        ruta = list(reversed(rutas[destino][1:]))
        categoria = str(propiedades.get("cat") or "").lower()
        candidatos_ruta.append(
            (
                prioridad_categoria.get(categoria, 99),
                float(distancias[destino]),
                str(propiedades.get("nombre") or ""),
                indice_corredor,
                corredor,
                ruta,
            )
        )

    if not candidatos_ruta:
        return resumen_vacio, vacio, vacio

    _, distancia_total, _, _, corredor, ruta = min(candidatos_ruta)
    geometria_corredor = corredor["geometria"]
    propiedades_corredor = corredor.get("propiedades") or {}
    conjunto_objetivo = set(indices_objetivo)
    tramos = []
    separaciones = []
    pares = list(zip(ruta, ruta[1:]))
    for orden, (origen, destino) in enumerate(pares, start=1):
        linea_m = _linea_entre_parches(parches[origen], parches[destino], deps)
        separacion = float(parches[origen].distance(parches[destino]))
        separaciones.append(separacion)
        if linea_m.is_empty or linea_m.length <= 0:
            continue
        linea_wgs = deps["transform"](area_a_wgs.transform, linea_m)
        tramos.append(
            {
                "type": "Feature",
                "properties": {
                    "orden": orden,
                    "tipo_tramo": "Entre fragmentos",
                    "distancia_m": round(separacion, 1),
                },
                "geometry": deps["mapping"](linea_wgs),
            }
        )

    ancla = ruta[-1]
    linea_final = _linea_entre_parches(parches[ancla], geometria_corredor, deps)
    separacion_final = float(parches[ancla].distance(geometria_corredor))
    separaciones.append(separacion_final)
    if not linea_final.is_empty and linea_final.length > 0:
        tramos.append(
            {
                "type": "Feature",
                "properties": {
                    "orden": len(pares) + 1,
                    "tipo_tramo": "Llegada al corredor de referencia",
                    "distancia_m": round(separacion_final, 1),
                },
                "geometry": deps["mapping"](
                    deps["transform"](area_a_wgs.transform, linea_final)
                ),
            }
        )
    distancia_separaciones = sum(separaciones)

    nombre = str(propiedades_corredor.get("nombre") or "Corredor de referencia")
    categoria = str(propiedades_corredor.get("cat") or "").lower() or None
    etiqueta = str(
        propiedades_corredor.get("categoria_etiqueta")
        or {"alta": "Alta", "mediana": "Mediana", "mediabaja": "Media-baja"}.get(
            categoria, "No indicada"
        )
    )
    es_directa = len(ruta) == 1 and separacion_final <= 0.01
    propiedades_comunes = {
        "corredor": nombre,
        "categoria_corredor": etiqueta,
        "tipo_conexion": "Directa" if es_directa else "Estructural potencial",
        "umbral_m": float(umbral_m),
        "distancia_acumulada_m": round(float(distancia_separaciones), 1),
    }
    for feature in tramos:
        feature["properties"].update(propiedades_comunes)

    resumen = {
        **resumen_vacio,
        "evaluada": True,
        "conecta": True,
        "tipo": propiedades_comunes["tipo_conexion"],
        "corredor_nombre": nombre,
        "categoria": categoria,
        "categoria_etiqueta": etiqueta,
        "distancia_acumulada_m": round(float(distancia_separaciones), 1),
        "mayor_separacion_m": round(max(separaciones, default=0.0), 1),
        "numero_fragmentos_ruta": len(ruta),
        "cruza_fuera_area": any(indice not in conjunto_objetivo for indice in ruta),
    }
    # Para la ficha se publica únicamente el tramo del corredor próximo a la
    # cadena seleccionada. Dibujar el polígono nacional completo reduciría el
    # área evaluada a un punto y haría ilegible el mapa explicativo.
    entorno_ruta = deps["unary_union"]([parches[indice] for indice in ruta]).buffer(
        max(float(umbral_m) * 2, 500.0)
    )
    corredor_mapa = deps["make_valid"](geometria_corredor.intersection(entorno_ruta))
    if corredor_mapa.is_empty:
        corredor_mapa = geometria_corredor
    corredor_wgs = deps["transform"](area_a_wgs.transform, corredor_mapa)
    corredor_referencia = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "nombre": nombre,
                    "categoria": categoria,
                    "categoria_etiqueta": etiqueta,
                },
                "geometry": deps["mapping"](corredor_wgs),
            }
        ],
    }
    return (
        resumen,
        {"type": "FeatureCollection", "features": tramos},
        corredor_referencia,
    )


def _resultado_sin_parches(
    *,
    area_paisaje_ha: float,
    umbral_m: float,
    area_min_ha: float,
    campo_clase: str | None,
    valores_bosque: Iterable[Any],
    origen_datos: str,
    area_objetivo_m=None,
    distancia_contexto_m: float = 0.0,
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
            "numero_parches_contexto": 0,
            "numero_aristas": 0,
            "numero_aristas_contexto": 0,
            "numero_conexiones_fuera_area": 0,
            "numero_parches_continuidad_exterior": 0,
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
        "ruta_corredor_geojson": {"type": "FeatureCollection", "features": []},
        "corredor_referencia_geojson": {
            "type": "FeatureCollection",
            "features": [],
        },
        "area_objetivo_geojson": {
            "type": "FeatureCollection",
            "features": [],
        },
        "conexion_corredor": {
            "evaluada": False,
            "conecta": False,
            "tipo": "No evaluada",
            "participa_puntaje": False,
        },
        "hay_parches_aislados": False,
        "campo_clase": campo_clase,
        "valores_bosque": sorted(str(valor) for valor in valores_bosque),
        "area_min_ha": float(area_min_ha),
        "area_paisaje_ha": round(float(area_paisaje_ha), 4),
        "considera_contexto_exterior": area_objetivo_m is not None,
        "distancia_contexto_m": float(distancia_contexto_m),
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
    area_objetivo_m=None,
    distancia_contexto_m: float = 0.0,
    corredores_contexto: list[dict[str, Any]] | None = None,
    radio_busqueda_corredor_m: float = 0.0,
) -> dict[str, Any]:
    if not parches:
        resultado = _resultado_sin_parches(
            area_paisaje_ha=area_paisaje_ha,
            umbral_m=umbral_m,
            area_min_ha=area_min_ha,
            campo_clase=campo_clase,
            valores_bosque=valores_bosque,
            origen_datos=origen_datos,
        )
        resultado["considera_contexto_exterior"] = area_objetivo_m is not None
        resultado["distancia_contexto_m"] = float(distancia_contexto_m)
        return resultado

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

    geometrias_visibles = {}
    continuidad_exterior = {}
    for indice, parche in enumerate(parches):
        if area_objetivo_m is None:
            geometrias_visibles[indice] = parche
            continuidad_exterior[indice] = False
            continue
        recorte = deps["make_valid"](parche.intersection(area_objetivo_m))
        partes = _partes_poligonales(recorte, deps)
        if not partes:
            continue
        geometria_visible = deps["unary_union"](partes)
        if geometria_visible.is_empty or geometria_visible.area <= 0:
            continue
        geometrias_visibles[indice] = geometria_visible
        continuidad_exterior[indice] = parche.area - geometria_visible.area > 0.01

    indices_objetivo = list(geometrias_visibles)
    conjunto_objetivo = set(indices_objetivo)
    if not indices_objetivo:
        resultado = _resultado_sin_parches(
            area_paisaje_ha=area_paisaje_ha,
            umbral_m=umbral_m,
            area_min_ha=area_min_ha,
            campo_clase=campo_clase,
            valores_bosque=valores_bosque,
            origen_datos=origen_datos,
        )
        resultado["metricas_red"]["numero_parches_contexto"] = len(parches)
        resultado["metricas_red"]["numero_aristas_contexto"] = grafo.number_of_edges()
        resultado["considera_contexto_exterior"] = area_objetivo_m is not None
        resultado["distancia_contexto_m"] = float(distancia_contexto_m)
        return resultado

    areas_contexto = {
        indice: parche.area / 10_000 for indice, parche in enumerate(parches)
    }
    areas_objetivo = {
        indice: geometrias_visibles[indice].area / 10_000
        for indice in indices_objetivo
    }
    grado_01 = _escala01({i: float(v) for i, v in grados.items()})
    fuerza_01 = _escala01({i: float(v) for i, v in fuerza.items()})
    intermediacion_01 = _escala01(intermediacion)
    area_01 = _escala01(areas_contexto)
    indices = {
        i: 0.40 * grado_01[i]
        + 0.30 * intermediacion_01[i]
        + 0.20 * area_01[i]
        + 0.10 * fuerza_01[i]
        for i in range(len(parches))
    }
    indices_area = [indices[indice] for indice in indices_objetivo]
    q75 = _percentil(indices_area, 0.75)
    q50 = _percentil(indices_area, 0.50)

    features = []
    nodos = []
    for i in indices_objetivo:
        parche = parches[i]
        parche_visible = geometrias_visibles[i]
        prioridad = "Alta" if indices[i] >= q75 else "Media" if indices[i] >= q50 else "Baja"
        indice_vecino, distancia_vecino = vecinos_mas_cercanos[i]
        conexiones_externas = sum(
            1 for vecino in grafo.neighbors(i) if vecino not in conjunto_objetivo
        )
        propiedades = {
            "patch_id": i + 1,
            "area_ha": round(areas_objetivo[i], 4),
            "area_contexto_ha": round(areas_contexto[i], 4),
            "grado": int(grados[i]),
            "grado_ponderado": round(float(fuerza[i]), 6),
            "intermediacion": round(float(intermediacion[i]), 6),
            "cercania": round(float(cercania[i]), 6),
            "componente": componente_por_nodo[i],
            "indice_conector": round(indices[i], 6),
            "prioridad_conectividad": prioridad,
            "esta_aislado": int(grados[i]) == 0,
            "condicion_cercania": (
                "Separado" if int(grados[i]) == 0 else "Conectado"
            ),
            "continua_fuera_area": (
                "Sí" if continuidad_exterior[i] or conexiones_externas else "No"
            ),
            "conexiones_fuera_area": conexiones_externas,
            "distancia_vecino_mas_cercano_m": (
                round(distancia_vecino, 1) if distancia_vecino is not None else None
            ),
            "patch_id_vecino_mas_cercano": (
                indice_vecino + 1 if indice_vecino is not None else None
            ),
        }
        nodos.append(propiedades)
        geometria_wgs = deps["transform"](area_a_wgs.transform, parche_visible)
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
        if origen not in conjunto_objetivo and destino not in conjunto_objetivo:
            continue
        distancias_conexiones.append(distancia)

    # Las métricas y el índice conservan la red completa. La visualización usa
    # solo la estructura mínima de cada componente para eliminar líneas repetidas.
    subgrafo_objetivo = grafo.subgraph(indices_objetivo)
    estructura_visible = nx.minimum_spanning_tree(
        subgrafo_objetivo, weight="distancia_m"
    )
    for origen, destino, atributos in estructura_visible.edges(data=True):
        distancia = float(atributos["distancia_m"])
        linea_m = _linea_entre_parches(
            geometrias_visibles[origen], geometrias_visibles[destino], deps
        )
        if area_objetivo_m is not None:
            linea_m = linea_m.intersection(area_objetivo_m)
        if linea_m.is_empty:
            continue
        linea_wgs = deps["transform"](
            area_a_wgs.transform,
            linea_m,
        )
        conexiones.append(
            {
                "type": "Feature",
                "properties": {
                    "tipo": "Enlace esencial dentro del umbral",
                    "patch_id_origen": origen + 1,
                    "patch_id_destino": destino + 1,
                    "distancia_m": round(distancia, 1),
                    "umbral_m": float(umbral_m),
                },
                "geometry": deps["mapping"](linea_wgs),
            }
        )

    aislados = [
        indice
        for indice in indices_objetivo
        if int(grados[indice]) == 0
    ]
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
        destino_geometria = geometrias_visibles.get(destino, parches[destino])
        linea_m = _linea_entre_parches(
            geometrias_visibles[origen], destino_geometria, deps
        )
        if area_objetivo_m is not None:
            linea_m = linea_m.intersection(area_objetivo_m)
        if linea_m.is_empty:
            continue
        linea_wgs = deps["transform"](area_a_wgs.transform, linea_m)
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

    total_bosque_ha = sum(areas_objetivo.values())
    perimetro_total_m = sum(
        geometria.length for geometria in geometrias_visibles.values()
    )
    valores_area = list(areas_objetivo.values())
    tamanos_componentes_objetivo = defaultdict(int)
    for indice in indices_objetivo:
        tamanos_componentes_objetivo[componente_por_nodo[indice]] += 1
    mayor_componente = max(tamanos_componentes_objetivo.values(), default=0)
    (
        conexion_corredor,
        ruta_corredor_geojson,
        corredor_referencia_geojson,
    ) = _conexion_hacia_corredor(
        grafo=grafo,
        parches=parches,
        arbol=arbol,
        indices_objetivo=indices_objetivo,
        corredores_contexto=corredores_contexto or [],
        umbral_m=umbral_m,
        deps=deps,
        area_a_wgs=area_a_wgs,
        radio_busqueda_m=radio_busqueda_corredor_m,
    )
    numero_conexiones_externas = sum(
        1
        for origen, destino in grafo.edges()
        if (origen in conjunto_objetivo) != (destino in conjunto_objetivo)
    )
    numero_continuidad_exterior = sum(
        1
        for indice in indices_objetivo
        if continuidad_exterior[indice]
        or any(vecino not in conjunto_objetivo for vecino in grafo.neighbors(indice))
    )
    distancias_brechas = [
        float(feature["properties"]["distancia_m"])
        for feature in conexiones_potenciales
    ]
    metricas_clase = {
        "numero_parches": len(indices_objetivo),
        "area_total_bosque_ha": round(total_bosque_ha, 4),
        "porcentaje_paisaje_bosque": round(total_bosque_ha / area_paisaje_ha * 100, 4)
        if area_paisaje_ha
        else 0.0,
        "densidad_parches_por_100ha": round(len(indices_objetivo) / area_paisaje_ha * 100, 4)
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
                for parche in geometrias_visibles.values()
            ),
            4,
        ),
    }
    metricas_red = {
        "umbral_m": float(umbral_m),
        "numero_nodos": len(indices_objetivo),
        "numero_aristas": subgrafo_objetivo.number_of_edges(),
        "numero_relaciones_mostradas": len(conexiones),
        "numero_parches_conectados": len(indices_objetivo) - len(aislados),
        "numero_parches_aislados": len(aislados),
        "porcentaje_parches_aislados": round(
            len(aislados) / len(indices_objetivo) * 100, 4
        ),
        "numero_componentes": len(tamanos_componentes_objetivo),
        "tamano_componente_mayor": mayor_componente,
        "porcentaje_nodos_componente_mayor": round(
            mayor_componente / len(indices_objetivo) * 100, 4
        ),
        "densidad_red": round(nx.density(subgrafo_objetivo), 8),
        "numero_parches_contexto": grafo.number_of_nodes(),
        "numero_aristas_contexto": grafo.number_of_edges(),
        "numero_conexiones_fuera_area": numero_conexiones_externas,
        "numero_parches_continuidad_exterior": numero_continuidad_exterior,
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
        "red_totalmente_conectada": len(tamanos_componentes_objetivo) == 1,
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
        "ruta_corredor_geojson": ruta_corredor_geojson,
        "corredor_referencia_geojson": corredor_referencia_geojson,
        "conexion_corredor": conexion_corredor,
        "hay_parches_aislados": bool(aislados),
        "campo_clase": campo_clase,
        "valores_bosque": sorted(str(valor) for valor in valores_bosque),
        "area_min_ha": float(area_min_ha),
        "area_paisaje_ha": round(float(area_paisaje_ha), 4),
        "origen_datos": origen_datos,
        "considera_contexto_exterior": area_objetivo_m is not None,
        "distancia_contexto_m": float(distancia_contexto_m),
        "metodo": (
            "Parches de bosque como nodos; aristas por distancia; indice conector "
            "40% grado, 30% intermediacion, 20% area y 10% fuerza de conexion; "
            "brechas potenciales desde parches aislados hacia su vecino mas cercano; "
            "las metricas usan la red completa y el mapa muestra su estructura minima; "
            "la conectividad puede considerar bosque exterior mientras las superficies "
            "y geometrias publicadas permanecen dentro del area objetivo; la ruta hacia "
            "un corredor es estructural potencial y no conectividad funcional."
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
    incluir_contexto_exterior: bool = False,
    corredores_geojson: dict[str, Any] | None = None,
    radio_busqueda_corredor_m: float = 0.0,
) -> dict[str, Any]:
    """Analiza una cobertura preclasificada como bosque recibida desde Earth Engine.

    Todas las geometrias del asset representan bosque; por eso el usuario final no
    debe cargar archivos ni escoger un campo de clase. Cuando se activa el contexto
    exterior, la red considera un buffer de contexto, pero las superficies y
    geometrias devueltas permanecen dentro del area objetivo. Un radio mayor
    puede usarse solo para buscar una cadena estructural hacia un corredor.
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
    distancia_contexto_m = (
        max(float(umbral_m), float(radio_busqueda_corredor_m or 0.0))
        if incluir_contexto_exterior
        else 0.0
    )
    limite_analisis_m = (
        aoi_m.buffer(distancia_contexto_m) if incluir_contexto_exterior else aoi_m
    )

    corredores_contexto = []
    if corredores_geojson:
        for feature in corredores_geojson.get("features", []):
            geometria_geojson = feature.get("geometry")
            if not geometria_geojson:
                continue
            geometria = deps["shape"](geometria_geojson)
            if not geometria.is_valid:
                geometria = deps["make_valid"](geometria)
            geometria_m = deps["transform"](wgs_a_area.transform, geometria)
            if geometria_m.intersects(limite_analisis_m):
                corredores_contexto.append(
                    {
                        "geometria": geometria_m,
                        "propiedades": feature.get("properties") or {},
                    }
                )

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
        if not geometria_m.intersects(limite_analisis_m):
            continue
        recorte = deps["make_valid"](geometria_m.intersection(limite_analisis_m))
        for parte in _partes_poligonales(recorte, deps):
            area_ha = parte.area / 10_000
            if area_ha >= area_min_ha and area_ha > 0:
                parches.append(parte)

    resultado = _calcular_metricas_parches(
        parches=parches,
        deps=deps,
        area_paisaje_ha=area_paisaje_ha,
        area_a_wgs=area_a_wgs,
        umbral_m=umbral_m,
        area_min_ha=area_min_ha,
        campo_clase=None,
        valores_bosque=("bosque preclasificado",),
        origen_datos="asset_institucional_earth_engine",
        area_objetivo_m=aoi_m if incluir_contexto_exterior else None,
        distancia_contexto_m=distancia_contexto_m,
        corredores_contexto=corredores_contexto,
        radio_busqueda_corredor_m=float(radio_busqueda_corredor_m or 0.0),
    )
    resultado["area_objetivo_geojson"] = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"tipo": "Área evaluada"},
                "geometry": {
                    "type": aoi_geojson["type"],
                    "coordinates": aoi_geojson["coordinates"],
                },
            }
        ],
    }
    return resultado


def agregar_resultados_fragmentacion(
    mapa,
    resultados: dict[str, Any],
    *,
    mostrar_parches: bool = True,
    mostrar_conexiones: bool = False,
    mostrar_brechas: bool = False,
    mostrar_ruta_corredor: bool = False,
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
                "condicion_cercania",
                "grado",
                "distancia_vecino_mas_cercano_m",
                "continua_fuera_area",
            ],
            aliases=[
                "Fragmento de bosque",
                "Área dentro del polígono (ha)",
                "Importancia relativa dentro del área",
                "Condición de cercanía",
                "Fragmentos cercanos",
                "Vecino más próximo (m)",
                "Tiene continuidad o conexión exterior",
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

    fragmentos_separados = {
        "type": "FeatureCollection",
        "features": [
            feature
            for feature in resultados["parches_geojson"]["features"]
            if feature.get("properties", {}).get("esta_aislado")
        ],
    }
    if fragmentos_separados["features"]:
        grupo_separados = folium.FeatureGroup(
            name="Fragmentos separados · resaltar",
            overlay=True,
            control=False,
            show=mostrar_brechas,
        )
        folium.GeoJson(
            fragmentos_separados,
            style_function=lambda _: {
                "color": "#7c2d12",
                "weight": 3.2,
                "dashArray": "7 5",
                "fillColor": "#f6c7b8",
                "fillOpacity": 0.56,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[
                    "patch_id",
                    "area_ha",
                    "distancia_vecino_mas_cercano_m",
                    "continua_fuera_area",
                ],
                aliases=[
                    "Fragmento separado",
                    "Área dentro del polígono (ha)",
                    "Vecino más próximo (m)",
                    "Tiene continuidad o conexión exterior",
                ],
                localize=True,
                sticky=False,
            ),
        ).add_to(grupo_separados)
        grupo_separados.add_to(mapa)
        capas.append(grupo_separados)

    if resultados.get("conexiones_geojson", {}).get("features"):
        grupo_conexiones = folium.FeatureGroup(
            name="Estructura esencial entre fragmentos · opcional",
            overlay=True,
            control=False,
            show=mostrar_conexiones,
        )
        folium.GeoJson(
            resultados["conexiones_geojson"],
            style_function=lambda _: {
                "color": "#ffffff",
                "weight": 5.0,
                "opacity": 0.88,
            },
            interactive=False,
        ).add_to(grupo_conexiones)
        folium.GeoJson(
            resultados["conexiones_geojson"],
            style_function=lambda _: {
                "color": "#00544d",
                "weight": 2.4,
                "opacity": 0.96,
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

    if resultados.get("ruta_corredor_geojson", {}).get("features"):
        grupo_ruta = folium.FeatureGroup(
            name="Conexión estructural potencial hacia corredor",
            overlay=True,
            control=False,
            show=mostrar_ruta_corredor,
        )
        folium.GeoJson(
            resultados["ruta_corredor_geojson"],
            style_function=lambda _: {
                "color": "#ffffff",
                "weight": 8.0,
                "opacity": 0.94,
            },
            interactive=False,
        ).add_to(grupo_ruta)
        folium.GeoJson(
            resultados["ruta_corredor_geojson"],
            style_function=lambda _: {
                "color": "#d97904",
                "weight": 4.2,
                "opacity": 1.0,
                "dashArray": "12 7",
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[
                    "corredor",
                    "categoria_corredor",
                    "tipo_tramo",
                    "distancia_m",
                    "distancia_acumulada_m",
                    "umbral_m",
                ],
                aliases=[
                    "Corredor de referencia",
                    "Categoría publicada",
                    "Tramo",
                    "Separación de este tramo (m)",
                    "Separación acumulada (m)",
                    "Máximo permitido por salto (m)",
                ],
                localize=True,
                sticky=False,
            ),
        ).add_to(grupo_ruta)
        grupo_ruta.add_to(mapa)
        capas.append(grupo_ruta)

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
