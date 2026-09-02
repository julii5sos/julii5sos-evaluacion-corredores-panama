# Sistema de diseño · Evaluación de Corredores Panamá

Este archivo adapta las recomendaciones de UI/UX al sistema institucional ya establecido por la aplicación de origen. La identidad existente prevalece sobre la paleta genérica sugerida por la herramienta.

## Principios

- Interfaz científica y guiada, con divulgación progresiva.
- Separar visualmente evidencia satelital, fuente cartográfica externa y cálculo propio.
- No depender solo del color: toda clase lleva etiqueta y explicación.
- Controles de al menos 44 px, foco visible y contraste WCAG AA.
- Sin desplazamiento horizontal a 375, 768, 1024 y 1440 px.
- Movimiento mínimo y desactivable con `prefers-reduced-motion`.

## Paleta institucional

| Rol | Valor |
|---|---|
| Verde principal | `#00544d` |
| Verde oscuro | `#00403a` |
| Acento | `#76b72a` |
| Fondo claro | `#f6faf8` |
| Superficie | `#ffffff` |
| Texto principal | `#00544d` |
| Texto secundario | `#356b61` |
| Borde | `#b6d1c8` |
| Error / alta atención | `#b42318` |
| Atención media | `#f79009` |

Los colores originales de Almanaque Azul (`#345a01`, `#a1d303`, `#e0c504`) solo se usan en sus capas y leyendas, acompañados siempre por las etiquetas Alta, Mediana y Media-baja.

## Tipografía y densidad

- Se conserva la tipografía nativa y accesible de Streamlit para evitar descargas externas y saltos de diseño.
- Texto base mínimo de 16 px en controles y lectura principal.
- Interlineado de 1.5 o mayor en textos explicativos.
- Escala de espacio: 4, 8, 16, 24, 32, 48 y 64 px.
- Tarjetas compactas, sin sombras decorativas; jerarquía mediante borde, espaciado y encabezados.

## Componentes

- Botón primario: fondo `#00544d`, texto blanco y foco de 3 px.
- Botón secundario: superficie blanca, borde `#00544d` y texto del mismo color.
- Resultados: métricas en cuadrícula adaptable; tablas con encabezados explícitos.
- Mapas: grupos independientes para capas temáticas, corredores externos, parches calculados y referencias.
- Alertas metodológicas: borde izquierdo de 4–5 px y texto que explique qué participa o no en el índice.

## Reglas de interacción

- El shapefile se configura dentro de un expander opcional para no bloquear el flujo principal.
- Los errores aparecen junto al archivo o campo que los produce.
- La aplicación nunca presenta `Alta/Media/Baja` de parches como si fueran las categorías de Almanaque Azul.
- Los enlaces de fuente permanecen visibles en resultados, metodología y atribuciones.

## Verificación previa a entrega

- [x] Foco visible y controles de 44 px.
- [x] `prefers-reduced-motion` respetado.
- [x] Sin desbordamiento horizontal a 375, 768 y 1440 px.
- [x] Leyendas con texto además de color.
- [x] Carga sin secretos produce un mensaje amigable, no un traceback público.
- [ ] Verificar el flujo completo con secretos válidos de Earth Engine en el entorno de despliegue.
- [ ] Verificar el shapefile nacional real y confirmar el campo/valor de bosque.
