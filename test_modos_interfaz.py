import ast
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from modos_app import (
    TIPO_AREA_DIBUJADA,
    TIPO_AREA_SUBCUENCA,
    aplicar_limite_cuenca,
    area_debe_recortarse_a_cuenca,
)


class GeometriaPrueba:
    def __init__(self):
        self.intersecciones = []

    def intersection(self, otra, tolerancia):
        self.intersecciones.append((otra, tolerancia))
        return "geometria-recortada"


class ModosInterfazTests(unittest.TestCase):
    def test_aplicacion_importa_la_regla_de_recorte(self):
        arbol = ast.parse(
            Path("app_experiencia.py").read_text(encoding="utf-8")
        )
        importados = {
            alias.name
            for nodo in arbol.body
            if isinstance(nodo, ast.ImportFrom) and nodo.module == "modos_app"
            for alias in nodo.names
        }

        self.assertIn("area_debe_recortarse_a_cuenca", importados)

    def test_la_pantalla_inicial_ofrece_tres_analisis_separados(self):
        app = AppTest.from_file("app.py", default_timeout=30).run()

        self.assertFalse(app.exception)
        self.assertEqual(
            [boton.label for boton in app.button],
            [
                "Elegir evaluación territorial",
                "Elegir corredores y conectividad",
                "Elegir evaluación integral",
            ],
        )

    def test_subcuenca_se_recorta_a_la_cuenca(self):
        geometria = GeometriaPrueba()

        resultado = aplicar_limite_cuenca(
            TIPO_AREA_SUBCUENCA,
            geometria,
            "limite-cuenca",
        )

        self.assertEqual(resultado, "geometria-recortada")
        self.assertEqual(geometria.intersecciones, [("limite-cuenca", 1)])
        self.assertTrue(area_debe_recortarse_a_cuenca(TIPO_AREA_SUBCUENCA))

    def test_poligono_dibujado_se_recorta_a_la_cuenca(self):
        geometria = GeometriaPrueba()

        resultado = aplicar_limite_cuenca(
            TIPO_AREA_DIBUJADA,
            geometria,
            "limite-cuenca",
        )

        self.assertEqual(resultado, "geometria-recortada")
        self.assertEqual(geometria.intersecciones, [("limite-cuenca", 1)])
        self.assertTrue(area_debe_recortarse_a_cuenca(TIPO_AREA_DIBUJADA))

    def test_finca_se_recorta_a_la_cuenca(self):
        geometria = GeometriaPrueba()

        resultado = aplicar_limite_cuenca(
            "Finca de monitoreo",
            geometria,
            "limite-cuenca",
        )

        self.assertEqual(resultado, "geometria-recortada")
        self.assertTrue(area_debe_recortarse_a_cuenca("Finca de monitoreo"))

    def test_cuenca_completa_no_se_recorta_contra_si_misma(self):
        geometria = GeometriaPrueba()

        resultado = aplicar_limite_cuenca(
            "Toda la cuenca",
            geometria,
            "limite-cuenca",
        )

        self.assertIs(resultado, geometria)
        self.assertFalse(geometria.intersecciones)
        self.assertFalse(area_debe_recortarse_a_cuenca("Toda la cuenca"))


if __name__ == "__main__":
    unittest.main()
