"""Comportamiento cartográfico para el comparador y el área seleccionada."""

from branca.element import MacroElement, Template
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


class RotulosComparadorFijos(MacroElement):
    """Mantiene los años visibles aunque el usuario acerque o desplace el mapa."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
            var {{ this.get_name() }}_mapa = {{ this._parent.get_name() }};
            var {{ this.get_name() }}_contenedor = L.DomUtil.create(
                'div',
                'rotulos-comparador-fijos',
                {{ this.get_name() }}_mapa.getContainer()
            );
            {{ this.get_name() }}_contenedor.setAttribute('role', 'group');
            {{ this.get_name() }}_contenedor.setAttribute(
                'aria-label',
                'Años visibles en el comparador'
            );
            Object.assign({{ this.get_name() }}_contenedor.style, {
                position: 'absolute',
                top: '12px',
                left: '58px',
                right: '12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                gap: '12px',
                pointerEvents: 'none',
                zIndex: '800'
            });

            var {{ this.get_name() }}_crear_rotulo = function (titulo, valor, alineacion) {
                var rotulo = L.DomUtil.create('div', '', {{ this.get_name() }}_contenedor);
                var encabezado = L.DomUtil.create('div', '', rotulo);
                var dato = L.DomUtil.create('strong', '', rotulo);
                encabezado.textContent = titulo;
                dato.textContent = valor;
                Object.assign(rotulo.style, {
                    boxSizing: 'border-box',
                    maxWidth: '44%',
                    padding: '7px 10px',
                    color: 'white',
                    background: 'rgba(17,50,74,.92)',
                    border: '2px solid white',
                    borderRadius: '6px',
                    boxShadow: '0 2px 7px rgba(0,0,0,.35)',
                    font: '12px Arial,sans-serif',
                    lineHeight: '1.25',
                    textAlign: alineacion
                });
                Object.assign(encabezado.style, {
                    fontSize: '10px',
                    letterSpacing: '.02em'
                });
                dato.style.display = 'block';
                dato.style.marginTop = '2px';
            };

            {{ this.get_name() }}_crear_rotulo(
                'AÑO INICIAL',
                {{ this.etiqueta_inicial | tojson }},
                'left'
            );
            {{ this.get_name() }}_crear_rotulo(
                'AÑO FINAL',
                {{ this.etiqueta_final | tojson }},
                'right'
            );
        {% endmacro %}
        """
    )

    def __init__(self, etiqueta_inicial, etiqueta_final):
        super().__init__()
        self._name = "RotulosComparadorFijos"
        self.etiqueta_inicial = str(etiqueta_inicial)
        self.etiqueta_final = str(etiqueta_final)


class NavegacionAcotadaAlArea(MacroElement):
    """Evita perder el área de interés al navegar con zoom o desplazamiento."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
            var {{ this.get_name() }}_mapa = {{ this._parent.get_name() }};
            var {{ this.get_name() }}_area = L.latLngBounds(
                [{{ this.sur }}, {{ this.oeste }}],
                [{{ this.norte }}, {{ this.este }}]
            );
            var {{ this.get_name() }}_navegacion =
                {{ this.get_name() }}_area.pad({{ this.margen }});

            {{ this.get_name() }}_mapa.setMaxBounds(
                {{ this.get_name() }}_navegacion
            );
            {{ this.get_name() }}_mapa.options.maxBoundsViscosity = 0.9;
            {{ this.get_name() }}_mapa.on('zoomend resize', function () {
                {{ this.get_name() }}_mapa.panInsideBounds(
                    {{ this.get_name() }}_navegacion,
                    {animate: false}
                );
            });
        {% endmacro %}
        """
    )

    def __init__(self, limites, margen=0.5):
        super().__init__()
        self._name = "NavegacionAcotadaAlArea"
        (sur, oeste), (norte, este) = limites
        self.sur = float(sur)
        self.oeste = float(oeste)
        self.norte = float(norte)
        self.este = float(este)
        self.margen = float(margen)
