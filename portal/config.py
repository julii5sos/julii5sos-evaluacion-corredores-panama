"""Configuración central del portal Conectividad Panamá.

Todo lo que se repite entre Python, las plantillas HTML y el JavaScript
(paleta de mapas, menú, catálogo de capas, textos) vive aquí.
"""
import os
from pathlib import Path

# ---------------- Earth Engine (valores por defecto; una variable de entorno los sobrescribe) ----------------
# Son identificadores de proyecto y de assets, no credenciales: la autenticación sigue siendo `earthengine authenticate`.
os.environ.setdefault('EE_PROJECT', 'ee-julissaguevaravega')
os.environ.setdefault('EE_ASSET_BOSQUE_2021', 'projects/ee-julissaguevaravega/assets/CBOTB_2021_BOSQUE')
os.environ.setdefault('EE_ASSET_SubCuencas', 'projects/ee-julissaguevaravega/assets/SubCuenca_CHCP')

BASE = Path(__file__).resolve().parent
DATOS_ENTRADA = BASE / 'datos_entrada'          # shapefiles originales (.zip)
STATIC = BASE / 'static'
DATOS_SALIDA = STATIC / 'data'                  # capas y estadísticas generadas
DIST = BASE / 'dist'                            # sitio estático exportado

SITIO = {
    'nombre': 'Conectividad Panamá',
    'subtitulo': 'Proyecto Copernicus',
    'atribucion': 'Contiene datos Copernicus Sentinel modificados (2026), procesados en Google Earth Engine.',
}

# Menú principal: (endpoint, texto, archivo exportado)
MENU = [
    ('herramienta', 'Conoce la herramienta', 'herramienta.html'),
    ('panel', 'Panel', 'panel.html'),
    ('plataforma', 'Plataforma', 'plataforma.html'),
    ('datos', 'Uso de datos', 'datos.html'),
    ('tutoriales', 'Tutoriales', 'tutoriales.html'),
    ('faq', 'FAQ', 'faq.html'),
]

# ---------------- Paleta de marca ----------------
MARCA = {
    'azul': '#0a4393', 'azul_2': '#1d529b', 'azul_tinta': '#062a5e', 'azul_suave': '#eef1f7',
    'verde': '#77cc09', 'amarillo': '#fabc20',
}

# ---------------- Simbología de mapas (sólida y tenue) ----------------
CLASES = ['Bosque maduro', 'Bosque secundario', 'Manglar', 'Pastos', 'Cultivos', 'Urbano', 'Agua']
PALETA_COBERTURA = ['#4f7f3a', '#9fc46f', '#3f8a86', '#ecebdc', '#f1d68f', '#b6bcc8', '#a9c5e6']
CLASES_CONECTIVIDAD = ['Muy baja', 'Baja', 'Media', 'Alta', 'Muy alta']
PALETA_CONECTIVIDAD = ['#eef1f7', '#cbd8ea', '#93b2d8', '#4f7fbc', '#0a4393']
COLOR_NUCLEOS = '#5c9a1b'
COLOR_BOSQUE_2000 = '#b7d39a'
PERDIDA_RAMPA = ('#fabc20', '#d0442c')          # 2001 → 2025
CORREDORES = {'Alta': '#062a5e', 'Media': '#e09a12', 'Baja': '#d0442c'}

# ---------------- Contenido de páginas ----------------
FLUJO = [
    ('sat', 'Insumos', 'Sentinel-1, Sentinel-2 y Landsat', 'Dynamic World (10 m), Hansen 2001–2025, radar Sentinel-1, Copernicus DEM, MERIT Hydro y altura de dosel.'),
    ('lay', 'Bosque', 'Bosque por año', 'Clase árboles de Dynamic World para el año base y el actual; pérdida y ganancia entre ambos.'),
    ('mtn', 'Fragmentación', 'Métricas FRAGSTATS', 'LPI, CONNECT, ED y ENN por unidad, y CONNECT en ventana móvil de 1,5 km.'),
    ('net', 'Resiliencia', 'ERI y prioridades', 'ERI = 0,35 estructura + 0,25 conectividad + 0,20 topografía + 0,20 riparia; riesgo y dónde intervenir.'),
]

INDICADORES = [
    ('ERI', '0 – 1', 'Índice de Resiliencia Ecológica. > 0,75: núcleos íntegros y estables; < 0,40: paisaje fragmentado o modificado.'),
    ('LPI', '%', 'Largest Patch Index: porcentaje del área ocupado por el parche de bosque más grande.'),
    ('CONNECT', '%', 'Pares de parches de bosque unidos a ≤ 300 m (borde a borde) sobre el total de pares posibles.'),
    ('ED', 'm/ha', 'Edge Density: metros de borde bosque/no bosque por hectárea. Sube cuando el bosque se fragmenta.'),
    ('ENN', 'm', 'Distancia euclidiana media de cada parche a su vecino más cercano. Mide el aislamiento.'),
    ('Pérdida de conectividad', 'ha', 'Superficie donde la conectividad de parches cayó más de 5 puntos entre el año base y el actual.'),
    ('Riesgo de pérdida', '0 – 1', 'Probabilidad de pérdida de bosque según presiones recientes (Random Forest en Earth Engine).'),
]

