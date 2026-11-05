// Revisión visual en el Code Editor de Earth Engine (code.earthengine.google.com)
// Pega este script, dibuja o importa el área y revisa que los insumos del motor
// se vean bien antes de ejecutar ejecutar_motor.py.
// Sube static/data/area_estudio.geojson como asset y reemplaza la ruta:
var aoi = ee.FeatureCollection('projects/TU-PROYECTO/assets/area_estudio').geometry();
Map.centerObject(aoi, 10);

function bosque(anio) {
  var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(aoi)
    .filterDate(anio + '-01-01', (anio + 1) + '-01-01');
  return dw.select('label').reduce(ee.Reducer.mode()).eq(1)
    .and(dw.select('trees').mean().gte(0.5)).clip(aoi);
}
var b0 = bosque(2017), b1 = bosque(2025);
Map.addLayer(b0.selfMask(), {palette: ['9fc46f']}, 'Bosque 2017', false);
Map.addLayer(b1.selfMask(), {palette: ['4f7f3a']}, 'Bosque 2025');
Map.addLayer(b0.and(b1.not()).selfMask(), {palette: ['d0442c']}, 'Pérdida 2017–2025');
Map.addLayer(b0.not().and(b1).selfMask(), {palette: ['77cc09']}, 'Ganancia 2017–2025');

var han = ee.Image('UMD/hansen/global_forest_change_2025_v1_13').clip(aoi);
Map.addLayer(han.select('lossyear').selfMask(), {min: 1, max: 25, palette: ['fabc20', 'd0442c']}, 'Hansen pérdida 2001–2025', false);

// Alertas propias con radar Sentinel-1: caída de VH ≥ 3 dB frente al año anterior
var hoy = ee.Date(Date.now()), ini = hoy.advance(-60, 'day');
function s1(a, b) {
  return ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(aoi).filterDate(a, b)
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')).select('VH');
}
var caida = s1(ini.advance(-1, 'year'), hoy.advance(-1, 'year')).median().subtract(s1(ini, hoy).median());
Map.addLayer(caida.gte(3).and(b1.or(b0)).selfMask().clip(aoi), {palette: ['ff0000']}, 'Alertas S1 (60 días)');

// RADD: confirma si Panamá está dentro de la cobertura
var radd = ee.ImageCollection('projects/radar-wur/raddalert/v1').filterBounds(aoi)
  .filter(ee.Filter.eq('layer', 'alert'));
print('Imágenes RADD sobre el área (0 = Panamá sin cobertura):', radd.size());
