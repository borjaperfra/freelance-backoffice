// La página del cliente (/c/<slug>/) de un proyecto compartido: lo mínimo que trabajo.js necesita del admin
// (window.Admin) para pintar el trabajo de ese proyecto, en solo lectura. Lee datos.json de su carpeta,
// que solo trae ese proyecto. Lo copia trabajo.py al montar la web.
(function () {
  var D, app = document.getElementById('app'), P = (window.ES_CLIENTE || {}).proyecto;
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  var MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'];
  var fecha = function (iso) {
    if (!iso) return '—';
    var p = iso.split('-');
    return p.length < 3 ? MESES[+p[1] - 1] + ' ' + p[0] : +p[2] + ' ' + MESES[+p[1] - 1] + ' ' + p[0];
  };
  var V = {};
  var pintar = function () {
    var partes = (location.hash.slice(1) || '').split('/');
    // Solo este proyecto: cualquier otra ruta vuelve a su portada
    if (!V[partes[0]] || decodeURIComponent(partes[1] || '') !== P) partes = ['trabajo', P];
    document.body.classList.remove('presentando');
    app.innerHTML = V[partes[0]].apply(null, partes.slice(1).map(function (x) { return decodeURIComponent(x); }).concat(['', '']));
    document.title = ((app.querySelector('h1') || {}).textContent || 'Proyecto') + (D.negocio.nombre ? ' · ' + D.negocio.nombre : '');
    if (Admin.despues) Admin.despues(partes[0]);
    if (!Admin.mantenerScroll) window.scrollTo(0, 0);
    Admin.mantenerScroll = false;
  };
  window.addEventListener('hashchange', pintar);
  var Admin = window.Admin = {
    V: V, esc: esc, fecha: fecha, hoy: new Date().toISOString().slice(0, 10), pintar: pintar,
    datos: function () { return D; },
    proyecto: function () { return { nombre: ((D.trabajo || {})[P] || { espacio: {} }).espacio.titulo }; }
  };
  document.addEventListener('DOMContentLoaded', function () {
    fetch('datos.json', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) {
      D = d;
      document.getElementById('pie').textContent = 'Actualizado el ' + fecha(d.generado.slice(0, 10)) + '. Documento privado.';
      pintar();
    }).catch(function () {
      app.innerHTML = '<h1>No se ha podido cargar</h1><p class="sub">Vuelve a abrir el enlace o recarga la página.</p>';
    });
  });
})();