CATALOGO = [  # nombre, tipo, resolución, periodo, estado, fuente
    ('Cuenca del Canal y subcuencas', 'Vector · polígonos', 'Subcuenca', '—', 'real', 'Shapefile del proyecto (Panama_Canal_Subwatersheds)'),
    ('Corredores naturales de Panamá', 'Vector · 22 polígonos', '—', '2024.05', 'real', 'Fundación Almanaque Azul (Omniscape, ventana de 6 km) · CC'),
    ('Puntos críticos de conectividad', 'Vector · 14 puntos', '—', '2024.05', 'real', 'Fundación Almanaque Azul'),
    ('Bosque y otros usos', 'Vector · polígonos', '1:25 000', '2021', 'gee', 'SINIA–MiAMBIENTE · asset privado EE_ASSET_BOSQUE_2021'),
    ('JRC Tropical Moist Forest', 'Ráster · 6 clases', '30 m', '2025', 'gee', 'projects/JRC/TMF/v1_2025/AnnualChanges'),
    ('ESRI Land Use / Land Cover', 'Ráster · 9 clases', '10 m', '2017–2024', 'gee', 'projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS'),
    ('Altura del dosel GEDI', 'Ráster · m', '100 m', '—', 'gee', 'OpenForis · CanopyHeight_GEDI_V27'),
    ('NDVI Sentinel-2', 'Ráster · índice', '10 m (resumen 20 m)', '2020–2025', 'gee', 'COPERNICUS/S2_SR_HARMONIZED con máscara SCL'),
    ('Área de estudio (cuenca + 10 km)', 'Vector · polígono', '—', '—', 'real', 'Derivada en motor/area.py'),
    ('Áreas Clave para la Biodiversidad', 'Vector · polígonos', '—', 'Junio 2024', 'real', 'KBAs_LATAM_June2024 (ArcGIS Feature Service)'),
    ('Bosque por año', 'Ráster · binario', '10 m', '2017–actual', 'gee', 'GOOGLE/DYNAMICWORLD/V1'),
    ('Pérdida anual de bosque (Hansen)', 'Ráster · año', '30 m', '2001–2025', 'gee', 'UMD/hansen/global_forest_change_2025_v1_13 · motor y preevaluación'),
    ('Alertas de pérdida', 'Ráster · binario', '10 m', 'Últimos 60 días', 'gee', 'COPERNICUS/S1_GRD (detector propio) · RADD si cubre Panamá'),
    ('Altura de dosel', 'Ráster · m', '10 m', '2020', 'gee', 'ETH Global Canopy Height (componente estructural del ERI)'),
    ('Pendiente', 'Ráster · grados', '30 m', '—', 'gee', 'COPERNICUS/DEM/GLO30'),
    ('Cauces perennes', 'Ráster · binario', '90 m', '—', 'gee', 'MERIT/Hydro/v1_0_1 (área de drenaje ≥ 1 km²)'),
    ('ERI, CONNECT, riesgo y prioridades', 'Ráster', '30 m', 'Año base y actual', 'motor', 'Calculados por ejecutar_motor.py'),
]

TUTORIALES = [
    ('Panel', '3 min', 'Consultar una subcuenca', 'panel', ['Abre el Panel desde el menú superior.', 'Elige la cuenca (con o sin la franja de 10 km) o una subcuenca.', 'Recorre Resumen, Conectividad, Cambio de cobertura y Prioridades.', 'Pulsa “i” en cada tarjeta para ver cómo se calcula.']),
    ('Plataforma', '2 min', 'Verificar un área dibujada', 'plataforma', ['En la Plataforma abre la pestaña Polígono.', 'Dibuja tu área de interés (clic en cada vértice, doble clic para cerrar) o sube un GeoJSON, KML o Shapefile .zip.', 'Elige el periodo y pulsa “Verificar polígono”.', 'Lee el veredicto, la pérdida y ganancia, las alertas y el ERI dentro del área.']),
    ('Plataforma', '3 min', 'Responder una pregunta de conectividad', 'plataforma', ['Pulsa “Realizar análisis”.', 'Elige la pregunta: conectividad, fragmentación, ERI, pérdida, cobertura o prioridades.', 'Elige la cuenca, una subcuenca o tu polígono.', 'El mapa enciende las capas de esa pregunta y los resultados aparecen a la derecha.']),
    ('Conceptos', '4 min', 'Leer el ERI', 'herramienta', ['El ERI va de 0 a 1.', 'Más de 0,75: núcleos de bosque íntegros e hidrológicamente estables.', 'Menos de 0,40: paisaje fragmentado o modificado.', 'Abre cada componente en la Plataforma para ver qué lo baja.']),
    ('Equipo técnico', '15 min', 'Ejecutar el motor con Earth Engine', 'datos', ['Registra el proyecto de Google Cloud para uso no comercial en Earth Engine.', 'pip install earthengine-api y earthengine authenticate.', 'EE_PROJECT ya viene con el proyecto ee-julissaguevaravega; cámbialo solo si usas otro.', 'python ejecutar_motor.py y luego python app.py.']),
    ('Equipo técnico', '5 min', 'Actualizar las alertas', 'datos', ['Programa python ejecutar_motor.py cada semana (cron o Programador de tareas).', 'La verificación de polígonos siempre consulta Earth Engine en vivo.', 'Revisa las alertas nuevas en la capa Alertas recientes.']),
]

