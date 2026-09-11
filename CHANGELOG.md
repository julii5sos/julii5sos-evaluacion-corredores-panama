# Historial de versiones

Este historial documenta la evolución de la aplicación UX. Las versiones siguen
el formato `MAJOR.MINOR.PATCH`: una versión principal, mejoras compatibles y
correcciones compatibles, respectivamente.

## [0.8.0] - 2026-09-10 — versión actual

### Red legible y conexión potencial hacia un corredor

- Mantiene todas las relaciones entre fragmentos para las métricas, pero muestra en el mapa solo la estructura mínima necesaria de cada grupo.
- Sustituye las líneas radiales entre puntos interiores por segmentos entre los bordes más próximos de los fragmentos.
- Añade un halo blanco y un trazo institucional oscuro para que los enlaces sigan siendo visibles sobre la imagen satelital.
- Busca en un entorno de 5 km una cadena estructural hacia un corredor publicado, exigiendo que cada salto respete la distancia seleccionada.
- Prefiere corredores de categoría original alta, luego mediana y media-baja, y muestra una sola ruta naranja para evitar ruido visual.
- Usa la ruta para orientar la revisión, sin añadir puntos ni presentarla como movimiento de fauna o conectividad funcional confirmada.

## [0.7.1] - 2026-09-10

### Contexto exterior sin ampliar el mapa ni las hectáreas

- Evalúa la conectividad con un entorno exterior igual a la distancia seleccionada.
- Mantiene las geometrías visibles y las hectáreas reportadas dentro del polígono original.
- Evita clasificar como separado un fragmento que continúa o se conecta con bosque exterior.
- Indica en cada fragmento si existe continuidad o una conexión fuera del área.
- La capa opcional resalta los fragmentos realmente separados y muestra su distancia al vecino.

## [0.7.0] - 2026-09-10

### Lectura guiada y mapa sin ruido visual

- Sustituye los términos principales de red por explicaciones sobre fragmentos cercanos o separados.
- Presenta primero cuatro indicadores comprensibles y una lectura rápida en lenguaje cotidiano.
- Conserva métricas, tablas y descargas técnicas dentro de una sección opcional cerrada.
- Traslada la activación de capas satelitales, bosque, relaciones y corredores al panel lateral.
- Elimina los controles flotantes superpuestos que cubrían el mapa y mantiene la leyenda fuera del área cartográfica.
- Muestra los fragmentos de bosque con menor opacidad y deja apagadas por defecto las relaciones y separaciones potenciales.
- Simplifica los textos emergentes para que indiquen área, valor relativo y condición de separación.

## [0.6.1] - 2026-09-09

### Red de conectividad visible y descargable

- Dibuja en el mapa las conexiones entre parches que cumplen el umbral seleccionado.
- Identifica los parches aislados y propone una línea discontinua a su vecino más cercano como brecha para revisión, no como corredor confirmado.
- Separa los controles de parches, conexiones y brechas potenciales para evitar ruido visual.
- Añade métricas de parches conectados y aislados, distancias de las aristas y componentes de red.
- Permite descargar los parches y la red de conectividad en GeoJSON.
- Mantiene Earth Engine como fuente oficial; no usa la copia nacional simplificada porque su integridad espacial no está validada.

## [0.6.0] - 2026-09-08

### Cobertura de bosque automática

- Elimina el cargador de shapefiles de la interfaz pública.
- Lee el recorte forestal 2021 desde un asset institucional privado de Earth Engine.
- Filtra automáticamente la categoría oficial `Bosques y Otras Tierras Boscosas` de la capa nacional; el usuario no selecciona clases.
- Recorta automáticamente la cobertura al área seleccionada antes de calcular fragmentación y conectividad.
- Mantiene configurables únicamente la distancia entre parches y el área mínima, como opciones de análisis.
- Distingue correctamente un recorte sin bosque de un paisaje formado por un solo parche.
- Documenta el secreto `EE_ASSET_BOSQUE_2021` y el flujo de publicación administrado.
- Coloca el mapa interactivo inmediatamente después de ejecutar el análisis, antes de las tablas y descargas.

## [0.5.0] - 2026-09-08

### Diagnóstico territorial integrado

- Conecta cambios recientes, corredores y estructura del bosque 2021 en una sola lectura operativa.
- Mantiene el puntaje trazable: los cambios determinan urgencia y los corredores aportan valor estratégico.
- Usa la fragmentación y la red de parches para focalizar la visita sin asignar un peso ecológico no calibrado.
- Presenta cuatro resultados coordinados: urgencia, valor del corredor, condición estructural y prioridad final.
- Lleva la combinación territorial y el foco de visita al mapa, al informe PDF y al registro metodológico JSON.
- Activa automáticamente los corredores en el perfil **Diagnóstico territorial integrado** y reduce las capas iniciales para evitar ruido visual.

