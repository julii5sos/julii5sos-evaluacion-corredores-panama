# Metodología del índice operativo de prioridad

**Versión del método:** MT-2026.7-DIAGNOSTICO-INTEGRADO

**Versión de implementación auditada:** UX-0.5.0-DIAGNOSTICO-INTEGRADO

## Finalidad y alcance

El índice organiza áreas para revisión posterior mediante señales satelitales
complementarias. No representa una probabilidad de deforestación, no identifica por
sí solo la causa de un cambio y no constituye validación de campo, certificación ni
determinación de cumplimiento EUDR.

## Fuentes integradas

| Fuente | Resolución de trabajo | Uso |
|---|---:|---|
| JRC Tropical Moist Forest 2025 | 30 m | Estado anual de bosque, degradación y deforestación |
| Hansen Global Forest Change 2025 | 30 m | Pérdida anual de cobertura arbórea |
| ESRI Land Use/Land Cover | 10 m | Transición de la clase árboles a otra cobertura |
| Altura de dosel GEDI / OpenForis | 100 m | Contexto estructural y cobertura válida |
| Sentinel-2 SR Harmonized | 10 m | NDVI y cambio de vigor vegetal, solo visual |
| Corredores de Almanaque Azul, versión publicada 2024.05 | Vector | Valor estratégico y ubicación respecto a corredores |
| SINIA–MiAMBIENTE, Bosque y otros usos 2021 | Vector aportado | Fragmentación, red de parches y foco espacial de la visita |

Cada producto se procesa en su propia proyección y resolución. Las superficies se
calculan dentro del área seleccionada y se integran como evidencia por fuente para
el índice. Solo el mapa de coincidencia espacial descrito más adelante estandariza
JRC, Hansen y ESRI en una malla común.

## Períodos fijos y controles visuales

Para que todas las áreas sean comparables, el cálculo usa períodos fijos:

- JRC Tropical Moist Forest: estado forestal 2025. La señal mide las clases de
  degradación y deforestación de la banda `Dec2025`; no resta 2020 de 2025.
- Hansen Global Forest Change: edición 2025 y pérdidas 2021-2025, posteriores al
  corte de referencia del 31/12/2020.
- ESRI Land Use/Land Cover: transición 2017-2024, porque 2024 es la última
  anualidad disponible en la serie utilizada.
- GEDI: producto estructural configurado en la metodología.
- NDVI: evidencia visual hasta 2025 y aporte 0.0 al índice.

El valor inicial 2020 del comparador JRC corresponde al año del corte de referencia
EUDR y 2025 al estado más reciente del producto; ese barrido es exclusivamente
visual. En ESRI se muestran 2017 y 2024 por ser los extremos de la serie utilizada.

Los años que el usuario selecciona modifican únicamente los mapas interactivos y
las imágenes cartográficas. La consulta de una capa anual y los comparadores de dos
años se presentan como opciones separadas. Ninguna cambia los períodos fijos usados
para calcular señales, puntaje o prioridad.

Para JRC TMF se calculan las seis clases anuales: bosque estable, degradación,
deforestación, recuperación, agua y otra cobertura. Las seis se muestran en las
estadísticas; solo degradación y deforestación pueden activar la señal de deterioro.

## Activación de señales

### JRC TMF

La señal se activa cuando se cumple al menos una condición:

- deforestación ≥ 0.5 ha;
- deforestación ≥ 1% del área;
- degradación ≥ 2.0 ha;
- degradación ≥ 5% del área.

Los criterios absoluto y relativo conservan sensibilidad en áreas de tamaños
diferentes. La degradación utiliza valores más conservadores porque puede ser
gradual y presentar mayor ambigüedad espectral.

### Hansen Global Forest Change

La señal se activa con pérdida posterior al 31/12/2020 ≥ 0.18 ha. Este valor
equivale aproximadamente a dos píxeles de 30 m, por lo que evita que un único píxel
aislado determine el resultado y mantiene sensibilidad a eventos pequeños.

### ESRI Land Use/Land Cover

La señal se activa únicamente cuando se cumplen simultáneamente:

- salida de la clase árboles ≥ 0.10 ha; y
- salida de la clase árboles ≥ 5% del área.

A 10 m, 0.10 ha representa diez píxeles. Exigir extensión y proporción reduce
transiciones aisladas por variabilidad de clasificación. Esta regla y el peso 1.5
impiden que ESRI domine a los productos forestales especializados.

### GEDI

La señal contextual se activa únicamente cuando:

- al menos 20% del área tiene datos válidos;
- la altura media del dosel es menor de 8 m; y
- la línea base arbórea cubre al menos 10% del área.

La combinación evita interpretar dosel bajo en zonas sin cobertura arbórea previa o
con disponibilidad espacial insuficiente.

### NDVI de Sentinel-2

Se calcula como `(B8 - B4) / (B8 + B4)` sobre compuestos anuales con máscara SCL.
Se utiliza solo como evidencia visual porque puede responder a estacionalidad,
humedad, cultivos, pastizales, nubes y sombras. Su aporte al índice es 0.0.

