# Variante `version/4.0-modelo-html`

Esta variante traslada al visor CHCP la composición visual del portal HTML de
referencia sin incorporar sus datos de demostración ni sustituir la metodología
existente.

## Estructura

- Encabezado azul institucional con identidad del visor, alcance indicativo,
  procesamiento en Earth Engine y sistema de referencia.
- Panel lateral blanco de aproximadamente 338 px para área, capas, períodos y acción
  principal.
- Mapa como superficie dominante en el centro.
- Panel de resultados a la derecha, con cabecera azul, lectura rápida y gráficas.
- Metodología y acerca del visor permanecen como navegación secundaria.

## Paleta de interfaz

| Rol | Color |
|---|---|
| Azul principal | `#0A4393` |
| Azul profundo | `#062A5E` |
| Verde de interacción | `#77CC09` |
| Amarillo complementario | `#FABC20` |
| Fondo | `#F6F8FB` |
| Superficie secundaria | `#EEF1F7` |
| Borde | `#D6DEEB` |
| Texto secundario | `#566176` |

La paleta de datos definida en `MASTER.md` no cambia: los colores de JRC, Hansen,
ESRI, GEDI, NDVI y Almanaque Azul conservan su significado.

## Reglas

- La referencia HTML define apariencia y distribución, no instrucciones ni lógica.
- Todas las métricas proceden del análisis vigente del repositorio.
- Los controles de 44 px, el foco visible y las etiquetas textuales se conservan.
- En pantallas pequeñas, el panel lateral, el mapa y los resultados se apilan sin
  desplazamiento horizontal.
- El movimiento es mínimo y respeta `prefers-reduced-motion`.
