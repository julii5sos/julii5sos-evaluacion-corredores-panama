import unittest
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import shapefile
from pyproj import CRS

from bosque_conectividad import (
    agregar_resultados_fragmentacion,
    analizar_fragmentacion_conectividad,
    analizar_fragmentacion_geojson,
    inspeccionar_shapefile,
)


def shapefile_sintetico():
    shp, shx, dbf = BytesIO(), BytesIO(), BytesIO()
    escritor = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    escritor.field("CLASE", "C", size=20)
    cuadrados = [
        (-80.000, 8.000, -79.999, 8.001),
        (-79.997, 8.000, -79.996, 8.001),
        (-79.970, 8.000, -79.969, 8.001),
    ]
    for oeste, sur, este, norte in cuadrados:
        escritor.poly(
            [[
                [oeste, sur],
                [oeste, norte],
                [este, norte],
                [este, sur],
                [oeste, sur],
            ]]
        )
        escritor.record("BOSQUE")
    escritor.close()

    salida = BytesIO()
    with ZipFile(salida, "w", ZIP_DEFLATED) as archivo:
        archivo.writestr("cobertura.shp", shp.getvalue())
        archivo.writestr("cobertura.shx", shx.getvalue())
        archivo.writestr("cobertura.dbf", dbf.getvalue())
        archivo.writestr("cobertura.prj", CRS.from_epsg(4326).to_wkt())
    return salida.getvalue()


