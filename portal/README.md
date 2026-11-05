# Conectividad Panamá · Portal SIG de la Cuenca del Canal

Detecta dónde hay conectividad y dónde hay fragmentación, dónde se está perdiendo
la conectividad y dónde hay riesgo de perderla. Calcula el Índice de Resiliencia
Ecológica (ERI), la pérdida y ganancia de bosque y las prioridades de
intervención en la Cuenca del Canal de Panamá + 10 km. También verifica bajo
demanda el polígono de un área de interés dibujada o subida.

Metodología completa: **METODOLOGIA.md**.

## Puesta en marcha

### 1. Instalar
Con Miniconda (recomendado en Windows):
```
conda create -n portal -c conda-forge python=3.11 geopandas rasterio scipy scikit-image pillow flask requests pyproj
conda activate portal
pip install earthengine-api
```

### 2. Earth Engine (cuenta no comercial)
1. Entra a https://code.earthengine.google.com/register y registra un
   proyecto de Google Cloud para **uso no comercial** (ONG / investigación).
2. Anota el **id del proyecto** (por ejemplo, `conectividad-canal`).
3. En la terminal: `earthengine authenticate` y sigue el enlace.
4. Define la variable con el id:
   - Windows: `set EE_PROJECT=conectividad-canal`
   - Mac/Linux: `export EE_PROJECT=conectividad-canal`
5. (Opcional) Pega `gee_code_editor.js` en el Code Editor para revisar los insumos.

### 3. Ejecutar el motor
```
python ejecutar_motor.py                 # datos reales (Earth Engine), 30 m
python ejecutar_motor.py --demo          # sin Earth Engine, para probar
python ejecutar_motor.py --anio0 2018 --anio1 2025
```
El motor descarga las KBA, prepara los insumos, calcula fragmentación, ERI,
pérdida de conectividad, riesgo y prioridades, y deja GeoTIFF y capas para el
visor en `static/data/motor/`. Puede tardar de 20 a 60 minutos la primera vez.

### 4. Abrir el portal
```
python app.py        →  http://127.0.0.1:5000
```
- **Panel**: indicadores por cuenca y subcuenca.
- **Plataforma**: capas, asistente de análisis y verificación de polígonos.
  En la pestaña *Polígono* puedes dibujar o subir un GeoJSON, KML, KMZ o
  Shapefile en .zip.

### 4b. Preevaluación (análisis del repositorio de corredores)
Las tres rutas del modelo `evaluacion-corredores-panama` (territorial,
corredores y conectividad, integral) están en `evaluacion/` y se usan desde la
Plataforma (asistente y pestaña *Polígono*) y desde la pestaña *Corredores* del Panel.
```
python preparar_evaluacion.py        # una vez: corredores e intersecciones por subcuenca
```
Variables de entorno (nunca las subas a Git):
- `EE_PROJECT` o `EE_SERVICE_ACCOUNT_JSON` (ruta o contenido del JSON de la cuenta de servicio).
- `EE_ASSET_BOSQUE_2021`: asset privado de Bosque 2021 (SINIA–MiAMBIENTE). La cuenta
  debe poder leerlo. Si no está disponible, la fragmentación usa el bosque del motor y
  el resultado lo indica.
- `PREEVALUACION_EJEMPLO=1` solo para probar la interfaz sin Earth Engine (cifras inventadas).

Pruebas: `cd evaluacion && python -m unittest test_metodologia_indice test_corredores test_bosque_conectividad`

### 5. Mantenerlo al día
Programa `python ejecutar_motor.py` cada semana (Programador de tareas de
Windows o cron) para refrescar las alertas. Recalcula el ERI una vez al año. La
verificación de polígonos consulta Earth Engine en el momento.

### Sitio sin servidor
`python exportar.py` genera `dist/`. Ahí la verificación de polígonos es
aproximada (rejilla de 180 m en el navegador) y no incluye métricas FRAGSTATS.
La ruta *Corredores* funciona por cuenca y subcuenca; las preevaluaciones territorial
e integral necesitan el servidor con Earth Engine.

## Estructura
```
config.py            Pesos del ERI, umbrales, paletas, menú y textos
ejecutar_motor.py    Ejecuta la cadena completa
motor/area.py        Cuenca + 10 km y subcuencas
motor/kba.py         Descarga de KBA desde ArcGIS
motor/gee.py         Insumos de Earth Engine (Dynamic World, Hansen, S1, DEM, MERIT, altura)
motor/fragstats.py   LPI, CONNECT, ED, ENN y conectividad equivalente
motor/pipeline.py    ERI, pérdida de conectividad, prioridades, estadísticas y salidas
motor/verificar.py   Verificación bajo demanda de polígonos
evaluacion/          Análisis del repositorio de corredores (índice, corredores, fragmentación, Earth Engine)
preparar_evaluacion.py  Genera static/data/evaluacion.js
app.py               Servidor Flask: páginas y API (/api/verificar, /api/leer_poligono, /api/motor/estado)
templates/, static/  Interfaz (Jinja + JavaScript + Leaflet)
```

## Atribución
Contiene datos Copernicus Sentinel modificados, procesados en Google Earth Engine.
Dynamic World (Google y WRI), Hansen/UMD/Google/USGS/NASA, ETH Global Canopy
Height, MERIT Hydro, KBA (BirdLife International en nombre de la KBA Partnership).
Corredores y puntos críticos: Almanaque Azul (ver `evaluacion/THIRD_PARTY_DATA.md`).
Bosque 2021: SINIA–MiAMBIENTE. JRC TMF, ESRI Land Cover 10 m, GEDI y Sentinel-2.
