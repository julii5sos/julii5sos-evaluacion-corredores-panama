import unittest

from eri_indicativo import (
    CLASES_ERI,
    PESOS_ERI,
    calcular_valor_eri,
    clasificar_eri,
    construir_resultado_eri,
)


class EriIndicativoTests(unittest.TestCase):
    def test_pesos_suman_uno(self):
        self.assertAlmostEqual(sum(PESOS_ERI.values()), 1.0)

    def test_clases_cubren_todo_el_intervalo(self):
        self.assertEqual(clasificar_eri(0)["etiqueta"], "Muy baja")
        self.assertEqual(clasificar_eri(0.25)["etiqueta"], "Baja")
        self.assertEqual(clasificar_eri(0.40)["etiqueta"], "Media")
        self.assertEqual(clasificar_eri(0.60)["etiqueta"], "Alta")
        self.assertEqual(clasificar_eri(0.75)["etiqueta"], "Muy alta")
        self.assertEqual(clasificar_eri(1)["etiqueta"], "Muy alta")
        self.assertEqual(len(CLASES_ERI), 5)

    def test_valor_es_promedio_ponderado_transparente(self):
        componentes = {
            "integridad_estructural": 0.8,
            "conectividad": 0.4,
            "estabilidad_topografica": 0.6,
            "proximidad_riparia": 0.5,
        }
        self.assertAlmostEqual(calcular_valor_eri(componentes), 0.6)

    def test_resultado_identifica_limitante_y_no_cambia_prioridad(self):
        resumen = {
            "integridad_estructural": 0.8,
            "conectividad": 0.2,
            "estabilidad_topografica": 0.7,
            "proximidad_riparia": 0.6,
            "eri_muy_baja_ha": 2,
            "eri_baja_ha": 3,
            "eri_media_ha": 5,
            "eri_alta_ha": 7,
            "eri_muy_alta_ha": 11,
        }

        resultado = construir_resultado_eri(resumen)

        self.assertEqual(resultado["componente_limitante"], "conectividad")
        self.assertFalse(resultado["participa_en_prioridad"])
        self.assertEqual(
            sum(item["area_ha"] for item in resultado["distribucion_clases"]),
            28,
        )


if __name__ == "__main__":
    unittest.main()
