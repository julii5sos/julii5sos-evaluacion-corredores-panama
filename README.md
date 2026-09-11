# Evaluación territorial y corredores ecológicos de Panamá

Aplicación Streamlit para conectar tres lecturas en un diagnóstico territorial
único, conservando la trazabilidad de cada una:

1. señales satelitales de cambio forestal y prioridad de revisión;
2. corredores ecológicos interpretados y publicados por Fundación Almanaque Azul;
3. fragmentación y conectividad estructural calculadas desde un recorte institucional de la capa **Bosque y otros usos 2021** de SINIA–MiAMBIENTE, almacenado como asset privado de Earth Engine.

La aplicación orienta revisiones territoriales. No es una certificación, no determina cumplimiento EUDR y no demuestra por sí sola conectividad funcional para una especie.

## Qué se añadió en este repositorio

- 22 polígonos de corredores y 14 puntos críticos publicados por Almanaque Azul.
- Las categorías originales `alta`, `mediana` y `media-baja`, sin sustituirlas por una clasificación inventada.
- Los tres tramos panameños identificados como Corredor Biológico Mesoamericano: oeste, San Lorenzo y este.
- Intersección del área evaluada con corredores, medida en hectáreas mediante un sistema equivalente en área.
- Lectura automática del recorte vectorial de **Bosque y otros usos 2021** desde un asset privado de Earth Engine.
- Métricas de fragmentación equivalentes a las utilizadas en los ejercicios R: número y densidad de parches, área total/media/mediana, borde, forma y parche mayor.
- Red de parches conectados por una distancia configurable e índice conector compuesto por grado (40%), intermediación (30%), área (20%) y fuerza de conexión (10%).
- Red completa para las métricas y una estructura mínima legible en el mapa, trazada entre los bordes más próximos de los fragmentos.
- Ruta estructural potencial hacia un corredor publicado cuando existe una cadena de bosque en la que cada salto cumple la distancia seleccionada; la búsqueda se limita a un entorno de 5 km.
- Brechas potenciales desde parches aislados hacia su vecino más cercano; las capas se pueden consultar y descargar como GeoJSON.
- Resultados de corredores y fragmentación en la interfaz, el PDF y el registro metodológico JSON.
- Diagnóstico de visita que combina la urgencia por cambios con el valor estratégico
  del corredor y usa la estructura del bosque 2021 para indicar dónde focalizarla.

El índice satelital de cambios no se altera. La prioridad de visita lo conserva
como componente dominante y añade hasta 1.5 puntos de valor estratégico: hasta
1.0 por la proporción del área dentro de corredores y 0.5 por pertenencia al
Corredor Biológico Mesoamericano. Un corredor sin señales suficientes de cambio
nunca genera por sí solo una prioridad alta. La fragmentación no recibe un peso
inventado: clasifica la condición estructural y dirige la revisión hacia parches
conectores, separaciones y componentes aislados.

## Flujo de uso

1. Seleccione una finca, dibuje un polígono o use toda la cuenca configurada.
2. La aplicación conserva el área elegida para las hectáreas, pero revisa también un entorno exterior de hasta 5 km para evitar falsos aislamientos y buscar una cadena estructural hacia un corredor publicado.
3. Si lo necesita, ajuste la distancia máxima entre parches y el área mínima de parche.
4. Elija **Diagnóstico territorial integrado** o cualquiera de las vistas satelitales.
5. Ejecute el análisis y revise sus cuatro lecturas: urgencia por cambios, valor del
   corredor, condición estructural 2021 y prioridad integrada de visita.
6. Use **Capas disponibles en el mapa** para encender o apagar los fragmentos, la
   estructura esencial, la ruta potencial hacia un corredor y las separaciones. La
   ruta naranja es una orientación estructural para revisar, no un corredor nuevo ni
   evidencia de movimiento de fauna.
7. Descargue el PDF, el registro metodológico y los GeoJSON de parches y conexiones
   para conservar el diagnóstico.

## Fuentes