La clasificación visual utilizada en el mapa y el informe es:

| Intervalo NDVI | Lectura visual | Interpretación orientativa |
|---:|---|---|
| < 0 | Sin vegetación activa | Agua, sombra, nubes residuales o superficies no vegetadas |
| 0.0 a < 0.2 | Suelo o cobertura muy escasa | Suelo desnudo, área construida o vegetación muy dispersa |
| 0.2 a < 0.4 | Vegetación escasa | Cobertura poco densa, pastizal o cultivo en etapa temprana |
| 0.4 a < 0.6 | Vegetación moderada | Actividad vegetal y cobertura intermedias |
| ≥ 0.6 | Vegetación densa | Señal alta de vegetación verde y densa |

Los intervalos describen vigor espectral, no tipo de cobertura. Un valor alto no
confirma por sí solo bosque natural, y uno bajo no demuestra por sí solo pérdida
forestal. En la aplicación, cada clase incluye un botón de información accesible
mediante pulsación o teclado.

## Índice ponderado

Cada fuente puede sumar una sola vez:

| Fuente | Peso |
|---|---:|
| JRC TMF | 2.0 |
| Hansen GFC | 2.0 |
| ESRI LULC | 1.5 |
| GEDI | 0.5 |
| NDVI | 0.0 |

La fórmula es:

`puntaje = 2·JRC + 2·Hansen + 1.5·ESRI + 0.5·GEDI`

donde cada variable vale `1` si su señal está activa y `0` en caso contrario. El
puntaje máximo es 6.0. No se suman áreas, píxeles ni subcriterios adicionales al
peso de una misma fuente.

## Reglas de prioridad

| Puntaje | Prioridad |
|---:|---|
| ≥ 3.0 | Alta |
| ≥ 1.5 y < 3.0 | Media |
| ≥ 0.5 y < 1.5 | Preventiva |
| < 0.5 | Baja |

Una señal ESRI aislada produce 1.5 puntos. Una señal JRC aislada produce 2.0 y una
señal Hansen aislada produce 2.0. Por diseño, ESRI nunca aporta más que cualquiera
de las dos fuentes forestales principales.

## Consistencia entre fuentes

La consistencia es una lectura adicional y no modifica el puntaje:

| Lectura | Regla |
|---|---|
| Alta consistencia | JRC TMF, Hansen GFC y ESRI LULC presentan señal de deterioro |
| Consistencia parcial | Exactamente dos de las tres fuentes presentan señal |
| Lectura mixta | Coexisten señales de deterioro y de recuperación o ganancia |
| Sin señal consistente | Menos de dos fuentes principales coinciden en deterioro |

Para evitar que cambios mínimos produzcan una lectura mixta, la recuperación JRC
se filtra con 0.5 ha o 1% del área y la ganancia de árboles ESRI con 0.10 ha y 5%
del área. Son criterios simétricos a los umbrales de cambio usados para esas
fuentes. Las ganancias no compensan ni restan puntos a una señal de deterioro,
porque pueden ocurrir simultáneamente en sectores diferentes de la misma área.

## Mapa de coincidencia espacial

El séptimo mapa, **Sectores que requieren revisión**, responde a una pregunta
distinta del índice: ubica dónde se superponen las señales de deterioro de las tres
fuentes principales. Utiliza:

- JRC TMF 2025: degradación o deforestación;
- Hansen GFC: pérdida posterior al 31/12/2020;
- ESRI LULC 2017-2024: transición de árboles a no árboles.

JRC conserva su malla de 30 m. Hansen se reproyecta por vecino más cercano y la
señal ESRI de 10 m se agrega por presencia máxima antes de llevarse a la misma malla.
Las tres imágenes binarias se suman y producen:

| Valor | Clase | Lectura |
|---:|---|---|
| 1 | Señal de una fuente | Evidencia aislada; revisar el producto correspondiente |
| 2 | Coincidencia de dos fuentes | Sector de revisión prioritaria |
| 3 | Coincidencia de tres fuentes | Sector con coincidencia espacial de JRC, Hansen y ESRI |

GEDI y NDVI no participan en esta superposición porque son fuentes de contexto y
apoyo visual, respectivamente. El mapa no agrega puntos, no modifica la prioridad,
no demuestra causalidad y no sustituye la revisión documental, imágenes recientes
o verificación de campo.

## Trazabilidad

Las constantes y funciones se mantienen en `metodologia_indice.py`. Las pruebas de
`test_metodologia_indice.py` verifican pesos, umbrales, suma única por fuente,
clasificación, consistencia, exclusión de NDVI e integración estructural sin aumento
del puntaje. El registro JSON conserva fuentes,
períodos, umbrales, justificaciones, pesos, aportes efectivos, estadísticas y reglas
de prioridad, consistencia y contexto estructural, además de la regla y las
superficies del mapa de coincidencia espacial.

## Corredores ecológicos de Almanaque Azul

La capa vectorial externa contiene 22 polígonos interpretados y 14 puntos críticos. Se conservan sus atributos `nombre`, `notas`, `cond_promedio`, `area_ha` y `cat`. Las tres categorías verificadas en el dato publicado son:

