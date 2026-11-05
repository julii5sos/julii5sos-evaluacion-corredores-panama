# Publicar el portal con Earth Engine real

El análisis (JRC, Hansen, ESRI, GEDI, NDVI, ERI), el PDF con mapas y el comparador de años se calculan en el
servidor Python, así que el portal debe correr en un servidor y no en GitHub Pages.

1. **Cuenta de servicio** (una sola vez): en Google Cloud, proyecto `ee-julissaguevaravega`, crea una cuenta de
   servicio, descarga su clave JSON, regístrala en https://code.earthengine.google.com/register (servicio) y
   comparte con ella tus assets `CBOTB_2021_BOSQUE` y `SubCuenca_CHCP` como lectores.
2. **Render** (o Railway): New → Blueprint → elige este repositorio y la rama. Lee `render.yaml` y el `Dockerfile`.
3. Pega el contenido del JSON en la variable `EE_SERVICE_ACCOUNT_JSON`.
4. Abre la URL que te da Render: la plataforma calcula con Earth Engine en vivo.

Prueba local: `earthengine authenticate` y `cd portal && python app.py`.
