import unittest

from streamlit.testing.v1 import AppTest


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


if __name__ == "__main__":
    unittest.main()
