import unittest

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

    def test_subcuenca_se_conserva_completa_aunque_sobresalga(self):
        geometria = GeometriaPrueba()

        resultado = aplicar_limite_cuenca(
            TIPO_AREA_SUBCUENCA,
            geometria,
            "limite-cuenca",
        )

        self.assertIs(resultado, geometria)
        self.assertFalse(geometria.intersecciones)
        self.assertFalse(area_debe_recortarse_a_cuenca(TIPO_AREA_SUBCUENCA))

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


if __name__ == "__main__":
    unittest.main()
