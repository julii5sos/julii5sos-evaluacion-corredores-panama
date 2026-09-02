import ast
import unittest
from pathlib import Path


RUTA_APLICACION = Path(__file__).with_name("app_experiencia.py")


def llamadas_de_funcion(nombre_funcion):
    arbol = ast.parse(RUTA_APLICACION.read_text(encoding="utf-8"))
    funcion = next(
        nodo
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef) and nodo.name == nombre_funcion
    )
    return {
        nodo.func.attr
        for nodo in ast.walk(funcion)
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
    }


class ProyeccionesMosaicosTest(unittest.TestCase):
    def test_mosaico_tmf_define_proyeccion_predeterminada(self):
        self.assertIn("setDefaultProjection", llamadas_de_funcion("obtener_tmf"))

    def test_mosaico_esri_define_proyeccion_predeterminada(self):
        self.assertIn("setDefaultProjection", llamadas_de_funcion("obtener_esri"))

    def test_reduccion_esri_conserva_proyeccion_de_origen(self):
        llamadas = llamadas_de_funcion("imagen_coincidencia_revision")
        self.assertIn("setDefaultProjection", llamadas)
        self.assertIn("reduceResolution", llamadas)


if __name__ == "__main__":
    unittest.main()
