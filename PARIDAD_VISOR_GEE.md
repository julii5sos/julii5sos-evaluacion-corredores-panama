# Correspondencia funcional con el visor original de Google Earth Engine

**Documento de referencia:** `Visor_PreEvaluacion_Territorial_NATURA_Documentacion.docx`

**Implementación Streamlit:** UX-0.2.9

**Método:** MT-2026.4

Esta matriz verifica que la migración a Python, Streamlit y GitHub conserve las
funciones descritas para el visor original. La interfaz se reorganiza para facilitar
su uso, pero las fuentes, las comparaciones y el diagnóstico permanecen disponibles.

| Función descrita | Implementación en Streamlit |
|---|---|
| Selección ordenada de fincas | Lista con orden natural y zoom automático; acceso protegido mediante secreto del servidor |
| Análisis de toda la cuenca | Disponible como área regional, con advertencia de mayor tiempo de procesamiento |
| Polígono dibujado por el usuario | Herramienta de dibujo y análisis del GeoJSON recortado a la cuenca |
| Comparador visual JRC | Barrido sincronizado entre año inicial y final, con rótulos visibles |
| Comparador visual ESRI | Barrido sincronizado entre año inicial y final |
| Comparador visual NDVI | Barrido entre dos años seleccionados con clases de vigor; no altera el índice |
| Selección de años | Comparadores visuales JRC, ESRI y NDVI; no alteran JRC 2025, Hansen 2021-2025 ni ESRI 2017-2024 usados por el diagnóstico |
| Capas temáticas | JRC, Hansen histórico y posterior a 2020, línea base, ESRI, GEDI, NDVI y sectores que requieren revisión; JRC, ESRI y NDVI admiten consulta de un solo año sin comparador, y las capas pueden combinarse y ordenarse |
| Leyenda activa | Leyendas dependientes del comparador y de las capas seleccionadas |
| JRC TMF | Seis clases, estadísticas, mapa, gráfico y señal ponderada |
| Hansen GFC | Cobertura persistente a 2020, pérdida 2001-2020 y pérdida posterior a 2020 |
| ESRI LULC 10 m | Cobertura final, árboles estables, salida y ganancia de árboles |
| GEDI | Altura media y porcentaje del área con datos válidos; el análisis continúa si la cobertura es insuficiente |
| Sentinel-2 NDVI | NDVI anual, cambio visual y respaldo del año anterior; aporte 0 al índice |
| Índice integrado | JRC 2.0, Hansen 2.0, ESRI 1.5, GEDI 0.5 y NDVI 0.0 |
| Consistencia entre fuentes | Alta, parcial, mixta o sin señal consistente; no modifica el puntaje |
| Coincidencia espacial | Séptimo mapa en malla común de 30 m con señal de una, dos o tres fuentes; no modifica el índice |
| Gráficos | Distribución de las seis clases JRC, transiciones ESRI y aporte ponderado por fuente |
| Ficha exportable | PDF directo con texto, tablas, siete mapas, leyendas, metodología y limitaciones |
| Registro reproducible | JSON sin geometría de las fincas privadas; incluye fuentes, períodos, umbrales, resultados y aportes |
| Actualización anual | Años y activos centralizados en el bloque de configuración |

## Diferencias intencionales

- El PDF se genera con un botón y no mediante `Ctrl+P`; así puede incluir mapas
  temáticos completos aunque no estén visibles simultáneamente en la pantalla.
- La selección de fincas puede estar protegida por contraseña y el registro JSON no
  contiene su geometría.
- Los criterios porcentuales y de cobertura válida reducen falsas señales en áreas
  pequeñas o con datos GEDI insuficientes.
- La herramienta se presenta como preevaluación indicativa. No certifica, no valida
  en campo y no determina cumplimiento EUDR.

## Criterio de aceptación

La migración se considera funcionalmente equivalente cuando una misma geometría y
los mismos períodos producen las mismas estadísticas por fuente y la misma
activación de señales, dentro de las diferencias de redondeo y disponibilidad
temporal de los servicios de Earth Engine.
