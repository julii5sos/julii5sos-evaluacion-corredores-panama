"""Motor de análisis de conectividad.

Recibe los criterios del asistente (tipo, área, especie focal, dispersión,
umbral, núcleo mínimo, clases de hábitat y periodo) y devuelve los
indicadores que muestra el panel de resultados de la Plataforma.

Mientras las capas sean de demostración, los resultados se derivan de las
estadísticas precalculadas por unidad (static/data/estadisticas.json).
Con Earth Engine conectado, `calcular()` es el punto donde se lanzaría la
reducción real (ee.Image.reduceRegion) sobre el área elegida.
"""
from __future__ import annotations
import json, math
from dataclasses import dataclass, field
from functools import lru_cache

import config as C

TIPOS = {
    'estructural': 'Conectividad estructural',
    'corredores': 'Corredores de menor costo',
    'cambio': 'Cambio en el tiempo',
    'restauracion': 'Prioridades de restauración',
}


@dataclass
class Criterios:
    tipo: str = 'estructural'
    cu: str = ''            # id de cuenca ('' = todo Panamá)
    su: str = ''            # id de subcuenca
    esp: str = 'mam'
    disp: float = 15.0      # km
    umbral: int = 60        # % de bosque en 1 km
    minCore: int = 50       # ha
    clases: list[int] = field(default_factory=lambda: [0, 1, 2])
    y0: int = 2000
    y1: int = 2025

    @classmethod
    def desde_dict(cls, d: dict) -> 'Criterios':
        c = cls()
        for k in c.__dataclass_fields__:
            if k in d and d[k] is not None:
                setattr(c, k, d[k])
        c.disp = float(c.disp); c.umbral = int(c.umbral); c.minCore = int(c.minCore)
        c.y0 = int(c.y0); c.y1 = int(c.y1); c.clases = [int(x) for x in c.clases]
        return c

    def validar(self, unidades: dict) -> str:
        if self.tipo not in TIPOS:
            return 'Tipo de análisis no reconocido.'
        uid = self.su or self.cu or 'pa'
        if uid not in unidades:
            return 'El área elegida no existe.'
        if not self.clases:
            return 'Elige al menos una clase de hábitat.'
        if self.y1 <= self.y0:
            return 'El año final debe ser posterior al inicial.'
        if not 0.5 <= self.disp <= 20:
            return 'La distancia de dispersión debe estar entre 0,5 y 20 km.'
        return ''


@lru_cache(maxsize=1)
def estadisticas() -> dict:
    est = json.loads((C.DATOS_SALIDA / 'estadisticas.json').read_text(encoding='utf-8'))
    unidades = {'pa': est['nat']}
    for u in est['cuencas'] + est['subcuencas']:
        unidades[u['id']] = u
    est['unidades'] = unidades
    return est


def calcular(c: Criterios) -> dict:
    """Devuelve los indicadores del análisis (misma forma que usa plataforma.js)."""
    est = estadisticas()
    u = est['unidades'][c.su or c.cu or 'pa']
    bosque = sum(u['clases'][:3])
    f = math.log(c.disp + 1) / math.log(21)              # 0–1 según dispersión
    ex = 1.25 - 0.6 * f                                   # dispersión alta suaviza el índice
    umb = 1 + (c.umbral - 60) / 120                       # umbral exigente lo reduce
    hab = sum(u['clases'][i] for i in c.clases)
    conn = min(0.99, (u['conn'] ** ex) / umb)
    conn0 = min(0.99, (u['conn2000'] ** ex) / umb)
    core_f = min(1.2, (50 / c.minCore) ** 0.18) * min(1, hab / max(1, bosque))
    nnuc = max(1, round(u['nnuc'] * (50 / c.minCore) ** 0.35)) if u['nnuc'] else 0
    i0, i1 = max(0, c.y0 - 2000), c.y1 - 2001   # pérdida de y0+1 a y1
    loss_p = u['perdida'][i0:i1 + 1]
    h5 = [u['hist'][k] + u['hist'][k + 1] for k in (0, 2, 4, 6, 8)]
    return dict(
        uid=u['id'], tipo=c.tipo, titulo=TIPOS[c.tipo], motor='python',
        hab=hab, conn=round(conn, 3), conn0=round(conn0, 3), core=round(u['nucleo'] * core_f),
        nnuc=nnuc, loss=sum(loss_p), lossP=loss_p, lossY=est['years'][i0:i1 + 1], h5=h5,
    )
