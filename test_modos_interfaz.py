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
                "Elegir preevaluación territorial",
                "Elegir corredores y conectividad",
                "Elegir preevaluación integral",
            ],
        )

    def test_navegacion_explica_objetivo_y_metodo_sin_iniciar_el_motor(self):
        app = AppTest.from_file("app.py", default_timeout=30).run()

        self.assertEqual(
            app.segmented_control[0].options,
            ["Preevaluar un área", "Objetivo y alcance", "Método y fuentes"],
        )

        app.segmented_control[0].set_value("Objetivo y alcance").run()
        self.assertFalse(app.exception)
        self.assertIn("¿Para qué sirve esta preevaluación?", app.markdown[1].value)
        self.assertTrue(
            any(
                "Propósito y utilidad de la preevaluación" in bloque.value
                for bloque in app.markdown
            )
        )
        self.assertFalse(
            any("De una selección a un argumento claro" in bloque.value for bloque in app.markdown)
        )
        self.assertTrue(any(boton.label == "Comenzar una preevaluación" for boton in app.button))

        app.segmented_control[0].set_value("Método y fuentes").run()
        self.assertFalse(app.exception)
        self.assertIn("Cómo se construye la preevaluación", app.markdown[1].value)
        self.assertTrue(any(boton.label == "Ir a la preevaluación" for boton in app.button))

    def test_la_navegacion_introductoria_desaparece_al_elegir_un_enfoque(self):
        codigo = Path("app.py").read_text(encoding="utf-8")

        bloque_modo = codigo.index('if modo_analisis is None:')
        bloque_navegacion = codigo.index('vista_principal = st.segmented_control(', bloque_modo)
        bloque_aplicacion = codigo.index('APLICACION_ACTIVA =', bloque_navegacion)

        self.assertLess(bloque_modo, bloque_navegacion)
        self.assertLess(bloque_navegacion, bloque_aplicacion)

    def test_el_analisis_se_presenta_como_tablero_cartografico(self):
        codigo = Path("app_experiencia.py").read_text(encoding="utf-8")

        self.assertIn("Visor cartográfico", codigo)
        self.assertIn("Mapa y evidencia espacial", codigo)
        self.assertIn("Área y resultado", codigo)
        self.assertIn("Resultados completos", codigo)
        self.assertIn('["Resumen"]', codigo)
        self.assertNotIn("mostrar_flujo(2)", codigo)
        self.assertNotIn("Ver detalles del análisis · opcional", codigo)

    def test_subcuenca_se_recorta_a_la_cuenca(self):
        geometria = GeometriaPrueba()

        resultado = aplicar_limite_cuenca(
            TIPO_AREA_SUBCUENCA,
            geometria,
            "limite-cuenca",
        )

        self.assertEqual(resultado, "geometria-recortada")
        self.assertEqual(geometria.intersecciones, [("limite-cuenca", 10)])
        self.assertTrue(area_debe_recortarse_a_cuenca(TIPO_AREA_SUBCUENCA))

    def test_poligono_dibujado_se_recorta_a_la_cuenca(self):
        geometria = GeometriaPrueba()

        resultado = aplicar_limite_cuenca(
            TIPO_AREA_DIBUJADA,
            geometria,
            "limite-cuenca",
        )

        self.assertEqual(resultado, "geometria-recortada")
        self.assertEqual(geometria.intersecciones, [("limite-cuenca", 10)])
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
