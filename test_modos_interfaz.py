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
            ["Mapa", "Metodología y ayuda", "Acerca del visor"],
        )

        app.segmented_control[0].set_value("Metodología y ayuda").run()
        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                "Cómo se construye la preevaluación" in bloque.value
                for bloque in app.markdown
            )
        )
        self.assertTrue(any(boton.label == "Abrir el mapa" for boton in app.button))

        app.segmented_control[0].set_value("Acerca del visor").run()
        self.assertFalse(app.exception)
        self.assertTrue(
            any("Qué problema ayuda a resolver" in bloque.value for bloque in app.markdown)
        )
        self.assertTrue(any(boton.label == "Abrir el mapa" for boton in app.button))

    def test_la_navegacion_principal_permanece_antes_del_selector_de_enfoque(self):
        codigo = Path("app.py").read_text(encoding="utf-8")

        self.assertNotIn('SECCION_ANALISIS = "Análisis"', codigo)
        bloque_navegacion = codigo.index('seccion_tablero = st.segmented_control(')
        bloque_modo = codigo.index('if modo_analisis is None:')
        bloque_aplicacion = codigo.index('APLICACION_ACTIVA =', bloque_modo)

        self.assertLess(bloque_navegacion, bloque_modo)
        self.assertLess(bloque_modo, bloque_aplicacion)

    def test_el_analisis_se_presenta_como_tablero_cartografico(self):
        codigo = Path("app_experiencia.py").read_text(encoding="utf-8")

        self.assertIn("Visor cartográfico", codigo)
        self.assertIn("Mapa y evidencia espacial", codigo)
        self.assertIn("Área y resultado", codigo)
        self.assertIn("Resultados completos", codigo)
        self.assertIn("Crear análisis", codigo)
        self.assertIn("Ver resultados", codigo)
        self.assertIn("Volver al mapa", codigo)
        self.assertIn('st.session_state["mostrar_resultados"] = True', codigo)
        self.assertIn("Evolución por fuente", codigo)
        self.assertIn("JRC Tropical Moist Forest", codigo)
        self.assertIn("Hansen Global Forest Change", codigo)
        self.assertIn("ESRI Land Use / Land Cover", codigo)
        self.assertIn("Sentinel-2 · NDVI", codigo)
        self.assertIn("GEDI · altura del dosel", codigo)
        self.assertIn('if seccion_tablero == "Análisis":', codigo)
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
