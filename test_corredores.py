import unittest

from corredores import (
    CATEGORIAS,
    agregar_capas_corredores,
    analizar_interseccion_corredores,
    calcular_radio_contexto,
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
        self.assertEqual(resultado["distancia_corredor_mas_cercano_m"], 0.0)

    def test_no_serializa_corredores_si_las_capas_estan_apagadas(self):
        import folium

        mapa = folium.Map()
        capas = agregar_capas_corredores(
            mapa,
            mostrar=False,
            mostrar_puntos_criticos=False,
        )
        html = mapa.get_root().render()

        self.assertEqual(capas, [])
        self.assertNotIn("Conectividad alta · Almanaque Azul", html)
        self.assertLess(len(html), 10_000)

    def test_contexto_se_adapta_a_la_distancia_del_corredor(self):
        self.assertEqual(calcular_radio_contexto(0, 500), 500)
        self.assertEqual(calcular_radio_contexto(1_200, 500), 1_700)
        self.assertEqual(calcular_radio_contexto(9_000, 500), 5_000)
        self.assertEqual(calcular_radio_contexto(None, 500), 5_000)

    def test_acepta_area_como_geometry_collection(self):
        poligono = {
            "type": "Polygon",
            "coordinates": [[
                [-80.02, 8.98],
                [-80.02, 9.02],
                [-79.98, 9.02],
                [-79.98, 8.98],
                [-80.02, 8.98],
            ]],
        }
        area_compuesta = {
            "type": "GeometryCollection",
            "geometries": [poligono],
        }

        resultado = analizar_interseccion_corredores(area_compuesta)

        self.assertGreater(resultado["area_aoi_ha"], 0)


if __name__ == "__main__":
    unittest.main()