| Valor original | Etiqueta mostrada | Color original |
|---|---|---|
| `alta` | Alta | `#345a01` |
| `mediana` | Mediana | `#a1d303` |
| `mediabaja` | Media-baja | `#e0c504` |

Los originales están en EPSG:3857 y se convierten a EPSG:4326 mediante `scripts/preparar_datos_corredores.py`. Para medir intersecciones, el área evaluada y los corredores se proyectan a Equal Earth Americas (EPSG:8857). Se informa el área y porcentaje de superposición total, por categoría y con los tramos mesoamericanos.

Esta superposición no modifica el índice satelital de cambios. Se utiliza como
valor estratégico en una prioridad separada de visita y tampoco demuestra
conectividad funcional para una especie particular.

## Prioridad integrada de visita

La aplicación conserva tres dimensiones visibles para evitar que el contexto
ecológico se confunda con evidencia de deterioro:

1. **Urgencia por cambios:** el índice satelital original, de 0 a 6 puntos.
2. **Valor estratégico del corredor:** hasta 1.5 puntos adicionales.
3. **Condición estructural 2021:** indica dónde focalizar la visita, sin sumar puntos.

El aporte por corredor se calcula así:

```text
aporte por solapamiento = mínimo(% del AOI en corredores / 25, 1.0)
aporte mesoamericano = 0.5 cuando existe intersección
puntaje integrado = puntaje de cambios + ambos aportes
```

El aporte por superficie alcanza su máximo cuando al menos 25% del área está
dentro de corredores. Las categorías alta, mediana y media-baja publicadas por
Almanaque Azul se muestran como atributos, pero no se convierten en señales de
deterioro ni en una jerarquía inventada de valor ecológico.

El corredor por sí solo puede justificar seguimiento preventivo, pero nunca una
prioridad alta o muy alta. La clase **Muy alta** exige que la prioridad por
cambios ya sea alta y que el aporte estratégico del corredor alcance al menos
1 punto. Así, la herramienta responde dos preguntas diferentes: por qué urge
revisar el área y por qué esa revisión tiene relevancia para la continuidad ecológica.
La tercera pregunta —dónde concentrar el trabajo de campo— se responde con la red
de parches de la cobertura 2021.

## Fragmentación del bosque de referencia 2021

La cobertura utilizada corresponde a la capa **Bosque y otros usos**, referencia 2021, publicada por SINIA–MiAMBIENTE. La administración publica el shapefile nacional una sola vez como asset privado de Earth Engine. La aplicación filtra internamente el campo `Categoria` por el valor `Bosques y Otras Tierras Boscosas` y recorta el resultado al área evaluada; la persona usuaria no carga archivos ni selecciona campos de clase. Las geometrías se transforman a EPSG:8857, se validan y se separan en parches poligonales.

Esta capa representa la cobertura clasificada para 2021. Se utiliza para describir la fragmentación y conectividad estructural del bosque de ese año; por sí sola no permite determinar cuándo ocurrió un cambio ni debe interpretarse como una serie anual de deforestación.

Las métricas de clase son:

- número de parches;
- área total y porcentaje de bosque en el paisaje;
- densidad de parches por 100 ha;
- densidad de borde en m/ha;
- porcentaje ocupado por el parche mayor;
- área media, mediana y desviación poblacional;
- índice de forma medio `perímetro / (2 × √(π × área))`.

## Red de conectividad estructural

Cada parche es un nodo. Dos nodos se conectan cuando la distancia mínima entre sus polígonos es menor o igual al umbral seleccionado. Para una distancia `d` y umbral `u`, la fuerza de la arista es `exp(-d/u)` y el costo mínimo utilizado es 1 m.

El índice conector por parche reproduce los pesos de los ejercicios R:

```text
0.40 × grado normalizado
+ 0.30 × intermediación normalizada
+ 0.20 × área normalizada
+ 0.10 × fuerza normalizada
```

La importancia `Alta`, `Media` o `Baja` se asigna mediante los cuantiles 75% y 50% del índice dentro del área analizada. Es una clasificación relativa y no equivale a las categorías publicadas por Almanaque Azul. Con más de 400 nodos, la intermediación se aproxima con una muestra reproducible de hasta 200 nodos.

La condición estructural se resume con reglas operativas transparentes:

| Condición | Regla |
|---|---|
| Un solo parche | La cobertura seleccionada forma un parche |
| Conectada al umbral | Todos los parches forman un componente |
| Conectividad predominante | El componente mayor reúne al menos 75% de los parches |
| Conectividad intermedia | El componente mayor reúne entre 50% y menos de 75% |
| Red dividida | El componente mayor reúne menos de 50% |

Estas categorías dependen del umbral de distancia elegido y describen conectividad
estructural, no movimiento comprobado de fauna. Se conectan con el diagnóstico para
orientar la visita hacia parches conectores y componentes aislados, pero no modifican
el puntaje: asignarles peso requeriría calibración ecológica para el territorio y las
especies objetivo.
