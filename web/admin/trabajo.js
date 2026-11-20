// El trabajo de un proyecto: fases, entregables en carpetas, documentos (página y PDF), decisiones, pruebas
// y un resumen, con un visor que siempre deja volver y cerrar. Pinta D.trabajo[<proyecto>] y solo lee:
// los cambios los hace tu agente de código en datos/trabajo/ (ver docs/trabajo.md).
// La página del cliente (/c/<slug>/) usa este mismo archivo, en solo lectura y sin lo interno del admin.
(function () {
  var A = window.Admin, V = A.V, esc = A.esc, fecha = A.fecha;
  var CLIENTE = !!window.ES_CLIENTE;
  var app = document.getElementById('app');

  // ---- Etiquetas ----
  var L = {
    doc: { borrador: 'Borrador', en_revision: 'En revisión', revisado: 'Revisado', aprobado: 'Aprobado', sustituido: 'Sustituido' },
    ent: { sin_empezar: 'Sin empezar', en_curso: 'En curso', en_revision: 'En revisión', revisado: 'Revisado', aprobado: 'Aprobado' },
    fase: { pendiente: 'Pendiente', en_curso: 'En curso', hecha: 'Hecha' },
    decision: { propuesta: 'Propuesta', aprobada: 'Aprobada', rechazada: 'Rechazada', sustituida: 'Sustituida' },
    decisiones: { propuesta: 'Propuestas', aprobada: 'Aprobadas', rechazada: 'Rechazadas', sustituida: 'Sustituidas' },
    prueba: { prevista: 'Prevista', en_marcha: 'En marcha', hecha: 'Hecha', descartada: 'Descartada' },
    formato: { presentacion: 'Presentación', documento: 'Documento' }
  };
  var TONO = {
    aprobado: 'ok', aprobada: 'ok', revisado: 'ok', hecha: 'ok', en_revision: 'warn', en_marcha: 'warn',
    sin_empezar: 'off', pendiente: 'off', sustituido: 'off', sustituida: 'off', rechazada: 'off', descartada: 'off', prevista: 'off'
  };
  var chip = function (grupo, v) {
    return '<span class="es-chip ' + (TONO[v] || '') + '">' + esc((L[grupo] || {})[v] || v) + '</span>';
  };

  // ---- Datos ----
  var D = function () { return A.datos(); };
  var E = function (p) { return (D().trabajo || {})[p]; };
  var fases = function (p) { return E(p).espacio.fases || []; };
  var nombreFase = function (p, id) { return (fases(p).filter(function (f) { return f.id === id; })[0] || { nombre: id || '' }).nombre; };
  var ent = function (p, c) { return E(p).entregables.filter(function (x) { return x.codigo === c; })[0]; };
  var doc = function (p, id) { return E(p).documentos.filter(function (x) { return x.id === id; })[0]; };
  var docsDe = function (p, c, conSustituidos) {
    return E(p).documentos.filter(function (d) {
      return d.entregable === c && (conSustituidos || d.estado !== 'sustituido');
    }).sort(function (a, b) { return (a.etiqueta || a.id) < (b.etiqueta || b.id) ? -1 : 1; });
  };
  var archivo = function (p, nombre) { return 'trabajo/' + encodeURIComponent(p) + '/' + encodeURIComponent(nombre); };
  var peso = function (b) { return b > 1048576 ? (b / 1048576).toFixed(1).replace('.', ',') + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB'; };
  var nombreDoc = function (d) { return d.etiqueta || L.formato[d.formato]; };
  // Abrir un documento dentro del admin, en el visor: siempre con Volver y Cerrar a la vista
  var verUrl = function (p, id, modo) { return '#ver/' + encodeURIComponent(p) + '/' + encodeURIComponent(id) + (modo ? '/' + encodeURIComponent(modo) : ''); };
  var abrir = function (p, d) {
    if (!d.pagina) return '';
    return (d.formato === 'presentacion' ? '<a href="' + verUrl(p, d.id, 'presentar') + '" data-pantalla>Presentar</a>' : '') +
      '<a href="' + verUrl(p, d.id) + '">' + (d.formato === 'presentacion' ? 'Ver las pantallas' : 'Leer') + '</a>';
  };
  var descargar = function (p, d) {
    return d.pdf ? '<a href="' + archivo(p, d.pdf) + '" download>Descargar PDF</a>' : '';
  };
  var activo = function (p, x) { return x.estado !== 'sin_empezar' || docsDe(p, x.codigo).length > 0; };
  var porCodigo = function (a, b) { return a.codigo < b.codigo ? -1 : 1; };
  var abiertas = function (p) { return E(p).decisiones.filter(function (x) { return x.estado === 'propuesta'; }).sort(porCodigo); };
  var decisionesDe = function (p, c, id) {
    return E(p).decisiones.filter(function (x) {
      return (c && (x.entregables || []).indexOf(c) >= 0) || (id && (x.documentos || []).indexOf(id) >= 0);
    });
  };

  // Texto con párrafos, listas (- o 1.) y **negrita**. Todo escapado antes.
  var prosa = function (t) {
    if (!t) return '';
    return t.split(/\n{2,}/).map(function (bloque) {
      var lineas = bloque.split('\n');
      var fmt = function (s) { return esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'); };
      if (lineas.every(function (l) { return /^\s*(-|\*|\d+\.)\s+/.test(l); })) {
        var ord = /^\s*\d+\./.test(lineas[0]);
        return '<' + (ord ? 'ol' : 'ul') + '>' + lineas.map(function (l) {
          return '<li>' + fmt(l.replace(/^\s*(-|\*|\d+\.)\s+/, '')) + '</li>';
        }).join('') + '</' + (ord ? 'ol' : 'ul') + '>';
      }
      return '<p>' + lineas.map(fmt).join('<br>') + '</p>';
    }).join('');
  };

  var migas = function (lista) {
    return '<nav class="es-migas" aria-label="Ruta">' + lista.map(function (m, i) {
      return i < lista.length - 1 ? '<a href="' + m[0] + '">' + esc(m[1]) + '</a>' : '<span>' + esc(m[1]) + '</span>';
    }).join('<i>/</i>') + '</nav>';
  };
  var base = function (p) {
    return CLIENTE ? [['#trabajo/' + p, E(p).espacio.titulo]]
      : [['#proyecto/' + p, (A.proyecto(p) || {}).nombre || p], ['#trabajo/' + p, E(p).espacio.titulo]];
  };
  var noExiste = function () {
    return '<h1>No existe</h1><p class="sub"><a href="' + (CLIENTE ? '#' : '#proyectos') + '">' + (CLIENTE ? 'Volver al inicio' : 'Volver a proyectos') + '</a></p>';
  };
  var pista = function (texto) { return CLIENTE ? '' : '<p class="pista">' + texto + '</p>'; };

  // ---- Entrada desde la ficha del proyecto ----
  A.bloqueProyecto = function (slug) {
    var e = E(slug);
    if (!e) return '';
    var n = abiertas(slug).length;
    return '<a class="es-entrada" href="#trabajo/' + esc(slug) + '"><b>Fases, entregables y documentos</b>' +
      '<small>' + esc(e.espacio.descripcion || '') + ' Fase actual: ' + esc(nombreFase(slug, e.espacio.fase_actual)) + '. ' +
      n + (n === 1 ? ' decisión abierta.' : ' decisiones abiertas.') + '</small><i aria-hidden="true">→</i></a>';
  };
  ['trabajo', 'entregable', 'doc', 'ver', 'resumen', 'decisiones', 'prueba', 'documentos', 'comocliente'].forEach(function (v) {
    if (A.seccion) A.seccion[v] = 'proyectos';
  });

  // ---- Portada ----
  var timeline = function (p, activa) {
    var esp = E(p).espacio;
    return '<ol class="es-fases" aria-label="Fases">' + fases(p).map(function (f) {
      var actual = esp.fase_actual === f.id;
      return '<li class="' + esc(f.estado) + (actual ? ' actual' : '') + (activa === f.id ? ' on' : '') + '">' +
        '<a href="#trabajo/' + esc(p) + (activa === f.id ? '' : '/' + esc(f.id)) + '"' + (activa === f.id ? ' aria-current="true"' : '') + '>' +
        '<span class="es-punto" aria-hidden="true"></span>' +
        '<b>' + esc(f.nombre) + '</b><em>' + esc(actual ? 'Fase actual' : L.fase[f.estado] || f.estado) + '</em></a></li>';
    }).join('') + '</ol>';
  };

  var contenido = function (p, x) {
    var n = docsDe(p, x.codigo).length + (x.capitulos || []).length;
    var t = n ? n + (n === 1 ? ' documento' : ' documentos') : '';
    if (x.tipo === 'pruebas') {
      var m = E(p).pruebas.length;
      t += (t ? ' y ' : '') + m + (m === 1 ? ' prueba' : ' pruebas');
    }
    return t;
  };

  var carpeta = function (p, x) {
    return '<a class="es-carpeta" href="#entregable/' + esc(p) + '/' + esc(x.codigo) + '">' +
      '<span class="es-pestana">' + esc(x.codigo) + '</span>' +
      '<span class="es-carpeta-cuerpo"><b>' + esc(x.titulo) + '</b>' +
      '<span class="es-carpeta-desc">' + esc(x.descripcion || '') + '</span>' +
      '<span class="es-carpeta-pie"><span>' + esc(contenido(p, x)) + '</span>' +
      (x.estado === 'en_curso' ? '' : chip('ent', x.estado)) + '</span></span></a>';
  };

  // Cómo seguir: el resumen (dónde estamos), la presentación de la reunión y el documento que la respalda
  var fechaLarga = function (iso) {
    var m = 'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split(' ');
    return +iso.slice(8, 10) + ' de ' + m[+iso.slice(5, 7) - 1];
  };
  var seguir = function (p) {
    var esp = E(p).espacio, r = esp.reunion || {};
    var pres = r.presentacion && doc(p, r.presentacion), dos = esp.dossier && doc(p, esp.dossier);
    var parte = function (titulo, texto, href, accion, extra) {
      return '<div class="es-seguir-p"><h3>' + titulo + '</h3><p>' + texto + '</p>' +
        '<a class="es-boton claro" href="' + href + '"' + (extra || '') + '>' + accion + '</a></div>';
    };
    var out = '';
    if (esp.resumen) out += parte('Dónde estamos', 'El estado del proyecto hoy y las decisiones que siguen abiertas.', '#resumen/' + esc(p), 'Ver el resumen');
    if (pres && pres.pagina) {
      var pasada = r.fecha && r.fecha < A.hoy;
      var cuando = r.fecha ? (pasada ? 'Última reunión, ' : 'Reunión del ') + fechaLarga(r.fecha) : 'Para la reunión';
      out += parte(esc(cuando), 'La presentación «' + esc(pres.titulo) + '»' + (pasada ? ', la última que vimos.' : ', la que vamos a ver.'),
        verUrl(p, pres.id, pres.formato === 'presentacion' ? 'presentar' : ''), pres.formato === 'presentacion' ? 'Presentar' : 'Leer', pres.formato === 'presentacion' ? ' data-pantalla' : '');
    }
    if (dos && dos.pagina) out += parte('A fondo', esc(dos.descripcion || 'El documento que lo respalda, con todo el detalle.'), verUrl(p, dos.id), 'Leer');
    return out ? '<section class="es-seguir" aria-labelledby="es-seguir-t"><h2 id="es-seguir-t">Cómo seguir</h2><div class="es-seguir-in">' + out + '</div></section>' : '';
  };

  // Lo que aún no ha empezado va en lista, sin forma de carpeta
  var proximas = function (p, lista) {
    return '<ul class="es-proximas">' + lista.map(function (x) {
      return '<li><a href="#entregable/' + esc(p) + '/' + esc(x.codigo) + '"><span class="es-code">' + esc(x.codigo) + '</span>' +
        '<b>' + esc(x.titulo) + '</b><small>' + esc(nombreFase(p, x.fase)) + '</small></a></li>';
    }).join('') + '</ul>';
  };

  // Compartir con el cliente: quién lo ve y cómo darle acceso (los enlaces los crea tu agente)
  var compartir = function (p) {
    var c = E(p).compartir;
    if (CLIENTE) return '';
    if (!c) {
      return '<div class="es-pie-portada"><p class="muted">Tu cliente aún no lo ve. Para enseñárselo, dile a tu agente ' +
        '<code>comparte el proyecto con el cliente</code>.</p></div>';
    }
    var quien = (c.accesos || []).map(function (a) { return esc(a.nombre); });
    return '<div class="es-pie-portada"><h2>Lo ve tu cliente</h2><p>En <b>/c/' + esc(c.slug) + '/</b>, igual que aquí y en solo lectura. ' +
      (quien.length ? 'Entran con su enlace: ' + quien.join(', ') + '.' : 'Nadie tiene enlace todavía.') + '</p>' +
      '<p class="acciones"><a href="#comocliente/' + esc(p) + '">Ver como el cliente</a></p>' +
      '<p class="muted">Para dar acceso a alguien, dile a tu agente <code>dale acceso a Ana al proyecto</code>. Los cambios le llegan al publicar.</p></div>';
  };

  V.trabajo = function (p, fase) {
    var e = E(p);
    if (!e) return noExiste();
    var esp = e.espacio;
    if (fase && !fases(p).some(function (f) { return f.id === fase; })) fase = '';
    var html = '<div class="es es-portada"><div class="es-top">' + (CLIENTE ? '<span></span>' : migas([base(p)[0], ['', esp.titulo]])) +
      '<a class="es-buscar" href="#documentos/' + esc(p) + '">Buscar documentos</a></div>';
    html += '<div class="es-cab"><h1>' + esc(esp.titulo) + '</h1>' + (esp.descripcion ? '<p class="es-lead">' + esc(esp.descripcion) + '</p>' : '') + '</div>';
    html += timeline(p, fase);
    if (!fase) {
      var hito = esp.proximo_hito || {};
      html += '<dl class="es-resumen"><div><dt>Próximo hito</dt><dd>' + (hito.texto ? esc(hito.texto) +
        (hito.fecha ? '<small>' + fecha(hito.fecha) + '</small>' : '') : 'Sin fecha') + '</dd></div>' +
        '<div><dt>Decisiones abiertas</dt><dd><a href="#decisiones/' + esc(p) + '">' + abiertas(p).length + '</a></dd></div></dl>';
      html += seguir(p);
    }
    var deFase = function (x) { return !fase || x.fase === fase; };
    var activos = e.entregables.filter(function (x) { return deFase(x) && activo(p, x); }).sort(porCodigo);
    var futuros = e.entregables.filter(function (x) { return deFase(x) && !activo(p, x); }).sort(porCodigo);
    html += '<h2>Entregables' + (fase ? ' de ' + esc(nombreFase(p, fase)) + ' <small><a href="#trabajo/' + esc(p) + '">Ver todos</a></small>' : '') + '</h2>';
    html += activos.length ? '<div class="es-carpetas">' + activos.map(function (x) { return carpeta(p, x); }).join('') + '</div>'
      : '<p class="vacio">' + (fase ? 'Esta fase aún no tiene entregables en marcha.' : 'Aún no hay entregables en marcha.') + '</p>';
    if (futuros.length) html += '<h2>Próximas fases</h2>' + proximas(p, futuros);
    if (!fase) {
      html += '<h2>Decisiones abiertas <small><a href="#decisiones/' + esc(p) + '">Ver todas</a></small></h2>' + listaDecisiones(p, abiertas(p), true);
      html += compartir(p);
    }
    return html + '</div>';
  };

  // ---- Capas a pantalla entera (visor y resumen): Volver a la izquierda, Cerrar a la derecha ----
  // A dónde vuelve cada capa: el visor, a donde estabas (también al resumen); el resumen, a la vista de antes
  var vuelta = { base: '', ver: '' };
  var volverA = function (p, tipo) { return (tipo === 'ver' && vuelta.ver) || vuelta.base || '#trabajo/' + p; };
  var barraCapa = function (p, titulo, sub, acciones, tipo) {
    var v = esc(volverA(p, tipo));
    return '<div class="es-capa-barra"><a class="es-volver" href="' + v + '"><span aria-hidden="true">←</span> Volver</a>' +
      '<span class="es-capa-t"><b>' + titulo + '</b>' + (sub ? '<small>' + sub + '</small>' : '') + '</span>' +
      '<span class="es-capa-acc">' + (acciones || '') +
      '<a class="es-cerrar" href="' + v + '" aria-label="Cerrar" title="Cerrar (Esc)"><span aria-hidden="true">✕</span></a></span></div>';
  };

  // ---- Resumen: el proyecto contado por capítulos ----
  var capAnterior = null;
  V.resumen = function (p, n) {
    var e = E(p);
    if (!e) return noExiste();
    var h = e.espacio.resumen;
    if (!h) { location.replace('#trabajo/' + p); return ''; }
    var caps = h.capitulos || [], total = caps.length, i = Math.max(0, Math.min(total, parseInt(n, 10) || 0));
    var entra = capAnterior === null || capAnterior === i ? '' : i > capAnterior ? ' entra-sig' : ' entra-ant';
    capAnterior = i;
    var ir = function (k) { return '#resumen/' + encodeURIComponent(p) + (k ? '/' + k : ''); };
    var enlace = function (r) {
      return r && doc(p, r.doc) ? '<a class="es-hist-ref" href="' + verUrl(p, r.doc, r.ancla) + '">' + esc(r.texto || doc(p, r.doc).titulo) + ' <span aria-hidden="true">→</span></a>' : '';
    };
    var cuerpo;
    if (!i) {
      cuerpo = '<h1>' + esc(h.frase || e.espacio.titulo) + '</h1>' + (h.entradilla ? '<p class="es-lead">' + esc(h.entradilla) + '</p>' : '') +
        '<ol class="es-hist-pasos grande">' + caps.map(function (c, k) {
          return '<li><a href="' + ir(k + 1) + '"><b>' + esc(c.titulo) + '</b><small>' + esc(c.entradilla || '') + '</small></a></li>';
        }).join('') + '</ol>';
    } else {
      var c = caps[i - 1];
      cuerpo = '<h1>' + esc(c.titulo) + '</h1>' + (c.entradilla ? '<p class="es-lead">' + esc(c.entradilla) + '</p>' : '');
      if ((c.puntos || []).length) {
        cuerpo += '<div class="es-hist-puntos">' + c.puntos.map(function (q) {
          return '<article><h3>' + esc(q.titulo) + '</h3><p>' + esc(q.texto) + '</p>' + enlace(q.ref) + '</article>';
        }).join('') + '</div>';
      }
      if (c.decisiones) {
        cuerpo += '<ol class="es-hist-decs">' + abiertas(p).map(function (x) {
          return '<li><span class="es-code">' + esc(x.codigo) + '</span><div><b>' + esc(x.titulo) + '</b>' +
            (x.descripcion ? '<p>' + esc(x.descripcion) + '</p>' : '') + '</div></li>';
        }).join('') + '</ol><p class="es-hist-links"><a class="es-hist-ref" href="#decisiones/' + esc(p) + '">Todas las decisiones <span aria-hidden="true">→</span></a>' + enlace(c.ref) + '</p>';
      }
      if (c.aparte && (c.aparte.puntos || []).length) {
        cuerpo += '<h2>' + esc(c.aparte.titulo || '') + '</h2><ul class="es-hist-no">' + c.aparte.puntos.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' +
          '<p class="es-hist-links">' + enlace(c.aparte.ref) + '</p>';
      }
    }
    var pasos = '<nav class="es-hist-nav" aria-label="Capítulos">' + ['Inicio'].concat(caps.map(function (c) { return c.titulo; })).map(function (t, k) {
      return k === i ? '<span aria-current="step">' + esc(t) + '</span>' : '<a href="' + ir(k) + '">' + esc(t) + '</a>';
    }).join('') + '</nav>';
    var pie = '<div class="es-hist-pie">' + (i > 0 ? '<a href="' + ir(i - 1) + '" data-hist="ant"><span aria-hidden="true">←</span> ' + esc(i > 1 ? caps[i - 2].titulo : 'Inicio') + '</a>' : '<span></span>') +
      (i < total ? '<a class="es-boton" href="' + ir(i + 1) + '" data-hist="sig">' + esc(caps[i].titulo) + ' <span aria-hidden="true">→</span></a>'
        : '<a class="es-boton" href="' + esc(volverA(p)) + '">Terminar</a>') + '</div>';
    return '<div class="es-capa es-hist" data-volver="' + esc(volverA(p)) + '">' +
      barraCapa(p, 'Resumen', esc(e.espacio.titulo), '', 'resumen') +
      '<div class="es-hist-scroll"><div class="es-hist-in' + entra + '">' + pasos + cuerpo + pie + '</div></div></div>';
  };

  // ---- La página del cliente, tal como la ve (copia dentro del admin) ----
  V.comocliente = function (p) {
    var e = E(p);
    if (!e || !e.compartir || CLIENTE) return noExiste();
    return '<div class="es-capa es-visor-capa" data-volver="' + esc(volverA(p, 'ver')) + '">' +
      barraCapa(p, 'Como lo ve el cliente', esc('/c/' + e.compartir.slug + '/'), '', 'ver') +
      '<iframe src="espacios/' + encodeURIComponent(e.compartir.slug) + '/index.html" title="Página del cliente"></iframe></div>';
  };

  // ---- Visor de un documento ----
  V.ver = function (p, id, modo) {
    var e = E(p), d = e && doc(p, id);
    if (!d) return noExiste();
    if (!d.pagina) { location.replace('#doc/' + p + '/' + id); return ''; }
    var src = archivo(p, d.pagina) + (modo === 'presentar' ? '#presentar' : modo ? '#' + encodeURIComponent(modo) : '');
    var acciones = chip('doc', d.estado) + (d.formato === 'presentacion' ? '<button type="button" data-capa="presentar">Presentar</button>' : '') + descargar(p, d);
    return '<div class="es-capa es-visor-capa" data-volver="' + esc(volverA(p, 'ver')) + '">' +
      barraCapa(p, esc(d.titulo), esc(nombreDoc(d) + ' · v' + d.version + ' · ' + L.doc[d.estado]), acciones, 'ver') +
      '<iframe src="' + src + '" title="' + esc(d.titulo) + '"></iframe></div>';
  };

  // ---- Entregable ----
  V.entregable = function (p, c, ver) {
    var e = E(p), x = e && ent(p, c);
    if (!x) return noExiste();
    var html = '<div class="es">' + migas(base(p).concat([['', x.codigo + ' · ' + x.titulo]]));
    html += '<div class="es-cab"><h1>' + esc(x.titulo) + '</h1>' + (x.descripcion ? '<p class="es-lead">' + esc(x.descripcion) + '</p>' : '') +
      '<p class="sub">' + chip('ent', x.estado) + ' <span class="muted">' + esc(nombreFase(p, x.fase)) + '</span></p></div>';
    html += lector(p, x, ver, '#entregable/' + esc(p) + '/' + esc(c));
    html += capitulos(p, x);
    if (x.tipo === 'pruebas') html += pruebas(p, x);
    if (!docsDe(p, c).length && !(x.capitulos || []).length && x.tipo !== 'pruebas') {
      html += '<p class="vacio">Aún no hay documentos en esta carpeta.</p>';
    }
    var viejos = docsDe(p, c, true).filter(function (d) { return d.estado === 'sustituido'; });
    if (viejos.length) html += '<h2>Sustituidos</h2><div class="es-filas">' + viejos.map(function (d) { return fila(p, d); }).join('') + '</div>';
    var ds = decisionesDe(p, c);
    if (ds.length) html += '<h2>Decisiones <small><a href="#decisiones/' + esc(p) + '">Ver todas</a></small></h2>' + listaDecisiones(p, ds, true);
    return html + '</div>';
  };

  // Pestañas con los documentos de la carpeta y la página del elegido
  var lector = function (p, x, ver, enlace) {
    var docs = docsDe(p, x.codigo);
    if (!docs.length) return '';
    var d = docs.filter(function (y) { return y.id === ver; })[0] || docs[0];
    var html = '<section class="es-lector"><div class="es-lector-cab"><div class="es-saltos" role="tablist">' + docs.map(function (y) {
      return y.id === d.id ? '<span class="on" role="tab" aria-selected="true">' + esc(nombreDoc(y)) + '</span>'
        : '<a role="tab" href="' + enlace + '/' + esc(y.id) + '">' + esc(nombreDoc(y)) + '</a>';
    }).join('') + '</div><p class="es-chips">' + chip('doc', d.estado) + '<span>v' + esc(d.version) + '</span><span>' + fecha(d.fecha) + '</span></p></div>';
    html += '<div class="es-acciones">' + abrir(p, d) + descargar(p, d) + '<a href="#doc/' + esc(p) + '/' + esc(d.id) + '">Versiones y detalles</a></div>';
    html += d.pagina ? '<div class="es-pagina"><iframe src="' + archivo(p, d.pagina) + '" title="' + esc(d.titulo) + '"></iframe></div>'
      : '<p class="vacio">Este documento aún no tiene página.</p>';
    return html + '</section>';
  };

  // Capítulos de esta carpeta que viven dentro de otro documento
  var capitulos = function (p, x) {
    var caps = (x.capitulos || []).filter(function (c) { return doc(p, c.doc); });
    if (!caps.length) return '';
    return '<h2>Dónde está ahora</h2><div class="es-filas">' + caps.map(function (c) {
      var d = doc(p, c.doc);
      return '<a class="es-fila" href="' + verUrl(p, c.doc, c.ancla) + '"><span class="es-fila-code">' + esc(nombreDoc(d)) + '</span>' +
        '<span class="es-fila-t"><b>' + esc(c.texto) + '</b><small>' + esc(d.titulo) + '</small></span>' +
        '<span class="es-fila-m">' + chip('doc', d.estado) + '<small>v' + esc(d.version) + '</small></span></a>';
    }).join('') + '</div>';
  };

  var fila = function (p, d) {
    var x = ent(p, d.entregable);
    return '<a class="es-fila" href="#doc/' + esc(p) + '/' + esc(d.id) + '">' +
      '<span class="es-fila-code">' + esc((d.entregable ? d.entregable + ' · ' : '') + L.formato[d.formato]) + '</span>' +
      '<span class="es-fila-t"><b>' + esc(d.titulo) + '</b><small>' + esc(x ? x.titulo : 'Del proyecto') + '</small></span>' +
      '<span class="es-fila-m">' + chip('doc', d.estado) + '<small>v' + esc(d.version) + ' · ' + fecha(d.fecha) + '</small></span></a>';
  };

  // ---- Documento: la página, sus versiones y lo relacionado ----
  V.doc = function (p, id) {
    var e = E(p), d = e && doc(p, id);
    if (!d) return noExiste();
    var x = ent(p, d.entregable);
    var html = '<div class="es es-lectura">' + migas(base(p).concat(x ? [['#entregable/' + p + '/' + x.codigo, x.codigo + ' · ' + x.titulo]] : []).concat([['', nombreDoc(d)]]));
    html += '<div class="es-cab"><h1>' + esc(d.titulo) + '</h1>' + (d.descripcion ? '<p class="es-lead">' + esc(d.descripcion) + '</p>' : '') +
      '<p class="es-chips">' + chip('doc', d.estado) + '<span>v' + esc(d.version) + '</span><span>' + esc(L.formato[d.formato]) + '</span><span>' + fecha(d.fecha) + '</span></p></div>';
    if (d.sustituido_por) {
      html += '<div class="es-aviso">Lo sustituye <a href="#doc/' + esc(p) + '/' + esc(d.sustituido_por) + '">' +
        esc((doc(p, d.sustituido_por) || {}).titulo || d.sustituido_por) + '</a>. Se conserva para saber de dónde venimos.</div>';
    }
    html += '<div class="es-acciones">' + abrir(p, d) + descargar(p, d) + '</div>';
    html += '<div class="es-doc"><div class="es-doc-cuerpo">' + (d.pagina ? '<div class="es-pagina"><iframe src="' + archivo(p, d.pagina) + '" title="' + esc(d.titulo) + '"></iframe></div>'
      : '<p class="vacio">Este documento aún no tiene página.</p>') + '</div><aside class="es-doc-lado">' + lado(p, d) + '</aside></div>';
    return html + '</div>';
  };

  var lado = function (p, d) {
    var vers = (d.versiones || []).slice().reverse();
    var html = '<h3>Versiones</h3>' + (vers.length ? '<ol class="es-versiones">' + vers.map(function (v, i) {
      return '<li' + (i === 0 ? ' class="actual"' : '') + '><b>v' + esc(v.version) + (v.version === d.version ? ', actual' : '') + '</b>' +
        '<a href="' + archivo(p, v.pdf) + '" download>' + esc(v.pdf) + '</a><small>' + fecha(v.fecha) + ' · ' + peso(v.bytes) + '</small></li>';
    }).join('') + '</ol>' : '<p class="es-vacio-mini">Sin PDF todavía.</p>');
    if (d.sustituye && doc(p, d.sustituye)) {
      html += '<h3>Sustituye a</h3><p><a href="#doc/' + esc(p) + '/' + esc(d.sustituye) + '">' + esc(doc(p, d.sustituye).titulo) + '</a></p>';
    }
    var ds = decisionesDe(p, null, d.id);
    if (ds.length) {
      html += '<h3>Decisiones</h3><ul class="es-rel">' + ds.map(function (x) {
        return '<li><a href="#decisiones/' + esc(p) + '"><small>' + esc(x.codigo) + ' · ' + esc(L.decision[x.estado]) + '</small>' + esc(x.titulo) + '</a></li>';
      }).join('') + '</ul>';
    }
    if (!CLIENTE) html += '<h3>Archivo</h3><p class="es-vacio-mini"><code>datos/trabajo/' + esc(p) + '/documentos/' + esc(d.id) + '.md</code></p>';
    return html;
  };

  // ---- Pruebas: qué se ha probado y qué se ha aprendido ----
  var recoge = function (p, k) {
    return E(p).pruebas.filter(function (y) { return y[k] && y.estado !== 'descartada'; }).map(function (y) { return { id: y.id, texto: y[k] }; });
  };
  var hallazgos = function (p, lista) {
    return lista.length ? '<ul class="es-hallazgos">' + lista.map(function (h) {
      return '<li><a href="#prueba/' + esc(p) + '/' + esc(h.id) + '">' + esc(h.id) + '</a>' + esc(h.texto.length > 240 ? h.texto.slice(0, 240) + '…' : h.texto) + '</li>';
    }).join('') + '</ul>' : '<p class="es-vacio-mini">Nada anotado.</p>';
  };
  var pruebas = function (p, x) {
    var lista = E(p).pruebas.slice().sort(function (a, b) { return a.id < b.id ? 1 : -1; });
    var html = '';
    if (x.sintesis) html += '<h2>Lo que nos dicen</h2><div class="es-prosa">' + prosa(x.sintesis) + '</div>';
    if (lista.length) {
      html += '<div class="es-tres"><div><h3>Qué ha funcionado</h3>' + hallazgos(p, recoge(p, 'funciono')) + '</div>' +
        '<div><h3>Fricciones</h3>' + hallazgos(p, recoge(p, 'fricciones')) + '</div>' +
        '<div><h3>Qué implica</h3>' + hallazgos(p, recoge(p, 'implicaciones')) + '</div></div>';
    }
    html += '<h2>Registro de pruebas <small>' + lista.length + (lista.length === 1 ? ' prueba' : ' pruebas') + '</small></h2>';
    html += lista.length ? '<div class="es-grid">' + lista.map(function (y) {
      return '<article class="es-card"><a class="es-card-main" href="#prueba/' + esc(p) + '/' + esc(y.id) + '">' +
        '<div class="es-card-top"><span class="es-code">' + esc(y.id) + '</span>' + chip('prueba', y.estado) + '</div>' +
        '<h3>' + esc(y.nombre) + '</h3><p>' + esc(y.objetivo || y.hipotesis || '') + '</p></a>' +
        '<p class="es-meta">' + fecha(y.fecha) + '</p></article>';
    }).join('') + '</div>' : '<p class="vacio">Todavía no hay pruebas.</p>';
    return html;
  };

  V.prueba = function (p, id) {
    var e = E(p), y = e && e.pruebas.filter(function (z) { return z.id === id; })[0];
    if (!y) return noExiste();
    var x = e.entregables.filter(function (z) { return z.tipo === 'pruebas'; })[0];
    var html = '<div class="es es-lectura">' + migas(base(p).concat(x ? [['#entregable/' + p + '/' + x.codigo, x.codigo + ' · ' + x.titulo]] : []).concat([['', y.id]]));
    html += '<div class="es-cab"><h1>' + esc(y.nombre) + '</h1><p class="es-chips">' + chip('prueba', y.estado) + '<span>' + fecha(y.fecha) + '</span></p></div>';
    var campo = function (t, v) {
      return v ? '<section><h2>' + t + '</h2><div class="es-prosa">' + prosa(v) + '</div></section>' : '';
    };
    html += '<div class="es-exp">' + campo('Objetivo', y.objetivo) + campo('Hipótesis', y.hipotesis) +
      '<div class="es-dos">' + campo('Qué esperábamos', y.esperado) + campo('Qué pasó', y.observado) + '</div>' +
      '<div class="es-dos">' + campo('Qué ha funcionado', y.funciono) + campo('Fricciones', y.fricciones) + '</div>' +
      campo('Qué implica', y.implicaciones) + campo('Notas', y.notas) + '</div>';
    return html + '</div>';
  };

  // ---- Decisiones ----
  var listaDecisiones = function (p, lista, compacta) {
    if (!lista.length) return '<p class="vacio">Ninguna.</p>';
    return '<div class="es-decs' + (compacta ? ' compacta' : '') + '">' + lista.map(function (x) {
      var docs = (x.documentos || []).map(function (id) { return doc(p, id); }).filter(Boolean);
      var ents = (x.entregables || []).map(function (c) { return ent(p, c); }).filter(Boolean);
      var cuerpo = compacta ? '' :
        (x.descripcion ? '<div class="es-prosa">' + prosa(x.descripcion) + '</div>' : '') +
        '<dl class="es-ficha">' + (x.justificacion ? '<dt>Por qué</dt><dd>' + prosa(x.justificacion) + '</dd>' : '') +
        (x.riesgos ? '<dt>Riesgos o dudas</dt><dd>' + prosa(x.riesgos) + '</dd>' : '') +
        (ents.length || docs.length ? '<dt>Relacionado</dt><dd class="es-links">' + ents.map(function (y) {
          return '<a href="#entregable/' + esc(p) + '/' + esc(y.codigo) + '">' + esc(y.codigo + ' · ' + y.titulo) + '</a>';
        }).join('') + docs.map(function (d) {
          return '<a href="#doc/' + esc(p) + '/' + esc(d.id) + '">' + esc(d.titulo) + '</a>';
        }).join('') + '</dd>' : '') + '</dl>';
      return '<article class="es-dec ' + esc(x.estado) + '"' + (compacta ? '' : ' id="' + esc(x.codigo) + '"') + '>' +
        '<a class="es-dec-cab" href="#decisiones/' + esc(p) + '"><span class="es-code">' + esc(x.codigo) + '</span><b>' + esc(x.titulo) + '</b>' +
        (x.estado === 'propuesta' ? '' : chip('decision', x.estado)) + '</a>' +
        (compacta ? '' : '<p class="es-meta">' + fecha(x.fecha) + (x.responsable ? ' · ' + esc(x.responsable) : '') + '</p>') + cuerpo + '</article>';
    }).join('') + '</div>';
  };

  V.decisiones = function (p, filtro) {
    var e = E(p);
    if (!e) return noExiste();
    var estados = ['propuesta', 'aprobada', 'rechazada', 'sustituida'];
    if (estados.indexOf(filtro) < 0) filtro = '';
    var lista = e.decisiones.filter(function (x) { return !filtro || x.estado === filtro; }).sort(porCodigo);
    var html = '<div class="es">' + migas(base(p).concat([['', 'Decisiones']])) + '<div class="es-cab"><h1>Decisiones</h1></div>';
    html += '<div class="filtros"><a href="#decisiones/' + esc(p) + '"' + (filtro ? '' : ' class="on"') + '>Todas <small>' + e.decisiones.length + '</small></a>' +
      estados.map(function (s) {
        var n = e.decisiones.filter(function (x) { return x.estado === s; }).length;
        return '<a href="#decisiones/' + esc(p) + '/' + s + '"' + (filtro === s ? ' class="on"' : '') + (n ? '' : ' data-vacio') + '>' + L.decisiones[s] + ' <small>' + n + '</small></a>';
      }).join('') + '</div>';
    return html + listaDecisiones(p, lista, false) + pista('Para apuntar una decisión o cambiar su estado, díselo a tu agente: <code>apunta la decisión de …</code>') + '</div>';
  };

  // ---- Buscar documentos ----
  var filtro = { q: '', fase: '', formato: '', estado: '' };
  var resultados = function (p) {
    var q = filtro.q.toLowerCase();
    return E(p).documentos.filter(function (d) {
      var x = ent(p, d.entregable) || {};
      if (filtro.fase && x.fase !== filtro.fase) return false;
      if (filtro.formato && d.formato !== filtro.formato) return false;
      if (filtro.estado && d.estado !== filtro.estado) return false;
      return !q || [d.titulo, d.descripcion, d.texto, x.titulo, d.id].join(' ').toLowerCase().indexOf(q) >= 0;
    }).sort(function (a, b) { return (a.entregable || '') + a.id < (b.entregable || '') + b.id ? -1 : 1; });
  };
  var pintarResultados = function (p) {
    var r = resultados(p), cont = document.getElementById('es-bib-lista');
    if (!cont) return;
    cont.innerHTML = '<p class="muted es-expl">' + r.length + (r.length === 1 ? ' documento' : ' documentos') + '</p>' +
      (r.length ? '<div class="es-filas">' + r.map(function (d) { return fila(p, d); }).join('') + '</div>' : '<p class="vacio">Nada con esos filtros.</p>');
  };
  V.documentos = function (p) {
    var e = E(p);
    if (!e) return noExiste();
    var sel = function (k, etiqueta, opciones) {
      return '<label><span>' + etiqueta + '</span><select data-bib="' + k + '"><option value="">Todos</option>' + opciones.map(function (o) {
        return '<option value="' + esc(o[0]) + '"' + (filtro[k] === o[0] ? ' selected' : '') + '>' + esc(o[1]) + '</option>';
      }).join('') + '</select></label>';
    };
    var html = '<div class="es">' + migas(base(p).concat([['', 'Documentos']])) + '<div class="es-cab"><h1>Documentos</h1></div>';
    html += '<div class="es-buscador"><label class="q"><span>Buscar</span><input type="search" data-bib="q" value="' + esc(filtro.q) + '" placeholder="Título o texto"></label>' +
      sel('fase', 'Fase', fases(p).map(function (f) { return [f.id, f.nombre]; })) +
      sel('formato', 'Tipo', Object.keys(L.formato).map(function (k) { return [k, L.formato[k]]; })) +
      sel('estado', 'Estado', Object.keys(L.doc).map(function (k) { return [k, L.doc[k]]; })) + '</div>';
    return html + '<div id="es-bib-lista"></div></div>';
  };
  app.addEventListener('input', function (ev) {
    var el = ev.target.closest('[data-bib]');
    if (!el) return;
    filtro[el.dataset.bib] = el.value;
    pintarResultados(decodeURIComponent(location.hash.split('/')[1] || ''));
  });

  // ---- Después de pintar ----
  A.despues = function (vista) {
    var partes = location.hash.slice(1).split('/');
    if (vista === 'documentos') pintarResultados(decodeURIComponent(partes[1] || ''));
    var capa = app.querySelector('.es-capa');
    if (capa) {
      document.body.classList.add('presentando');
      var fr = capa.querySelector('iframe');
      if (fr) fr.addEventListener('load', function () { fr.focus(); });
    } else if (document.fullscreenElement) document.exitFullscreen().catch(function () {});
    if (vista === 'resumen') vuelta.ver = location.hash;
    else if (vista !== 'ver' && vista !== 'comocliente') vuelta.base = vuelta.ver = location.hash;
  };

  // ---- Capas: cerrar con Esc (también desde dentro del iframe), presentar y pantalla completa ----
  var cerrarCapa = function () {
    var c = app.querySelector('.es-capa');
    if (c) location.hash = c.dataset.volver;
  };
  window.addEventListener('message', function (ev) {
    var f = app.querySelector('.es-capa iframe');
    if (f && ev.source === f.contentWindow && ev.data && ev.data.tipo === 'entregable-cerrar') cerrarCapa();
  });
  var pantallaCompleta = function () {
    var el = document.documentElement;
    if (!document.fullscreenElement && el.requestFullscreen) el.requestFullscreen().catch(function () {});
  };
  app.addEventListener('click', function (ev) {
    if (ev.target.closest('a[data-pantalla]')) pantallaCompleta();
    var b = ev.target.closest('[data-capa="presentar"]');
    var f = b && app.querySelector('.es-capa iframe');
    if (f) {
      pantallaCompleta();
      f.contentWindow.postMessage({ tipo: 'entregable-presentar' }, '*');
      f.focus();
    }
  }, true);
  document.addEventListener('keydown', function (ev) {
    if (ev.target.closest('input,textarea,select')) return;
    if (ev.key === 'Escape' && !document.fullscreenElement) cerrarCapa();
    var paso = app.querySelector('.es-hist [data-hist="' + (ev.key === 'ArrowRight' ? 'sig' : ev.key === 'ArrowLeft' ? 'ant' : '') + '"]');
    if (paso) { ev.preventDefault(); location.replace(paso.getAttribute('href')); }
  });
})();
