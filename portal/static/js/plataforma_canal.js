/* Plataforma SIG · Cuenca del Canal + 10 km
   Capas del motor, verificación de polígonos (dibujados o subidos) y asistente de análisis. */
(function () {
  const { $, $$, fmt, esc, icon, baseMap, setBase } = CP;
  const { M, CAPAS, VECTORES, leyenda, crearCapas, verificar, leerArchivo, dibujador, htmlVerificacion, htmlUnidad } = CANAL;

  // ------------------------------------------------------------ mapa
  const mEl = $('#smap');
  const { map, grat, labels } = baseMap(mEl, { grat: false });
  const T = crearCapas(map);
  const PE = window.PREEVAL;
  Object.assign(T, PE.capasCorredores());
  const B = M.vector.area_estudio ? L.geoJSON(M.vector.area_estudio).getBounds() : null;
  if (B) map.fitBounds(B, { padding: [20, 20] });
  map.on('mousemove', (e) => { $('#coords').textContent = `lat ${fmt(e.latlng.lat, 4)} · lon ${fmt(e.latlng.lng, 4)}`; });

  // ------------------------------------------------------------ capas
  const EST = { area_estudio: true, eri: true, kba_canal: true, corredores_aa: true, puntos_aa: false };
  let RES = [];   // capas del último resultado de preevaluación
  const OP = {};
  const X = {};
  function setOn(k, on) {
    EST[k] = on;
    const l = T[k]; if (!l) return;
    if (on && !map.hasLayer(l)) l.addTo(map);
    if (!on && map.hasLayer(l)) map.removeLayer(l);
    renderLegend();
  }
  function fila(k, n, sub, d, tag) {
    const disp = !!T[k];
    return `<div class="ly ${X[k] ? 'x' : ''}" data-k="${k}"><div class="ly-h"><span class="tg"><input type="checkbox" id="ly-${k}" ${EST[k] ? 'checked' : ''} ${disp ? '' : 'disabled'} aria-label="Mostrar ${esc(n)}"><span></span></span>
      <label class="nm" for="ly-${k}">${esc(n)}<small>${esc(sub)}</small></label>${tag}<button type="button" class="more" aria-label="Detalles de ${esc(n)}">⋯</button></div>
      <div class="ly-x"><p>${d}</p>${M.capas[k] ? leyenda(k) : ''}${M.capas[k] ? `<label class="op">Opacidad<input type="range" min="0" max="100" value="${Math.round((OP[k] ?? T[k].options.opacity) * 100)}" data-op="${k}"><span>${Math.round((OP[k] ?? T[k].options.opacity) * 100)} %</span></label>` : ''}</div></div>`;
  }
  const tagModo = M.modo === 'demo' ? '<span class="tag demo">Demo</span>' : '<span class="tag real">GEE</span>';
  function renderLayers() {
    const g = (titulo, ic, html, abierto = true) => `<div class="lg ${abierto ? 'open' : ''}"><button type="button">${icon(ic)}<span>${titulo}</span><svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="m9 6 6 6-6 6"/></svg></button><div class="lg-items">${html}</div></div>`;
    let h = g('Límites y KBA', 'border', VECTORES.map((v) => fila(v.k, v.n, v.k === 'kba_canal' && !T.kba_canal ? 'Ejecuta el motor con internet para descargarlas' : v.k === 'kba_canal' ? `${M.vector.kba_canal.features.length} áreas` : '', v.d, '<span class="tag real">Real</span>')).join(''));
    h += g('Corredores · Almanaque Azul', 'link', fila('corredores_aa', 'Corredores naturales de Panamá', `${PE.E.corredores.features.length} polígonos · versión 2024.05`, 'Corredores interpretados por la Fundación Almanaque Azul (Omniscape, ventana de 6 km). Categorías originales: alta, mediana y media-baja.', '<span class="tag real">Real</span>')
      + fila('puntos_aa', 'Puntos críticos', `${PE.E.puntos.features.length} puntos`, 'Sitios donde la conectividad está amenazada según Almanaque Azul.', '<span class="tag real">Real</span>'));
    if (RES.length) h += g('Resultado de la preevaluación', 'chart', RES.map((c) => fila(c.k, c.n, '', c.ley ? PE.leyendaHtml(c.ley) : '', '<span class="tag resu">Resultado</span>')).join(''));
    const ics = { 'Conectividad': 'net', 'Resiliencia (ERI)': 'leaf', 'Cobertura y prioridades': 'layers' };
    CAPAS.forEach((gr) => { h += g(gr.g, ics[gr.g], gr.items.map((it) => fila(it.k, M.capas[it.k].nombre, '', it.d, tagModo)).join('')); });
    $('#s-capas').innerHTML = h;
    $$('#s-capas .lg>button').forEach((b) => b.addEventListener('click', () => b.parentElement.classList.toggle('open')));
    $$('#s-capas .ly').forEach((row) => {
      const k = row.dataset.k;
      $('input[type=checkbox]', row).addEventListener('change', (e) => setOn(k, e.target.checked));
      $('.more', row).addEventListener('click', () => { X[k] = !X[k]; row.classList.toggle('x'); });
      const op = $('[data-op]', row);
      if (op) op.addEventListener('input', () => { OP[k] = op.value / 100; T[k].setOpacity(OP[k]); op.nextElementSibling.textContent = op.value + ' %'; });
    });
  }
  function renderLegend() {
    const preOn = RES.filter((c) => EST[c.k] && c.ley);
    if (preOn.length) {
      const c = preOn[0];
      $('#m-legend').hidden = false;
      $('#m-legend').innerHTML = `<span class="eyebrow">${esc(c.n)}</span>${PE.leyendaHtml(c.ley)}`;
      return;
    }
    const on = CAPAS.flatMap((g) => g.items.map((i) => i.k)).filter((k) => EST[k]);
    const k = on[on.length - 1];
    if (k) { $('#m-legend').hidden = false; $('#m-legend').innerHTML = `<span class="eyebrow">${esc(M.capas[k].nombre)}</span>${leyenda(k)}`; return; }
    $('#m-legend').hidden = !EST.corredores_aa;
    if (EST.corredores_aa) $('#m-legend').innerHTML = `<span class="eyebrow">Corredores · Almanaque Azul</span>${PE.leyendaHtml('Corredores Almanaque Azul')}`;
  }
  Object.keys(EST).forEach((k) => EST[k] && T[k] && T[k].addTo(map));
  renderLayers(); renderLegend();

  $$('#s-tabs button').forEach((b) => b.addEventListener('click', () => {
    $$('#s-tabs button').forEach((x) => x.setAttribute('aria-selected', x === b));
    ['capas', 'poligono', 'comparar', 'base'].forEach((s) => ($('#s-' + s).hidden = s !== b.dataset.s));
  }));

  // mapas base
  const BASES = [['auto', 'Gris azulado', 'linear-gradient(#e6ebf3 45%,#ffffff 45%)'], ['claro', 'Blanco', 'linear-gradient(#ffffff 45%,#f3f5f9 45%)'], ['oscuro', 'Azul noche', 'linear-gradient(#0b1d3a 45%,#16305a 45%)'], ['relieve', 'Arena', 'linear-gradient(#efede6 45%,#f8f5ea 45%)']];
  let base = 'auto';
  function renderBases() {
    $('#bm').innerHTML = BASES.map(([k, n, bg]) => `<button type="button" data-b="${k}" aria-pressed="${k === base}"><i style="background:${bg}"></i>${n}</button>`).join('');
    $$('#bm button').forEach((b) => b.addEventListener('click', () => { base = b.dataset.b; setBase(mEl, base); renderBases(); }));
  }
  renderBases();
  $('#bm-lbl').addEventListener('change', (e) => (e.target.checked ? labels.addTo(map) : map.removeLayer(labels)));
  $('#bm-grat').addEventListener('change', (e) => (e.target.checked ? grat.addTo(map) : map.removeLayer(grat)));

  // ------------------------------------------------------------ resultados
  const res = $('#res');
  function mostrar(eyebrow, titulo, sub, html) {
    $('#res-eyebrow').textContent = eyebrow; $('#res-title').textContent = titulo; $('#res-sub').textContent = sub;
    $('#res-b').innerHTML = html;
    res.classList.remove('closed'); $('#res-reopen').hidden = true;
    setTimeout(() => map.invalidateSize(), 220);
  }
  $('#res-close').addEventListener('click', () => { res.classList.add('closed'); $('#res-reopen').hidden = false; setTimeout(() => map.invalidateSize(), 220); });
  $('#res-reopen').addEventListener('click', () => { res.classList.remove('closed'); $('#res-reopen').hidden = true; setTimeout(() => map.invalidateSize(), 220); });

  const busy = $('#busy');
  function ocupado(titulo, pasos) {
    $('#busy-t').textContent = titulo; busy.hidden = false;
    let i = 0;
    const tick = () => {
      $('#busy-steps').innerHTML = pasos.map((s, j) => `<li class="${j < i ? 'done' : j === i ? 'now' : ''}">${j < i ? '✓' : j === i ? '●' : '○'} ${s}</li>`).join('');
      $('#busy-bar').style.width = Math.min(95, (i / pasos.length) * 100) + '%';
      if (i < pasos.length - 1) { i++; t = setTimeout(tick, 700); }
    };
    let t; tick();
    return () => { clearTimeout(t); busy.hidden = true; };
  }

  // ------------------------------------------------------------ polígono
  let poli = null, poliLayer = null;
  const anioMax = M.anio1, anios = [];
  for (let a = Math.min(M.anio0, 2017); a <= anioMax; a++) anios.push(a);
  $('#p-y0').innerHTML = anios.map((a) => `<option ${a === Math.max(M.anio0, anioMax - 5) ? 'selected' : ''}>${a}</option>`).join('');
  $('#p-y1').innerHTML = anios.map((a) => `<option ${a === anioMax ? 'selected' : ''}>${a}</option>`).join('');
  const conServidor = !!(window.PORTAL && window.PORTAL.api);
  $('#p-modo').textContent = conServidor
    ? 'El servidor Python calcula la verificación (con Earth Engine si EE_PROJECT está configurado).'
    : `Sin servidor: cálculo aproximado en el navegador (rejilla de ${window.MOTOR_REJILLA ? window.MOTOR_REJILLA.celda : 180} m, periodo ${M.anio0}–${M.anio1}). Inicia python app.py para el cálculo completo.`;
  if (!conServidor) { $('#p-y0').disabled = true; $('#p-y1').disabled = true; $('#p-y0').value = M.anio0; $('#p-y1').value = M.anio1; }

  if (conServidor && window.COMPARADOR) COMPARADOR.iniciar({ map, getArea: () => (poli ? { geojson: poli } : { unidad: 'cuenca' }), leyendaHtml: PE.leyendaHtml });

  function ponerPoligono(geo, origen) {
    poli = geo;
    if (poliLayer) map.removeLayer(poliLayer);
    poliLayer = L.geoJSON(geo, { pane: 'hl', style: () => ({ className: 'lf-poly' }) }).addTo(map);
    map.flyToBounds(poliLayer.getBounds(), { padding: [60, 60], maxZoom: 14, duration: 0.6 });
    $('#p-run').disabled = false; $('#p-clear').disabled = false;
    $('#p-info').hidden = false;
    $('#p-info').innerHTML = `<b>Polígono listo</b><span>${esc(origen)}</span>`;
  }
  const dib = dibujador(map, (geo) => { $('#drawbar').hidden = true; ponerPoligono(geo, 'Dibujado en el mapa'); }, (n) => { $('#draw-n').textContent = `${n} vértice${n === 1 ? '' : 's'}`; });
  $('#p-draw').addEventListener('click', () => { dib.iniciar(); $('#drawbar').hidden = false; });
  $('#draw-end').addEventListener('click', () => dib.terminar());
  $('#draw-undo').addEventListener('click', () => dib.deshacer());
  $('#draw-cancel').addEventListener('click', () => { dib.cancelar(); $('#drawbar').hidden = true; });
  $('#p-file').addEventListener('change', (e) => {
    const f = e.target.files[0]; if (!f) return;
    leerArchivo(f).then((geo) => ponerPoligono(geo, f.name)).catch((err) => CP.toast(err.message));
    e.target.value = '';
  });
  $('#p-clear').addEventListener('click', () => {
    poli = null; if (poliLayer) map.removeLayer(poliLayer); poliLayer = null;
    $('#p-run').disabled = true; $('#p-clear').disabled = true; $('#p-info').hidden = true;
  });
  $('#p-tipo').addEventListener('change', () => { $('#p-umbral-fld').hidden = !['corredores', 'integral'].includes($('#p-tipo').value); $('#p-anios').hidden = $('#p-tipo').value !== 'motor'; });
  function correrVerificacion() {
    if (!poli) return;
    const tipo = $('#p-tipo').value;
    if (tipo !== 'motor') { ejecutarPre({ geojson: poli, modo: tipo, umbral_m: +$('#p-umbral').value, area_min_ha: 0 }, 'Polígono dibujado o subido'); return; }
    const a0 = +$('#p-y0').value, a1 = +$('#p-y1').value;
    if (a1 <= a0) { CP.toast('El año final debe ser posterior al inicial.'); return; }
    const fin = ocupado('Verificando polígono', conServidor
      ? ['Enviando polígono al servidor', 'Bosque por año (Dynamic World)', 'Pérdida, ganancia y alertas', 'Fragmentación y conectividad', 'ERI, prioridades y KBA']
      : ['Leyendo rejilla del motor', 'Recortando al polígono', 'Pérdida, ganancia y alertas', 'ERI y prioridades']);
    verificar(poli, a0, a1).then((r) => {
      fin();
      mostrar('Verificación de polígono', 'Polígono verificado', `${CANAL.ha(r.area_ha, 1)} · ${r.anio0}–${r.anio1}`, htmlVerificacion(r));
    }).catch((err) => { fin(); CP.toast(err.message); });
  }
  $('#p-run').addEventListener('click', correrVerificacion);

  // ------------------------------------------------------------ asistente de análisis
  const TIPOS = [
    { k: 'territorial', pre: true, n: 'Preevaluación territorial', d: 'Indicios satelitales de cambio forestal (JRC, Hansen, ESRI, GEDI y NDVI) y atención sugerida. Índice de 0 a 6,5.', ic: 'warn', capas: [] },
    { k: 'corredores', pre: true, n: 'Corredores y conectividad', d: 'Corredores de Almanaque Azul, fragmentación del bosque, red de parches y ruta estructural potencial a un corredor.', ic: 'link', capas: [] },
    { k: 'integral', pre: true, n: 'Preevaluación integral', d: 'Une cambios, corredores y estructura del bosque en una prioridad de visita y dónde enfocarla.', ic: 'core', capas: [] },
    { k: 'conectividad', n: '¿Dónde hay conectividad?', d: 'CONNECT, LPI y ENN por unidad; mapa de conectividad de parches.', ic: 'net', capas: ['connect'] },
    { k: 'fragmentacion', n: '¿Dónde hay fragmentación?', d: 'Métricas FRAGSTATS: LPI, CONNECT, ED y ENN, año base frente a actual.', ic: 'chart', capas: ['connect', 'cambio'] },
    { k: 'eri', n: 'Índice de Resiliencia Ecológica (ERI)', d: 'Integridad estructural, conectividad, estabilidad topográfica y proximidad riparia.', ic: 'leaf', capas: ['eri'] },
    { k: 'perdida_conectividad', n: '¿Dónde se está perdiendo conectividad?', d: 'Caída de conectividad, alertas recientes y riesgo de pérdida.', ic: 'down', capas: ['perdida_conectividad', 'riesgo', 'alertas'] },
    { k: 'cobertura', n: 'Pérdida y ganancia de cobertura', d: 'Bosque perdido y ganado; pérdida anual Hansen 2001–2025.', ic: 'layers', capas: ['cambio'] },
    { k: 'prioridades', n: '¿Dónde es prioritario intervenir?', d: 'Proteger, restaurar o vigilar según ERI, riesgo, alertas y cauces.', ic: 'core', capas: ['prioridad'] },
  ];
  const UNIDADES = Object.entries(M.stats).map(([id, s]) => ({ id, n: s.nombre }));
  const cfg = { tipo: 'integral', area: 'cuenca', umbral: 500, areaMin: 0 };
  let step = 0;
  const esPre = () => !!(TIPOS.find((x) => x.k === cfg.tipo) || {}).pre;
  const STEPS_ = () => (esPre() ? ['Pregunta', 'Área', 'Parámetros', 'Revisión'] : ['Pregunta', 'Área', 'Revisión']);
  const modal = $('#modal');
  function abrir() { step = 0; dibujarPaso(); modal.hidden = false; $('#m-next').focus(); }
  function cerrar() { modal.hidden = true; $('#run-open').focus(); }
  $('#run-open').addEventListener('click', abrir);
  $('#m-close').addEventListener('click', cerrar);
  modal.addEventListener('click', (e) => { if (e.target === modal) cerrar(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !modal.hidden) cerrar(); });
  function nombreArea() { return cfg.area === 'poligono' ? 'Polígono dibujado o subido' : M.stats[cfg.area].nombre; }
  function dibujarPaso() {
    const STEPS = STEPS_(), ultimo = STEPS.length - 1, nombre = STEPS[step];
    $('#m-steps').innerHTML = STEPS.map((s, i) => `<li class="${i === step ? 'cur' : i < step ? 'ok' : ''}"><i>${i < step ? '✓' : i + 1}</i><span>${s}</span></li>`).join('');
    $('#m-back').disabled = step === 0; $('#m-next').textContent = step === ultimo ? 'Hacer análisis' : 'Siguiente'; $('#m-err').textContent = '';
    const b = $('#m-body');
    const opt = (t) => `<label class="opt"><input type="radio" name="tipo" value="${t.k}" ${cfg.tipo === t.k ? 'checked' : ''}>${icon(t.ic)}<div><b>${t.n}</b><span>${t.d}</span></div></label>`;
    if (nombre === 'Pregunta') {
      b.innerHTML = '<h3>¿Qué quieres saber?</h3><p class="sub">Todos los análisis cubren la Cuenca del Canal y su franja de 10 km.</p>'
        + '<p class="eyebrow">Preevaluación para orientar visitas</p>' + TIPOS.filter((t) => t.pre).map(opt).join('')
        + '<p class="eyebrow" style="margin-top:6px">Indicadores del motor de la cuenca</p>' + TIPOS.filter((t) => !t.pre).map(opt).join('');
      $$('input[name=tipo]', b).forEach((r) => r.addEventListener('change', () => { cfg.tipo = r.value; dibujarPaso(); }));
    } else if (nombre === 'Parámetros') {
      const P = PE.E.metodo.periodos;
      const conect = cfg.tipo !== 'territorial';
      b.innerHTML = `<h3>Parámetros</h3>${cfg.tipo !== 'corredores' ? `<p class="sub">Los periodos del índice son fijos para que todas las áreas sean comparables.</p><dl class="rev"><dt>JRC TMF</dt><dd>Estado ${P.jrc_diagnostico}</dd><dt>Hansen</dt><dd>Pérdida 2021–${P.hansen_diagnostico}</dd><dt>ESRI</dt><dd>Transición ${P.esri_inicial}–${P.esri_final}</dd><dt>NDVI</dt><dd>${P.ndvi_inicial}–${P.ndvi_final}</dd></dl>` : ''}
        ${conect ? `<div class="sel-grid"><div class="fld"><label for="m-umbral">Distancia máxima entre fragmentos</label><select id="m-umbral">${[100, 200, 300, 500, 750, 1000, 1500, 2000].map((v) => `<option value="${v}" ${v === cfg.umbral ? 'selected' : ''}>${v} m</option>`).join('')}</select><span class="hint">Dos fragmentos se consideran cercanos si sus bordes están a esta distancia o menos.</span></div>
        <div class="fld"><label for="m-amin">Área mínima de fragmento (ha)</label><input type="number" id="m-amin" min="0" step="0.5" value="${cfg.areaMin}"><span class="hint">Aumenta este valor en áreas con miles de fragmentos.</span></div></div>` : ''}`;
      if (conect) { $('#m-umbral').addEventListener('change', (e) => (cfg.umbral = +e.target.value)); $('#m-amin').addEventListener('input', (e) => (cfg.areaMin = Math.max(0, +e.target.value || 0))); }
    } else if (nombre === 'Área') {
      const subs = UNIDADES.filter((u) => u.id[0] === 's').sort((a, c) => a.n.localeCompare(c.n, 'es'));
      b.innerHTML = `<h3>Elige el área</h3><p class="sub">Cuenca completa, con amortiguamiento, una subcuenca o el polígono que dibujaste o subiste.</p>
        <div class="fld"><label for="m-area">Área de análisis</label><select id="m-area">
          <option value="cuenca">Cuenca del Canal</option><option value="area">Cuenca del Canal + 10 km</option>
          <optgroup label="Subcuencas">${subs.map((u) => `<option value="${u.id}">${esc(u.n)}</option>`).join('')}</optgroup>
          <option value="poligono" ${poli ? '' : 'disabled'}>Polígono dibujado o subido${poli ? '' : ' (dibújalo primero en la pestaña Polígono)'}</option></select></div>`;
      $('#m-area').value = cfg.area; $('#m-area').addEventListener('change', (e) => (cfg.area = e.target.value));
    } else {
      const t = TIPOS.find((x) => x.k === cfg.tipo);
      b.innerHTML = t.pre
        ? `<h3>Revisa y ejecuta</h3><dl class="rev"><dt>Análisis</dt><dd>${t.n}</dd><dt>Área</dt><dd>${esc(nombreArea())}</dd>${t.k !== 'territorial' ? `<dt>Distancia entre fragmentos</dt><dd>${cfg.umbral} m</dd>` : ''}<dt>Fuentes</dt><dd>${t.k === 'corredores' ? 'Almanaque Azul 2024.05 · bosque 2021' : 'JRC · Hansen · ESRI · GEDI · NDVI' + (t.k === 'integral' ? ' · corredores · bosque 2021' : '')}</dd></dl><p class="sub" style="margin-top:4px">Preevaluación indicativa para orientar una revisión; no certifica ni confirma hallazgos en campo.</p>`
        : `<h3>Revisa y ejecuta</h3><dl class="rev"><dt>Pregunta</dt><dd>${t.n}</dd><dt>Área</dt><dd>${esc(nombreArea())}</dd><dt>Periodo</dt><dd>${M.anio0}–${M.anio1}</dd><dt>Resolución</dt><dd>${M.escala_m} m</dd><dt>Datos</dt><dd>${M.modo === 'demo' ? 'Capas de demostración' : 'Google Earth Engine'}</dd></dl>`;
    }
  }
  $('#m-back').addEventListener('click', () => { if (step > 0) { step--; dibujarPaso(); } });
  $('#m-next').addEventListener('click', () => {
    if (step < STEPS_().length - 1) { step++; dibujarPaso(); return; }
    cerrar(); ejecutar();
  });
  let hl = null;
  function ejecutar() {
    const t = TIPOS.find((x) => x.k === cfg.tipo);
    if (t.pre) {
      const p = { modo: t.k, umbral_m: cfg.umbral, area_min_ha: cfg.areaMin };
      if (cfg.area === 'poligono') p.geojson = poli; else p.unidad = cfg.area;
      ejecutarPre(p, nombreArea());
      return;
    }
    CAPAS.forEach((g) => g.items.forEach((i) => setOn(i.k, t.capas.includes(i.k))));
    renderLayers();
    if (cfg.area === 'poligono') { correrVerificacion(); return; }
    if (hl) map.removeLayer(hl);
    const geo = cfg.area === 'cuenca' ? M.vector.area_estudio.features.find((f) => f.properties.tipo === 'cuenca')
      : cfg.area === 'area' ? M.vector.area_estudio.features.find((f) => f.properties.tipo === 'area_estudio')
        : M.vector.subcuencas_canal.features.find((f) => f.properties.id === cfg.area);
    if (geo) { hl = L.geoJSON(geo, { pane: 'hl', interactive: false, style: () => ({ className: 'lf-hl' }) }).addTo(map); map.flyToBounds(hl.getBounds(), { padding: [30, 30], duration: 0.6 }); }
    const fin = ocupado(t.n, ['Leyendo resultados del motor', 'Resumiendo por área']);
    setTimeout(() => { fin(); mostrar(t.n, nombreArea(), `${M.anio0}–${M.anio1} · ${CANAL.ha(M.stats[cfg.area].area_ha)}`, htmlUnidad(M.stats[cfg.area], cfg.tipo)); }, 600);
  }

  // ------------------------------------------------------------ preevaluación (método del repositorio)
  function quitarResultado() {
    RES.forEach((c) => { if (map.hasLayer(c.layer)) map.removeLayer(c.layer); delete T[c.k]; delete EST[c.k]; });
    RES = [];
  }
  function ejecutarPre(p, nombre) {
    const t = TIPOS.find((x) => x.k === p.modo);
    const pasos = { territorial: ['Preparando el área', 'JRC TMF y Hansen', 'ESRI, GEDI y NDVI', 'Señales, puntaje y consistencia', 'Capas del mapa'],
      corredores: ['Preparando el área', 'Intersección con corredores', 'Bosque y entorno de 5 km', 'Red de parches e índice conector', 'Ruta potencial al corredor'],
      integral: ['Preparando el área', 'Señales satelitales', 'Corredores', 'Red de parches', 'Prioridad integrada de visita'] }[p.modo];
    const fin = ocupado(t.n, pasos);
    PE.pedir(p).then((r) => { fin(); mostrarPre(r, nombre, p); }).catch((err) => { fin(); CP.toast(err.message); });
  }
  function mostrarPre(r, nombre, p) {
    quitarResultado();
    RES = PE.capasResultado(r);
    RES.forEach((c) => { T[c.k] = c.layer; EST[c.k] = c.on; if (c.on) c.layer.addTo(map); });
    CAPAS.forEach((g) => g.items.forEach((i) => setOn(i.k, false)));
    setOn('corredores_aa', r.modo_analisis !== 'territorial');
    renderLayers(); renderLegend();
    if (hl) map.removeLayer(hl);
    const geo = r.geometria || (p.unidad === 'cuenca' ? M.vector.area_estudio.features.find((f) => f.properties.tipo === 'cuenca')
      : p.unidad === 'area' ? M.vector.area_estudio.features.find((f) => f.properties.tipo === 'area_estudio')
        : M.vector.subcuencas_canal.features.find((f) => f.properties.id === p.unidad));
    if (geo) { hl = L.geoJSON(geo, { pane: 'hl', interactive: false, style: () => ({ className: 'lf-hl' }) }).addTo(map); map.flyToBounds(hl.getBounds(), { padding: [30, 30], duration: 0.6 }); }
    const html = `<div class="rtabs" role="tablist"><button type="button" role="tab" data-r="lectura" aria-selected="true">Lectura</button><button type="button" role="tab" data-r="graficas" aria-selected="false">Gráficas</button></div>
      <div id="r-lectura" class="rpanel">${PE.lectura(r)}</div><div id="r-graficas" class="rpanel" hidden>${PE.graficas(r)}</div>`;
    mostrar(r.modo_titulo || 'Preevaluación', nombre, `${CANAL.ha(r.area_ha, 1)}${r.umbral_m && r.modo_analisis !== 'territorial' ? ' · distancia ' + r.umbral_m + ' m' : ''}`, html);
    $$('#res-b .rtabs button').forEach((b) => b.addEventListener('click', () => {
      $$('#res-b .rtabs button').forEach((x) => x.setAttribute('aria-selected', x === b));
      $('#r-lectura').hidden = b.dataset.r !== 'lectura'; $('#r-graficas').hidden = b.dataset.r !== 'graficas';
    }));
    $$('#res-b [data-desc]').forEach((b) => b.addEventListener('click', () => {
      const m = $('#desc-msg'), txt = b.textContent; b.disabled = true; b.textContent = 'Preparando…';
      PE.descargar(b.dataset.desc, Object.assign({ modo: p.modo, umbral_m: p.umbral_m, area_min_ha: p.area_min_ha }, p.geojson ? { geojson: p.geojson } : { unidad: p.unidad }), nombre)
        .then((av) => { m.textContent = av || 'Descarga lista.'; }).catch((e) => { m.textContent = e.message; })
        .finally(() => { b.disabled = false; b.textContent = txt; });
    }));
    $$('#pre-series button').forEach((b) => b.addEventListener('click', () => {
      $('#pre-serie').innerHTML = '<p class="sim">Calculando en Earth Engine…</p>';
      PE.pedirSerie(Object.assign({ fuente: b.dataset.fuente }, p.geojson ? { geojson: p.geojson } : { unidad: p.unidad }))
        .then((s) => { $('#pre-serie').innerHTML = PE.serieHtml(s); }).catch((e) => { $('#pre-serie').innerHTML = `<p class="sim">${esc(e.message)}</p>`; });
    }));
  }

  // estado del servidor
  function fijarAnios(txt) { $('#p-y0').value = M.anio0; $('#p-y1').value = M.anio1; $('#p-y0').disabled = true; $('#p-y1').disabled = true; $('#p-modo').textContent = txt; }
  if (conServidor) fetch(window.PORTAL.api + 'motor/estado').then((r) => r.json()).then((e) => {
    if (e.earth_engine) $('#p-modo').textContent = 'Earth Engine conectado: la verificación usa Dynamic World a 10 m, Hansen y alertas Sentinel-1 en vivo, para el periodo que elijas.';
    else fijarAnios(`Servidor Python sin Earth Engine: se usan los rásters del motor (periodo ${M.anio0}–${M.anio1}). Define EE_PROJECT para elegir otro periodo y calcular en vivo.`);
  }).catch(() => fijarAnios(`No se pudo consultar el servidor; periodo ${M.anio0}–${M.anio1}.`));
  setTimeout(() => map.invalidateSize(), 60);
})();