## [0.4.0] - 2026-09-08

### Prioridad integrada de visita

- Conserva sin cambios el índice satelital de 0 a 6 puntos y lo presenta como urgencia por cambios.
- Añade hasta 1 punto según la proporción del área dentro de corredores y 0.5 por intersección con el Corredor Biológico Mesoamericano.
- Presenta por separado la urgencia por cambios, el valor estratégico del corredor y la prioridad final de visita.
- Impide que la presencia de un corredor, sin señales suficientes de cambio, genere por sí sola una prioridad alta.
- Incorpora la prioridad de visita en la interfaz, el PDF y el registro metodológico JSON.
- Identifica la cobertura usada para fragmentación como **SINIA–MiAMBIENTE, Bosque y otros usos, 2021**, y separa este corte de cobertura de las series anuales de cambio.

## [0.3.0] - 2026-09-01

### Corredores y conectividad

- Integra los corredores y puntos críticos publicados por Fundación Almanaque Azul.
- Conserva las categorías originales alta, mediana y media-baja y destaca los tramos mesoamericanos oeste, San Lorenzo y este.
- Calcula la intersección del área evaluada con corredores sin alterar el índice satelital.
- Permite cargar temporalmente un shapefile bosque/no bosque y reproducir métricas de fragmentación y conectividad de los ejercicios R.
- Añade resultados contextuales a la interfaz, el PDF y el registro metodológico JSON.
- Separa visual y metodológicamente las categorías externas de Almanaque Azul y los cuantiles internos del índice conector de parches.

## [0.2.10] - 2026-08-03

### Proyección explícita para mosaicos de Earth Engine

- Los mosaicos JRC TMF y ESRI conservan la proyección nativa de su primera
  imagen antes de cualquier operación espacial.
- La señal ESRI establece nuevamente esa proyección antes de ejecutar
  `reduceResolution`, evitando el error de proyección predeterminada inválida.
- El índice, sus pesos, umbrales y períodos metodológicos no cambian.

## [0.2.9] - 2026-08-03

### Vistas y períodos comprensibles

- Se eliminaron las etiquetas que presentaban JRC como vista recomendada frente a
  ESRI; las cuatro opciones principales ahora describen acciones neutrales.
- **Consultar capas individuales** pasó al selector principal y permite elegir un
  solo año para JRC, ESRI o NDVI sin activar el comparador.
- Los barridos de JRC, ESRI y NDVI quedaron como tres opciones independientes con
  selección explícita de año inicial y final.
- El orden de las capas y la capa visible al abrir continúan disponibles, pero en
  un panel secundario que no interfiere con la selección principal.
- La interfaz y la documentación distinguen el comparador JRC 2020-2025 del
  diagnóstico JRC 2025, la pérdida Hansen 2021-2025 y la transición ESRI 2017-2024.

## [0.2.8] - 2026-08-01

### Comparador y explorador de capas independientes

- La visualización personalizada separa **Comparar años** de **Explorar capas**,
  evitando que el barrido temporal cubra GEDI, Hansen, JRC, ESRI o NDVI.
- El comparador admite JRC TMF, ESRI LULC y clases de vigor NDVI; sus años son
  exclusivamente visuales y no alteran el diagnóstico.
- El explorador permite encender varias capas, conservarlas disponibles y
  ordenarlas de arriba hacia abajo mediante controles explícitos.
- Las capas utilizan niveles de dibujo estables y los límites de referencia
  permanecen por encima de la información temática.
- Se reforzó el estilo del botón primario para mantener texto blanco en las
  versiones actuales de Streamlit.
- La portada incorpora una explicación en lenguaje sencillo para personas sin
  conocimientos de sistemas de información geográfica.

## [0.2.7] - 2026-07-24

### Séptimo mapa de orientación espacial

- Se incorporó **Sectores que requieren revisión**, un mapa que suma las señales
  espaciales de JRC TMF 2025, Hansen posterior a 2020 y ESRI 2017-2024.
- Las tres fuentes se estandarizan en la malla JRC de 30 m y se muestran como
  señal de una fuente, coincidencia de dos fuentes o coincidencia de tres fuentes.
- La lectura rápida, el PDF y el registro metodológico informan las hectáreas de
  cada clase y priorizan las coincidencias de dos o tres fuentes.
- GEDI y NDVI no participan en la superposición. El séptimo mapa no modifica el
  índice ponderado ni constituye evidencia causal o una determinación EUDR.

## [0.2.6] - 2026-07-24

### Identidad visual Natura Panamá

