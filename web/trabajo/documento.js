// Documentos de un proyecto: modo oscuro, barra de lectura, índice activo y modo presentación.
(function () {
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };

  // Modo oscuro: el del sistema; el botón manda durante la visita
  try { var guardado = sessionStorage.getItem('theme'); if (guardado) document.documentElement.dataset.theme = guardado; } catch (e) {}
  var modo = $('#mode');
  if (modo) modo.addEventListener('click', function () {
    var oscuro = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    var next = oscuro ? 'light' : 'dark';
    try { sessionStorage.setItem('theme', next); } catch (e) {}
    document.documentElement.dataset.theme = next;
  });

  // Barra de lectura e índice activo
  var barra = $('.progress span');
  var enlaces = $$('.toc a');
  var titulos = enlaces.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
  var alDesplazar = function () {
    var max = document.documentElement.scrollHeight - innerHeight;
    if (barra) barra.style.width = (max > 0 ? scrollY / max * 100 : 0) + '%';
    var actual = -1;
    titulos.forEach(function (t, i) { if (t && t.getBoundingClientRect().top < 120) actual = i; });
    enlaces.forEach(function (a, i) { a.classList.toggle('on', i === actual); });
  };
  addEventListener('scroll', alDesplazar, { passive: true });
  alDesplazar();

  // Dentro del admin (en un iframe), Esc sin estar presentando cierra el visor
  if (window.parent !== window) document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !document.body.classList.contains('presentando')) parent.postMessage({ tipo: 'entregable-cerrar' }, '*');
  });

  // Presentar: una diapositiva cada vez, a pantalla completa, con flechas
  var slides = $$('.slide');
  if (!slides.length) return;
  var n = 0, cuenta = $('.pres-n');
  var ir = function (i) {
    n = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach(function (s, j) { s.classList.toggle('on', j === n); });
    if (cuenta) cuenta.textContent = (n + 1) + ' / ' + slides.length;
  };
  var presentar = function (desde) {
    document.body.classList.add('presentando');
    ir(desde || 0);
    var el = document.documentElement;
    // Dentro del admin no: la pantalla completa la pone el admin, con su barra de Volver y Cerrar
    if (window.parent === window && el.requestFullscreen && !document.fullscreenElement) el.requestFullscreen().catch(function () {});
  };
  var salir = function () {
    document.body.classList.remove('presentando');
    if (document.fullscreenElement) document.exitFullscreen().catch(function () {});
    slides[n].scrollIntoView({ block: 'center' });
  };
  $$('[data-presentar]').forEach(function (b) { b.addEventListener('click', function () { presentar(0); }); });
  slides.forEach(function (s, i) { s.addEventListener('dblclick', function () { if (!document.body.classList.contains('presentando')) presentar(i); }); });
  var bar = $('.pres-bar');
  if (bar) bar.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-ir]');
    if (b) ir(n + Number(b.dataset.ir));
  });
  $$('[data-salir]').forEach(function (b) { b.addEventListener('click', salir); });
  // El admin puede pedir que se presente
  addEventListener('message', function (e) {
    if (e.source === parent && e.data && e.data.tipo === 'entregable-presentar') presentar(0);
  });
  document.addEventListener('fullscreenchange', function () {
    if (!document.fullscreenElement && document.body.classList.contains('presentando')) salir();
  });
  document.addEventListener('keydown', function (e) {
    if (!document.body.classList.contains('presentando')) return;
    if (['ArrowRight', 'PageDown', ' ', 'Enter'].indexOf(e.key) >= 0) { e.preventDefault(); ir(n + 1); }
    if (['ArrowLeft', 'PageUp', 'Backspace'].indexOf(e.key) >= 0) { e.preventDefault(); ir(n - 1); }
    if (e.key === 'Home') ir(0);
    if (e.key === 'End') ir(slides.length - 1);
    if (e.key === 'Escape') salir();
  });
  // Abrir directamente presentando: <página>#presentar
  if (location.hash === '#presentar') presentar(0);
})();