FAQ = [
    ('¿Qué es la preevaluación territorial, de corredores e integral?', 'Son las tres rutas del método de campo. La territorial busca indicios satelitales de cambio forestal (JRC, Hansen, ESRI, GEDI y NDVI) y propone un nivel de atención con un puntaje de 0 a 6,5. La de corredores revisa los corredores de Almanaque Azul y la fragmentación del bosque 2021. La integral une ambas en una prioridad de visita.'),
    ('¿La preevaluación confirma deforestación o cumplimiento EUDR?', 'No. Es indicativa: ayuda a justificar por qué un área merece una revisión más detallada y dónde mirar primero. No confirma hallazgos en campo, no certifica, no determina cumplimiento EUDR y no demuestra conectividad funcional para una especie.'),
    ('¿Por qué un corredor no sube la prioridad a alta?', 'El corredor aporta valor estratégico (hasta 1,5 puntos), pero un corredor sin señales de cambio nunca genera por sí solo una prioridad alta. La clase Muy alta exige cambios con prioridad alta y un aporte del corredor de al menos 1 punto.'),
    ('¿Qué bosque usa la red de parches?', 'La capa Bosque y otros usos 2021 de SINIA–MiAMBIENTE, publicada como asset privado de Earth Engine. Si no está disponible, el portal usa el bosque del motor (Dynamic World) y lo indica en el resultado.'),
    ('¿Qué área cubre la herramienta?', 'La Cuenca Hidrográfica del Canal de Panamá y una franja de amortiguamiento de 10 km a su alrededor. Todos los análisis se recortan a esa área.'),
    ('¿Qué tan “en tiempo real” es?', 'La verificación de polígonos consulta Earth Engine en el momento. Las alertas de radar Sentinel-1 tienen una revisita de 6 a 12 días y no dependen de las nubes. Los mapas de ERI y conectividad se recalculan cuando se ejecuta el motor (se recomienda cada semana para alertas y cada año para el ERI).'),
    ('¿Cómo se calcula el ERI?', 'ERI = 0,35 × integridad estructural + 0,25 × conectividad (CONNECT) + 0,20 × estabilidad topográfica + 0,20 × proximidad riparia. Cada componente se normaliza entre 0 y 1. Valores mayores a 0,75 indican núcleos íntegros y estables; menores a 0,40, paisaje fragmentado.'),
    ('¿Por qué no hay especie focal?', 'Es un análisis de conectividad estructural: mide la forma y disposición del bosque (LPI, CONNECT, ED, ENN), no el movimiento de una especie en particular.'),
    ('¿Qué distancia usa CONNECT?', 'Dos parches se consideran conectados si están a 300 m o menos, borde a borde. El valor se cambia en config.py (CONNECT_UMBRAL_M).'),
    ('¿Cómo verifico un área propia?', 'En la Plataforma, pestaña Polígono: dibújala en el mapa o sube un GeoJSON, KML, KMZ o Shapefile en .zip, elige el periodo y pulsa “Verificar polígono”. El polígono no se guarda.'),
    ('¿Qué cuenta de Earth Engine se necesita?', 'Una cuenta registrada para uso no comercial (investigación u ONG), vinculada a un proyecto de Google Cloud. El id de ese proyecto va en la variable EE_PROJECT.'),
    ('¿Qué significa el modo demostración?', 'Si el motor se ejecuta sin Earth Engine (python ejecutar_motor.py --demo), la cuenca, subcuencas y KBA son reales, pero la cobertura, el ERI y las alertas son sintéticos. Sirve para probar el portal.'),
]

# ---------------- Motor de análisis (Cuenca del Canal + 10 km) ----------------
ERI_PESOS = {'estructura': 0.35, 'conectividad': 0.25, 'topografia': 0.20, 'riparia': 0.20}
ERI_CORTES = (0.40, 0.75)            # < 0.40 baja · 0.40–0.75 media · > 0.75 alta
CONNECT_UMBRAL_M = 300               # distancia borde a borde para unir parches (CONNECT)
CONNECT_VENTANA_M = 1500             # radio de la ventana móvil de CONNECT
CAIDA_CONECTIVIDAD = 0.05            # caída de conectividad (0–1) que se marca como pérdida
ANIO_BASE = 2017                     # primer año completo de Dynamic World
PALETA_ERI = ['#d0442c', '#f2a541', '#f6e7a1', '#93b2d8', '#0a4393']        # 0 → 1
PALETA_PRIORIDAD = {1: ('Proteger', '#0a4393'), 2: ('Restaurar', '#77cc09'),
                    3: ('Vigilar', '#fabc20'), 4: ('Mantener', '#dfe6f2')}