- La interfaz adopta el verde institucional `#00544D` de Natura Panamá para
  títulos, texto principal, controles y enlaces.
- El texto secundario utiliza un verde complementario de alto contraste y el
  verde `#76B72A` queda reservado para acentos y subrayados.
- La configuración global de Streamlit aplica la misma identidad cromática a
  los widgets nativos, la barra lateral y ambas entradas de la aplicación.
- Los colores científicos de las capas, las prioridades y los avisos
  semánticos se conservan para no alterar su interpretación.

## [0.2.5] - 2026-07-24

### Claridad entre cálculo y visualización

- El paso 2 se presenta como **Vista inicial de los mapas** y deja de prometer
  que la opción seleccionada cambia el método analítico.
- Todas las vistas ejecutan el mismo cálculo; únicamente determinan qué
  comparador y qué capas aparecen primero.
- Los selectores de años se identifican como controles exclusivamente visuales.
- Los períodos del diagnóstico quedaron centralizados y fijos: referencia 2025,
  JRC 2025, Hansen 2025 y ESRI 2017-2024 por ser la última serie disponible.
- El registro metodológico separa los períodos fijos del diagnóstico de los años
  elegidos para la visualización.

## [0.2.4] - 2026-07-24

### Control de capas del mapa

- Las capas temáticas funcionan como opciones exclusivas: al seleccionar una,
  la anterior se apaga automáticamente.
- Se añadió la opción **Sin capa temática** para volver a la imagen satelital
  sin superposiciones.
- El límite de la cuenca y el área seleccionada permanecen en un grupo de
  referencias independiente.
- La configuración avanzada ahora aclara que allí se eligen las capas
  disponibles, mientras que dentro del mapa se visualiza una temática a la vez.

## [0.2.3] - 2026-07-24

### Lectura del vigor vegetal

- La metodología muestra los cinco intervalos numéricos de NDVI junto a su clase
  de vigor vegetal.
- Cada clase dispone de una ayuda nativa y accesible que se abre mediante
  pulsación o teclado.
- La escala y sus precauciones de interpretación se incorporaron al PDF y al
  registro metodológico JSON.
- La leyenda activa conserva los intervalos visibles sin depender únicamente del
  color.

## [0.2.2] - 2026-07-24

### Correspondencia con el visor original

- Se documentó la matriz funcional entre el visor de Google Earth Engine y la
  aplicación Streamlit.
- El análisis ahora conserva las seis clases JRC: bosque estable, degradación,
  deforestación, recuperación, agua y otra cobertura.
- Se muestran la cobertura arbórea persistente a 2020 y las pérdidas Hansen
  anteriores y posteriores al corte.
- Se añadió la lectura de consistencia alta, parcial, mixta o sin señal
  consistente, sin modificar el índice ponderado.
- El detalle incorpora un gráfico comparable del aporte de JRC, Hansen, ESRI,
  GEDI y NDVI.
- El PDF y el registro metodológico incluyen las nuevas estadísticas y la
  consistencia entre fuentes.

### Validación

- Se ampliaron las pruebas unitarias para cubrir las cuatro lecturas de
  consistencia y evitar que ganancias mínimas produzcan una lectura mixta.

## [0.2.1] - 2026-07-24

### Metodología y trazabilidad

- Se centralizaron pesos, umbrales, justificaciones y reglas de prioridad en
  `metodologia_indice.py`.
- El índice suma cada fuente una sola vez: JRC 2.0, Hansen 2.0, ESRI 1.5,
  GEDI 0.5 y NDVI 0.0.
- Se añadieron pruebas que demuestran que ESRI no puede superar el aporte
  individual de JRC ni de Hansen.
- El registro metodológico JSON incluye la justificación de cada peso y umbral,
  además del aporte efectivo por fuente.

### Interfaz e informe

- La composición ponderada se muestra antes que las métricas temáticas.
- JRC, Hansen, ESRI y GEDI reciben una métrica principal cada uno, en ese orden.
- El PDF incorpora una columna de aporte al índice y la justificación de pesos y
  umbrales; NDVI queda identificado explícitamente como evidencia visual.

## [0.2.0] - 2026-07-24

### Mejorado

- El recorrido muestra visualmente qué etapas están completadas, cuál es el paso
  actual y qué falta por hacer.
- Las opciones de área utilizan nombres cotidianos y explican cuándo conviene usar
  una finca, dibujar un polígono o analizar la cuenca completa.
- Antes de ejecutar se anticipan los tres productos que recibirá el usuario:
  conclusión resumida, evidencia cartográfica e informe trazable.
- El resultado incorpora una lectura rápida organizada en tres preguntas:
  qué se detectó, dónde mirar y qué hacer después.

