/* Conectividad Panamá · utilidades del motor de la Cuenca del Canal (+10 km)
   Usa window.MOTOR (capas y estadísticas que genera ejecutar_motor.py) y
   window.MOTOR_REJILLA (rejilla para verificar polígonos en el navegador). */
(function () {
  const { $, fmt, esc, icon, bars } = CP;
  const M = window.MOTOR;
  const nf = (v, d = 0) => (v == null || Number.isNaN(v) ? '—' : fmt(v, d));
  const ha = (v, d = 0) => (v == null ? '—' : v >= 10000 ? fmt(v / 1000, 1) + ' kha' : fmt(v, d) + ' ha');

  // ------------------------------------------------------------ capas
  const CAPAS = [
    { g: 'Conectividad', items: [
      { k: 'connect', d: '¿Dónde hay conectividad? Conectividad de parches de bosque (CONNECT ponderado por área) en una ventana de 1,5 km.' },
      { k: 'perdida_conectividad', d: '¿Dónde se está perdiendo? Caída de la conectividad entre el año base y el actual.' },
      { k: 'riesgo', d: '¿Dónde hay riesgo de perderla? Probabilidad de pérdida de bosque según presiones recientes (Random Forest).' },
      { k: 'alertas', d: 'Alertas recientes de pérdida detectadas con radar Sentinel-1 (ve a través de las nubes).' },
    ] },
    { g: 'Resiliencia (ERI)', items: [
      { k: 'eri', d: 'ERI = 0,35 integridad estructural + 0,25 conectividad + 0,20 estabilidad topográfica + 0,20 proximidad riparia.' },
      { k: 'estructura', d: 'Altura de dosel y área basal (o probabilidad de árboles si no hay parcelas de campo).' },
      { k: 'topografia', d: 'Inverso del riesgo de erosión ponderado por pendiente.' },
      { k: 'riparia', d: 'Cercanía a cauces perennes (1 sobre el cauce, 0 a 1 km o más).' },
    ] },
    { g: 'Cobertura y prioridades', items: [
      { k: 'cambio', d: 'Bosque perdido y ganado entre el año base y el actual (Dynamic World).' },
      { k: 'prioridad', d: 'Proteger: bosque de alto ERI con riesgo alto. Restaurar: pasto o cultivo cerca de bosque y cauces. Vigilar: alertas o pérdida de conectividad.' },
    ] },
  ];
  const VECTORES = [
    { k: 'area_estudio', n: 'Cuenca del Canal + 10 km', d: 'Área de estudio: cuenca hidrográfica y su franja de amortiguamiento de 10 km.' },
    { k: 'subcuencas_canal', n: 'Subcuencas del Canal', d: 'Subcuencas oficiales de la Cuenca Hidrográfica del Canal de Panamá.' },
    { k: 'kba_canal', n: 'Áreas Clave para la Biodiversidad (KBA)', d: 'KBA de Latinoamérica (junio 2024) que tocan el área de estudio.' },
  ];

  function leyenda(k) {
    const c = M.capas[k];
    if (!c) return '';
    if (c.tipo === 'rampa') {
      const st = c.paleta.map((col, i) => `${col} ${(i * 100) / c.paleta.length}% ${((i + 1) * 100) / c.paleta.length}%`).join(',');
      const r = c.rango;
      if (c.cortes) return `<div class="clsrow">${c.paleta.map((col, i) => `<span><i style="background:${col}"></i>${['Muy baja', 'Baja', 'Media', 'Alta', 'Muy alta'][i]}<small>${fmt(c.cortes[i], 2)}–${fmt(c.cortes[i + 1], 2)}</small></span>`).join('')}</div>`;
      const n = c.paleta.length, paso = (r[1] - r[0]) / n;
      return `<div class="ramp" style="background:linear-gradient(90deg,${st})"></div><div class="ramp-l">${c.paleta.map((_, i) => `<span>${fmt(r[0] + paso * i, r[1] > 2 ? 0 : 1)}</span>`).join('')}<span>${fmt(r[1], r[1] > 2 ? 0 : 1)}</span></div>`;
    }
    return `<div class="cls-l">${c.clases.map(([n, col]) => `<span><i style="background:${col}"></i>${n}</span>`).join('')}</div>`;
  }

  function crearCapas(map) {
    const L_ = {};
    Object.entries(M.capas).forEach(([k, c]) => {
      L_[k] = L.imageOverlay(c.url, c.bounds, { pane: 'rasters', opacity: k === 'eri' || k === 'connect' ? 0.85 : 1, interactive: false });
    });
    const V = M.vector || {};
    if (V.area_estudio) {
      L_.area_estudio = L.geoJSON(V.area_estudio, { pane: 'vec', interactive: false,
        style: (f) => (f.properties.tipo === 'cuenca' ? { className: 'lf-canal' } : { className: 'lf-buffer' }) });
    }
    if (V.subcuencas_canal) {
      L_.subcuencas_canal = L.geoJSON(V.subcuencas_canal, { pane: 'vec', style: () => ({ className: 'lf-sub' }),
        onEachFeature: (f, l) => l.bindTooltip(`<b>${esc(f.properties.nombre)}</b><br>${esc(f.properties.grupo)}`, { className: 'tt', sticky: true }) });
    }
    if (V.kba_canal && V.kba_canal.features && V.kba_canal.features.length) {
      L_.kba_canal = L.geoJSON(V.kba_canal, { pane: 'vec', style: () => ({ className: 'lf-kba' }),
        onEachFeature: (f, l) => { const p = f.properties; const n = p.IntName || p.NatName || p.Name || p.name || 'KBA'; l.bindTooltip(`<b>${esc(n)}</b><br>KBA`, { className: 'tt', sticky: true }); } });
    }
    return L_;
  }

  // ------------------------------------------------------------ geometría
  // WGS 84 → UTM 17N (fórmulas de Snyder), suficiente para la precisión de la rejilla.
  function utm17(lat, lon) {
    const a = 6378137, f = 1 / 298.257223563, k0 = 0.9996, e2 = f * (2 - f), ep2 = e2 / (1 - e2);
    const lam0 = (-81 * Math.PI) / 180, phi = (lat * Math.PI) / 180, lam = (lon * Math.PI) / 180;
    const N = a / Math.sqrt(1 - e2 * Math.sin(phi) ** 2), T = Math.tan(phi) ** 2, Cc = ep2 * Math.cos(phi) ** 2, A = Math.cos(phi) * (lam - lam0);
    const Mm = a * ((1 - e2 / 4 - (3 * e2 ** 2) / 64 - (5 * e2 ** 3) / 256) * phi - ((3 * e2) / 8 + (3 * e2 ** 2) / 32 + (45 * e2 ** 3) / 1024) * Math.sin(2 * phi)
      + ((15 * e2 ** 2) / 256 + (45 * e2 ** 3) / 1024) * Math.sin(4 * phi) - ((35 * e2 ** 3) / 3072) * Math.sin(6 * phi));
    const x = k0 * N * (A + ((1 - T + Cc) * A ** 3) / 6 + ((5 - 18 * T + T ** 2 + 72 * Cc - 58 * ep2) * A ** 5) / 120) + 500000;
    const y = k0 * (Mm + N * Math.tan(phi) * (A ** 2 / 2 + ((5 - T + 9 * Cc + 4 * Cc ** 2) * A ** 4) / 24 + ((61 - 58 * T + T ** 2 + 600 * Cc - 330 * ep2) * A ** 6) / 720));
    return [x, y];
  }
  function anillos(geo) {
    const out = [];
    const add = (g) => { if (!g) return; if (g.type === 'Polygon') out.push(g.coordinates); else if (g.type === 'MultiPolygon') g.coordinates.forEach((p) => out.push(p)); };
    if (geo.type === 'FeatureCollection') geo.features.forEach((f) => add(f.geometry));
    else if (geo.type === 'Feature') add(geo.geometry); else add(geo);
    return out;
  }
  function dentro(x, y, ring) {
    let c = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
    }
    return c;
  }
  function areaUTM(polys) {
    let s = 0;
    polys.forEach((p) => p.forEach((r, ri) => { let a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += r[j][0] * r[i][1] - r[i][0] * r[j][1]; s += (ri === 0 ? 1 : -1) * Math.abs(a / 2); }));
    return s;
  }

  // ------------------------------------------------------------ verificación en el navegador
  let RJ = null;
  function rejilla() {
    if (RJ || !window.MOTOR_REJILLA) return RJ;
    const R = window.MOTOR_REJILLA, dec = (b) => Uint8Array.from(atob(b), (c) => c.charCodeAt(0));
    RJ = Object.assign({}, R, { flags: dec(R.flags), eri: dec(R.eri), prioridad: dec(R.prioridad) });
    return RJ;
  }
  function verificarNavegador(geo) {
    const R = rejilla();
    if (!R) throw new Error('Falta la rejilla del motor.');
    const polys = anillos(geo).map((p) => p.map((r) => r.map(([lon, lat]) => utm17(lat, lon))));
    if (!polys.length) throw new Error('El archivo no contiene polígonos.');
    const area = areaUTM(polys) / 1e4;
    if (area < 0.1) throw new Error('El polígono es demasiado pequeño (menos de 0,1 ha).');
    let xmin = Infinity, ymin = Infinity, xmax = -Infinity, ymax = -Infinity;
    polys.forEach((p) => p[0].forEach(([x, y]) => { xmin = Math.min(xmin, x); xmax = Math.max(xmax, x); ymin = Math.min(ymin, y); ymax = Math.max(ymax, y); }));
    const c = R.celda, c0 = Math.max(0, Math.floor((xmin - R.x0) / c)), c1 = Math.min(R.w - 1, Math.floor((xmax - R.x0) / c));
    const f0 = Math.max(0, Math.floor((R.y1 - ymax) / c)), f1 = Math.min(R.h - 1, Math.floor((R.y1 - ymin) / c));
    const n = { tot: 0, val: 0, b0: 0, b1: 0, perd: 0, gan: 0, al: 0, pc: 0, eri: 0, ec: [0, 0, 0], pri: [0, 0, 0, 0] };
    for (let fy = f0; fy <= f1; fy++) {
      for (let fx = c0; fx <= c1; fx++) {
        const x = R.x0 + (fx + 0.5) * c, y = R.y1 - (fy + 0.5) * c;
        const inside = polys.some((p) => dentro(x, y, p[0]) && !p.slice(1).some((h) => dentro(x, y, h)));
        if (!inside) continue;
        n.tot++;
        const i = fy * R.w + fx, fl = R.flags[i];
        if (!(fl & 1)) continue;
        n.val++;
        const b0 = fl & 2, b1 = fl & 4;
        if (b0) n.b0++; if (b1) n.b1++; if (b0 && !b1) n.perd++; if (!b0 && b1) n.gan++;
        if (fl & 8) n.al++; if (fl & 16) n.pc++;
        const e = (R.eri[i] - 1) / 254; n.eri += e; n.ec[e < R.cortes[0] ? 0 : e > R.cortes[1] ? 2 : 1]++;
        n.pri[R.prioridad[i] - 1]++;
      }
    }
    if (!n.val) throw new Error('El polígono está fuera del área de estudio (Cuenca del Canal + 10 km) o es más pequeño que la celda de 180 m del modo sin servidor.');
    const k = (c * c) / 1e4, esc_ = area / Math.max(1, n.tot * k);   // ajusta el conteo de celdas al área real
    const h = (v) => Math.round(v * k * esc_ * 10) / 10;
    const pct = (v) => Math.round((v / n.val) * 1000) / 10;
    const perd = h(n.perd), gan = h(n.gan), al = h(n.al);
    const neto = Math.round((gan - perd) * 10) / 10;
    let estado = 'estable', ver = 'La cobertura de bosque se mantuvo estable en el periodo.';
    if (al > 0) { estado = 'alerta'; ver = `Hay ${fmt(al, 1)} ha con alertas recientes de pérdida dentro del polígono. Conviene revisarlas en campo.`; }
    else if (neto > 0.01 * area) { estado = 'mejora'; ver = `La cobertura de bosque aumentó ${fmt(neto, 1)} ha netas en el periodo.`; }
    else if (neto < -0.01 * area) { estado = 'deterioro'; ver = `La cobertura de bosque disminuyó ${fmt(Math.abs(neto), 1)} ha netas en el periodo.`; }
    return {
      modo: 'navegador', resolucion_m: c, anio0: R.anio0, anio1: R.anio1, area_ha: Math.round(area * 100) / 100,
      fuera_area_pct: Math.round((1 - n.val / n.tot) * 1000) / 10,
      perdida_ha: perd, ganancia_ha: gan, neto_ha: neto, alertas_ha: al,
      serie_bosque_ha: { [R.anio0]: h(n.b0), [R.anio1]: h(n.b1) },
      perdida_conectividad_ha: h(n.pc),
      eri: { medio: Math.round((n.eri / n.val) * 1000) / 1000, clases: { baja: pct(n.ec[0]), media: pct(n.ec[1]), alta: pct(n.ec[2]) } },
      prioridad_ha: { Proteger: h(n.pri[0]), Restaurar: h(n.pri[1]), Vigilar: h(n.pri[2]) },
      frag: null, kba: null, estado, veredicto: ver,
    };
  }

  function verificar(geo, anio0, anio1) {
    if (window.PORTAL && window.PORTAL.api) {
      return fetch(window.PORTAL.api + 'verificar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ geojson: geo, anio0, anio1 }) })
        .then((r) => r.json().then((j) => { if (!r.ok) throw new Error(j.error || 'Error del servidor'); return j; }));
    }
    return new Promise((ok, mal) => setTimeout(() => { try { ok(verificarNavegador(geo)); } catch (e) { mal(e); } }, 50));
  }

  function leerArchivo(file) {
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    if (ext === 'geojson' || ext === 'json') return file.text().then((t) => JSON.parse(t));
    if (window.PORTAL && window.PORTAL.api) {
      const fd = new FormData(); fd.append('archivo', file);
      return fetch(window.PORTAL.api + 'leer_poligono', { method: 'POST', body: fd })
        .then((r) => r.json().then((j) => { if (!r.ok) throw new Error(j.error); return j; }));
    }
    if (ext === 'kml') return file.text().then(kmlAGeojson);
    return Promise.reject(new Error('Sin servidor solo se leen GeoJSON y KML. Para Shapefile (.zip) o KMZ, inicia el portal con python app.py.'));
  }
  function kmlAGeojson(txt) {
    const xml = new DOMParser().parseFromString(txt, 'text/xml');
    const polys = Array.from(xml.getElementsByTagName('Polygon')).map((p) => {
      const ring = (tag) => Array.from(p.getElementsByTagName(tag)).map((b) => b.getElementsByTagName('coordinates')[0].textContent.trim().split(/\s+/).map((c) => c.split(',').slice(0, 2).map(Number)));
      return [...ring('outerBoundaryIs'), ...ring('innerBoundaryIs')];
    });
    if (!polys.length) throw new Error('El KML no contiene polígonos.');
    return { type: 'Feature', properties: {}, geometry: { type: 'MultiPolygon', coordinates: polys } };
  }

  // ------------------------------------------------------------ dibujo de polígonos (sin librerías)
  function dibujador(map, alTerminar, alCambiar) {
    let pts = [], linea = null, marcas = L.layerGroup().addTo(map), activo = false;
    const pintar = () => {
      marcas.clearLayers();
      if (linea) map.removeLayer(linea);
      if (pts.length) linea = L.polygon(pts, { pane: 'hl', className: 'lf-draw', interactive: false }).addTo(map);
      pts.forEach((p) => L.circleMarker(p, { pane: 'hl', radius: 4, className: 'lf-vtx', interactive: false }).addTo(marcas));
      alCambiar && alCambiar(pts.length);
    };
    const clic = (e) => { pts.push([e.latlng.lat, e.latlng.lng]); pintar(); };
    const dbl = (e) => { L.DomEvent.stop(e); terminar(); };
    function iniciar() { if (activo) return; activo = true; pts = []; map.doubleClickZoom.disable(); map.on('click', clic); map.on('dblclick', dbl); map.getContainer().classList.add('drawing'); pintar(); }
    function parar() { activo = false; map.off('click', clic); map.off('dblclick', dbl); map.doubleClickZoom.enable(); map.getContainer().classList.remove('drawing'); marcas.clearLayers(); if (linea) { map.removeLayer(linea); linea = null; } }
    function terminar() {
      // un doble clic agrega dos vértices repetidos: se descartan
      pts = pts.filter((p, i) => i === 0 || p[0] !== pts[i - 1][0] || p[1] !== pts[i - 1][1]);
      if (pts.length < 3) return;
      const ring = pts.map(([la, lo]) => [lo, la]); ring.push(ring[0]);
      parar(); alTerminar({ type: 'Feature', properties: { origen: 'dibujado' }, geometry: { type: 'Polygon', coordinates: [ring] } });
    }
    return { iniciar, terminar, cancelar: parar, deshacer() { pts.pop(); pintar(); }, get activo() { return activo; } };
  }

  // ------------------------------------------------------------ fichas de resultados
  const EST = { mejora: ['Mejora', 'up', 'trend'], deterioro: ['Deterioro', 'dn', 'down'], alerta: ['Alerta', 'dn', 'warn'], estable: ['Estable', 'up', 'check'] };
  function tarjeta(ic, v, l, col) { return `<div class="mc"><span style="color:${col || 'var(--azul)'}">${icon(ic, 'ico')}</span><b class="num">${v}</b><span>${l}</span></div>`; }
  function fragTabla(fr, a0, a1) {
    if (!fr) return '<p>Las métricas de fragmentación (LPI, CONNECT, ED, ENN) se calculan con el servidor Python. Inicia el portal con <b>python app.py</b>.</p>';
    const filas = [['LPI', 'Parche mayor (% del área)', 1], ['CONNECT', 'Conectancia (%)', 1], ['ED', 'Densidad de borde (m/ha)', 1], ['ENN_MN', 'Distancia al vecino (m)', 0], ['n_parches', 'Número de parches', 0], ['ECA_pct', 'Conectividad equivalente (%)', 1]];
    const b = fr.base || fr[a0], a = fr.actual || fr[a1];
    return `<div class="tbl"><table class="mini"><thead><tr><th>Métrica</th><th class="c">${a0}</th><th class="c">${a1}</th></tr></thead><tbody>${filas.filter(([k]) => b && k in b).map(([k, n, d]) => `<tr><td>${n}</td><td class="c num">${nf(b[k], d)}</td><td class="c num">${nf(a[k], d)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function eriBloque(e) {
    if (!e) return '';
    const c = e.clases || {};
    return `<div class="res-sec"><h3>Índice de Resiliencia Ecológica</h3>
      <p>ERI medio <b class="num">${nf(e.medio, 2)}</b> · ${e.medio > M.cortes[1] ? 'núcleo íntegro y estable' : e.medio < M.cortes[0] ? 'paisaje fragmentado o modificado' : 'resiliencia intermedia'}.</p>
      <div class="qbar"><i style="width:${c.baja}%;background:${M.capas.eri.paleta[0]}"></i><i style="width:${c.media}%;background:${M.capas.eri.paleta[2]}"></i><i style="width:${c.alta}%;background:${M.capas.eri.paleta[4]}"></i></div>
      <div class="legend-row"><span><i style="background:${M.capas.eri.paleta[0]}"></i>Baja ${nf(c.baja, 0)} %</span><span><i style="background:${M.capas.eri.paleta[2]}"></i>Media ${nf(c.media, 0)} %</span><span><i style="background:${M.capas.eri.paleta[4]}"></i>Alta ${nf(c.alta, 0)} %</span></div></div>`;
  }
  function prioridadBloque(p, pc) {
    if (!p) return '';
    const col = Object.fromEntries((M.capas.prioridad.clases || []).map(([n, c]) => [n, c]));
    return `<div class="res-sec"><h3>Dónde intervenir</h3><ul class="prio">${Object.entries(p).map(([n, v]) => `<li><span class="sw" style="background:${col[n]}"></span><span>${n}</span><b class="num">${ha(v, 1)}</b></li>`).join('')}</ul>
      ${pc != null ? `<p>Pérdida de conectividad detectada en <b class="num">${ha(pc, 1)}</b>.</p>` : ''}</div>`;
  }
  function serieBloque(s, han) {
    let h = '';
    const ks = Object.keys(s || {});
    if (ks.length > 2) h += `<div class="res-sec"><h3>Bosque por año</h3>${bars(ks.map((k) => s[k]), ks.map((k) => "'" + k.slice(2)), 'var(--verde-osc)', { w: 360, h: 160, fy: (v) => fmt(v, 0) + ' ha', label: 'Bosque por año' })}</div>`;
    const hk = Object.keys(han || {});
    if (hk.length) h += `<div class="res-sec"><h3>Pérdida anual (Hansen)</h3>${bars(hk.map((k) => han[k]), hk.map((k) => "'" + k.slice(2)), hk.map((_, i) => CP.lossColor(i / Math.max(1, hk.length - 1))), { w: 360, h: 160, every: Math.ceil(hk.length / 7), fy: (v) => fmt(v, 0) + ' ha', label: 'Pérdida anual Hansen' })}</div>`;
    return h;
  }
  function htmlVerificacion(r) {
    const [et, cl, ic] = EST[r.estado] || EST.estable;
    const ks = Object.keys(r.serie_bosque_ha || {});
    const b0 = r.serie_bosque_ha[ks[0]], b1 = r.serie_bosque_ha[ks[ks.length - 1]];
    let h = `<div class="verd ${cl}"><span>${icon(ic)}</span><div><b>${et}</b><p>${esc(r.veredicto)}</p></div></div>`;
    h += `<div class="cards2">${tarjeta('area', ha(r.area_ha, 1), 'área del polígono')}${tarjeta('leaf', ha(b1, 1), `bosque en ${r.anio1} (${ha(b0, 1)} en ${r.anio0})`, 'var(--verde-osc)')}
      ${tarjeta('down', ha(r.perdida_ha, 1), `pérdida ${r.anio0}–${r.anio1}`, 'var(--rojo)')}${tarjeta('trend', ha(r.ganancia_ha, 1), `ganancia ${r.anio0}–${r.anio1}`, 'var(--verde-osc)')}
      ${tarjeta('warn', ha(r.alertas_ha, 1), 'con alertas recientes' + (r.alertas_radd_ha != null ? ` · RADD ${ha(r.alertas_radd_ha, 1)}` : ''), 'var(--amarillo)')}${tarjeta('net', r.neto_ha >= 0 ? '+' + ha(r.neto_ha, 1) : '−' + ha(-r.neto_ha, 1), 'cambio neto de bosque')}</div>`;
    h += serieBloque(r.serie_bosque_ha, r.hansen_perdida_anual);
    h += `<div class="res-sec"><h3>Fragmentación y conectividad</h3>${fragTabla(r.frag, r.anio0, r.anio1)}</div>`;
    h += eriBloque(r.eri) + prioridadBloque(r.prioridad_ha, r.perdida_conectividad_ha);
    if (r.kba && r.kba.length) h += `<div class="res-sec"><h3>KBA que toca</h3><p>${r.kba.map(esc).join(' · ')}</p></div>`;
    if (r.fuera_area_pct > 1) h += `<p class="sim">El ${fmt(r.fuera_area_pct, 0)} % del polígono queda fuera del área de estudio y no se analiza.</p>`;
    const modo = { 'earth-engine': `Calculado en vivo con Google Earth Engine a ${r.resolucion_m} m.`, demo: `Calculado por el servidor Python con las capas de demostración del motor (${r.resolucion_m} m). Con Earth Engine el cálculo usa Dynamic World a 10 m.`, navegador: `Cálculo aproximado en el navegador con una rejilla de ${r.resolucion_m} m de las capas del motor. Para el cálculo completo inicia el portal con python app.py.` };
    h += `<p class="sim">${modo[r.modo] || ''}</p>`;
    return h;
  }
  function htmlUnidad(s, tipo) {
    const a0 = String(M.anio0), a1 = String(M.anio1), f0 = s.frag[a0], f1 = s.frag[a1];
    let h = '';
    const big = (ic, v, l) => `<div class="big">${icon(ic)}<b class="num">${v}</b><span>${l}</span></div>`;
    if (tipo === 'conectividad') {
      h += big('net', nf(f1.CONNECT, 2) + ' %', `CONNECT ${a1} (${nf(f0.CONNECT, 2)} % en ${a0})`);
      h += `<div class="cards2">${tarjeta('core', nf(f1.LPI, 1) + ' %', 'LPI: área en el parche mayor')}${tarjeta('link', nf(f1.ENN_MN, 0) + ' m', 'distancia media al vecino')}${tarjeta('leaf', nf(f1.bosque_pct, 1) + ' %', 'cobertura de bosque')}${tarjeta('area', fmt(f1.n_parches), 'parches de bosque')}</div>`;
    } else if (tipo === 'fragmentacion') {
      h += big('chart', nf(f1.ED, 2) + ' m/ha', `densidad de borde ${a1} (${nf(f0.ED, 2)} en ${a0})`);
      h += `<div class="res-sec"><h3>Métricas FRAGSTATS</h3>${fragTabla({ base: f0, actual: f1 }, a0, a1)}</div>`;
    } else if (tipo === 'eri') {
      h += big('leaf', nf(s.eri, 2), 'ERI medio del área');
      h += eriBloque({ medio: s.eri, clases: s.eri_clases });
    } else if (tipo === 'perdida_conectividad') {
      h += big('down', ha(s.perdida_conectividad_ha), `con pérdida de conectividad ${a0}–${a1}`);
      h += `<div class="cards2">${tarjeta('warn', ha(s.alertas_ha, 1), 'con alertas recientes', 'var(--amarillo)')}${tarjeta('q', nf(s.riesgo_medio, 2), 'riesgo medio de pérdida (0–1)', 'var(--rojo)')}${tarjeta('net', nf(f1.CONNECT - f0.CONNECT, 2) + ' pp', 'cambio de CONNECT')}${tarjeta('core', nf(f1.LPI - f0.LPI, 1) + ' pp', 'cambio de LPI')}</div>`;
    } else if (tipo === 'cobertura') {
      h += big('leaf', (s.ganancia_ha - s.perdida_ha >= 0 ? '+' : '−') + ha(Math.abs(s.ganancia_ha - s.perdida_ha)), `cambio neto de bosque ${a0}–${a1}`);
      h += `<div class="cards2">${tarjeta('down', ha(s.perdida_ha), 'pérdida de bosque', 'var(--rojo)')}${tarjeta('trend', ha(s.ganancia_ha), 'ganancia de bosque', 'var(--verde-osc)')}</div>`;
      h += serieBloque(null, s.hansen_perdida_anual);
    } else {
      h += prioridadBloque(s.prioridad_ha, s.perdida_conectividad_ha);
      h += `<div class="cards2">${tarjeta('q', nf(s.riesgo_medio, 2), 'riesgo medio de pérdida', 'var(--rojo)')}${tarjeta('leaf', nf(s.eri, 2), 'ERI medio')}</div>`;
    }
    if (s.kba_ha != null) h += `<p class="sim">KBA dentro del área: ${ha(s.kba_ha)}.</p>`;
    h += `<p class="sim">Motor ejecutado el ${esc(M.generado.replace('T', ' '))} · modo ${M.modo === 'demo' ? 'demostración (capas sintéticas)' : 'Earth Engine'} · celda ${M.escala_m} m.</p>`;
    return h;
  }

  window.CANAL = { M, CAPAS, VECTORES, leyenda, crearCapas, verificar, verificarNavegador, leerArchivo, dibujador, htmlVerificacion, htmlUnidad, ha, nf };
})();