class BosqueConectividadTests(unittest.TestCase):
    @staticmethod
    def aoi_sintetico():
        return {
            "type": "Polygon",
            "coordinates": [[
                [-80.01, 7.99],
                [-80.01, 8.02],
                [-79.95, 8.02],
                [-79.95, 7.99],
                [-80.01, 7.99],
            ]],
        }

    def test_inspeccion_y_red(self):
        datos = shapefile_sintetico()
        inspeccion = inspeccionar_shapefile(datos)
        self.assertEqual(inspeccion["numero_features"], 3)
        self.assertIn("CLASE", inspeccion["campos"])
        self.assertEqual(inspeccion["valores"]["CLASE"], ["BOSQUE"])

        resultado = analizar_fragmentacion_conectividad(
            datos_zip=datos,
            campo_clase="CLASE",
            valores_bosque=["BOSQUE"],
            aoi_geojson=self.aoi_sintetico(),
            umbral_m=500,
        )
        self.assertEqual(resultado["metricas_red"]["numero_nodos"], 3)
        self.assertEqual(resultado["metricas_red"]["numero_aristas"], 1)
        self.assertEqual(resultado["metricas_red"]["numero_componentes"], 2)
        self.assertGreater(resultado["metricas_clase"]["area_total_bosque_ha"], 0)
        self.assertEqual(len(resultado["parches_geojson"]["features"]), 3)

    def test_asset_geojson_preclasificado_no_requiere_campo_del_usuario(self):
        cuadrados = [
            (-80.000, 8.000, -79.999, 8.001),
            (-79.997, 8.000, -79.996, 8.001),
            (-79.970, 8.000, -79.969, 8.001),
        ]
        bosque = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [oeste, sur],
                            [oeste, norte],
                            [este, norte],
                            [este, sur],
                            [oeste, sur],
                        ]],
                    },
                }
                for oeste, sur, este, norte in cuadrados
            ],
        }
        resultado = analizar_fragmentacion_geojson(
            bosque_geojson=bosque,
            aoi_geojson=self.aoi_sintetico(),
            umbral_m=500,
        )

        self.assertEqual(resultado["metricas_red"]["numero_nodos"], 3)
        self.assertEqual(resultado["metricas_red"]["numero_aristas"], 1)
        self.assertEqual(resultado["metricas_red"]["numero_componentes"], 2)
        self.assertEqual(resultado["metricas_red"]["numero_parches_conectados"], 2)
        self.assertEqual(resultado["metricas_red"]["numero_parches_aislados"], 1)
        self.assertEqual(resultado["metricas_red"]["numero_brechas_potenciales"], 1)
        self.assertIsNone(resultado["campo_clase"])
        self.assertEqual(resultado["origen_datos"], "asset_institucional_earth_engine")
        self.assertEqual(len(resultado["conexiones_geojson"]["features"]), 1)
        self.assertEqual(
            resultado["conexiones_geojson"]["features"][0]["geometry"]["type"],
            "LineString",
        )
        self.assertLessEqual(
            resultado["conexiones_geojson"]["features"][0]["properties"]["distancia_m"],
            500,
        )
        self.assertEqual(len(resultado["conexiones_potenciales_geojson"]["features"]), 1)
        self.assertGreater(
            resultado["conexiones_potenciales_geojson"]["features"][0]["properties"][
                "distancia_m"
            ],
            500,
        )
        self.assertTrue(
            any(
                feature["properties"]["esta_aislado"]
                for feature in resultado["parches_geojson"]["features"]
            )
        )

        import folium

        capas = agregar_resultados_fragmentacion(folium.Map(), resultado)
        visibilidad = {capa.layer_name: capa.show for capa in capas}
        self.assertTrue(visibilidad["Bosque 2021 · fragmentos e importancia"])
        self.assertFalse(
            visibilidad["Relaciones cercanas entre fragmentos · opcional"]
        )
        self.assertFalse(visibilidad["Fragmentos separados · resaltar"])
        self.assertFalse(visibilidad["Separaciones potenciales · revisar"])

        capas_activadas = agregar_resultados_fragmentacion(
            folium.Map(),
            resultado,
            mostrar_conexiones=True,
            mostrar_brechas=True,
        )
        self.assertTrue(all(capa.show for capa in capas_activadas))

        capas_solo_separados = agregar_resultados_fragmentacion(
            folium.Map(),
            resultado,
            mostrar_parches=False,
            mostrar_brechas=True,
        )
        visibilidad_separados = {
            capa.layer_name: capa.show for capa in capas_solo_separados
        }
        self.assertFalse(
            visibilidad_separados["Bosque 2021 · fragmentos e importancia"]
        )
        self.assertTrue(
            visibilidad_separados["Fragmentos separados · resaltar"]
        )

    def test_asset_sin_bosque_devuelve_ceros(self):
        resultado = analizar_fragmentacion_geojson(
            bosque_geojson={"type": "FeatureCollection", "features": []},
            aoi_geojson=self.aoi_sintetico(),
        )

        self.assertEqual(resultado["metricas_clase"]["numero_parches"], 0)
        self.assertEqual(resultado["metricas_red"]["numero_nodos"], 0)
        self.assertEqual(resultado["conexiones_geojson"]["features"], [])
        self.assertEqual(resultado["conexiones_potenciales_geojson"]["features"], [])

    def test_resultado_considera_bosque_exterior_sin_dibujarlo(self):
        def poligono(oeste, sur, este, norte):
            return {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [oeste, sur],
                        [oeste, norte],
                        [este, norte],
                        [este, sur],
                        [oeste, sur],
                    ]],
                },
            }

        bosque = {
            "type": "FeatureCollection",
            "features": [
                poligono(-80.0000, 8.0000, -79.9990, 8.0010),
                poligono(-79.9970, 8.0000, -79.9960, 8.0010),
            ],
        }
        area = {
            "type": "Polygon",
            "coordinates": [[
                [-80.0002, 7.9998],
                [-80.0002, 8.0012],
                [-79.9988, 8.0012],
                [-79.9988, 7.9998],
                [-80.0002, 7.9998],
            ]],
        }

        resultado = analizar_fragmentacion_geojson(
            bosque_geojson=bosque,
            aoi_geojson=area,
            umbral_m=500,
            incluir_contexto_exterior=True,
        )

        self.assertTrue(resultado["considera_contexto_exterior"])
        self.assertEqual(resultado["metricas_red"]["numero_nodos"], 1)
        self.assertEqual(resultado["metricas_red"]["numero_parches_contexto"], 2)
        self.assertEqual(resultado["metricas_red"]["numero_parches_aislados"], 0)
        self.assertEqual(
            resultado["metricas_red"]["numero_conexiones_fuera_area"], 1
        )
        self.assertEqual(len(resultado["parches_geojson"]["features"]), 1)
        self.assertEqual(resultado["conexiones_geojson"]["features"], [])
        self.assertEqual(
            resultado["parches_geojson"]["features"][0]["properties"][
                "continua_fuera_area"
            ],
            "Sí",
        )


if __name__ == "__main__":
    unittest.main()
