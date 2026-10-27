"""Comparador cartográfico sincronizado para capas ráster de Leaflet."""

from branca.element import Template
from folium.plugins import SideBySideLayers


def opciones_interaccion_mapa(comparador_activo):
    """Evita transformaciones animadas que desincronicen el recorte del comparador."""

    animaciones_activas = not comparador_activo
    return {
        "zoom_animation": animaciones_activas,
        "fade_animation": animaciones_activas,
        "marker_zoom_animation": animaciones_activas,
    }


class ComparadorCapasSincronizadas(SideBySideLayers):
    """Actualiza el divisor durante zoom, desplazamiento y cambios de tamaño.

    ``leaflet-side-by-side`` ya escucha el evento ``move``, pero dentro de un
    componente embebido el tamaño del mapa y las transformaciones de zoom pueden
    cambiar entre cuadros. Esta variante solicita de nuevo el recorte en cada fase
    relevante y después de que terminan de cargar los mosaicos.
    """

    _template = Template(
        """
        {% macro script(this, kwargs) %}
            var {{ this.get_name() }} = L.control.sideBySide(
                {{ this.layer_left.get_name() }},
                {{ this.layer_right.get_name() }},
                {padding: 12}
            ).addTo({{ this._parent.get_name() }});

            var {{ this.get_name() }}_actualizacion_pendiente = false;
            var {{ this.get_name() }}_sincronizar = function () {
                if (
                    {{ this.get_name() }}_actualizacion_pendiente ||
                    !{{ this.get_name() }}._map
                ) {
                    return;
                }
                {{ this.get_name() }}_actualizacion_pendiente = true;
                window.requestAnimationFrame(function () {
                    {{ this.get_name() }}_actualizacion_pendiente = false;
                    if ({{ this.get_name() }}._map) {
                        {{ this.get_name() }}._updateClip();
                    }
                });
            };

            {{ this._parent.get_name() }}.on(
                'zoomstart zoom zoomend move moveend resize viewreset '
                + 'enterFullscreen exitFullscreen',
                {{ this.get_name() }}_sincronizar
            );
            {{ this.layer_left.get_name() }}.on(
                'loading load tileload',
                {{ this.get_name() }}_sincronizar
            );
            {{ this.layer_right.get_name() }}.on(
                'loading load tileload',
                {{ this.get_name() }}_sincronizar
            );

            if (window.ResizeObserver) {
                var {{ this.get_name() }}_observador = new ResizeObserver(
                    {{ this.get_name() }}_sincronizar
                );
                {{ this.get_name() }}_observador.observe(
                    {{ this._parent.get_name() }}.getContainer()
                );
            }

            L.DomEvent.disableClickPropagation({{ this.get_name() }}._container);
            L.DomEvent.disableScrollPropagation({{ this.get_name() }}._container);
            {{ this.get_name() }}._range.setAttribute(
                'aria-label',
                'Mover el divisor para comparar el año inicial y el año final'
            );
            {{ this.get_name() }}._range.setAttribute(
                'title',
                'Arrastre para comparar los dos años'
            );
            {{ this.get_name() }}._range.style.cursor = 'ew-resize';
            {{ this.get_name() }}._range.style.touchAction = 'none';
            {{ this.get_name() }}._range.style.height = '44px';
            {{ this.get_name() }}._range.style.marginTop = '-22px';
            {{ this.get_name() }}._range.style.pointerEvents = 'auto';
            {{ this.get_name() }}._range.style.zIndex = '1000';

            window.setTimeout({{ this.get_name() }}_sincronizar, 0);
            window.setTimeout({{ this.get_name() }}_sincronizar, 250);
        {% endmacro %}
        """
    )
