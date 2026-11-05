"""Ejecuta el motor de conectividad para la Cuenca del Canal + 10 km.

    python ejecutar_motor.py                 # Earth Engine (requiere EE_PROJECT)
    python ejecutar_motor.py --demo          # sin Earth Engine, con capas de demostración
    python ejecutar_motor.py --anio0 2017 --anio1 2025 --escala 30
"""
import argparse

from motor.pipeline import ejecutar

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--demo', action='store_true', help='usar capas de demostración (sin Earth Engine)')
    p.add_argument('--anio0', type=int, help='año base (por defecto 2017)')
    p.add_argument('--anio1', type=int, help='año actual (por defecto el último año completo)')
    p.add_argument('--escala', type=int, help='tamaño de celda en m (30 con Earth Engine, 90 en demo)')
    a = p.parse_args()
    ejecutar(a.demo, a.anio0, a.anio1, a.escala)
