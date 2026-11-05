/* Preevaluación territorial, corredores y conectividad (método del repositorio
   julii5sos-evaluacion-corredores-panama). Usa window.EVAL (preparar_evaluacion.py)
   y la API /api/preevaluar del servidor Python. */
(function () {
  const { fmt, esc, icon, bars } = CP;
  const E = window.EVAL;
  const MODOS = { territorial: 'territorial', corredores: 'corredores', integral: 'integral' };
  const nf = (v, d = 1) => (v == null || Number.isNaN(+v) ? '—' : fmt(+v, d));
  const ha = (v, d = 1) => (v == null ? '—' : Math.abs(v) >= 10000 ? fmt(v / 1000, 1) + ' kha' : fmt(v, d) + ' ha');
  const COL_PRI = { 'Muy alta': '#8f1d12', Alta: '#d0442c', Media: '#e09a12', Preventiva: '#e8c547', Baja: '#4f8f00' };
  const COL_IMP = { Alta: '#a63f35', Media: '#d58a24', Baja: '#4f875f' };
  const FUENTES = [
    ['tmf', 'JRC TMF', 'Deforestación o degradación 2025'],
    ['hansen', 'Hansen GFC', 'Pérdida posterior al 31/12/2020'],
    ['esri', 'ESRI LULC', `Salida de árboles ${E.metodo.periodos.esri_inicial}–${E.metodo.periodos.esri_final}`],
    ['gedi', 'GEDI', 'Dosel bajo con línea base arbórea'],
    ['ndvi', 'NDVI Sentinel-2', `Disminución ${E.metodo.periodos.ndvi_inicial}–${E.metodo.periodos.ndvi_final}`],
  ];
  const SERIES = ['JRC Tropical Moist Forest', 'Hansen Global Forest Change', 'ESRI Land Use / Land Cover', 'Sentinel-2 · NDVI', 'GEDI · altura del dosel'];

  // ------------------------------------------------------------ petición
  function pedir(p) {
    if (window.PORTAL && window.PORTAL.api) {
      return fetch(window.PORTAL.api + 'preevaluar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) })
        .then((r) => r.json().then((j) => { if (!r.ok) throw new Error(j.error || 'Error del servidor'); return j; }));
    }
    // Sitio sin servidor: solo la intersección con corredores precalculada por unidad.
    return new Promise((ok, mal) => {
      if (p.modo !== MODOS.corredores) return mal(new Error('La preevaluación territorial e integral se calcula con Earth Engine en el servidor Python (python app.py).'));
      if (!p.unidad || !E.interseccion[p.unidad]) return mal(new Error('Sin servidor, la lectura de corredores está disponible para la cuenca y las subcuencas. Para un polígono inicia python app.py.'));
      ok({ modo_analisis: 'corredores', modo_titulo: E.modos.corredores.titulo, corredores: E.interseccion[p.unidad], area_ha: E.interseccion[p.unidad].area_aoi_ha,
        fragmentacion_error: 'La fragmentación y la red de parches se calculan en el servidor Python (python app.py).', umbral_m: p.umbral_m, sin_servidor: true });
    });
  }
  function pedirSerie(p) {
    return fetch(window.PORTAL.api + 'preevaluar/serie', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) })
      .then((r) => r.json().then((j) => { if (!r.ok) throw new Error(j.error); return j; }));
  }

  // ------------------------------------------------------------ piezas de HTML
  const sec = (t, h) => `<div class="res-sec"><h3>${t}</h3>${h}</div>`;
  const tarjeta = (ic, v, l, col) => `<div class="mc"><span style="color:${col || 'var(--azul)'}">${icon(ic, 'ico')}</span><b class="num">${v}</b><span>${l}</span></div>`;
  function badge(titulo, clase, puntaje, max, texto) {
    const c = COL_PRI[clase] || 'var(--azul)';
    return `<div class="pre-badge" style="--c:${c}"><div><span class="eyebrow">${titulo}</span><b>${esc(clase)}</b></div>${puntaje != null ? `<div class="pre-pts"><b class="num">${nf(puntaje, 1)}</b><span>de ${nf(max, 1)} puntos</span></div>` : ''}<p>${esc(texto)}</p></div>`;
  }
  function filaSenal(r, [k, n, d]) {
    const on = r['senal_' + k];
    const disp = k === 'gedi' ? r.gedi_disponible : k === 'ndvi' ? r.ndvi_disponible : true;
    const dato = {
      tmf: `Defor. ${ha(r.tmf_deforestacion, 2)} (${nf(r.pct_tmf_defor, 2)} %) · degr. ${ha(r.tmf_degradacion, 2)} (${nf(r.pct_tmf_degrad, 2)} %)`,
      hansen: `${ha(r.hansen_post, 2)} desde 2021`,
      esri: `${ha(r.esri_salida, 2)} (${nf(r.pct_esri_salida, 2)} %)`,
      gedi: disp ? `${nf(r.gedi_altura, 1)} m de altura media · ${nf(r.gedi_cobertura_pct, 0)} % con datos` : `Datos válidos en ${nf(r.gedi_cobertura_pct, 0)} % del área (insuficiente)`,
      ndvi: disp ? `${ha(r.ndvi_disminucion, 2)} (${nf(r.pct_ndvi_disminucion, 2)} %) · Δ medio ${nf(r.ndvi_delta_medio, 3)}` : `Datos válidos en ${nf(r.ndvi_cobertura_pct, 0)} % del área (insuficiente)`,
    }[k];
    return `<tr><td><b>${n}</b><br><small>${d}</small></td><td class="c"><span class="chip ${on ? 'b' : 'a'}">${on ? 'Activa' : 'No'}</span></td><td class="c num">${nf(r.aportes_indice[k], 1)}<small> / ${nf(E.metodo.pesos[k], 1)}</small></td><td><small>${dato}</small></td></tr>`;
  }
  function bloqueCambios(r) {
    let h = badge('Atención sugerida por cambios', r.prioridad, r.puntaje, E.metodo.puntaje_maximo, r.recomendacion || '');
    h += sec('Señales por fuente', `<div class="tbl"><table class="mini"><thead><tr><th>Fuente</th><th class="c">Señal</th><th class="c">Aporte</th><th>Dato clave</th></tr></thead><tbody>${FUENTES.map((f) => filaSenal(r, f)).join('')}</tbody></table></div>
      <p>Puntaje = 2·JRC + 2·Hansen + 1,5·ESRI + 0,5·GEDI + 0,5·NDVI. Cada fuente suma una sola vez.</p>`);
    const c = r.consistencia || {};
    h += sec('Consistencia entre fuentes', `<p><b>${esc(c.nivel || '—')}</b>. ${esc(c.detalle || '')}</p>${(c.fuentes_recuperacion || []).length ? `<p>Recuperación o ganancia: ${c.fuentes_recuperacion.map(esc).join(', ')}.</p>` : ''}`);
    const cl = E.metodo.coincidencia.clases;
    h += sec('Sectores que requieren revisión', `<ul class="prio">${[1, 2, 3].map((k) => `<li><span class="sw" style="background:${cl[k].color}"></span><span>${esc(cl[k].etiqueta)}</span><b class="num">${ha(r[['coincidencia_1_fuente', 'coincidencia_2_fuentes', 'coincidencia_3_fuentes'][k - 1]], 2)}</b></li>`).join('')}</ul><p>Malla común de 30 m con JRC, Hansen y ESRI. No modifica el puntaje.</p>`);
    return h;
  }
  function bloqueCorredores(c) {
    if (!c) return '';
    const cats = Object.entries(c.areas_categoria_ha || {}).filter(([, v]) => v > 0);
    let h = `<div class="cards2">${tarjeta('link', nf(c.porcentaje_aoi_en_corredores, 1) + ' %', `del área en corredores · ${ha(c.area_en_corredores_ha)}`, '#345a01')}${tarjeta('net', c.intersecta_mesoamericano ? 'Sí' : 'No', c.intersecta_mesoamericano ? `Corredor Biológico Mesoamericano · ${ha(c.area_corredor_mesoamericano_ha)}` : 'sin tramo mesoamericano', '#a1d303')}</div>`;
    if (cats.length) h += `<div class="legend-row">${cats.map(([k, v]) => `<span><i style="background:${E.colores[k]}"></i>${E.etiquetas[k]} ${ha(v)}</span>`).join('')}</div>`;
    if ((c.corredores || []).length) h += `<ul class="prio">${c.corredores.slice(0, 6).map((x) => `<li><span class="sw" style="background:${E.colores[x.categoria]}"></span><span>${esc(x.nombre)}<br><small>${x.categoria_etiqueta} · conductividad media ${nf(x.cond_promedio, 1)}</small></span><b class="num">${nf(x.porcentaje_aoi, 1)} %</b></li>`).join('')}</ul>`;
    h += `<p class="sim">${esc(c.fuente)}. ${esc(c.limitacion || '')}</p>`;
    return sec('Corredores ecológicos', h);
  }
  function bloqueFragmentacion(r) {
    const f = r.fragmentacion;
    if (!f) return sec('Fragmentación y conectividad del bosque', `<p>${esc(r.fragmentacion_error || 'No disponible.')}</p>`);
    const m = f.metricas_clase || {}, n = f.metricas_red || {}, ce = r.contexto_estructural || {}, cc = f.conexion_corredor || {};
    let h = `<p><b>${esc(ce.estado || '—')}</b>. ${esc(ce.interpretacion || '')}</p>`;
    h += `<div class="cards2">${tarjeta('area', fmt(m.numero_parches || 0), `fragmentos · ${nf(m.porcentaje_paisaje_bosque, 1)} % de bosque`)}${tarjeta('core', nf(m.indice_parche_mayor_pct, 1) + ' %', 'ocupado por el parche mayor')}
      ${tarjeta('net', fmt(n.numero_componentes || 0), `grupos conectados · el mayor reúne ${nf(n.porcentaje_nodos_componente_mayor, 0)} %`)}${tarjeta('warn', fmt(n.numero_parches_aislados || 0), `fragmentos aislados (${nf(n.porcentaje_parches_aislados, 0)} %)`, 'var(--rojo)')}</div>`;
    const filas = [['Densidad de parches', nf(m.densidad_parches_por_100ha, 2) + ' /100 ha'], ['Densidad de borde', nf(m.densidad_borde_m_ha, 1) + ' m/ha'], ['Área media / mediana', `${ha(m.area_media_parche_ha, 1)} / ${ha(m.area_mediana_parche_ha, 1)}`], ['Índice de forma medio', nf(m.indice_forma_medio, 2)], ['Enlaces en la red', fmt(n.numero_aristas || 0)], ['Distancia media de enlaces', n.distancia_media_conexiones_m != null ? nf(n.distancia_media_conexiones_m, 0) + ' m' : '—'], ['Distancia evaluada', nf(n.umbral_m, 0) + ' m']];
    h += `<div class="tbl"><table class="mini"><tbody>${filas.map(([a, b]) => `<tr><td>${a}</td><td class="c num">${b}</td></tr>`).join('')}</tbody></table></div>`;
    if (cc.evaluada) h += `<p>${cc.conecta ? `<b>Ruta estructural potencial</b> hacia <b>${esc(cc.corredor_nombre)}</b> (${esc(cc.categoria_etiqueta)}): ${fmt(cc.numero_fragmentos_ruta)} fragmento(s), salto mayor ${nf(cc.mayor_separacion_m, 0)} m.` : 'No se encontró una cadena de fragmentos hasta un corredor publicado dentro de 5 km con la distancia elegida.'}</p>`;
    h += `<p class="sim">Cobertura: ${esc(f.fuente_cobertura || '')}. ${r.fragmentacion_aviso ? esc(r.fragmentacion_aviso) + ' ' : ''}${esc(ce.limitacion || '')}</p>`;
    return sec('Fragmentación y conectividad del bosque', h);
  }
  function bloqueVisita(r) {
    const v = r.prioridad_visita;
    let h = badge('Prioridad integrada de visita', v.prioridad_visita, v.puntaje_integrado, v.puntaje_maximo, r.recomendacion_visita || '');
    h += `<div class="cards2">${tarjeta('warn', nf(v.puntaje_cambios, 1), `urgencia por cambios (${esc(v.prioridad_cambios)})`, 'var(--rojo)')}${tarjeta('link', '+' + nf(v.aporte_corredor, 2), `valor del corredor (${esc(v.valor_corredor)})`, '#345a01')}</div>`;
    h += sec('Dónde enfocar la visita', `<p><b>${esc(v.combinacion_territorial)}</b>. ${esc(v.foco_visita)}</p><p>${esc(v.lectura_integrada)}</p><p class="sim">${esc(v.limitacion)}</p>`);
    return h;
  }

  // ------------------------------------------------------------ resumen ejecutivo, ERI y descargas
  const COL_RES = { 'Muy alta': '#7f0000', Alta: '#b71c1c', Media: '#a33a00', Preventiva: '#8a5b00', Baja: '#2e7d32' };
  const ETQ_ERI = { integridad_estructural: 'Integridad estructural', conectividad: 'Conectividad', estabilidad_topografica: 'Estabilidad topográfica', proximidad_riparia: 'Proximidad riparia' };
  function resumenEjecutivo(r) {
    if (r.modo_analisis === 'corredores') return '';
    const v = r.prioridad_visita, prioridad = v ? v.prioridad_visita : r.prioridad;
    const col = COL_RES[prioridad] || '#345a01';
    const rec = v ? r.recomendacion_visita : r.recomendacion;
    const maxP = E.metodo.puntaje_maximo;
    const detalle = v ? `Cambios ${nf(v.puntaje_cambios, 1)}/${nf(maxP, 1)} · corredor +${nf(v.aporte_corredor, 2)} · estructura ${esc((v.contexto_estructural.estado || '').toLowerCase())}` : `Índice operativo ${nf(r.puntaje, 1)}/${nf(maxP, 1)}`;
    let h = `<div class="pre-badge" style="--c:${col}"><div><span class="eyebrow">Resumen ejecutivo · ${esc(detalle)}</span><b>Prioridad ${esc(prioridad.toLowerCase())} de visita</b></div><p>${esc(rec || '')}</p></div>`;
    if (v) {
      const c = r.corredores || {}, f = r.fragmentacion, cl = (f && f.metricas_clase) || {}, cons = r.consistencia || {};
      const senalados = ['coincidencia_1_fuente', 'coincidencia_2_fuentes', 'coincidencia_3_fuentes'].reduce((a, k) => a + (+r[k] || 0), 0);
      const nf3 = ['senal_tmf', 'senal_hansen', 'senal_esri'].filter((k) => r[k]).length;
      h += sec('Dónde empezar', `<p><b>${esc(v.foco_visita)}</b></p><p class="sim">${esc(v.combinacion_territorial)}</p>`);
      h += `<div class="cards2">${tarjeta('warn', ha(senalados, 2), `cambios señalados · ${nf3} de 3 fuentes principales`, 'var(--rojo)')}${tarjeta('link', ha(c.area_en_corredores_ha || 0, 1), `dentro de corredores · ${nf(c.porcentaje_aoi_en_corredores || 0, 1)} % del área`, '#345a01')}
        ${tarjeta('area', f ? ha(cl.area_total_bosque_ha || 0, 1) : 'No disponible', `bosque ${f && f.ano_referencia_cobertura ? f.ano_referencia_cobertura : 2021}${f ? ' · ' + nf(cl.porcentaje_paisaje_bosque || 0, 1) + ' % del área' : ''}`)}${tarjeta('net', esc(v.contexto_estructural.estado || '—'), `conectividad · consistencia satelital: ${esc(cons.nivel || 'No disponible')}`)}</div>`;
      h += sec('Por qué se obtuvo este resultado', `<ul class="prio">
        <li><span>La evidencia territorial produjo una prioridad ${esc(r.prioridad.toLowerCase())} y una consistencia ${esc(String(cons.nivel || 'no disponible').toLowerCase())}.</span></li>
        <li><span>${c.intersecta ? `El área coincide con ${ha(c.area_en_corredores_ha || 0, 1)} de corredores publicados.` : 'No se identificó una coincidencia directa con los corredores publicados.'}</span></li>
        <li><span>${esc(v.contexto_estructural.interpretacion || 'La estructura del bosque no estuvo disponible para esta ejecución.')}</span></li></ul>`);
    }
    return h;
  }
  function bloqueERI(r) {
    const e = r.eri;
    if (!e) return r.eri_error ? sec('Índice de Resiliencia Ecológica (ERI)', `<p class="sim">No disponible: ${esc(r.eri_error)}</p>`) : '';
    const cs = Object.entries(e.componentes || {});
    let h = badge('ERI indicativo', e.clase, null, null, e.lectura || '');
    h += `<div class="cards2">${tarjeta('core', nf(e.valor, 2), 'valor ERI (0–1)', e.color)}${tarjeta('warn', esc(e.componente_limitante_etiqueta || '—'), 'componente limitante', 'var(--rojo)')}</div>`;
    h += `<div class="tbl"><table class="mini"><thead><tr><th>Componente</th><th class="c">Peso</th><th class="c">Valor</th></tr></thead><tbody>${cs.map(([k, v]) => `<tr><td>${ETQ_ERI[k] || k}</td><td class="c num">${nf((e.pesos || {})[k], 2)}</td><td class="c num">${nf(v, 2)}</td></tr>`).join('')}</tbody></table></div>`;
    const d = e.distribucion_clases || [];
    if (d.length) h += `<ul class="prio">${d.map((x) => `<li><span class="sw" style="background:${x.color}"></span><span>${esc(x.clase)}</span><b class="num">${ha(x.area_ha, 1)}</b></li>`).join('')}</ul>`;
    h += `<p class="sim">${esc(e.caracter || '')} No participa en el puntaje de prioridad. ${esc(e.nota_conectividad || '')}</p>`;
    return sec('Índice de Resiliencia Ecológica (ERI)', h);
  }
  function descargasHtml(r) {
    const b = (tipo, txt, ok = true) => ok ? `<button type="button" class="btn btn-s" data-desc="${tipo}">${txt}</button>` : '';
    const frag = r.modo_analisis !== 'territorial' && r.fragmentacion;
    return sec('Descargas', `<div class="chk">${b('pdf', 'Ficha PDF', r.modo_analisis !== 'corredores')}${b('registro', 'Registro metodológico (JSON)')}${b('fragmentos', 'Fragmentos y métricas (GeoJSON)', !!frag)}${b('red', 'Estructura y ruta potencial (GeoJSON)', !!frag)}</div><p class="sim" id="desc-msg">El PDF incluye los siete mapas cuando Earth Engine está conectado y puede tardar un minuto.</p>`);
  }
  function descargar(tipo, p, nombre) {
    return fetch(window.PORTAL.api + 'descargar/' + tipo, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({}, p, { nombre })) })
      .then((r) => r.ok ? r.blob().then((bl) => ({ bl, av: r.headers.get('X-Avisos') ? decodeURIComponent(r.headers.get('X-Avisos')) : null, n: (/filename="([^"]+)"/.exec(r.headers.get('Content-Disposition') || '') || [])[1] || tipo }))
        : r.json().then((j) => { throw new Error(j.error || 'No se pudo descargar'); }))
      .then(({ bl, av, n }) => { const a = document.createElement('a'); a.href = URL.createObjectURL(bl); a.download = n; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000); return av; });
  }
  function lectura(r) {
    let h = '';
    if (r.ejemplo) h += '<div class="verd dn"><span>' + icon('warn') + '</span><div><b>Valores de ejemplo</b><p>Las superficies por fuente son inventadas para probar la interfaz (PREEVALUACION_EJEMPLO=1). Las reglas, pesos y clasificaciones son las reales.</p></div></div>';
    h += resumenEjecutivo(r);
    if (r.modo_analisis === 'integral') h += bloqueVisita(r);
    if (r.modo_analisis !== 'corredores') h += bloqueCambios(r);
    if (r.modo_analisis === 'corredores') {
      const ce = r.contexto_estructural;
      h += ce && ce.disponible ? badge('Condición estructural', ce.estado, null, null, ce.interpretacion) : '';
    }
    if (r.modo_analisis !== 'territorial') h += bloqueCorredores(r.corredores) + bloqueFragmentacion(r);
    h += bloqueERI(r);
    if (!r.sin_servidor && window.PORTAL && window.PORTAL.api) h += descargasHtml(r);
    h += `<p class="sim">Preevaluación indicativa: orienta una revisión. No confirma hallazgos en campo, no certifica ni determina cumplimiento EUDR, y no demuestra conectividad funcional para una especie.</p>`;
    return h;
  }
  function graficas(r) {
    let h = '';
    if (r.aportes_indice) {
      const ks = FUENTES.map((f) => f[0]);
      h += sec('Aporte al puntaje por fuente', bars(ks.map((k) => r.aportes_indice[k]), FUENTES.map((f) => f[1].split(' ')[0]), ks.map((k) => (r['senal_' + k] ? '#d0442c' : '#c9d2e0')), { w: 360, h: 160, fy: (v) => fmt(v, 1), label: 'Aporte por fuente' }));
      const jrc = [['Estable', r.tmf_estable, '#006400'], ['Degrad.', r.tmf_degradacion, '#FFCC00'], ['Defor.', r.tmf_deforestacion, '#FF0000'], ['Regen.', r.tmf_recuperacion, '#00FF00'], ['Agua', r.tmf_agua, '#0000FF'], ['Otra', r.tmf_otra_cobertura, '#BDBDBD']];
      h += sec(`JRC TMF ${E.metodo.periodos.jrc_diagnostico} · seis clases`, bars(jrc.map((x) => x[1]), jrc.map((x) => x[0]), jrc.map((x) => x[2]), { w: 360, h: 170, fy: (v) => ha(v, 0), label: 'Clases JRC' }));
      const es = [['Árboles estables', r.esri_estable, '#006400'], ['Salida de árboles', r.esri_salida, '#FF0000'], ['Ganancia de árboles', r.esri_ganancia, '#00FF00']];
      h += sec(`Transiciones ESRI ${E.metodo.periodos.esri_inicial}–${E.metodo.periodos.esri_final}`, bars(es.map((x) => x[1]), ['Estables', 'Salida', 'Ganancia'], es.map((x) => x[2]), { w: 360, h: 150, fy: (v) => ha(v, 0), label: 'Transiciones ESRI' }));
    }
    if (r.corredores && r.corredores.areas_categoria_ha) {
      const cs = ['alta', 'mediana', 'mediabaja'];
      h += sec('Superficie dentro de corredores', bars(cs.map((k) => r.corredores.areas_categoria_ha[k] || 0), cs.map((k) => E.etiquetas[k]), cs.map((k) => E.colores[k]), { w: 360, h: 150, fy: (v) => ha(v, 0), label: 'Corredores por categoría' }));
    }
    const f = r.fragmentacion;
    if (f && f.parches_geojson && f.parches_geojson.features.length) {
      const cnt = { Alta: 0, Media: 0, Baja: 0 };
      f.parches_geojson.features.forEach((x) => { cnt[x.properties.prioridad_conectividad] = (cnt[x.properties.prioridad_conectividad] || 0) + 1; });
      h += sec('Fragmentos por importancia como conectores', bars(['Alta', 'Media', 'Baja'].map((k) => cnt[k]), ['Alta', 'Media', 'Baja'], ['Alta', 'Media', 'Baja'].map((k) => COL_IMP[k]), { w: 360, h: 150, fy: (v) => fmt(v, 0), label: 'Fragmentos por importancia' })
        + '<p>Índice conector = 0,40 grado + 0,30 intermediación + 0,20 área + 0,10 fuerza (cuantiles 75 % y 50 %).</p>');
    }
    if (r.modo_analisis !== 'corredores' && window.PORTAL && window.PORTAL.api && !r.ejemplo) {
      h += sec('Series anuales por fuente', `<p>Se calculan una por vez en Earth Engine.</p><div class="chk" id="pre-series">${SERIES.map((s) => `<button type="button" class="btn btn-s" data-fuente="${esc(s)}" style="padding:5px 12px;font-size:12px">${esc(s.split(' ')[0])}</button>`).join('')}</div><div id="pre-serie"></div>`);
    }
    return h || '<p>Sin gráficas para este análisis.</p>';
  }
  function serieHtml(s) {
    const cols = Object.keys(s.columnas), x = s.columnas[cols[0]];
    return sec(esc(s.titulo), cols.slice(1).map((c) => `<p><b>${esc(c)}</b></p>` + bars(s.columnas[c], x.map((v) => (typeof v === 'number' && v > 1900 ? "'" + String(v).slice(2) : String(v))), 'var(--azul)', { w: 360, h: 150, every: Math.ceil(x.length / 8), fy: (v) => fmt(v, Math.abs(v) < 2 ? 2 : 0), label: c })).join('') + `<p>${esc(s.descripcion)}</p>`);
  }

  // ------------------------------------------------------------ capas del resultado
  function capasResultado(r) {
    const out = [];
    const f = r.fragmentacion;
    const gj = (k) => f && f[k] && f[k].features && f[k].features.length ? f[k] : null;
    if (r.capas) Object.entries(r.capas).forEach(([k, c]) => { if (c.url) out.push({ k: 'ee_' + k, n: c.nombre, layer: L.tileLayer(c.url, { pane: 'rasters', opacity: 0.9 }), on: k === 'coincidencia', ley: { coincidencia: 'Sectores para revisión', jrc: 'JRC TMF', hansen_post: 'Pérdida Hansen post-2020', hansen_pre: 'Pérdida Hansen 2001-2020', linea_base: 'Cobertura arbórea persistente', esri: 'ESRI LULC', esri_transicion: 'Transiciones ESRI', gedi: 'Altura GEDI', ndvi_delta: 'ΔNDVI', ndvi_clases: 'Vegetación NDVI', bosque_2021: 'Bosque 2021 de contexto' }[k] }); });
    if (gj('parches_geojson')) out.push({ k: 'pre_parches', n: 'Fragmentos de bosque e importancia', on: true, ley: 'Importancia de parches', layer: L.geoJSON(f.parches_geojson, { pane: 'vec', style: (x) => ({ color: '#0b3b36', weight: 1, fillColor: COL_IMP[x.properties.prioridad_conectividad], fillOpacity: 0.5 }), onEachFeature: (x, l) => { const p = x.properties; l.bindTooltip(`<b>Fragmento ${p.patch_id}</b><br>${ha(p.area_ha, 1)} · importancia ${esc(p.prioridad_conectividad)}<br>${esc(p.condicion_cercania)} · índice conector ${nf(p.indice_conector, 2)}`, { className: 'tt', sticky: true }); } }) });
    if (gj('conexiones_geojson')) out.push({ k: 'pre_conex', n: 'Estructura esencial (enlaces)', on: false, ley: 'Estructura esencial', layer: L.featureGroup([L.geoJSON(f.conexiones_geojson, { pane: 'lines', interactive: false, style: () => ({ color: '#fff', weight: 5, opacity: 0.9 }) }), L.geoJSON(f.conexiones_geojson, { pane: 'lines', style: () => ({ color: '#00544d', weight: 2.2 }), onEachFeature: (x, l) => l.bindTooltip(`Enlace · ${nf(x.properties.distancia_m, 0)} m`, { className: 'tt', sticky: true }) })]) });
    if (gj('ruta_corredor_geojson') || gj('corredor_referencia_geojson')) {
      const g = [];
      if (gj('corredor_referencia_geojson')) g.push(L.geoJSON(f.corredor_referencia_geojson, { pane: 'vec', interactive: false, style: () => ({ color: '#73950f', weight: 1.5, fillColor: '#dce8a5', fillOpacity: 0.35 }) }));
      if (gj('ruta_corredor_geojson')) { g.push(L.geoJSON(f.ruta_corredor_geojson, { pane: 'lines', interactive: false, style: () => ({ color: '#fff', weight: 7 }) })); g.push(L.geoJSON(f.ruta_corredor_geojson, { pane: 'lines', interactive: false, style: () => ({ color: '#d97904', weight: 3.5 }) })); }
      out.push({ k: 'pre_ruta', n: 'Ruta potencial al corredor', on: true, ley: 'Ruta potencial al corredor', layer: L.featureGroup(g) });
    }
    if (gj('conexiones_potenciales_geojson')) out.push({ k: 'pre_brechas', n: 'Separaciones potenciales', on: false, ley: 'Separaciones potenciales', layer: L.geoJSON(f.conexiones_potenciales_geojson, { pane: 'lines', style: () => ({ color: '#7c2d12', weight: 2, dashArray: '6 5' }), onEachFeature: (x, l) => l.bindTooltip(`Brecha potencial · ${nf(x.properties.distancia_m, 0)} m`, { className: 'tt', sticky: true }) }) });
    return out;
  }
  function leyendaHtml(nombre) {
    const it = E.leyendas[nombre];
    if (!it) return '';
    return `<div class="cls-l">${it.map(([c, n]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join('')}</div>`;
  }

  // ------------------------------------------------------------ capas fijas de corredores
  function capasCorredores() {
    const corr = L.geoJSON(E.corredores, { pane: 'vec', style: (x) => ({ color: E.colores[x.properties.cat], weight: 1.4, fillColor: E.colores[x.properties.cat], fillOpacity: 0.28 }),
      onEachFeature: (x, l) => { const p = x.properties; l.bindTooltip(`<b>${esc(p.nombre)}</b><br>${esc(p.categoria_etiqueta)} · ${ha(p.area_ha, 0)}${p.es_mesoamericano ? '<br>Corredor Biológico Mesoamericano' : ''}`, { className: 'tt', sticky: true }); } });
    const pts = L.geoJSON(E.puntos, { pane: 'labels', pointToLayer: (x, ll) => L.circleMarker(ll, { radius: 6, color: '#fff', weight: 2, fillColor: '#d0442c', fillOpacity: 1, pane: 'hl' }),
      onEachFeature: (x, l) => { const p = x.properties; l.bindTooltip(`<b>Punto crítico ${esc(p.nombre || '')}</b>${p.notas ? '<br>' + esc(String(p.notas).slice(0, 160)) + '…' : ''}`, { className: 'tt' }); } });
    return { corredores_aa: corr, puntos_aa: pts };
  }

  window.PREEVAL = { E, MODOS, descargar, pedir, pedirSerie, lectura, graficas, serieHtml, capasResultado, leyendaHtml, capasCorredores, COL_PRI };
})();
