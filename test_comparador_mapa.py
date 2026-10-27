import unittest

import folium

from comparador_mapa import (
    ComparadorCapasSincronizadas,
    opciones_interaccion_mapa,
)


class ComparadorMapaTests(unittest.TestCase):
    def crear_mapa(self):
        mapa = folium.Map(location=[8.7, -80.0], tiles=None, zoom_start=8)
        izquierda = folium.TileLayer(
            "OpenStreetMap",
            name="Año inicial",
            control=False,
        ).add_to(mapa)
        derecha = folium.TileLayer(
            tiles=(
                "https://server.arcgisonline.com/ArcGIS/rest/services/"
                "World_Imagery/MapServer/tile/{z}/{y}/{x}"
            ),
            attr="Esri",
            name="Año final",
            control=False,
        ).add_to(mapa)
        ComparadorCapasSincronizadas(izquierda, derecha).add_to(mapa)
        return mapa

    def test_comparador_actualiza_recorte_en_zoom_movimiento_y_redimension(self):
        html = self.crear_mapa().get_root().render()

        self.assertIn("zoomstart zoom zoomend move moveend resize viewreset", html)
        self.assertIn("enterFullscreen exitFullscreen", html)
        self.assertIn("requestAnimationFrame", html)
        self.assertIn("ResizeObserver", html)
        self.assertIn("._updateClip()", html)
        self.assertIn("loading load tileload", html)

    def test_divisor_es_accesible_y_no_interfiere_con_el_mapa(self):
        html = self.crear_mapa().get_root().render()

        self.assertIn("Mover el divisor para comparar", html)
        self.assertIn("disableClickPropagation", html)
        self.assertIn("disableScrollPropagation", html)
        self.assertIn("ew-resize", html)
        self.assertIn("touchAction", html)
        self.assertIn("height = '44px'", html)
        self.assertIn("marginTop = '-22px'", html)
        self.assertIn("pointerEvents = 'auto'", html)

    def test_comparador_desactiva_solo_las_animaciones_intermedias(self):
        self.assertEqual(
            opciones_interaccion_mapa(True),
            {
                "zoom_animation": False,
                "fade_animation": False,
                "marker_zoom_animation": False,
            },
        )
        self.assertEqual(
            opciones_interaccion_mapa(False),
            {
                "zoom_animation": True,
                "fade_animation": True,
                "marker_zoom_animation": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
