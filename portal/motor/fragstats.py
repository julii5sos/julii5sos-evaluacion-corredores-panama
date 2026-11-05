"""Métricas de fragmentación y conectividad estilo FRAGSTATS sobre un ráster binario
de bosque (1 = bosque, 0 = no bosque, nodata fuera del área).

Métricas a nivel de clase (clase = bosque), con la regla de vecindad de 8 celdas
que FRAGSTATS usa por defecto:

    LPI      Largest Patch Index: % del paisaje ocupado por el parche más grande.
    ED       Edge Density: m de borde bosque/no-bosque por hectárea de paisaje.
    ENN_MN   Distancia euclidiana media al vecino más cercano (borde a borde, m).
    CONNECT  Connectance: % de pares de parches unidos a ≤ umbral de distancia.

Además, `connect_ventana()` genera la superficie continua de CONNECT con una
ventana móvil (componente "Patch Connectivity" del ERI).

Solo depende de numpy y scipy, para poder correr en el servidor del portal.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

OCHO = np.ones((3, 3), dtype=bool)


def _parches(bosque: np.ndarray):
    lab, n = ndi.label(bosque, structure=OCHO)
    return lab, n


def _bordes_de_parche(lab: np.ndarray):
    """Celdas de cada parche que tocan una celda que no es de ese parche (4-vecinos)."""
    interior = ndi.binary_erosion(lab > 0, structure=ndi.generate_binary_structure(2, 1), border_value=0)
    borde = (lab > 0) & ~interior
    ys, xs = np.nonzero(borde)
    return ys, xs, lab[ys, xs]


def metricas(bosque: np.ndarray, valido: np.ndarray | None = None, celda: float = 30.0,
             umbral_connect: float = 300.0) -> dict:
    """Calcula LPI, ED, ENN_MN, CONNECT y datos básicos para un área.

    bosque: matriz booleana de bosque.
    valido: matriz booleana del área analizada (por defecto, toda la matriz).
    celda:  tamaño de celda en metros (proyección métrica, p. ej. UTM 17N).
    umbral_connect: distancia borde a borde para considerar dos parches unidos.
    """
    if valido is None:
        valido = np.ones_like(bosque, dtype=bool)
    b = bosque.astype(bool) & valido
    area_celda_ha = celda * celda / 10_000
    area_total_ha = valido.sum() * area_celda_ha
    lab, n = _parches(b)
    res = dict(n_parches=int(n), area_ha=round(float(area_total_ha), 2),
               bosque_ha=round(float(b.sum() * area_celda_ha), 2),
               bosque_pct=round(float(100 * b.sum() / max(1, valido.sum())), 2))
    if n == 0:
        return res | dict(LPI=0.0, ED=0.0, ENN_MN=None, CONNECT=None)

    tam = np.bincount(lab.ravel())[1:]
    res['LPI'] = round(float(100 * tam.max() * area_celda_ha / area_total_ha), 3)
    res['parche_mayor_ha'] = round(float(tam.max() * area_celda_ha), 2)

    # Borde: aristas entre celda de bosque y celda válida sin bosque (4-vecinos).
    # Como FRAGSTATS sin borde de paisaje, no se cuenta el límite del área.
    nb = valido & ~b
    aristas = (np.count_nonzero(b[:, :-1] & nb[:, 1:]) + np.count_nonzero(nb[:, :-1] & b[:, 1:])
               + np.count_nonzero(b[:-1, :] & nb[1:, :]) + np.count_nonzero(nb[:-1, :] & b[1:, :]))
    res['ED'] = round(float(aristas * celda / area_total_ha), 3)

    if n == 1:
        return res | dict(ENN_MN=None, CONNECT=None)

    ys, xs, pid = _bordes_de_parche(lab)
    pts = np.column_stack([ys, xs]).astype(float) * celda
    arbol = cKDTree(pts)

    # ENN: para cada parche, distancia (centro a centro de celda) al borde de otro parche.
    enn = np.full(n + 1, np.inf)
    k = min(64, len(pts))
    for i in range(1, n + 1):
        sel = pid == i
        d, j = arbol.query(pts[sel], k=k)
        d = np.where(pid[j] != i, d, np.inf)
        dm = d.min()
        if not np.isfinite(dm):  # vecino más lejano que k puntos: búsqueda completa
            otros = pts[pid != i]
            dm = cKDTree(otros).query(pts[sel], k=1)[0].min()
        enn[i] = dm
    res['ENN_MN'] = round(float(np.mean(enn[1:])), 2)

    # CONNECT: pares de parches con distancia borde a borde ≤ umbral.
    pares = arbol.query_pairs(r=umbral_connect + celda * 0.5, output_type='ndarray')
    if len(pares):
        a, c = pid[pares[:, 0]], pid[pares[:, 1]]
        dif = a != c
        unidos = {tuple(sorted(p)) for p in zip(a[dif].tolist(), c[dif].tolist())}
    else:
        unidos = set()
    posibles = n * (n - 1) / 2
    res['CONNECT'] = round(float(100 * len(unidos) / posibles), 3)
    res['umbral_connect_m'] = umbral_connect
    return res


def conectividad_equivalente(bosque: np.ndarray, valido: np.ndarray, celda: float = 30.0,
                             umbral: float = 300.0) -> float:
    """Conectividad equivalente (ECA/A, %) de un área.

    Los parches a ≤ `umbral` metros (borde a borde) forman un mismo componente
    funcional. ECA = √(Σ A_k²) con A_k el área de bosque de cada componente;
    se expresa como % del área analizada. Vale 100 si el área es bosque
    continuo y baja cuando el bosque es poco o está en parches aislados.
    Es la versión ponderada por área de CONNECT (PC con enlaces binarios) y,
    a diferencia de CONNECT, está definida aunque haya un solo parche.
    """
    b = bosque & valido
    if not b.any():
        return 0.0
    r = max(0, int(round(umbral / celda / 2)))
    unido = ndi.binary_dilation(b, structure=OCHO, iterations=r) if r else b
    lab, _ = ndi.label(unido, structure=OCHO)
    areas = np.bincount(lab[b])[1:].astype(float)
    return float(100 * np.sqrt((areas ** 2).sum()) / max(1, valido.sum()))


def connect_ventana(bosque: np.ndarray, valido: np.ndarray, celda: float = 30.0,
                    radio_m: float = 1500.0, paso_m: float = 300.0,
                    umbral_connect: float = 300.0) -> np.ndarray:
    """Superficie continua de conectividad de parches (0–100) con ventana móvil.

    En cada ventana se calcula la conectividad equivalente (ECA/A, ver arriba),
    que integra CONNECT ponderado por el área de los parches. Se evalúa en una
    grilla gruesa (cada `paso_m`) y se interpola a la resolución original.
    """
    r = int(round(radio_m / celda))
    paso = max(1, int(round(paso_m / celda)))
    filas = np.arange(0, bosque.shape[0], paso)
    cols = np.arange(0, bosque.shape[1], paso)
    grueso = np.full((len(filas), len(cols)), np.nan, dtype=np.float32)
    for a, y in enumerate(filas):
        y0, y1 = max(0, y - r), min(bosque.shape[0], y + r + 1)
        for c, x in enumerate(cols):
            if not valido[y, x]:
                continue
            x0, x1 = max(0, x - r), min(bosque.shape[1], x + r + 1)
            v = valido[y0:y1, x0:x1]
            grueso[a, c] = conectividad_equivalente(bosque[y0:y1, x0:x1], v, celda, umbral_connect)
    # interpolación bilineal a la grilla fina
    rellenado = np.where(np.isnan(grueso), 0, grueso)
    peso = (~np.isnan(grueso)).astype(np.float32)
    zy = bosque.shape[0] / grueso.shape[0]
    zx = bosque.shape[1] / grueso.shape[1]
    num = ndi.zoom(rellenado, (zy, zx), order=1)[:bosque.shape[0], :bosque.shape[1]]
    den = ndi.zoom(peso, (zy, zx), order=1)[:bosque.shape[0], :bosque.shape[1]]
    out = np.where(den > 0.05, num / np.maximum(den, 1e-6), np.nan)
    out = np.pad(out, ((0, bosque.shape[0] - out.shape[0]), (0, bosque.shape[1] - out.shape[1])), mode='edge')
    out[~valido] = np.nan
    return out.astype(np.float32)
