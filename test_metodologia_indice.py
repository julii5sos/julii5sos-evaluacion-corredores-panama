import unittest

from metodologia_indice import (
    CLASES_VIGOR_NDVI,
    PERIODOS_ANALISIS,
    PESOS_INDICE,
    PUNTAJE_MAXIMO,
    REGLAS_MAPA_COINCIDENCIA,
    calcular_indice_prioridad,
    evaluar_consistencia,
    evaluar_senales,
)


class IndicePrioridadTest(unittest.TestCase):
    def calcular(self, tmf=False, hansen=False, esri=False, gedi=False):
        return calcular_indice_prioridad(
            senal_tmf=tmf,
            senal_hansen=hansen,
            senal_esri=esri,
            senal_gedi=gedi,
        )

    def test_pesos_metodologicos(self):
        self.assertEqual(PESOS_INDICE["tmf"], 2.0)
        self.assertEqual(PESOS_INDICE["hansen"], 2.0)
        self.assertEqual(PESOS_INDICE["esri"], 1.5)
        self.assertEqual(PESOS_INDICE["gedi"], 0.5)
        self.assertEqual(PESOS_INDICE["ndvi"], 0.0)
        self.assertEqual(PUNTAJE_MAXIMO, 6.0)

    def test_periodos_del_diagnostico_son_fijos(self):
        self.assertEqual(PERIODOS_ANALISIS["referencia"], 2025)
        self.assertEqual(PERIODOS_ANALISIS["jrc_diagnostico"], 2025)
        self.assertEqual(PERIODOS_ANALISIS["hansen_diagnostico"], 2025)
        self.assertEqual(PERIODOS_ANALISIS["esri_inicial"], 2017)
        self.assertEqual(PERIODOS_ANALISIS["esri_final"], 2024)
        self.assertEqual(PERIODOS_ANALISIS["ndvi_final_visual"], 2025)

    def test_mapa_coincidencia_es_indicativo_y_no_cambia_indice(self):
        self.assertEqual(REGLAS_MAPA_COINCIDENCIA["malla_referencia_m"], 30)
        self.assertEqual(
            set(REGLAS_MAPA_COINCIDENCIA["fuentes"]),
            {"jrc", "hansen", "esri"},
        )
        self.assertEqual(
            set(REGLAS_MAPA_COINCIDENCIA["clases"]),
            {1, 2, 3},
        )
        self.assertFalse(REGLAS_MAPA_COINCIDENCIA["participa_indice"])
        for clase in REGLAS_MAPA_COINCIDENCIA["clases"].values():
            self.assertRegex(clase["color"], r"^#[0-9A-Fa-f]{6}$")
            self.assertTrue(clase["etiqueta"])
            self.assertTrue(clase["interpretacion"])
        self.assertEqual(PUNTAJE_MAXIMO, 6.0)

    def test_escala_ndvi_documenta_cinco_intervalos(self):
        self.assertEqual(len(CLASES_VIGOR_NDVI), 5)
        self.assertEqual(
            [clase["rango"] for clase in CLASES_VIGOR_NDVI],
            [
                "NDVI < 0",
                "0.0 ≤ NDVI < 0.2",
                "0.2 ≤ NDVI < 0.4",
                "0.4 ≤ NDVI < 0.6",
                "NDVI ≥ 0.6",
            ],
        )
        for clase in CLASES_VIGOR_NDVI:
            self.assertTrue(clase["etiqueta"])
            self.assertTrue(clase["interpretacion"])
            self.assertRegex(clase["color"], r"^#[0-9A-Fa-f]{6}$")

    def test_esri_no_supera_fuentes_forestales(self):
        aportes_esri, puntaje_esri, prioridad_esri = self.calcular(esri=True)
        _, puntaje_tmf, _ = self.calcular(tmf=True)
        _, puntaje_hansen, _ = self.calcular(hansen=True)

        self.assertEqual(aportes_esri["esri"], 1.5)
        self.assertEqual(aportes_esri["ndvi"], 0.0)
        self.assertEqual(puntaje_esri, 1.5)
        self.assertEqual(prioridad_esri, "Media")
        self.assertLess(puntaje_esri, puntaje_tmf)
        self.assertLess(puntaje_esri, puntaje_hansen)

    def test_cada_fuente_se_suma_una_sola_vez(self):
        aportes, puntaje, prioridad = self.calcular(
            tmf=True,
            hansen=True,
            esri=True,
            gedi=True,
        )

        self.assertEqual(aportes, PESOS_INDICE)
        self.assertEqual(puntaje, 6.0)
        self.assertEqual(prioridad, "Alta")

    def test_gedi_solo_genera_prioridad_preventiva(self):
        _, puntaje, prioridad = self.calcular(gedi=True)
        self.assertEqual(puntaje, 0.5)
        self.assertEqual(prioridad, "Preventiva")

    def test_sin_senales_la_prioridad_es_baja(self):
        aportes, puntaje, prioridad = self.calcular()
        self.assertTrue(all(valor == 0.0 for valor in aportes.values()))
        self.assertEqual(puntaje, 0.0)
        self.assertEqual(prioridad, "Baja")

    def evaluar(self, **cambios):
        valores = {
            "tmf_deforestacion_ha": 0.0,
            "tmf_deforestacion_pct": 0.0,
            "tmf_degradacion_ha": 0.0,
            "tmf_degradacion_pct": 0.0,
            "hansen_post_2020_ha": 0.0,
            "esri_salida_arboles_ha": 0.0,
            "esri_salida_arboles_pct": 0.0,
            "gedi_altura_media_m": 20.0,
            "gedi_cobertura_valida_pct": 100.0,
            "linea_base_arborea_pct": 100.0,
        }
        valores.update(cambios)
        return evaluar_senales(**valores)

    def test_esri_exige_extension_y_porcentaje(self):
        senales, _ = self.evaluar(
            esri_salida_arboles_ha=0.10,
            esri_salida_arboles_pct=4.9,
        )
        self.assertFalse(senales["esri"])

        senales, _ = self.evaluar(
            esri_salida_arboles_ha=0.09,
            esri_salida_arboles_pct=5.0,
        )
        self.assertFalse(senales["esri"])

        senales, _ = self.evaluar(
            esri_salida_arboles_ha=0.10,
            esri_salida_arboles_pct=5.0,
        )
        self.assertTrue(senales["esri"])

    def test_jrc_admite_umbral_absoluto_o_relativo(self):
        senales, _ = self.evaluar(tmf_deforestacion_pct=1.0)
        self.assertTrue(senales["tmf"])

        senales, _ = self.evaluar(tmf_degradacion_ha=2.0)
        self.assertTrue(senales["tmf"])

    def test_gedi_requiere_los_tres_criterios(self):
        senales, disponible = self.evaluar(
            gedi_altura_media_m=7.9,
            gedi_cobertura_valida_pct=20.0,
            linea_base_arborea_pct=10.0,
        )
        self.assertTrue(disponible)
        self.assertTrue(senales["gedi"])

        senales, disponible = self.evaluar(
            gedi_altura_media_m=7.9,
            gedi_cobertura_valida_pct=19.9,
            linea_base_arborea_pct=10.0,
        )
        self.assertFalse(disponible)
        self.assertFalse(senales["gedi"])

    def consistencia(self, **cambios):
        valores = {
            "senal_tmf": False,
            "senal_hansen": False,
            "senal_esri": False,
            "tmf_recuperacion_ha": 0.0,
            "tmf_recuperacion_pct": 0.0,
            "esri_ganancia_arboles_ha": 0.0,
            "esri_ganancia_arboles_pct": 0.0,
        }
        valores.update(cambios)
        return evaluar_consistencia(**valores)

    def test_consistencia_alta_requiere_tres_fuentes(self):
        resultado = self.consistencia(
            senal_tmf=True,
            senal_hansen=True,
            senal_esri=True,
        )
        self.assertEqual(resultado["nivel"], "Alta consistencia")
        self.assertEqual(len(resultado["fuentes_deterioro"]), 3)

    def test_consistencia_parcial_requiere_dos_fuentes(self):
        resultado = self.consistencia(senal_tmf=True, senal_esri=True)
        self.assertEqual(resultado["nivel"], "Consistencia parcial")

    def test_lectura_mixta_no_compensa_deterioro_y_ganancia(self):
        resultado = self.consistencia(
            senal_tmf=True,
            esri_ganancia_arboles_ha=0.10,
            esri_ganancia_arboles_pct=5.0,
        )
        self.assertEqual(resultado["nivel"], "Lectura mixta")
        self.assertTrue(resultado["fuentes_deterioro"])
        self.assertTrue(resultado["fuentes_recuperacion"])

    def test_ganancia_aislada_exige_umbral_completo(self):
        resultado = self.consistencia(
            senal_tmf=True,
            esri_ganancia_arboles_ha=0.10,
            esri_ganancia_arboles_pct=4.9,
        )
        self.assertEqual(resultado["nivel"], "Sin señal consistente")


if __name__ == "__main__":
    unittest.main()
