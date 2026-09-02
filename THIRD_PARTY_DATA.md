# Datos de terceros

## Corredores naturales de Panamá

La aplicación incorpora dos GeoJSON publicados por la Fundación Almanaque Azul:

- `interpretacion_conectividad_5_3857.geojson` (22 polígonos de corredores);
- `ojos_5_3857.geojson` (14 puntos críticos).

Fuente: [Mapa de corredores naturales de Panamá](https://www.almanaqueazul.org/conectividad/mapa/), versión mostrada por el visor `2024.05`. El sitio de la Fundación indica que su contenido se publica bajo licencias Creative Commons. Estos datos conservan su atribución y no se relicencian como parte del código de la aplicación.

Los originales están en EPSG:3857. El script `scripts/preparar_datos_corredores.py` los convierte a EPSG:4326 sin cambiar geometrías, nombres, notas, conductividad promedio ni categorías. Las categorías originales verificadas son `alta`, `mediana` y `media-baja`.

El raster continuo de conectividad de 6 km no se redistribuye en este repositorio. El visor enlaza al mapa original para esa lectura y utiliza los polígonos interpretados publicados para el análisis de intersección.

## Cobertura bosque/no bosque

El repositorio no incluye el shapefile nacional de bosque/no bosque aportado por la usuaria. Se carga como ZIP desde la interfaz y se procesa temporalmente durante la sesión. Debe contener un único conjunto `.shp`, `.shx`, `.dbf` y `.prj` con el mismo nombre.
