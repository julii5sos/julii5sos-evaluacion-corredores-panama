/* Panel · Cuenca del Canal + 10 km y subcuencas (estadísticas del motor) */
(function () {
  const { $, $$, fmt, esc, icon, donut, bars, baseMap } = CP;
  const { M, leyenda, crearCapas, ha, nf, verificar, dibujador, htmlVerificacion } = CANAL;
  const S = M.stats, a0 = String(M.anio0), a1 = String(M.anio1);
  const subs = Object.entries(S).filter(([id]) => id[0] === 's').map(([id, s]) => Object.assign({ id }, s));
  const st = { cu: 'cuenca', su: '', tab: 'resumen', area: null, resA: null, errA: null, met: 'eri', ord: { k: 'eri', d: -1 }, heat: 'k' };
  const h0 = (location.hash || '').slice(1);
  if (S[h0]) { if (h0[0] === 's') st.su = h0; else st.cu = h0; }

  // ------------------------------------------------------------ mapa
  const { map } = baseMap($('#pmap'), { grat: false });
  const T = crearCapas(map);
  const PE = window.PREEVAL;
  Object.assign(T, PE.capasCorredores());

  // ------------------------------------------------------------ datos derivados (comparaciones, series, puntos críticos)
  const AA = Object.keys(S.cuenca.hansen_perdida_anual);            // 2001 … 2025
  const perdTot = (u) => AA.reduce((a, y) => a + (u.hansen_perdida_anual[y] || 0), 0);
  const mediaAnual = (u, y0, y1) => { const ys = AA.filter((y) => +y >= y0 && +y <= y1); return ys.length ? ys.reduce((a, y) => a + (u.hansen_perdida_anual[y] || 0), 0) / ys.length : 0; };
  const geoDe = (id) => (id === 'cuenca' || id === 'area'
    ? M.vector.area_estudio.features.find((f) => f.properties.tipo === (id === 'area' ? 'area_estudio' : 'cuenca'))
    : M.vector.subcuencas_canal.features.find((f) => f.properties.id === id));
  function enAnillo(x, y, r) { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c; } return c; }
  function enGeom(x, y, g) { const ps = g.type === 'Polygon' ? [g.coordinates] : g.coordinates; return ps.some((p) => enAnillo(x, y, p[0]) && !p.slice(1).some((h) => enAnillo(x, y, h))); }
  const PUNTOS = (PE.E.puntos && PE.E.puntos.features) || [];
  const _pts = {};
  const puntosEn = (id) => _pts[id] || (_pts[id] = (() => { const f = geoDe(id); return f ? PUNTOS.filter((p) => enGeom(p.geometry.coordinates[0], p.geometry.coordinates[1], f.geometry)) : []; })());
  function km(la1, lo1, la2, lo2) { const r = Math.PI / 180, a = Math.sin(((la2 - la1) * r) / 2) ** 2 + Math.cos(la1 * r) * Math.cos(la2 * r) * Math.sin(((lo2 - lo1) * r) / 2) ** 2; return 12742 * Math.asin(Math.sqrt(a)); }
  function masCercano(id) {
    const f = geoDe(id); if (!f || !PUNTOS.length) return null;
    const ps = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates; let best = null;
    PUNTOS.forEach((p) => { const [lo, la] = p.geometry.coordinates; ps.forEach((pl) => pl[0].forEach(([x, y]) => { const d = km(la, lo, y, x); if (!best || d < best.km) best = { km: d, p }; })); });
    return best;
  }
  const sg = (v, d, suf) => (v > 0 ? '+' : v < 0 ? '−' : '') + fmt(Math.abs(v), d) + suf;
  const MET = [
    { k: 'eri', n: 'ERI medio', f: (u) => u.eri, t: (v) => fmt(v, 2) },
    { k: 'bosque', n: `Bosque ${a1} (%)`, f: (u) => u.frag[a1].bosque_pct, t: (v) => fmt(v, 1) + ' %' },
    { k: 'dbosque', n: `Cambio de bosque ${a0}–${a1} (pp)`, f: (u) => u.frag[a1].bosque_pct - u.frag[a0].bosque_pct, t: (v) => sg(v, 1, ' pp') },
    { k: 'lpi', n: 'LPI (%)', f: (u) => u.frag[a1].LPI, t: (v) => fmt(v, 1) + ' %' },
    { k: 'connect', n: 'CONNECT (%)', f: (u) => u.frag[a1].CONNECT, t: (v) => fmt(v, 2) + ' %' },
    { k: 'enn', n: 'ENN medio (m)', f: (u) => u.frag[a1].ENN_MN || 0, t: (v) => fmt(v, 0) + ' m' },
    { k: 'perdida', n: `Pérdida ${a0}–${a1} (ha)`, f: (u) => u.perdida_ha, t: (v) => ha(v) },
    { k: 'ganancia', n: `Ganancia ${a0}–${a1} (ha)`, f: (u) => u.ganancia_ha, t: (v) => ha(v) },
    { k: 'neto', n: 'Cambio neto de bosque (ha)', f: (u) => u.ganancia_ha - u.perdida_ha, t: (v) => (v < 0 ? '−' : '+') + ha(Math.abs(v)) },
    { k: 'perdida_pct', n: 'Pérdida (% del área)', f: (u) => (u.perdida_ha / u.area_ha) * 100, t: (v) => fmt(v, 2) + ' %' },
    { k: 'riesgo', n: 'Riesgo medio de pérdida (0–1)', f: (u) => u.riesgo_medio, t: (v) => fmt(v, 2) },
    { k: 'alertas', n: 'Alertas recientes (ha)', f: (u) => u.alertas_ha, t: (v) => ha(v, 1) },
    { k: 'hansen', n: `Pérdida Hansen ${AA[0]}–${AA[AA.length - 1]} (ha)`, f: perdTot, t: (v) => ha(v) },
    { k: 'hansen_k', n: 'Pérdida Hansen (ha por 1000 ha)', f: (u) => (perdTot(u) / u.area_ha) * 1000, t: (v) => fmt(v, 1) },
    { k: 'reciente', n: 'Pérdida Hansen media 2021–2025 (ha/año)', f: (u) => mediaAnual(u, 2021, 2025), t: (v) => fmt(v, 1) + ' ha/año' },
    { k: 'corr', n: 'Dentro de corredores (%)', f: (u) => ((PE.E.interseccion[u.id] || {}).porcentaje_aoi_en_corredores) || 0, t: (v) => fmt(v, 1) + ' %' },
    { k: 'pts', n: 'Puntos críticos (n)', f: (u) => puntosEn(u.id).length, t: (v) => fmt(v, 0) },
    { k: 'proteger', n: 'Por proteger (ha)', f: (u) => u.prioridad_ha.Proteger || 0, t: (v) => ha(v) },
    { k: 'restaurar', n: 'Por restaurar (ha)', f: (u) => u.prioridad_ha.Restaurar || 0, t: (v) => ha(v) },
    { k: 'vigilar', n: 'Por vigilar (ha)', f: (u) => u.prioridad_ha.Vigilar || 0, t: (v) => ha(v) },
  ];
  const MK = Object.fromEntries(MET.map((m) => [m.k, m]));
  let _filas = null;
  const filas = () => _filas || (_filas = subs.map((s) => { const r = { id: s.id, nombre: s.nombre, grupo: s_grupo(s), area: s.area_ha }; MET.forEach((m) => (r[m.k] = m.f(s))); return r; }));
  const COLS = ['area', 'bosque', 'eri', 'lpi', 'connect', 'perdida', 'ganancia', 'riesgo', 'corr', 'pts'];
  const mediana = (a) => { const b = a.slice().sort((x, y) => x - y), n = b.length; return n % 2 ? b[(n - 1) / 2] : (b[n / 2 - 1] + b[n / 2]) / 2; };
  function linea(vals, labs, o) {
    const W = 520, H = o.h || 190, L = 52, B = 26, T = 8, R = 10, iw = W - L - R, ih = H - T - B;
    const m0 = Math.max(...vals, 1), pw = Math.pow(10, Math.floor(Math.log10(m0))), nn = m0 / pw, max = (nn <= 1 ? 1 : nn <= 2 ? 2 : nn <= 5 ? 5 : 10) * pw;
    const X = (i) => L + (vals.length < 2 ? iw / 2 : (iw * i) / (vals.length - 1)), Y = (v) => T + ih - (v / max) * ih;
    let g = '';
    for (let i = 0; i <= 4; i++) { const y = T + ih - (ih * i) / 4; g += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/><text x="${L - 6}" y="${y + 3}" text-anchor="end">${o.fy((max * i) / 4)}</text>`; }
    const pts = vals.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
    g += `<polygon points="${X(0)},${T + ih} ${pts} ${X(vals.length - 1)},${T + ih}" style="fill:${o.col};fill-opacity:.12"/><polyline points="${pts}" fill="none" style="stroke:${o.col};stroke-width:2.2"/>`;
    vals.forEach((v, i) => { if (i % (o.every || 4) === 0 || i === vals.length - 1) g += `<text x="${X(i)}" y="${H - 8}" text-anchor="middle">${labs[i]}</text>`; g += `<circle cx="${X(i)}" cy="${Y(v)}" r="2.6" style="fill:${o.col}"><title>${labs[i]}: ${o.fy(v)}</title></circle>`; });
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label || 'Serie')}">${g}</svg>`;
  }
  function descargarCSV() {
    const cab = ['id', 'subcuenca', 'grupo', 'area_ha'].concat(MET.map((m) => m.n));
    const q = (v) => (typeof v === 'string' ? '"' + v.replace(/"/g, '""') + '"' : v == null ? '' : Math.round(v * 1000) / 1000);
    const txt = [cab.map(q).join(',')].concat(filas().map((r) => [r.id, r.nombre, r.grupo, r.area].concat(MET.map((m) => r[m.k])).map(q).join(','))).join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['﻿' + txt], { type: 'text/csv;charset=utf-8' }));
    a.download = 'subcuencas_conectividad_canal.csv'; document.body.appendChild(a); a.click(); a.remove();
  }
  if (T.area_estudio) T.area_estudio.addTo(map);
  const sub = M.vector.subcuencas_canal ? L.geoJSON(M.vector.subcuencas_canal, {
    pane: 'vec', style: () => ({ className: 'lf-sub' }),
    onEachFeature: (f, l) => { l.bindTooltip(`<b>${esc(f.properties.nombre)}</b><br>${esc(f.properties.grupo)}`, { className: 'tt', sticky: true }); l.on('click', () => { if (dib && dib.activo) return; st.su = f.properties.id; update(true); }); },
  }).addTo(map) : null;
  let hl = L.layerGroup().addTo(map);

  const LEG = [
    { k: 'eri', on: true }, { k: 'connect', on: false }, { k: 'perdida_conectividad', on: false }, { k: 'cambio', on: false },
    { k: 'prioridad', on: false }, { k: 'kba_canal', on: true, n: 'Áreas Clave para la Biodiversidad' },
    { k: 'corredores_aa', on: false, n: 'Corredores · Almanaque Azul' }, { k: 'puntos_aa', on: false, n: 'Puntos críticos de conectividad' },
  ].filter((x) => T[x.k]);
  const PRESET = { resumen: ['eri', 'kba_canal'], conectividad: ['connect', 'perdida_conectividad'], cambio: ['cambio'], prioridades: ['prioridad', 'kba_canal'], corredores: ['corredores_aa', 'puntos_aa'], comparar: ['eri'] };
  function renderLegend() {
    const ult = LEG.filter((x) => x.on && M.capas[x.k]).pop();
    const corrOn = LEG.find((x) => x.k === 'corredores_aa' && x.on);
    $('#p-legend').innerHTML = '<span class="eyebrow">Capas</span>' + LEG.map((x) => `<div class="row"><label for="lg-${x.k}">${esc(x.n || M.capas[x.k].nombre)}</label><span class="tg"><input type="checkbox" id="lg-${x.k}" data-k="${x.k}" ${x.on ? 'checked' : ''}><span></span></span></div>`).join('') + (ult ? leyenda(ult.k) : corrOn ? PE.leyendaHtml('Corredores Almanaque Azul') : '');
    $$('#p-legend input').forEach((i) => i.addEventListener('change', () => { LEG.find((x) => x.k === i.dataset.k).on = i.checked; aplicar(); }));
  }
  function aplicar() { LEG.forEach((x) => { const l = T[x.k]; if (x.on && !map.hasLayer(l)) l.addTo(map); if (!x.on && map.hasLayer(l)) map.removeLayer(l); }); renderLegend(); }
  aplicar();


  // ------------------------------------------------------------ área dibujada por el usuario
  let capaArea = null;
  const dib = dibujador(map, (geo) => { $('#drawbar').hidden = true; ponerArea(geo); }, (n) => { $('#draw-n').textContent = `${n} vértice${n === 1 ? '' : 's'}`; });
  $('#p-draw').addEventListener('click', () => { if (st.area) limpiarArea(); dib.iniciar(); $('#drawbar').hidden = false; });
  $('#draw-end').addEventListener('click', () => dib.terminar());
  $('#draw-undo').addEventListener('click', () => dib.deshacer());
  $('#draw-cancel').addEventListener('click', () => { dib.cancelar(); $('#drawbar').hidden = true; });
  $('#p-clear').addEventListener('click', () => { limpiarArea(); update(true); });
  function limpiarArea() {
    st.area = null; st.resA = null; st.errA = null;
    if (capaArea) { map.removeLayer(capaArea); capaArea = null; }
    $('#p-clear').hidden = true; $('#p-tabs').hidden = false;
  }
  function ponerArea(geo) {
    st.area = geo; st.resA = null; st.errA = null;
    if (capaArea) map.removeLayer(capaArea);
    capaArea = L.geoJSON(geo, { pane: 'hl', interactive: false, style: () => ({ className: 'lf-poly' }) }).addTo(map);
    map.flyToBounds(capaArea.getBounds(), { padding: [60, 60], maxZoom: 14, duration: 0.6 });
    $('#p-clear').hidden = false; $('#p-tabs').hidden = true;
    $('#v-panel').classList.remove('wide');
    render();
    verificar(geo, M.anio0, M.anio1).then((r) => { if (st.area !== geo) return; st.resA = r; render(); })
      .catch((e) => { if (st.area !== geo) return; st.errA = e.message; render(); });
  }
  function renderArea() {
    $('#p-title').textContent = 'Área dibujada';
    $('#crumbs').innerHTML = '<button type="button" data-go="cuenca">Cuenca del Canal</button><span>›</span><span>Área dibujada</span>';
    $$('#crumbs [data-go]').forEach((b) => b.addEventListener('click', () => { limpiarArea(); st.cu = 'cuenca'; st.su = ''; update(true); }));
    const r = st.resA;
    $('#p-lead').innerHTML = r ? `Tu área tiene <b>${ha(r.area_ha, 1)}</b>. Resultados para ${r.anio0}–${r.anio1}.` : st.errA ? '' : 'Calculando los indicadores de tu área…';
    const cuerpo = r ? htmlVerificacion(r) : st.errA ? `<p class="s">${esc(st.errA)}</p>` : '<p class="sim">Calculando…</p>';
    $('#p-wgs').innerHTML = wg('area', 'Resultados del área dibujada', cuerpo, 'Pérdida, ganancia, alertas, ERI y prioridades dentro de tu polígono. El área no se guarda.');
    $$('#p-wgs [data-exp]').forEach((b) => b.addEventListener('click', () => { const x = $('#x-' + b.dataset.exp); x.hidden = !x.hidden; }));
  }

  // ------------------------------------------------------------ selectores
  const selC = $('#p-cuenca'), selS = $('#p-sub');
  const g = {}; subs.forEach((s) => (g[s_grupo(s)] = g[s_grupo(s)] || []).push(s));
  function s_grupo(s) { const f = M.vector.subcuencas_canal.features.find((x) => x.properties.id === s.id); return f ? f.properties.grupo : 'Subcuencas'; }
  selS.innerHTML = '<option value="">Toda la cuenca</option>' + Object.keys(g).sort().map((k) => `<optgroup label="${esc(k)}">${g[k].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')).map((s) => `<option value="${s.id}">${esc(s.nombre)}</option>`).join('')}</optgroup>`).join('');
  $('#p-subhint').textContent = `${subs.length} subcuencas de la Cuenca del Canal`;
  selC.addEventListener('change', () => { st.cu = selC.value; st.su = ''; update(true); });
  selS.addEventListener('change', () => { st.su = selS.value; update(true); });
  $$('#p-tabs button').forEach((b) => b.addEventListener('click', () => {
    st.tab = b.dataset.t; $$('#p-tabs button').forEach((x) => x.setAttribute('aria-selected', x === b));
    LEG.forEach((x) => (x.on = PRESET[st.tab].includes(x.k))); aplicar(); render(); ancho();
  }));
  function ancho() { $('#v-panel').classList.toggle('wide', st.tab === 'comparar'); setTimeout(() => map.invalidateSize(), 260); }

  // ------------------------------------------------------------ widgets
  const uid = () => st.su || st.cu;
  function wg(id, titulo, cuerpo, exp) {
    return `<section class="wg"><div class="wg-h"><h3>${titulo}</h3><div class="wg-tools"><button type="button" data-exp="${id}" aria-label="Qué muestra">i</button></div></div><div class="exp" hidden id="x-${id}">${exp}</div>${cuerpo}</section>`;
  }
  function delta(v, d = 1, suf = '') {
    if (v == null || Math.abs(v) < Math.pow(10, -d) / 2) return '<span class="delta up">sin cambio</span>';
    return `<span class="delta ${v < 0 ? 'dn' : 'up'}">${v < 0 ? '▼' : '▲'} ${fmt(Math.abs(v), d)}${suf}</span>`;
  }
  function ranking(u, clave, f, etiqueta, desc = true) {
    const arr = subs.slice().sort((a, b) => (desc ? clave(b) - clave(a) : clave(a) - clave(b)));
    const ix = arr.findIndex((x) => x.id === u.id);
    const lo = ix >= 0 ? Math.max(0, Math.min(ix - 2, arr.length - 5)) : 0;
    const filas = arr.slice(lo, lo + 5).map((x, i) => `<li class="${x.id === u.id ? 'me' : ''}"><span class="pos">${lo + i + 1}</span><span class="nm">${esc(x.nombre)}</span><span class="num">${f(clave(x))}</span></li>`).join('');
    const frase = ix >= 0 ? `<p class="s"><b>${esc(u.nombre)}</b> ocupa el puesto <b>${ix + 1} de ${arr.length}</b> subcuencas por ${etiqueta}.</p>` : `<p class="s">Subcuencas con ${desc ? 'mayor' : 'menor'} ${etiqueta}.</p>`;
    return frase + `<ol class="rank">${filas}</ol>`;
  }
  function render() {
    if (st.area) { renderArea(); return; }
    const u = Object.assign({ id: uid() }, S[uid()]), f0 = u.frag[a0], f1 = u.frag[a1], nm = esc(u.nombre);
    $('#p-title').textContent = u.nombre;
    const migas = [`<button type="button" data-go="cuenca">Cuenca del Canal</button>`];
    if (st.su) migas.push(`<span>${nm}</span>`);
    $('#crumbs').innerHTML = migas.join('<span>›</span>');
    $$('#crumbs [data-go]').forEach((b) => b.addEventListener('click', () => { st.cu = 'cuenca'; st.su = ''; update(true); }));
    const eriTxt = u.eri > M.cortes[1] ? 'alta' : u.eri < M.cortes[0] ? 'baja' : 'media';
    $('#p-lead').innerHTML = `En <b>${a1}</b>, ${nm} tenía <b>${fmt(f1.bosque_pct, 0)} %</b> de bosque y un ERI medio de <b>${fmt(u.eri, 2)}</b> (resiliencia ${eriTxt}). Entre ${a0} y ${a1} perdió <b>${ha(u.perdida_ha)}</b> y ganó <b>${ha(u.ganancia_ha)}</b> de bosque.`;
    let h = '';
    const PAL_ERI = M.capas.eri.paleta;
    if (st.tab === 'resumen') {
      const c = u.eri_clases;
      const partes = [{ v: c.baja, c: PAL_ERI[0] }, { v: c.media, c: PAL_ERI[2] }, { v: c.alta, c: PAL_ERI[4] }];
      h += wg('eri', 'Índice de Resiliencia Ecológica', `<p class="s">El <b>${fmt(c.alta, 0)} %</b> de ${nm} tiene resiliencia alta (ERI > ${M.cortes[1]}) y el <b>${fmt(c.baja, 0)} %</b> baja (< ${M.cortes[0]}).</p>
        <div class="wg-row"><div class="kv"><div><span><i style="background:${PAL_ERI[4]}"></i>Alta · núcleos íntegros</span><b class="num">${fmt(c.alta, 1)} %</b></div><div><span><i style="background:${PAL_ERI[2]}"></i>Media</span><b class="num">${fmt(c.media, 1)} %</b></div><div><span><i style="background:${PAL_ERI[0]}"></i>Baja · fragmentado o modificado</span><b class="num">${fmt(c.baja, 1)} %</b></div></div>${donut(partes, 150)}</div>`,
        'ERI = 0,35 integridad estructural + 0,25 conectividad (CONNECT) + 0,20 estabilidad topográfica + 0,20 proximidad riparia. Cada componente va de 0 a 1.');
      h += wg('cob', 'Bosque y cambio', `<div class="cards2"><div class="mc"><span>Bosque ${a0}</span><b class="num">${fmt(f0.bosque_pct, 1)} %</b></div><div class="mc"><span>Bosque ${a1}</span><b class="num">${fmt(f1.bosque_pct, 1)} % ${delta(f1.bosque_pct - f0.bosque_pct, 1, ' pp')}</b></div>
        <div class="mc"><span>Pérdida ${a0}–${a1}</span><b class="num" style="color:var(--rojo)">${ha(u.perdida_ha)}</b></div><div class="mc"><span>Ganancia ${a0}–${a1}</span><b class="num" style="color:var(--verde-osc)">${ha(u.ganancia_ha)}</b></div></div>`,
        'Bosque según Dynamic World (clase árboles) en el año base y el actual.');
      if (st.su) h += wg('rk', 'Comparación con otras subcuencas', ranking(u, (x) => x.eri, (v) => fmt(v, 2), 'ERI medio'), 'Posición de la subcuenca según su ERI medio.');
    }
    if (st.tab === 'conectividad') {
      const filas = [['LPI', 'Parche mayor (% del área)', 1], ['CONNECT', 'Conectancia (%)', 2], ['ED', 'Densidad de borde (m/ha)', 2], ['ENN_MN', 'Distancia al vecino más cercano (m)', 0], ['n_parches', 'Número de parches', 0]];
      h += wg('fs', 'Métricas de fragmentación (FRAGSTATS)', `<p class="s">El parche de bosque más grande ocupa el <b>${fmt(f1.LPI, 1)} %</b> de ${nm}; la distancia media entre parches vecinos es <b>${fmt(f1.ENN_MN || 0, 0)} m</b>.</p>
        <div class="tbl"><table class="mini"><thead><tr><th>Métrica</th><th class="c">${a0}</th><th class="c">${a1}</th><th class="c">Cambio</th></tr></thead><tbody>${filas.map(([k, n, d]) => `<tr><td>${n}</td><td class="c num">${nf(f0[k], d)}</td><td class="c num">${nf(f1[k], d)}</td><td class="c">${f0[k] == null || f1[k] == null ? '—' : delta(f1[k] - f0[k], d)}</td></tr>`).join('')}</tbody></table></div>`,
        `Regla de 8 vecinos. CONNECT cuenta los pares de parches a ≤ ${M.connect_umbral_m} m (borde a borde). Un LPI que baja o un ENN que sube indican fragmentación.`);
      h += wg('pc', '¿Dónde se está perdiendo conectividad?', `<div class="cards2"><div class="mc"><span>Con pérdida de conectividad</span><b class="num">${ha(u.perdida_conectividad_ha)}</b></div><div class="mc"><span>Alertas recientes</span><b class="num">${ha(u.alertas_ha, 1)}</b></div><div class="mc"><span>Riesgo medio de pérdida</span><b class="num">${nf(u.riesgo_medio, 2)}</b></div><div class="mc"><span>Cambio de LPI</span><b class="num">${delta(f1.LPI - f0.LPI, 1, ' pp')}</b></div></div>`,
        'Pérdida de conectividad: caída de la superficie de conectividad entre años. Riesgo: probabilidad de pérdida de bosque (0–1).');
      if (st.su) h += wg('rk2', 'Ranking por conectividad', ranking(u, (x) => x.frag[a1].LPI, (v) => fmt(v, 1) + ' %', 'LPI'), 'Posición de la subcuenca según el índice del parche mayor.');
    }
    if (st.tab === 'cambio') {
      const hk = Object.keys(u.hansen_perdida_anual), hv = hk.map((k) => u.hansen_perdida_anual[k]);
      const mx = Math.max(...hv), my = hk[hv.indexOf(mx)];
      h += wg('han', 'Pérdida anual de bosque (Hansen)', `<p class="s">De 2001 a 2025, ${nm} perdió <b>${ha(hv.reduce((a, b) => a + b, 0))}</b> de cobertura arbórea. El año con más pérdida fue <b>${my}</b>.</p>${bars(hv, hk.map((k) => "'" + k.slice(2)), hv.map((_, i) => CP.lossColor(i / 24)), { label: 'Pérdida anual', every: 4, hi: hv.indexOf(mx), fy: (v) => fmt(v, 0) + ' ha' })}`,
        'Hansen Global Forest Change v1.13 (Landsat, 30 m), año de pérdida 2001–2025.');
      h += wg('pg', `Pérdida y ganancia ${a0}–${a1}`, `${bars([u.perdida_ha, u.ganancia_ha], ['Pérdida', 'Ganancia'], ['#d0442c', '#77cc09'], { label: 'Pérdida y ganancia', h: 150, fy: (v) => fmt(v, 0) + ' ha' })}<p class="s">Cambio neto: <b>${u.ganancia_ha - u.perdida_ha >= 0 ? '+' : '−'}${ha(Math.abs(u.ganancia_ha - u.perdida_ha))}</b>.</p>`,
        'Transiciones bosque → no bosque (pérdida) y no bosque → bosque (ganancia) con Dynamic World.');

      const cum = []; hv.reduce((a, v, i) => { cum[i] = a + v; return cum[i]; }, 0);
      const tot = cum[cum.length - 1], r1 = mediaAnual(u, 2016, 2020), r2 = mediaAnual(u, 2021, 2025);
      const tend = r1 > 0 ? ((r2 - r1) / r1) * 100 : null;
      h += wg('cum', 'Pérdida acumulada de cobertura arbórea', `<p class="s">Entre ${hk[0]} y ${hk[hk.length - 1]} se acumularon <b>${ha(tot)}</b> de pérdida, el <b>${fmt((tot / u.area_ha) * 100, 1)} %</b> de la superficie de ${nm}.</p>${linea(cum, hk.map((k) => "'" + k.slice(2)), { col: '#d0442c', fy: (v) => fmt(v, 0) + ' ha', label: 'Pérdida acumulada Hansen' })}`,
        'Suma acumulada de la pérdida anual de Hansen Global Forest Change v1.13. Una curva más empinada significa pérdida más rápida.');
      h += wg('tasa', 'Ritmo de pérdida por periodo', `<div class="cards2"><div class="mc"><span>${hk[0]}–2010</span><b class="num">${fmt(mediaAnual(u, 2001, 2010), 1)} ha/año</b></div><div class="mc"><span>2011–2020</span><b class="num">${fmt(mediaAnual(u, 2011, 2020), 1)} ha/año</b></div><div class="mc"><span>2016–2020</span><b class="num">${fmt(r1, 1)} ha/año</b></div><div class="mc"><span>2021–${hk[hk.length - 1]}</span><b class="num">${fmt(r2, 1)} ha/año ${tend == null ? '' : `<span class="delta ${tend > 0 ? 'dn' : 'up'}">${tend > 0 ? '▲' : '▼'} ${fmt(Math.abs(tend), 0)} %</span>`}</b></div></div>
        <p class="s">${tend == null ? 'No hubo pérdida registrada en 2016–2020 para comparar.' : `Los últimos cinco años pierden <b>${fmt(Math.abs(tend), 0)} % ${tend > 0 ? 'más' : 'menos'}</b> por año que los cinco anteriores.`}</p>`,
        'Promedio anual de pérdida Hansen por periodo. La flecha compara 2021–2025 con 2016–2020 (▲ más pérdida, ▼ menos).');
      if (st.su) h += wg('rk5', 'Pérdida acumulada frente a otras subcuencas', ranking(u, (x) => (perdTot(x) / x.area_ha) * 1000, (v) => fmt(v, 1) + ' ha/1000 ha', 'pérdida acumulada por superficie'), 'Pérdida Hansen acumulada dividida entre el área de la subcuenca, para comparar subcuencas de distinto tamaño.');
    }
    if (st.tab === 'prioridades') {
      const pc = Object.fromEntries(M.capas.prioridad.clases);
      h += wg('pr', '¿Dónde es prioritario intervenir?', `<ul class="prio">${Object.entries(u.prioridad_ha).map(([n, v]) => `<li><span class="sw" style="background:${pc[n]}"></span><span>${n}</span><b class="num">${ha(v)}</b></li>`).join('')}</ul>`,
        'Proteger: bosque con ERI ≥ 0,6 y riesgo alto. Restaurar: pasto o cultivo cerca de bosque y cauces, en laderas. Vigilar: alertas o pérdida de conectividad.');
      h += wg('kb', 'Áreas Clave para la Biodiversidad', u.kba_ha != null ? `<p class="s"><b>${ha(u.kba_ha)}</b> de ${nm} están dentro de una KBA.</p>` : '<p class="s">Las KBA se descargan del servicio de ArcGIS al ejecutar el motor con conexión a internet.</p>', 'KBAs_LATAM_June2024 (ArcGIS Feature Service).');
      if (st.su) h += wg('rk3', 'Subcuencas con más área por restaurar', ranking(u, (x) => x.prioridad_ha.Restaurar, (v) => ha(v), 'área por restaurar'), 'Hectáreas clasificadas como Restaurar.');
    }
    if (st.tab === 'corredores') {
      const c = PE.E.interseccion[uid()];
      if (c) {
        const cats = ['alta', 'mediana', 'mediabaja'];
        h += wg('ci', 'Superficie dentro de corredores', `<p class="s"><b>${fmt(c.porcentaje_aoi_en_corredores, 1)} %</b> de ${nm} (${ha(c.area_en_corredores_ha)}) está dentro de corredores naturales publicados${c.intersecta_mesoamericano ? `, incluidas <b>${ha(c.area_corredor_mesoamericano_ha)}</b> del Corredor Biológico Mesoamericano` : ''}.</p>
          ${c.area_en_corredores_ha > 0 ? bars(cats.map((k) => c.areas_categoria_ha[k] || 0), cats.map((k) => PE.E.etiquetas[k]), cats.map((k) => PE.E.colores[k]), { label: 'Corredores por categoría', h: 170, fy: (v) => ha(v) }) : '<p class="note">Esta área no intersecta ningún corredor publicado. Revisa en la Plataforma si existe una ruta estructural potencial hacia uno cercano.</p>'}`,
          'Intersección medida en Equal Earth Americas (EPSG:8857), un sistema de área equivalente. Categorías originales de Almanaque Azul: alta, mediana y media-baja.');
        if (c.corredores.length) h += wg('cl', 'Corredores que cruzan el área', `<ul class="prio">${c.corredores.map((x) => `<li><span class="sw" style="background:${PE.E.colores[x.categoria]}"></span><span>${esc(x.nombre)}<br><small>${x.categoria_etiqueta} · conductividad media ${fmt(x.cond_promedio, 1)}</small></span><b class="num">${ha(x.interseccion_ha)}</b></li>`).join('')}</ul>`, 'Superficie de cada corredor dentro del área y su conductividad media según Almanaque Azul.');
        const aporte = Math.min(c.porcentaje_aoi_en_corredores / PE.E.metodo.prioridad_visita.porcentaje_saturacion_corredor, 1) + (c.intersecta_mesoamericano ? PE.E.metodo.prioridad_visita.aporte_corredor_mesoamericano : 0);
        h += wg('cv', 'Valor estratégico para la prioridad de visita', `<p class="s">El corredor aportaría <b>+${fmt(aporte, 2)}</b> de un máximo de ${fmt(PE.E.metodo.prioridad_visita.aporte_maximo_corredor, 1)} puntos a la prioridad integrada de visita.</p><p class="note">Aporte = mín(% en corredores / 25, 1) + 0,5 si toca el Corredor Biológico Mesoamericano. Un corredor sin señales de cambio nunca genera por sí solo una prioridad alta.</p>`, 'Regla de calcular_prioridad_visita() en metodologia_indice.py.');
        h += `<a class="btn btn-p" href="plataforma.html" style="align-self:flex-start">Preevaluar en la Plataforma</a>`;
      }

      const pts = puntosEn(uid());
      let cuerpoPts;
      if (pts.length) {
        cuerpoPts = `<p class="s"><b>${pts.length}</b> punto${pts.length === 1 ? '' : 's'} crítico${pts.length === 1 ? '' : 's'} de Almanaque Azul dentro de ${nm}.</p><ul class="prio ptl">${pts.map((q) => { const pr = q.properties.prioridad; return `<li><span class="sw" style="background:${pr === 1 ? '#d0442c' : pr ? '#f2a541' : '#b6bcc8'}"></span><span>Punto ${esc(q.properties.nombre)} · <small>${pr ? 'prioridad ' + pr : 'sin prioridad asignada'}</small><br><small>${esc((q.properties.notas || '').length > 190 ? q.properties.notas.slice(0, 190) + '…' : q.properties.notas || '')}</small></span></li>`; }).join('')}</ul>`;
      } else {
        const c2 = masCercano(uid());
        cuerpoPts = `<p class="s">No hay puntos críticos dentro de ${nm}.${c2 ? ` El más cercano es el <b>Punto ${esc(c2.p.properties.nombre)}</b>, a unos <b>${fmt(c2.km, 0)} km</b> del límite.` : ''}</p>`;
      }
      h += wg('pk', 'Puntos críticos de conectividad', cuerpoPts, `Sitios donde Almanaque Azul marca que la conectividad está amenazada (${PUNTOS.length} en todo Panamá). Distancia aproximada al límite del área, en línea recta.`);
      const CF = (PE.E.corredores && PE.E.corredores.features) || [];
      const CAT = ['alta', 'mediana', 'mediabaja'];
      const resumen = CAT.map((k) => { const fs = CF.filter((x) => x.properties.cat === k); const a = fs.reduce((s, x) => s + (x.properties.area_ha || 0), 0); return { k, n: fs.length, a, cond: a ? fs.reduce((s, x) => s + x.properties.cond_promedio * (x.properties.area_ha || 0), 0) / a : 0 }; });
      const topC = CF.slice().sort((x, y) => (y.properties.area_ha || 0) - (x.properties.area_ha || 0)).slice(0, 5);
      h += wg('red', 'Red de corredores de Panamá', `<div class="tbl"><table class="mini"><thead><tr><th>Categoría</th><th class="c">Corredores</th><th class="c">Superficie</th><th class="c">Conductividad media</th></tr></thead><tbody>${resumen.map((r) => `<tr><td><span class="sw" style="background:${PE.E.colores[r.k]};display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px"></span>${PE.E.etiquetas[r.k]}</td><td class="c num">${r.n}</td><td class="c num">${ha(r.a)}</td><td class="c num">${fmt(r.cond, 1)}</td></tr>`).join('')}</tbody></table></div>
        <p class="s">Los cinco corredores más extensos: ${topC.map((x) => `<b>${esc(x.properties.nombre)}</b> (${ha(x.properties.area_ha)})`).join(', ')}.</p>`, 'Resumen de los polígonos publicados por Almanaque Azul (versión 2024.05). Conductividad media ponderada por superficie.');
    }

    if (st.tab === 'comparar') {
      const F = filas(), M0 = MK[st.met], vals = F.map((r) => r[st.met]), mx = Math.max(...vals.map(Math.abs), 1e-9);
      const orden = F.slice().sort((x, y) => y[st.met] - x[st.met]), mn = orden[orden.length - 1], mxr = orden[0];
      h += wg('cmp1', 'Ranking de subcuencas', `<div class="fld"><label for="cmp-m">Indicador</label><select id="cmp-m">${MET.map((m) => `<option value="${m.k}" ${m.k === st.met ? 'selected' : ''}>${esc(m.n)}</option>`).join('')}</select></div>
        <p class="s">${esc(M0.n)}: mediana <b>${M0.t(mediana(vals))}</b> entre ${F.length} subcuencas; el valor más alto es <b>${esc(mxr.nombre)}</b> (${M0.t(mxr[st.met])}) y el más bajo <b>${esc(mn.nombre)}</b> (${M0.t(mn[st.met])}).</p>
        <ol class="rank cb">${orden.map((r, i) => `<li class="${r.id === st.su ? 'me' : ''}" data-go="${r.id}" tabindex="0"><span class="pos">${i + 1}</span><span class="nm">${esc(r.nombre)}</span><span class="bar"><i style="width:${Math.max(1, (Math.abs(r[st.met]) / mx) * 100)}%;${r[st.met] < 0 ? 'background:var(--rojo)' : ''}"></i></span><span class="num">${M0.t(r[st.met])}</span></li>`).join('')}</ol>`,
        'Todas las subcuencas ordenadas por el indicador elegido. Haz clic en una fila para verla en el mapa y en las demás pestañas. Las subcuencas “L.” (Lago) agregan áreas de otras subcuencas.');
      const ord = st.ord, rowsT = F.slice().sort((x, y) => (typeof x[ord.k] === 'string' ? x[ord.k].localeCompare(y[ord.k], 'es') : x[ord.k] - y[ord.k]) * ord.d);
      const th = (k, n) => `<th class="${k === 'nombre' ? '' : 'c'}"><button type="button" class="sortb" data-sort="${k}">${n}${ord.k === k ? (ord.d > 0 ? ' ▲' : ' ▼') : ''}</button></th>`;
      h += wg('cmp2', 'Tabla comparativa', `<div class="tbl cmp"><table class="mini"><thead><tr>${th('nombre', 'Subcuenca')}${COLS.map((k) => th(k, ({ area: 'Área', bosque: 'Bosque %', eri: 'ERI', lpi: 'LPI', connect: 'CONNECT', perdida: 'Pérdida', ganancia: 'Ganancia', riesgo: 'Riesgo', corr: 'Corredores %', pts: 'Pts. críticos' })[k])).join('')}</tr></thead>
        <tbody>${rowsT.map((r) => `<tr class="${r.id === st.su ? 'me' : ''}" data-go="${r.id}" tabindex="0"><td>${esc(r.nombre)}</td>${COLS.map((k) => `<td class="c num">${k === 'area' ? ha(r.area) : MK[k] ? MK[k].t(r[k]) : fmt(r[k], 0)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
        <button type="button" class="btn btn-s" id="cmp-csv" style="align-self:flex-start">Descargar CSV con todos los indicadores</button>`,
        `Bosque, LPI y CONNECT del año ${a1}; pérdida y ganancia entre ${a0} y ${a1}. Clic en un encabezado para ordenar. El CSV incluye ${MET.length} indicadores por subcuenca.`);
      const top = F.slice().sort((x, y) => y.hansen - x.hansen).slice(0, 15), por = st.heat === 'k';
      const cel = (r, y) => { const v = (r.hist[y] || 0) / (por ? r.area / 1000 : 1); return v; };
      top.forEach((r) => (r.hist = S[r.id].hansen_perdida_anual));
      const mxh = Math.max(...top.flatMap((r) => AA.map((y) => cel(r, y))), 1e-9);
      h += wg('cmp3', 'Pérdida anual por subcuenca', `<div class="fld"><label for="cmp-h">Unidad</label><select id="cmp-h"><option value="k" ${por ? 'selected' : ''}>ha por 1000 ha de superficie</option><option value="ha" ${por ? '' : 'selected'}>Hectáreas</option></select></div>
        <p class="s">Las 15 subcuencas con más pérdida acumulada desde ${AA[0]}. Cuanto más oscuro el cuadro, mayor la pérdida ese año.</p>
        <div class="heat"><table><thead><tr><th></th>${AA.map((y, i) => `<th>${i % 4 === 0 ? "'" + y.slice(2) : ''}</th>`).join('')}</tr></thead><tbody>${top.map((r) => `<tr data-go="${r.id}"><td class="n">${esc(r.nombre)}</td>${AA.map((y) => { const v = cel(r, y); return `<td class="c" style="background:rgba(208,68,44,${v <= 0 ? 0.04 : Math.min(1, 0.12 + Math.sqrt(v / mxh) * 0.88).toFixed(2)})" title="${esc(r.nombre)} · ${y}: ${fmt(v, por ? 1 : 0)} ${por ? 'ha/1000 ha' : 'ha'}"></td>`; }).join('')}</tr>`).join('')}</tbody></table></div>`,
        'Pérdida anual de cobertura arbórea (Hansen v1.13). La escala de color es la raíz cuadrada del valor para que se distingan los años de poca pérdida.');
    }
    h += `<p class="note" style="padding:0 2px">Motor: ${M.modo === 'demo' ? 'capas de demostración' : 'Google Earth Engine'} · ${esc(M.generado.replace('T', ' '))} · celda ${M.escala_m} m.</p>`;
    $('#p-wgs').innerHTML = h;
    $$('#p-wgs [data-exp]').forEach((b) => b.addEventListener('click', () => { const x = $('#x-' + b.dataset.exp); x.hidden = !x.hidden; }));

    $$('#p-wgs [data-go]').forEach((el) => { const ir = () => { st.su = el.dataset.go; update(true); }; el.addEventListener('click', ir); el.addEventListener('keydown', (e) => { if (e.key === 'Enter') ir(); }); });
    $$('#p-wgs [data-sort]').forEach((b) => b.addEventListener('click', (e) => { e.stopPropagation(); const k = b.dataset.sort; st.ord = { k, d: st.ord.k === k ? -st.ord.d : (k === 'nombre' ? 1 : -1) }; render(); }));
    const sm = $('#cmp-m'); if (sm) sm.addEventListener('change', () => { st.met = sm.value; render(); });
    const sh = $('#cmp-h'); if (sh) sh.addEventListener('change', () => { st.heat = sh.value; render(); });
    const sc = $('#cmp-csv'); if (sc) sc.addEventListener('click', descargarCSV);
  }
  function update(fit) {
    if (st.area) limpiarArea();
    selC.value = st.cu; selS.value = st.su;
    map.removeLayer(hl); hl = L.layerGroup().addTo(map);
    const f = st.su ? M.vector.subcuencas_canal.features.find((x) => x.properties.id === st.su)
      : M.vector.area_estudio.features.find((x) => x.properties.tipo === (st.cu === 'area' ? 'area_estudio' : 'cuenca'));
    if (f) { L.geoJSON(f, { pane: 'hl', interactive: false, style: () => ({ className: 'lf-hl' }) }).addTo(hl); if (fit) map.flyToBounds(L.geoJSON(f).getBounds(), { padding: [30, 30], duration: 0.6, maxZoom: 13 }); }
    try { history.replaceState(null, '', '#' + uid()); } catch (e) {}
    render();
  }
  update(true);
  setTimeout(() => map.invalidateSize(), 60);
})();
