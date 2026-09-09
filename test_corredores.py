import unittest

from corredores import (
    CATEGORIAS,
    analizar_interseccion_corredores,
    cargar_catalogo,
    cargar_corredores,
    cargar_puntos_criticos,
)
from scripts.preparar_datos_corredores import web_mercator_a_lon_lat


class CorredoresDatosTests(unittest.TestCase):
    def test_catalogo_conserva_conteos_y_categorias_originales(self):
        catalogo = cargar_catalogo()
        self.assertEqual(catalogo["corredores_poligonos"], 22)
        self.assertEqual(catalogo["puntos_criticos"], 14)
        self.assertEqual(set(catalogo["categorias_originales"]), set(CATEGORIAS))
        self.assertEqual(len(catalogo["tramos_mesoamericanos"]), 3)

    def test_geojson_preparados_estan_en_longitud_latitud(self):
        corredores = cargar_corredores()
        ojos = cargar_puntos_criticos()
        self.assertEqual(len(corredores["features"]), 22)
        self.assertEqual(len(ojos["features"]), 14)
        punto = ojos["features"][0]["geometry"]["coordinates"]
        self.assertGreaterEqual(punto[0], -84)
        self.assertLessEqual(punto[0], -76)
        self.assertGreaterEqual(punto[1], 5)
        self.assertLessEqual(punto[1], 11)

    def test_conversion_web_mercator(self):
        lon, lat = web_mercator_a_lon_lat([0, 0])
        self.assertAlmostEqual(lon, 0)
        self.assertAlmostEqual(lat, 0)

    def test_interseccion_nacional_incluye_tramos_mesoamericanos(self):
        aoi = {
            "type": "Polygon",
            "coordinates": [[
                [-84, 5],
                [-84, 11],
                [-76, 11],
                [-76, 5],
                [-84, 5],
            ]],
        }
        resultado = analizar_interseccion_corredores(aoi)
        self.assertTrue(resultado["intersecta"])
        self.assertTrue(resultado["intersecta_mesoamericano"])
        self.assertGreater(resultado["area_en_corredores_ha"], 0)
        self.assertEqual(len(resultado["corredores"]), 22)
        self.assertFalse(resultado["participa_indice_prioridad"])
        self.assertTrue(resultado["participa_prioridad_visita"])


if __name__ == "__main__":
    unittest.main()