### Accesibilidad y recuperación

- Las tarjetas se reorganizan en una sola columna en pantallas pequeñas y no
  dependen del color para comunicar el estado.
- Los errores de conexión incluyen una explicación comprensible y tres pasos de
  recuperación, conservando el detalle técnico en un panel secundario.

### Metodología

- No se modificaron fuentes, umbrales, pesos, reglas de prioridad ni cálculos
  territoriales.

## [0.1.7] - 2026-07-24

### Corregido

- Los controles de información de la leyenda NDVI ahora se abren con clic o toque,
  además de admitir navegación mediante teclado.
- Cada explicación aparece debajo de su categoría y muestra el intervalo NDVI
  correspondiente sin depender de una ayuda emergente al pasar el cursor.

### Accesibilidad

- El área interactiva ocupa toda la línea de la categoría, conserva un indicador
  de foco visible y funciona en pantallas táctiles.

## [0.1.6] - 2026-07-22

### Añadido

- Acceso mediante código privado antes de consultar o mostrar la lista de fincas.
- Caducidad de la autorización a los 30 minutos, cierre manual y bloqueo temporal
  después de cinco intentos incorrectos.

### Seguridad

- La dirección del asset de fincas se trasladó a los secretos de Streamlit.
- El mapa dejó de solicitar y mostrar la colección completa de fincas; conserva
  únicamente el contorno del área seleccionada.
- El registro metodológico JSON ya no contiene la dirección del asset ni la
  geometría vectorial de las fincas privadas.

## [0.1.5] - 2026-07-22

### Corregido

- Descargar el registro metodológico JSON ya no reinicia la aplicación ni
  interrumpe la preparación de los mapas del informe PDF.
- Descargar un PDF ya preparado tampoco provoca una nueva ejecución de
  Streamlit.

## [0.1.4] - 2026-07-21

### Mejorado

- Los seis mapas del informe se descargan en paralelo, en grupos de tres, en vez
  de esperar cada mapa de forma consecutiva.
- Los límites del área se solicitan una sola vez a Earth Engine para toda la
  generación cartográfica.
- Cada mapa dispone de un intento principal y un segundo intento más liviano;
  se eliminaron esperas consecutivas innecesarias.
- Cuando el usuario reintenta un informe parcial, se conservan los mapas que ya
  fueron descargados y se solicitan únicamente los faltantes.
- El primer informe conserva una clave de caché estable y solo se invalida cuando
  es necesario reintentar mapas faltantes.
- La interfaz informa cuántos mapas fueron entregados antes de armar el PDF y
  conserva los resultados si la generación cartográfica falla.

## [0.1.3] - 2026-07-21

### Mejorado

- El análisis entrega primero los resultados y deja la creación del PDF como una
  acción posterior solicitada por el usuario.
- Las reducciones de JRC, Hansen, ESRI y GEDI se agrupan en una sola respuesta de
  Earth Engine para reducir viajes de red.
- Los intentos de generación cartográfica pueden repetirse si una miniatura no
  está disponible temporalmente.

## [0.1.2] - 2026-07-21

### Mejorado

- El identificador técnico dejó de mostrarse en la experiencia principal y en el
  PDF.
- La interfaz indica de forma comprensible si la configuración es recomendada o
  personalizada.
- El identificador permanece en el JSON metodológico con una explicación de su
  finalidad técnica.

## [0.1.1] - 2026-07-21

### Mejorado

- Se corrigió el espacio superior de la aplicación para evitar que la barra de
  Streamlit cubriera la cabecera.
- “Preevaluación territorial” pasó a ser el título principal, con mayor tamaño y
  adaptación para pantallas pequeñas.
- Se retiró de la pantalla principal la línea interna de versión y metodología.

## [0.1.0] - 2026-07-21

### Añadido

- Nueva aplicación independiente en `app_experiencia.py`.
- Recorrido guiado para seleccionar el área, elegir el enfoque, revisar resultados
  y explorar evidencia cartográfica.
- Configuración recomendada para usuarios no especialistas y modo técnico mediante
  divulgación progresiva.
- Registro metodológico JSON con fuentes, periodos, umbrales, pesos y reglas.
- Informe PDF con resultados y seis mapas temáticos.
- Compatibilidad con fincas, toda la cuenca y polígonos dibujados por el usuario.

### Conservado

- El motor analítico de JRC TMF, Hansen, ESRI, GEDI y Sentinel-2/NDVI.
- El alcance indicativo: la aplicación no constituye validación de campo ni
  determina cumplimiento EUDR.

[0.2.0]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.7...v0.2.0
[0.1.7]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/julii5sos/visor-preevaluacion-territorial/releases/tag/v0.1.0
