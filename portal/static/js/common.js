/* Conectividad Panamá — utilidades compartidas entre páginas */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const nf = (d = 0) => new Intl.NumberFormat('es-PA', { maximumFractionDigits: d, minimumFractionDigits: d });
  const fmt = (v, d = 0) => nf(d).format(v);
  function fmtHa(v) {
    if (v >= 1e6) return fmt(v / 1e6, 2) + ' Mha';
    if (v >= 1e4) return fmt(v / 1e3, 0) + ' kha';
    if (v >= 1e3) return fmt(v / 1e3, 1) + ' kha';
    return fmt(v, 0) + ' ha';
  }
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // ---------- encabezado ----------
  const burger = $('#burger'), links = $('#links');
  if (burger) burger.addEventListener('click', () => {
    const o = links.classList.toggle('open'); burger.setAttribute('aria-expanded', o);
  });
  document.addEventListener('click', (e) => {
    const l = $('.lang'); if (l && l.open && !l.contains(e.target)) l.open = false;
  });

  function toast(msg) {
    let t = $('.toast'); if (!t) { t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => (t.hidden = true), 3200);
  }

  // ---------- datos ----------
  const D = window.D;
  const units = {}; units.pa = D.nat;
  D.cuencas.forEach((c) => (units[c.id] = c));
  D.subcuencas.forEach((s) => (units[s.id] = s));
  const feat = {};
  D.geo.cuencas.features.forEach((f) => (feat[f.properties.id] = f));
  D.geo.subcuencas.features.forEach((f) => (feat[f.properties.id] = f));
  const corById = {}; D.geo.corredores.features.forEach((f) => (corById[f.properties.id] = f.properties));
  const forestHa = (u) => u.clases[0] + u.clases[1] + u.clases[2];
  const CLS_ICON = ['forest', 'regrow', 'mangrove', 'pasture', 'crop', 'urban', 'water'];

  function fillCuencaSelect(sel, withNat, natLabel) {
    const byV = { Caribe: [], 'Pacífico': [] };
    D.cuencas.forEach((c) => byV[c.vertiente].push(c));
    let h = withNat ? `<option value="">${natLabel || 'Panamá (todas las cuencas)'}</option>` : '';
    for (const v of ['Caribe', 'Pacífico']) {
      h += `<optgroup label="Vertiente del ${v}">` + byV[v].slice().sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
        .map((c) => `<option value="${c.id}">${esc(c.nombre)}</option>`).join('') + '</optgroup>';
    }
    sel.innerHTML = h;
  }
  function fillSubSelect(sel, cu) {
    if (cu !== 'c115') { sel.innerHTML = '<option value="">No disponible para esta cuenca</option>'; sel.disabled = true; return false; }
    const g = {}; D.subcuencas.forEach((s) => (g[s.grupo] = g[s.grupo] || []).push(s));
    let h = '<option value="">Toda la cuenca</option>';
    for (const k of Object.keys(g).sort()) h += `<optgroup label="${esc(k)}">` + g[k].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')).map((s) => `<option value="${s.id}">${esc(s.nombre)}</option>`).join('') + '</optgroup>';
    sel.innerHTML = h; sel.disabled = false; return true;
  }

  // ---------- íconos ----------
  const ICONS = {
    forest: '<path d="M12 3 6 12h3l-4 6h14l-4-6h3z"/><path d="M12 18v3"/>',
    regrow: '<path d="M12 21v-8"/><path d="M12 13c0-4 3-6 7-6 0 4-3 6-7 6Z"/><path d="M12 15c0-3-2-5-6-5 0 3 2 5 6 5Z"/>',
    mangrove: '<path d="M12 4c-4 0-6 3-6 6h12c0-3-2-6-6-6Z"/><path d="M12 10v6m0 0-4 4m4-4 4 4m-4-4v5"/><path d="M3 20c2-1 3 1 5 0s3 1 5 0 3 1 5 0 3 1 3 0"/>',
    pasture: '<path d="M4 20c1-4 1-8 0-11M8 20c0-5 1-8 3-10M12 20c0-6-1-9-3-12M16 20c0-5 1-8 4-10M20 20c-1-3-1-6 0-8"/>',
    crop: '<path d="M12 21V8"/><path d="M12 8c-2 0-3-2-3-4 2 0 3 2 3 4Zm0 0c2 0 3-2 3-4-2 0-3 2-3 4Z"/><path d="M12 13c-2 0-4-1-4-3 2 0 4 1 4 3Zm0 0c2 0 4-1 4-3-2 0-4 1-4 3Z"/><path d="M12 18c-2 0-4-1-4-3 2 0 4 1 4 3Zm0 0c2 0 4-1 4-3-2 0-4 1-4 3Z"/>',
    urban: '<path d="M4 21V9l5-3v15M9 21V4l6 3v14M15 21V11l5 2v8M3 21h18"/>',
    water: '<path d="M3 9c2-1.5 4 1.5 6 0s4 1.5 6 0 4 1.5 6 0"/><path d="M3 14c2-1.5 4 1.5 6 0s4 1.5 6 0 4 1.5 6 0"/><path d="M3 19c2-1.5 4 1.5 6 0s4 1.5 6 0 4 1.5 6 0"/>',
    link: '<circle cx="5" cy="17" r="3"/><circle cx="19" cy="7" r="3"/><path d="M7.5 15.5 16.5 8.5"/>',
    core: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.5"/>',
    area: '<path d="M4 7l5-3 6 3 5-3v13l-5 3-6-3-5 3z"/><path d="M9 4v13M15 7v13"/>',
    trend: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    down: '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    warn: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17v.5"/>',
    ban: '<circle cx="12" cy="12" r="9"/><path d="m6 6 12 12"/>',
    q: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5V14M12 17v.5"/>',
    layers: '<path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="m3 13 9 5 9-5"/>',
    border: '<path d="M4 6c3-2 5 2 8 0s5 2 8 0v12c-3 2-5-2-8 0s-5-2-8 0z"/>',
    leaf: '<path d="M5 19C5 10 10 5 20 4c-1 10-6 15-15 15Z"/><path d="M5 19 13 11"/>',
    net: '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="8" r="2.5"/><circle cx="9" cy="18" r="2.5"/><path d="M8 7l8 1M7 8l2 8m2 0 6-6"/>',
    chart: '<path d="M4 19h16M7 15V9m5 6V5m5 10v-4"/>',
  };
  const icon = (k, cls = '') => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[k] || ''}</svg>`;

  // ---------- gráficos SVG ----------
  function donut(parts, size = 140) {
    const tot = parts.reduce((a, p) => a + p.v, 0) || 1, r = size / 2 - 12, c = 2 * Math.PI * r;
    let off = 0, segs = '';
    parts.forEach((p) => {
      const len = (p.v / tot) * c;
      segs += `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" style="stroke:${p.c}" stroke-width="22" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-off}" transform="rotate(-90 ${size / 2} ${size / 2})"/>`;
      off += len;
    });
    return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="Gráfico de anillo">${segs}</svg>`;
  }
  function niceMax(m) { if (m <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(m))); const n = m / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p; }
  function bars(vals, labels, colors, o = {}) {
    const W = o.w || 520, H = o.h || 190, L = 52, B = 26, T = 8, R = 6;
    const max = niceMax(Math.max(...vals) * 1.05), iw = W - L - R, ih = H - T - B, bw = iw / vals.length;
    let g = '';
    for (let i = 0; i <= 4; i++) { const y = T + ih - (ih * i) / 4; g += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/><text x="${L - 6}" y="${y + 3}" text-anchor="end">${o.fy ? o.fy((max * i) / 4) : fmtHa((max * i) / 4)}</text>`; }
    vals.forEach((v, i) => {
      const h = (v / max) * ih, x = L + i * bw + bw * 0.12;
      g += `<rect x="${x}" y="${T + ih - h}" width="${bw * 0.76}" height="${Math.max(h, 0)}" rx="1.5" style="fill:${Array.isArray(colors) ? colors[i] : colors}${o.hi === i ? ';stroke:var(--ink);stroke-width:1.5' : ''}"><title>${labels[i]}: ${o.fy ? o.fy(v) : fmt(v) + ' ha'}</title></rect>`;
      const every = o.every || 1;
      if (i % every === 0) g += `<text x="${x + bw * 0.38}" y="${H - 8}" text-anchor="middle">${labels[i]}</text>`;
    });
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label || 'Gráfico de barras')}">${g}</svg>`;
  }
  function stacked(series, labels, o = {}) {
    const W = o.w || 520, H = o.h || 200, L = 52, B = 26, T = 8, R = 6;
    const tots = labels.map((_, i) => series.reduce((a, s) => a + s.v[i], 0));
    const max = niceMax(Math.max(...tots)), iw = W - L - R, ih = H - T - B, bw = iw / labels.length;
    let g = '';
    for (let i = 0; i <= 4; i++) { const y = T + ih - (ih * i) / 4; g += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/><text x="${L - 6}" y="${y + 3}" text-anchor="end">${fmtHa((max * i) / 4)}</text>`; }
    labels.forEach((lab, i) => {
      let y = T + ih; const x = L + i * bw + bw * 0.14;
      series.forEach((s) => { const h = (s.v[i] / max) * ih; y -= h; g += `<rect x="${x}" y="${y}" width="${bw * 0.72}" height="${Math.max(h, 0)}" style="fill:${s.c}"><title>${lab} · ${s.n}: ${fmt(s.v[i])} ha</title></rect>`; });
      if (i % (o.every || 5) === 0 || i === labels.length - 1) g += `<text x="${x + bw * 0.36}" y="${H - 8}" text-anchor="middle">${lab}</text>`;
    });
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label || 'Serie temporal')}">${g}</svg>`;
  }
  function rampCss(stops) { const n = stops.length; return `linear-gradient(90deg,${stops.map((c, i) => `${c} ${(i * 100) / n}% ${((i + 1) * 100) / n}%`).join(',')})`; }
  function rampColor(t) { return D.ramp[Math.min(D.ramp.length - 1, Math.max(0, Math.floor(t * D.ramp.length)))]; }
  const CONN_CLS = D.ramp_clases;
  function connLegend() { return `<div class="clsrow">${D.ramp.map((c, i) => `<span><i style="background:${c}"></i>${CONN_CLS[i]}<small>${(i / 5).toFixed(1)}–${((i + 1) / 5).toFixed(1)}</small></span>`).join('')}</div>`; }

  // ---------- mapa base ----------
  const PLACES = [
    ['Ciudad de Panamá', 8.98, -79.52, 'city'], ['Colón', 9.36, -79.9, 'city'], ['David', 8.43, -82.43, 'city'], ['Santiago', 8.1, -80.98, 'city'],
    ['Chitré', 7.96, -80.43, 'city'], ['Penonomé', 8.52, -80.36, 'city'], ['Bocas del Toro', 9.34, -82.24, 'city'], ['La Palma', 8.41, -78.14, 'city'],
    ['Yaviza', 8.16, -77.69, 'city'], ['La Chorrera', 8.88, -79.78, 'city'],
    ['Mar Caribe', 9.95, -80.4, 'sea'], ['Océano Pacífico', 7.35, -79.6, 'sea'], ['Golfo de Panamá', 8.4, -79.0, 'sea'],
    ['Costa Rica', 9.75, -83.55, 'ctry'], ['Colombia', 7.45, -76.75, 'ctry'],
  ];
  function ll(c) { return [c[1], c[0]]; }
  function ringsOf(geom) { return geom.type === 'Polygon' ? [geom.coordinates[0]] : geom.coordinates.map((p) => p[0]); }

  function baseMap(el, opt = {}) {
    const map = L.map(el, { zoomControl: true, attributionControl: true, minZoom: 6, maxZoom: 13, zoomSnap: 0.25, preferCanvas: false, maxBounds: [[4.5, -87], [12.5, -73]] });
    L.control.scale({ imperial: false, position: 'bottomright', maxWidth: 140 }).addTo(map);
    map.attributionControl.setPrefix(false).addAttribution('Contiene datos Copernicus Sentinel modificados (demostración) · Cuencas: proyecto · Límites: Natural Earth');
    [['land', 200], ['grat', 250], ['rasters', 350], ['vec', 420], ['lines', 450], ['hl', 480], ['labels', 620]].forEach(([n, z]) => { map.createPane(n).style.zIndex = z; });
    map.getPane('labels').style.pointerEvents = 'none';
    map.getPane('grat').style.pointerEvents = 'none';
    L.geoJSON(D.geo.paises, { pane: 'land', interactive: false, style: () => ({ className: 'lf-land' }) }).addTo(map);
    const grat = L.layerGroup();
    for (let lo = -84; lo <= -76; lo++) {
      L.polyline([[5, lo], [11.5, lo]], { pane: 'grat', className: 'lf-grat', interactive: false }).addTo(grat);
      L.marker([7.0, lo], { pane: 'labels', interactive: false, icon: L.divIcon({ className: 'grat', html: `${Math.abs(lo)}°O`, iconSize: null }) }).addTo(grat);
    }
    for (let la = 6; la <= 11; la++) {
      L.polyline([[la, -86], [la, -74]], { pane: 'grat', className: 'lf-grat', interactive: false }).addTo(grat);
      L.marker([la, -83.6], { pane: 'labels', interactive: false, icon: L.divIcon({ className: 'grat', html: `${la}°N`, iconSize: null }) }).addTo(grat);
    }
    const labels = L.layerGroup();
    PLACES.forEach(([n, la, lo, k]) => L.marker([la, lo], { pane: 'labels', interactive: false, icon: L.divIcon({ className: 'lbl ' + k, html: n, iconSize: null }) }).addTo(labels));
    if (opt.grat !== false) grat.addTo(map);
    if (opt.labels !== false) labels.addTo(map);
    map.fitBounds(D.bounds, { padding: [10, 10] });
    setBase(el, opt.base || 'auto');
    return { map, grat, labels };
  }
  function setBase(el, b) {
    el.classList.remove('bm-claro', 'bm-oscuro', 'bm-relieve', 'bm-nada');
    if (b !== 'auto') el.classList.add('bm-' + b);
  }

  // ---------- capas temáticas ----------
  function hex2rgb(h) { return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); }
  function lossColor(t) { const a = hex2rgb(D.perdida_rampa[0]), b = hex2rgb(D.perdida_rampa[1]); return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * t)).join(',')})`; }
  let lossPx = null; const lossWaiters = [];
  (function () {
    const im = new Image();
    im.onload = () => {
      const c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
      const x = c.getContext('2d'); x.drawImage(im, 0, 0);
      lossPx = { w: im.width, h: im.height, d: x.getImageData(0, 0, im.width, im.height).data };
      lossWaiters.splice(0).forEach((f) => f());
    };
    im.src = D.imgs.perdidaidx;
  })();
  function lossURL(y0, y1, cb) {
    if (!lossPx) { lossWaiters.push(() => lossURL(y0, y1, cb)); return; }
    const { w, h, d } = lossPx, c = document.createElement('canvas'); c.width = w; c.height = h;
    const x = c.getContext('2d'), out = x.createImageData(w, h), o = out.data;
    const a = hex2rgb(D.perdida_rampa[0]), b = hex2rgb(D.perdida_rampa[1]);
    for (let i = 0; i < w * h; i++) {
      const yr = d[i * 4], al = d[i * 4 + 3];
      if (!al || yr + 2000 < y0 || yr + 2000 > y1) continue;
      const t = (yr - 1) / 24, col = a.map((v, k) => v + (b[k] - v) * t);
      const px = i % w, py = (i / w) | 0;
      for (const [dx, dy] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const X = px + dx, Y = py + dy; if (X < 0 || Y < 0 || X >= w || Y >= h) continue;
        const j = (Y * w + X) * 4; if (o[j + 3] && !(dx === 0 && dy === 0)) continue;
        o[j] = col[0]; o[j + 1] = col[1]; o[j + 2] = col[2]; o[j + 3] = dx || dy ? 170 : 255;
      }
    }
    x.putImageData(out, 0, 0); cb(c.toDataURL());
  }

  function thematic(map) {
    const B = D.bounds, img = (k, z, op) => L.imageOverlay(D.imgs[k], B, { pane: 'rasters', opacity: op, zIndex: z, interactive: false, className: 'lf-img' });
    const L_ = {};
    L_.cobertura = img('cobertura', 1, 0.9);
    L_.bosque2000 = img('bosque2000', 2, 0.85);
    L_.conectividad2000 = img('conectividad2000', 3, 0.85);
    L_.conectividad = img('conectividad', 4, 0.85);
    L_.nucleos = img('nucleos', 6, 0.9);
    L_.perdida = L.imageOverlay(D.imgs.perdida, B, { pane: 'rasters', opacity: 1, zIndex: 5, interactive: false });
    lossURL(2001, 2025, (u) => L_.perdida.setUrl(u));
    const cas = L.geoJSON(D.geo.corredores, { pane: 'lines', interactive: false, style: () => ({ className: 'lf-cas' }) });
    const cor = L.geoJSON(D.geo.corredores, {
      pane: 'lines',
      style: (f) => ({ className: 'lf-cor-' + f.properties.calidad }),
      onEachFeature: (f, l) => l.bindTooltip(`<b>Corredor ${f.properties.id}</b><br>${fmt(f.properties.km, 1)} km · calidad ${f.properties.calidad.toLowerCase()}<br>Tramo sin bosque: ${fmt(f.properties.brecha, 1)} %`, { className: 'tt', sticky: true }),
    });
    L_.corredores = L.featureGroup([cas, cor]);
    L_.corredores._cor = cor; L_.corredores._cas = cas;
    return L_;
  }
  // Con el servidor Python y Earth Engine configurados, /api/capas devuelve
  // URLs de teselas; se reemplazan las imágenes de demostración por ellas.
  function eeTiles(T, map) {
    if (!window.PORTAL || !window.PORTAL.api) return;
    fetch(window.PORTAL.api + 'capas').then((r) => (r.ok ? r.json() : {})).then((urls) => {
      Object.keys(urls || {}).forEach((k) => {
        if (!T[k]) return;
        const on = map.hasLayer(T[k]), op = T[k].options.opacity;
        if (on) map.removeLayer(T[k]);
        T[k] = L.tileLayer(urls[k], { pane: 'rasters', opacity: op });
        if (on) T[k].addTo(map);
      });
    }).catch(() => {});
  }
  function filterCorridors(layer, fn) {
    layer._cor.eachLayer((l) => { const ok = fn(l.feature.properties); const el = l.getElement && l.getElement(); if (el) el.style.display = ok ? '' : 'none'; });
    layer._cas.eachLayer((l) => { const ok = fn(l.feature.properties); const el = l.getElement && l.getElement(); if (el) el.style.display = ok ? '' : 'none'; });
  }

  function highlight(map, id) {
    const g = L.layerGroup();
    if (!id || id === 'pa') return g;
    const f = feat[id]; if (!f) return g;
    const holes = ringsOf(f.geometry).map((r) => r.map(ll));
    L.polygon([[[3, -90], [3, -70], [14, -70], [14, -90]], ...holes], { pane: 'hl', className: 'lf-mask', interactive: false }).addTo(g);
    L.geoJSON(f, { pane: 'hl', interactive: false, style: () => ({ className: 'lf-hl' }) }).addTo(g);
    return g;
  }
  function boundsOf(id) {
    if (!id || id === 'pa') return L.latLngBounds(D.bounds);
    return L.geoJSON(feat[id]).getBounds();
  }

  window.CP = { $, $$, fmt, fmtHa, esc, toast, D, units, feat, corById, forestHa, CLS_ICON, fillCuencaSelect, fillSubSelect, icon, donut, bars, stacked, rampCss, rampColor, connLegend, lossColor, baseMap, setBase, thematic, eeTiles, lossURL, highlight, boundsOf, filterCorridors };
})();
