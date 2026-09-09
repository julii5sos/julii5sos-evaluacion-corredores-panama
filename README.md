# Evaluación territorial y corredores ecológicos de Panamá

Aplicación Streamlit para integrar tres lecturas que conservan su trazabilidad:

1. señales satelitales de cambio forestal y prioridad de revisión;
2. corredores ecológicos interpretados y publicados por Fundación Almanaque Azul;
3. fragmentación y conectividad estructural calculadas desde un shapefile bosque/no bosque aportado durante la sesión.

La aplicación orienta revisiones territoriales. No es una certificación, no determina cumplimiento EUDR y no demuestra por sí sola conectividad funcional para una especie.

## Qué se añadió en este repositorio

- 22 polígonos de corredores y 14 puntos críticos publicados por Almanaque Azul.
- Las categorías originales `alta`, `mediana` y `media-baja`, sin sustituirlas por una clasificación inventada.
- Los tres tramos panameños identificados como Corredor Biológico Mesoamericano: oeste, San Lorenzo y este.
- Intersección del área evaluada con corredores, medida en hectáreas mediante un sistema equivalente en área.
- Carga temporal de un ZIP de shapefile bosque/no bosque.
- Métricas de fragmentación equivalentes a las utilizadas en los ejercicios R: número y densidad de parches, área total/media/mediana, borde, forma y parche mayor.
- Red de parches conectados por una distancia configurable e índice conector compuesto por grado (40%), intermediación (30%), área (20%) y fuerza de conexión (10%).
- Resultados de corredores y fragmentación en la interfaz, el PDF y el registro metodológico JSON.
- Prioridad de visita que combina la urgencia por cambios con el valor estratégico del corredor.

El índice satelital de cambios no se altera. La prioridad de visita lo conserva
como componente dominante y añade hasta 1.5 puntos de valor estratégico: hasta
1.0 por la proporción del área dentro de corredores y 0.5 por pertenencia al
Corredor Biológico Mesoamericano. Un corredor sin señales suficientes de cambio
nunca genera por sí solo una prioridad alta.

## Flujo de uso

1. Seleccione una finca, dibuje un polígono o use toda la cuenca configurada.
2. Opcionalmente cargue un ZIP con un único conjunto `.shp`, `.shx`, `.dbf` y `.prj`.
3. Seleccione el campo de clase y el valor o valores que representan bosque.
4. Defina la distancia máxima entre parches y el área mínima de parche.
5. Elija **Evaluar conectividad ecológica y corredores** o cualquiera de las vistas satelitales.
6. Ejecute el análisis y revise la prioridad integrada de visita, sus dos componentes y la red de bosque aportada.

## Fuentes

- JRC Tropical Moist Forest 2025.
- Hansen Global Forest Change 2025.
- ESRI Land Use/Land Cover 2017-2024.
- GEDI / OpenForis para altura del dosel.
- Sentinel-2 SR Harmonized para NDVI.
- [Mapa de corredores naturales de Panamá](https://www.almanaqueazul.org/conectividad/mapa/), Fundación Almanaque Azul, versión mostrada `2024.05`.
- Shapefile bosque/no bosque aportado por la persona usuaria; no se almacena en Git.

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

Nunca confirme en Git el JSON real de la cuenta de servicio, la dirección privada del asset de fincas, el código de acceso ni el shapefile nacional.

## Estructura principal

- `app_experiencia.py`: interfaz, motor Earth Engine e informe.
- `corredores.py`: capas de Almanaque Azul e intersección con el área evaluada.
- `bosque_conectividad.py`: lectura segura del ZIP, fragmentación y red de parches.
- `metodologia_indice.py`: reglas del índice satelital original.
- `scripts/preparar_datos_corredores.py`: conversión reproducible EPSG:3857 → EPSG:4326.
- `data/`: GeoJSON preparados, catálogo y originales públicos.
- `METODOLOGIA.md`: fórmulas, separaciones metodológicas y limitaciones.

## Pruebas

```powershell
python -m unittest discover -v
```

## Rendimiento y límites prácticos

El shapefile nacional se procesa en memoria. Para archivos con miles de fragmentos, aumente el área mínima de parche. A partir de 400 nodos, la intermediación se aproxima con una muestra reproducible para evitar bloquear la aplicación. Para operación institucional continua conviene preparar y versionar la cobertura fuera de la interfaz o publicarla como un asset privado de Earth Engine.
