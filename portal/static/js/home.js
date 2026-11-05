/* Portada: cifras del motor de la Cuenca del Canal y buscador de subcuencas */
(function () {
  const { $, $$, fmt, esc } = CP;
  const M = window.MOTOR;
  const c = M.stats.cuenca, a = M.stats.area, a1 = String(M.anio1);
  const kba = M.vector.kba_canal ? M.vector.kba_canal.features.length : null;
  const F = [
    ['Área de estudio', fmt(a.area_ha / 1000, 0) + ' kha', 'Cuenca del Canal más 10 km de amortiguamiento.'],
    ['Subcuencas', Object.keys(M.stats).filter((k) => k[0] === 's').length, 'Unidades de análisis dentro de la cuenca.'],
    ['Bosque ' + a1, fmt(c.frag[a1].bosque_pct, 0) + ' %', 'Cobertura de bosque en la cuenca.'],
    ['ERI medio', fmt(c.eri, 2), 'Índice de Resiliencia Ecológica (0–1).'],
    ['KBA', kba == null ? '—' : kba, kba == null ? 'Se descargan al ejecutar el motor.' : 'Áreas Clave para la Biodiversidad en el área.'],
  ];
  $('#hstats').innerHTML = F.map(([l, b, p]) => `<div class="fig"><span>${l}</span><b>${b}</b><p>${p}</p></div>`).join('');
  const all = Object.entries(M.stats).map(([id, s]) => ({ id, n: s.nombre, t: id[0] === 's' ? 'Subcuenca del Canal' : 'Área de estudio' }));
  const norm = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const q = $('#hq'), box = $('#hsugg');
  function show() {
    const v = norm(q.value.trim());
    if (!v) { box.hidden = true; return; }
    const m = all.filter((x) => norm(x.n).includes(v)).slice(0, 8);
    box.innerHTML = m.length ? m.map((x) => `<button type="button" data-id="${x.id}">${esc(x.n)}<br><small>${esc(x.t)}</small></button>`).join('') : '<div style="padding:10px 16px;color:var(--muted)">Sin coincidencias. Prueba con el nombre del río.</div>';
    box.hidden = false;
    $$('button', box).forEach((b) => b.addEventListener('click', () => (location.href = 'panel.html#' + b.dataset.id)));
  }
  q.addEventListener('input', show);
  q.addEventListener('focus', show);
  document.addEventListener('click', (e) => { if (!$('#hsearch').contains(e.target)) box.hidden = true; });
  $('#hsearch').addEventListener('submit', (e) => {
    e.preventDefault();
    const v = norm(q.value.trim()); const m = all.find((x) => norm(x.n).includes(v));
    location.href = 'panel.html' + (v && m ? '#' + m.id : '');
  });
})();
