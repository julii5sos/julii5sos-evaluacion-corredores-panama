import unittest
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import shapefile
from pyproj import CRS

from bosque_conectividad import (
    analizar_fragmentacion_conectividad,
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
    def test_inspeccion_y_red(self):
        datos = shapefile_sintetico()
        inspeccion = inspeccionar_shapefile(datos)
        self.assertEqual(inspeccion["numero_features"], 3)
        self.assertIn("CLASE", inspeccion["campos"])
        self.assertEqual(inspeccion["valores"]["CLASE"], ["BOSQUE"])

        aoi = {
            "type": "Polygon",
            "coordinates": [[
                [-80.01, 7.99],
                [-80.01, 8.02],
                [-79.95, 8.02],
                [-79.95, 7.99],
                [-80.01, 7.99],
            ]],
        }
        resultado = analizar_fragmentacion_conectividad(
            datos_zip=datos,
            campo_clase="CLASE",
            valores_bosque=["BOSQUE"],
            aoi_geojson=aoi,
            umbral_m=500,
        )
        self.assertEqual(resultado["metricas_red"]["numero_nodos"], 3)
        self.assertEqual(resultado["metricas_red"]["numero_aristas"], 1)
        self.assertEqual(resultado["metricas_red"]["numero_componentes"], 2)
        self.assertGreater(resultado["metricas_clase"]["area_total_bosque_ha"], 0)
        self.assertEqual(len(resultado["parches_geojson"]["features"]), 3)


if __name__ == "__main__":
    unittest.main()
