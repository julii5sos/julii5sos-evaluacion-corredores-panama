/* Comparador de años con divisor (JRC TMF, ESRI LULC, NDVI Sentinel-2).
   Las teselas de cada año las entrega Earth Engine vía /api/comparar; el divisor se recorta en el navegador. */
(function () {
  const { $, esc } = CP;
  function iniciar({ map, getArea, leyendaHtml }) {
    const cuerpo = $('#s-comparar');
    let OPC = null, izq = null, der = null, ctl = null, activo = false;
    map.createPane('cmpL'); map.createPane('cmpR');
    ['cmpL', 'cmpR'].forEach((n) => { map.getPane(n).style.zIndex = 330; map.getPane(n).style.pointerEvents = 'none'; });
    const opciones = (a, b, sel) => { let h = ''; for (let y = a; y <= b; y++) h += `<option ${y === sel ? 'selected' : ''}>${y}</option>`; return h; };
    function pintarAnios() {
      const o = OPC[$('#c-fuente').value];
      $('#c-y0').innerHTML = opciones(o.min, o.max - 1, Math.max(o.min, o.max - 5));
      $('#c-y1').innerHTML = opciones(o.min + 1, o.max, o.max);
    }
    function recortar() {
      if (!activo) return;
      const nw = map.containerPointToLayerPoint([0, 0]), se = map.containerPointToLayerPoint(map.getSize());
      const x = nw.x + (se.x - nw.x) * (+$('#c-div').value / 100);
      map.getPane('cmpL').style.clip = `rect(${nw.y}px,${x}px,${se.y}px,${nw.x}px)`;
      map.getPane('cmpR').style.clip = `rect(${nw.y}px,${se.x}px,${se.y}px,${x}px)`;
    }
    function quitar() {
      activo = false;
      [izq, der].forEach((l) => l && map.removeLayer(l)); izq = der = null;
      $('#c-div').hidden = true; $('#c-etq').hidden = true; $('#c-leyenda').innerHTML = '';
      map.getPane('cmpL').style.clip = map.getPane('cmpR').style.clip = '';
    }
    function pintar(r) {
      quitar();
      izq = L.tileLayer(r.izquierda.url, { pane: 'cmpL', opacity: 1 }).addTo(map);
      der = L.tileLayer(r.derecha.url, { pane: 'cmpR', opacity: 1 }).addTo(map);
      activo = true;
      $('#c-div').hidden = false; $('#c-div').value = 50;
      $('#c-etq').hidden = false; $('#c-etq').innerHTML = `<span>${esc(r.izquierda.etiqueta)}</span><span>${esc(r.derecha.etiqueta)}</span>`;
      $('#c-leyenda').innerHTML = leyendaHtml(r.leyenda);
      [izq, der].forEach((l) => l.on('load tileload', recortar));
      recortar();
    }
    cuerpo.innerHTML = `<p class="hint-p">Compara dos años de una misma fuente con un divisor sobre el mapa. Usa el polígono dibujado o, si no hay ninguno, la Cuenca del Canal. Requiere el servidor Python con Earth Engine.</p>
      <div class="fld"><label for="c-fuente">Fuente</label><select id="c-fuente"><option>JRC TMF</option><option>ESRI LULC</option><option>NDVI Sentinel-2</option></select></div>
      <div class="sel-grid"><div class="fld"><label for="c-y0">Año inicial (izquierda)</label><select id="c-y0"></select></div><div class="fld"><label for="c-y1">Año final (derecha)</label><select id="c-y1"></select></div></div>
      <div class="pbtns"><button class="btn btn-p" id="c-run" type="button">Comparar</button><button class="btn btn-s" id="c-clear" type="button">Quitar</button></div>
      <p class="hint-p small" id="c-msg"></p><div id="c-leyenda"></div>`;
    const barra = document.createElement('div');
    barra.className = 'cmp-bar'; barra.innerHTML = '<div id="c-etq" class="cmp-etq" hidden></div><input id="c-div" type="range" min="0" max="100" value="50" hidden aria-label="Mover el divisor para comparar el año inicial y el año final">';
    $('#smap').parentElement.appendChild(barra);
    $('#c-div').addEventListener('input', recortar);
    map.on('move zoom zoomend moveend resize viewreset', recortar);
    $('#c-fuente').addEventListener('change', pintarAnios);
    $('#c-clear').addEventListener('click', () => { quitar(); $('#c-msg').textContent = ''; });
    fetch(window.PORTAL.api + 'comparar/opciones').then((r) => r.json()).then((o) => { OPC = o; pintarAnios(); })
      .catch(() => { $('#c-msg').textContent = 'No se pudo consultar el servidor.'; $('#c-run').disabled = true; });
    $('#c-run').addEventListener('click', () => {
      const b = $('#c-run'); b.disabled = true; b.textContent = 'Consultando Earth Engine…'; $('#c-msg').textContent = '';
      fetch(window.PORTAL.api + 'comparar', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.assign({ fuente: $('#c-fuente').value, anio_inicial: +$('#c-y0').value, anio_final: +$('#c-y1').value }, getArea())) })
        .then((r) => r.json().then((j) => { if (!r.ok) throw new Error(j.error || 'Error del servidor'); return j; }))
        .then(pintar).catch((e) => { $('#c-msg').textContent = e.message; })
        .finally(() => { b.disabled = false; b.textContent = 'Comparar'; });
    });
    return { quitar };
  }
  window.COMPARADOR = { iniciar };
})();
