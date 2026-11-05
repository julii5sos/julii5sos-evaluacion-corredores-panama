"""Resultado de EJEMPLO del índice satelital, solo para probar la interfaz sin Earth Engine.

Se activa con la variable PREEVALUACION_EJEMPLO=1. Los valores por fuente son
inventados (proporciones fijas del área); las señales, el puntaje, la prioridad y
la consistencia sí se calculan con las funciones reales de metodologia_indice.py.
La interfaz muestra un aviso visible cuando el resultado es de ejemplo.
"""
from metodologia_indice import calcular_indice_prioridad, evaluar_consistencia, evaluar_senales


def resultado_cambios_ejemplo(area_ha: float) -> dict:
    a = max(area_ha, 1.0)
    r = dict(area_ha=a, tmf_estable=0.62 * a, tmf_degradacion=0.031 * a, tmf_deforestacion=0.012 * a,
             tmf_recuperacion=0.004 * a, tmf_agua=0.05 * a, tmf_otra_cobertura=0.283 * a,
             coincidencia_1_fuente=0.022 * a, coincidencia_2_fuentes=0.006 * a, coincidencia_3_fuentes=0.002 * a,
             hansen_post=0.009 * a, hansen_pre=0.021 * a, linea_base=0.58 * a, esri_arboles_final=0.6 * a,
             esri_salida=0.038 * a, esri_ganancia=0.011 * a, esri_estable=0.57 * a,
             ndvi_disminucion=0.018 * a, ndvi_area_datos=0.93 * a, gedi_altura=17.4, gedi_area_datos=0.71 * a,
             ndvi_inicial_medio=0.71, ndvi_final_medio=0.69, ndvi_delta_medio=-0.02)
    r['gedi_cobertura_pct'] = r['gedi_area_datos'] / a * 100
    r['ndvi_cobertura_pct'] = r['ndvi_area_datos'] / a * 100
    r['coincidencia_varias_fuentes'] = r['coincidencia_2_fuentes'] + r['coincidencia_3_fuentes']
    r['pct_coincidencia_varias_fuentes'] = r['coincidencia_varias_fuentes'] / a * 100
    pct = lambda k: r[k] / a * 100
    senales, disp = evaluar_senales(
        tmf_deforestacion_ha=r['tmf_deforestacion'], tmf_deforestacion_pct=pct('tmf_deforestacion'),
        tmf_degradacion_ha=r['tmf_degradacion'], tmf_degradacion_pct=pct('tmf_degradacion'),
        hansen_post_2020_ha=r['hansen_post'], esri_salida_arboles_ha=r['esri_salida'],
        esri_salida_arboles_pct=pct('esri_salida'), gedi_altura_media_m=r['gedi_altura'],
        gedi_cobertura_valida_pct=r['gedi_cobertura_pct'], linea_base_arborea_pct=pct('linea_base'),
        ndvi_disminucion_ha=r['ndvi_disminucion'], ndvi_disminucion_pct=pct('ndvi_disminucion'),
        ndvi_cobertura_valida_pct=r['ndvi_cobertura_pct'])
    aportes, puntaje, prioridad = calcular_indice_prioridad(
        senal_tmf=senales['tmf'], senal_hansen=senales['hansen'], senal_esri=senales['esri'],
        senal_gedi=senales['gedi'], senal_ndvi=senales['ndvi'])
    consistencia = evaluar_consistencia(
        senal_tmf=senales['tmf'], senal_hansen=senales['hansen'], senal_esri=senales['esri'],
        tmf_recuperacion_ha=r['tmf_recuperacion'], tmf_recuperacion_pct=pct('tmf_recuperacion'),
        esri_ganancia_arboles_ha=r['esri_ganancia'], esri_ganancia_arboles_pct=pct('esri_ganancia'))
    r.update(pct_tmf_defor=pct('tmf_deforestacion'), pct_tmf_degrad=pct('tmf_degradacion'),
             pct_tmf_recuperacion=pct('tmf_recuperacion'), pct_esri_salida=pct('esri_salida'),
             pct_esri_ganancia=pct('esri_ganancia'), pct_linea_base=pct('linea_base'),
             pct_ndvi_disminucion=pct('ndvi_disminucion'),
             **{f'senal_{k}': v for k, v in senales.items()}, gedi_disponible=disp['gedi'], ndvi_disponible=disp['ndvi'],
             aportes_indice=aportes, puntaje=puntaje, prioridad=prioridad, consistencia=consistencia, ejemplo=True)
    return r