- JRC Tropical Moist Forest 2025.
- Hansen Global Forest Change 2025.
- ESRI Land Use/Land Cover 2017-2024.
- GEDI / OpenForis para altura del dosel.
- Sentinel-2 SR Harmonized para NDVI.
- [Mapa de corredores naturales de Panamá](https://www.almanaqueazul.org/conectividad/mapa/), Fundación Almanaque Azul, versión mostrada `2024.05`.
- SINIA–MiAMBIENTE, capa **Bosque y otros usos**, referencia 2021. El recorte de bosque se conserva como asset institucional privado y no se almacena en Git.

La procedencia de los GeoJSON incluidos se documenta en [THIRD_PARTY_DATA.md](THIRD_PARTY_DATA.md).

## Ejecutar localmente

Requiere Python 3.11 o superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

## Configuración de Earth Engine

Guarde los secretos únicamente en `.streamlit/secrets.toml` para desarrollo local o en **App settings > Secrets** al desplegar:

```toml
EE_PROJECT = "proyecto-de-earth-engine"
EE_ASSET_FINCAS = "projects/PROYECTO/assets/COLECCION_PRIVADA_DE_FINCAS"
EE_ASSET_BOSQUE_2021 = "projects/ee-julissaguevaravega/assets/CBOTB_2021_25k"
FINCAS_ACCESS_CODE = "CODIGO_PRIVADO_DE_AL_MENOS_8_CARACTERES"

EE_SERVICE_ACCOUNT_JSON = '''
{
  "type": "service_account",
  "project_id": "proyecto-de-earth-engine",
  "private_key": "CLAVE_PRIVADA_COMPLETA",
  "client_email": "cuenta-de-servicio@proyecto.iam.gserviceaccount.com"
}
'''
```

Nunca confirme en Git el JSON real de la cuenta de servicio, las direcciones privadas de los assets, el código de acceso ni el shapefile nacional.

### Publicar la cobertura de bosque una sola vez

Esta tarea corresponde a la administración, no a las personas que consultan la aplicación:

1. Use `CBOTB_2021_25k.zip`, que contiene un único shapefile completo con `.shp`, `.shx`, `.dbf`, `.prj` y `.cpg`. Si prepara una copia normalizada, se recomienda EPSG:4326.
2. En **Earth Engine > Assets**, seleccione **NEW > Table upload** y cargue el ZIP.
3. Use una ruta estable, por ejemplo `projects/ee-julissaguevaravega/assets/CBOTB_2021_25k`.
4. Verifique que la cuenta de servicio de Streamlit pueda leer el asset.
5. Copie la ruta completa en el secreto `EE_ASSET_BOSQUE_2021` y reinicie la aplicación.

Desde ese momento, cada área seleccionada usa la misma fuente: la aplicación filtra internamente `Categoria = Bosques y Otras Tierras Boscosas`, conserva el recorte del área activa para las hectáreas y usa hasta 5 km de contexto exterior para calcular la red y buscar una conexión estructural potencial hacia un corredor. No muestra un cargador ni un selector de clases.

## Estructura principal

- `app_experiencia.py`: interfaz, motor Earth Engine e informe.
- `corredores.py`: capas de Almanaque Azul e intersección con el área evaluada.
- `bosque_conectividad.py`: preparación del recorte institucional, fragmentación y red de parches.
- `metodologia_indice.py`: reglas del índice satelital original.
- `scripts/preparar_datos_corredores.py`: conversión reproducible EPSG:3857 → EPSG:4326.
- `data/`: GeoJSON preparados, catálogo y originales públicos.
- `METODOLOGIA.md`: fórmulas, separaciones metodológicas y limitaciones.

## Pruebas

```powershell
python -m unittest discover -v
```

## Rendimiento y límites prácticos

El asset se recorta primero en Earth Engine usando el área activa más su buffer de contexto. El resultado se procesa en memoria, pero solo las porciones interiores se publican en el mapa y en las métricas de superficie. Para áreas con miles de fragmentos, aumente el área mínima de parche. A partir de 400 nodos, la intermediación se aproxima con una muestra reproducible para evitar bloquear la aplicación.
