import unittest

from reporte_cartografico import crear_mapa_conectividad, crear_mapa_fragmentacion


class ReporteCartograficoTests(unittest.TestCase):
    @staticmethod
    def resultados_sinteticos():
        poligono_area = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-80, 8], [-80, 8.02], [-79.96, 8.02], [-79.96, 8], [-80, 8]]],
                    },
                }
            ],
        }
        parches = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"prioridad_conectividad": prioridad},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[oeste, 8.005], [oeste, 8.015], [este, 8.015], [este, 8.005], [oeste, 8.005]]],
                    },
                }
                for oeste, este, prioridad in [
                    (-79.995, -79.988, "Alta"),
                    (-79.983, -79.976, "Media"),
                    (-79.971, -79.964, "Baja"),
                ]
            ],
        }
        linea = lambda x1, x2: {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"type": "LineString", "coordinates": [[x1, 8.01], [x2, 8.01]]},
                }
            ],
        }
        return {
            "area_objetivo_geojson": poligono_area,
            "parches_geojson": parches,
            "conexiones_geojson": linea(-79.988, -79.983),
            "conexiones_potenciales_geojson": linea(-79.976, -79.971),
            "ruta_corredor_geojson": linea(-79.964, -79.958),
            "corredor_referencia_geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"nombre": "Corredor de prueba"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-79.958, 8.004], [-79.958, 8.016], [-79.95, 8.016], [-79.95, 8.004], [-79.958, 8.004]]],
                        },
                    }
                ],
            },
        }

    def test_crea_dos_mapas_vectoriales_sin_basemap(self):
        datos = self.resultados_sinteticos()
        fragmentacion = crear_mapa_fragmentacion(datos)
        conectividad = crear_mapa_conectividad(datos)

        self.assertGreater(len(fragmentacion.contents), 5)
        self.assertGreater(len(conectividad.contents), len(fragmentacion.contents))
        self.assertFalse(hasattr(fragmentacion, "imageWidth"))
        self.assertFalse(hasattr(conectividad, "imageWidth"))


if __name__ == "__main__":
    unittest.main()
