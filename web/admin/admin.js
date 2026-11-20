// Freelance Backoffice: pinta datos.json. Solo lee; los cambios se hacen con tu agente de código y backoffice.py.
// El trabajo de cada proyecto (fases, entregables, documentos) está en trabajo.js, que se engancha con window.Admin.
(function () {
  var D, app = document.getElementById('app');

  // ---- Utilidades ----
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  var eur = function (n) {
    return (n || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: 'always' }) + ' €';
  };
  var MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'];
  var fecha = function (iso) {
    if (!iso) return '—';
    var p = iso.split('-');
    return p.length < 3 ? MESES[+p[1] - 1] + ' ' + p[0] : +p[2] + ' ' + MESES[+p[1] - 1] + ' ' + p[0];
  };
  var hoy = new Date().toISOString().slice(0, 10);
  var dias = function (iso) { return Math.round((new Date(iso) - new Date(hoy)) / 864e5); };
  var suma = function (lista, k) { return lista.reduce(function (s, x) { return s + (x[k] || 0); }, 0); };
  var trimestre = function (iso) { return iso.slice(0, 4) + '-' + (Math.floor((+iso.slice(5, 7) - 1) / 3) + 1) + 'T'; };

  var cliente = function (slug) {
    return D.clientes.filter(function (c) { return c.slug === slug; })[0] || { nombre: slug, slug: slug };
  };
  var proyecto = function (slug) {
    return D.proyectos.filter(function (p) { return p.slug === slug; })[0];
  };
  var factura = function (n) {
    return D.facturas.filter(function (f) { return f.numero === n; })[0];
  };
  var tri = function (t) {
    return D.trimestres.filter(function (x) { return x.trimestre === t; })[0] || { a_pagar: 0, m303: {}, m130: {}, facturas: [], gastos: [], avisos: [] };
  };
  var gasto = function (id) { return D.gastos.filter(function (g) { return g.id === id; })[0]; };
  // Lo que cuenta como facturado: emitidas y cobradas, y las rectificativas que restan
  var vivas = function () { return D.facturas.filter(function (f) { return f.estado !== 'rectificada' && f.tipo !== 'rectificativa'; }); };

  var TONO = {
    activo: 'ok', cobrada: 'ok', cobrado: 'ok', terminado: 'off', cerrado: 'off', perdido: 'off', rectificada: 'off',
    pausado: 'off', vencida: 'warn', hecho: 'warn',
    confirmado: 'ok', 'falta factura': 'warn', pendiente: 'warn', previsto: 'off'
  };
  var estado = function (e) { return '<span class="estado ' + (TONO[e] || '') + '">' + esc(e) + '</span>'; };
  var estadoFactura = function (f) {
    if (f.estado === 'emitida' && f.vence < hoy) return estado('vencida');
    if (f.estado === 'emitida' && f.tipo === 'rectificativa') return estado('rectificativa');
    return estado(f.estado);
  };

  var tabla = function (cols, filas, vacio) {
    if (!filas.length) return '<p class="vacio">' + esc(vacio || 'Nada por aquí.') + '</p>';
    return '<table class="tabla"><thead><tr>' + cols.map(function (c) {
      return '<th class="' + (c.cls || '') + '">' + c.t + '</th>';
    }).join('') + '</tr></thead><tbody>' + filas.map(function (f) {
      return '<tr' + (f.href ? ' data-href="' + f.href + '"' : '') + '>' + f.celdas.map(function (x, i) {
        return '<td class="' + (cols[i].cls || '') + '">' + x + '</td>';
      }).join('') + '</tr>';
    }).join('') + '</tbody></table>';
  };
  var kpis = function (lista) {
    return '<div class="kpis">' + lista.map(function (k) {
      return '<div class="kpi"><b>' + k[0] + '</b><span>' + esc(k[1]) + '</span></div>';
    }).join('') + '</div>';
  };
  var ficha = function (pares) {
    return '<dl class="ficha">' + pares.filter(function (p) { return p[1]; }).map(function (p) {
      return '<div><dt>' + esc(p[0]) + '</dt><dd>' + p[1] + '</dd></div>';
    }).join('') + '</dl>';
  };
  var pista = function (texto) { return '<p class="pista">' + texto + '</p>'; };
  var linkCliente = function (slug) { return '<a href="#cliente/' + esc(slug) + '">' + esc(cliente(slug).nombre) + '</a>'; };

  var filaFactura = function (f) {
    return {
      href: '#factura/' + f.numero,
      celdas: [esc(f.numero), fecha(f.fecha), esc(cliente(f.cliente).nombre), eur(f.base), eur(f.total), estadoFactura(f)]
    };
  };
  var COLS_FACTURA = [{ t: 'Número' }, { t: 'Fecha', cls: 'opc' }, { t: 'Cliente' }, { t: 'Base', cls: 'n opc' },
    { t: 'Total', cls: 'n' }, { t: 'Estado', cls: 'n' }];

  // Hitos de todos los proyectos, con su proyecto al lado
  var hitos = function () {
    var out = [];
    D.proyectos.forEach(function (p) {
      (p.hitos || []).forEach(function (h) { out.push({ h: h, p: p }); });
    });
    return out;
  };

  // Lo que queda del plan. Se quita de aquí cuando esté hecho.

  // ---- Vistas ----
  var V = {};

  V.hoy = function () {
    var anyo = hoy.slice(0, 4), t = trimestre(hoy);
    var delAnyo = D.facturas.filter(function (f) { return f.fecha.slice(0, 4) === anyo; });
    var porCobrar = D.facturas.filter(function (f) { return f.estado === 'emitida' && f.tipo !== 'rectificativa'; })
      .sort(function (a, b) { return a.vence < b.vence ? -1 : 1; });
    var cobradoAnyo = delAnyo.filter(function (f) { return f.estado === 'cobrada'; });
    var paraFacturar = hitos().filter(function (x) { return x.h.estado === 'hecho'; });
    var proximos = hitos().filter(function (x) { return x.h.estado === 'pendiente' && x.h.fecha && dias(x.h.fecha) <= 21; })
      .sort(function (a, b) { return a.h.fecha < b.h.fecha ? -1 : 1; });
    var activos = D.proyectos.filter(function (p) { return p.estado === 'activo'; });
    var abiertas = D.proyectos.filter(function (p) { return p.estado === 'propuesta'; });

    var saludo = new Date().getHours() < 14 ? 'Buenos días' : 'Buenas tardes';
    var html = '<h1>' + saludo + '</h1><p class="sub">' + fecha(hoy) + ' · ' + t + '</p>';

    if ((D.pendientes || []).length) {
      html += '<h2>Lo que falta <small>díselo a tu agente</small></h2><ul class="falta">' + D.pendientes.map(function (p) {
        return '<li><span>' + esc(p.texto) + '</span><code>' + esc(p.pide) + '</code></li>';
      }).join('') + '</ul>';
    }

    if (D.problemas.length) {
      html += '<div class="avisos"><b>Cosas que arreglar</b><ul>' + D.problemas.map(function (p) {
        return '<li>' + esc(p) + '</li>';
      }).join('') + '</ul></div>';
    }

    html += kpis([
      [eur(suma(delAnyo, 'base')), 'Facturado en ' + anyo + ' (base)'],
      [eur(suma(cobradoAnyo, 'total')), 'Cobrado en ' + anyo],
      [eur(suma(porCobrar, 'total')), 'Por cobrar (' + porCobrar.length + ')'],
      [eur(suma(D.gastos.filter(function (g) { return g.fecha.slice(0, 4) === anyo; }), 'base')), 'Gastos en ' + anyo + ' (base)'],
      ['<a href="#trimestre/' + t + '">' + eur(tri(t).a_pagar) + '</a>', 'A apartar para el ' + t + ' (303 + 130)']
    ]);

    html += '<h2>Por cobrar <small>' + eur(suma(porCobrar, 'total')) + '</small></h2>';
    html += tabla([{ t: 'Número' }, { t: 'Cliente' }, { t: 'Vence', cls: 'opc' }, { t: 'Total', cls: 'n' }, { t: '', cls: 'n' }],
      porCobrar.map(function (f) {
        var d = dias(f.vence);
        return {
          href: '#factura/' + f.numero,
          celdas: [esc(f.numero), esc(cliente(f.cliente).nombre), fecha(f.vence), eur(f.total),
            d < 0 ? estado('vencida hace ' + -d + ' d') : '<span class="muted">en ' + d + ' d</span>']
        };
      }), 'Nadie te debe nada.');

    html += tablaBorradores();

    html += '<h2>Hecho y sin facturar</h2>';
    html += tabla([{ t: 'Hito' }, { t: 'Proyecto' }, { t: 'Importe', cls: 'n' }],
      paraFacturar.map(function (x) {
        return { href: '#proyecto/' + x.p.slug, celdas: [esc(x.h.nombre), esc(cliente(x.p.cliente).nombre + ' · ' + x.p.nombre), eur(x.h.importe)] };
      }), 'Todo lo hecho está facturado.');

    html += '<h2>Próximas tres semanas</h2>';
    html += tabla([{ t: 'Fecha' }, { t: 'Hito' }, { t: 'Proyecto', cls: 'opc' }, { t: 'Importe', cls: 'n' }],
      proximos.map(function (x) {
        var d = dias(x.h.fecha);
        return {
          href: '#proyecto/' + x.p.slug,
          celdas: [d < 0 ? estado('hace ' + -d + ' d') : fecha(x.h.fecha), esc(x.h.nombre),
            esc(cliente(x.p.cliente).nombre + ' · ' + x.p.nombre), eur(x.h.importe)]
        };
      }), 'Sin entregas a la vista.');

    var pv = D.prevision || { meses: [] };
    if (pv.meses.some(function (m) { return m.base || m.gastos; })) {
      var NOMBRE_MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'];
      html += '<h2>Próximos 6 meses <small>estimación</small></h2>' + tabla(
        [{ t: 'Mes' }, { t: 'Facturas', cls: 'n' }, { t: 'Gastos fijos', cls: 'n opc' }, { t: 'Apartar', cls: 'n' }, { t: 'Te queda', cls: 'n' }],
        pv.meses.map(function (m) {
          var p = m.mes.split('-');
          return { celdas: [NOMBRE_MES[+p[1] - 1] + ' ' + p[0] + (m.detalle.length ? '<br><span class="muted">' + esc(m.detalle.join(' · ')) + '</span>' : ''),
            eur(m.base), eur(m.gastos), eur(m.apartar), '<b>' + eur(m.queda) + '</b>'] };
        })) + '<p class="pista" style="margin-top:12px">Con los hitos que tienen fecha (también los de propuestas) y tus gastos fijos. ' +
        '«Apartar» es IVA + IRPF; «Te queda» es lo tuyo antes de la renta.' +
        (pv.sin_fecha ? ' Hay ' + eur(pv.sin_fecha) + ' en hitos sin fecha que no salen aquí.' : '') + '</p>';
    }

    html += '<h2>Proyectos activos <small>' + activos.length + '</small></h2>' + tablaProyectos(activos, 'Ningún proyecto activo.');
    if (abiertas.length) html += '<h2>Propuestas en el aire <small>' + eur(suma(abiertas, 'precio')) + '</small></h2>' + tablaProyectos(abiertas);

    html += pista('Para cambiar algo, díselo a tu agente: <code>factura a Acme la Fase 1</code>, ' +
      '<code>me ha pagado Acme</code>, <code>nuevo cliente…</code>, <code>¿cuánto llevo este trimestre?</code>');
    return html;
  };

  var facturado = function (p) {
    return suma(vivas().filter(function (f) { return f.proyecto === p.slug; }), 'base');
  };
  var tablaProyectos = function (lista, vacio) {
    return tabla([{ t: 'Proyecto' }, { t: 'Cliente', cls: 'opc' }, { t: 'Estado', cls: 'opc' }, { t: 'Facturado', cls: 'n opc' }, { t: 'Precio', cls: 'n' }],
      lista.map(function (p) {
        return {
          href: '#proyecto/' + p.slug,
          celdas: [esc(p.nombre), esc(cliente(p.cliente).nombre), estado(p.estado), eur(facturado(p)), p.precio ? eur(p.precio) : '—']
        };
      }), vacio);
  };

  V.clientes = function () {
    var orden = ['activo', 'propuesta', 'contacto', 'pausado', 'cerrado'];
    var lista = D.clientes.slice().sort(function (a, b) {
      return orden.indexOf(a.estado) - orden.indexOf(b.estado) || a.nombre.localeCompare(b.nombre);
    });
    return '<h1>Clientes</h1><p class="sub">' + lista.length + ' en total</p>' +
      tabla([{ t: 'Cliente' }, { t: 'Estado' }, { t: 'Proyectos', cls: 'n opc' }, { t: 'Facturado', cls: 'n opc' }, { t: 'Por cobrar', cls: 'n' }],
        lista.map(function (c) {
          var fs = vivas().filter(function (f) { return f.cliente === c.slug; });
          return {
            href: '#cliente/' + c.slug,
            celdas: [esc(c.nombre), estado(c.estado),
              D.proyectos.filter(function (p) { return p.cliente === c.slug; }).length,
              eur(suma(fs, 'base')), eur(suma(fs.filter(function (f) { return f.estado === 'emitida'; }), 'total'))]
          };
        }), 'Aún no hay clientes.') +
      pista('Dile a tu agente <code>nuevo cliente: …</code> y pásale lo que tengas: su web, la firma de un email, el PDF de una factura suya.');
  };

  V.cliente = function (slug) {
    var c = cliente(slug);
    var prs = D.proyectos.filter(function (p) { return p.cliente === slug; });
    var fs = D.facturas.filter(function (f) { return f.cliente === slug; }).sort(function (a, b) { return a.numero < b.numero ? 1 : -1; });
    var direccion = [c.direccion, [c.cp, c.ciudad].filter(Boolean).join(' '), c.provincia, c.pais].filter(Boolean).join(', ');
    var html = '<h1>' + esc(c.nombre) + '</h1><p class="sub">' + estado(c.estado) + (c.desde ? ' · desde ' + fecha(c.desde) : '') + '</p>';
    html += ficha([
      ['Razón social', esc(c.razon_social)], ['NIF', esc(c.nif)], ['Dirección', esc(direccion)],
      ['Tipo', esc(c.tipo)], ['Email para facturas', c.email_facturas ? '<a href="mailto:' + esc(c.email_facturas) + '">' + esc(c.email_facturas) + '</a>' : ''],
      ['Facturado', eur(suma(vivas().filter(function (f) { return f.cliente === slug; }), 'base'))]
    ]);
    if ((c.contactos || []).length) {
      html += '<h2>Contactos</h2>' + tabla([{ t: 'Nombre' }, { t: 'Rol', cls: 'opc' }, { t: 'Email' }, { t: 'Teléfono', cls: 'opc' }],
        c.contactos.map(function (p) {
          return { celdas: [esc(p.nombre), esc(p.rol), p.email ? '<a href="mailto:' + esc(p.email) + '">' + esc(p.email) + '</a>' : '', esc(p.telefono)] };
        }));
    }
    html += '<h2>Proyectos</h2>' + tablaProyectos(prs, 'Sin proyectos.');
    var suyos = (D.espacios || []).filter(function (e) { return e.cliente === slug; });
    if (suyos.length) html += '<h2>Espacios</h2>' + tablaEspacios(suyos);
    html += '<h2>Facturas</h2>' + tabla(COLS_FACTURA, fs.map(filaFactura), 'Sin facturas.');
    if (c.notas) html += '<h2>Notas</h2><p class="notas">' + esc(c.notas) + '</p>';
    return html;
  };

  var tablaEspacios = function (lista, vacio) {
    return tabla([{ t: 'Espacio' }, { t: 'Tipo', cls: 'opc' }, { t: 'Quién entra' }, { t: '', cls: 'n' }],
      lista.map(function (e) {
        var quien = (e.accesos || []).map(function (a) { return esc(a.nombre); }).join(', ');
        return {
          celdas: [esc(e.titulo || e.slug) + '<br><span class="muted">/c/' + esc(e.slug) + '/</span>', esc(e.tipo || 'proyecto'),
            quien || '<span class="muted">nadie todavía</span>',
            '<a href="espacios/' + esc(e.slug) + '/" target="_blank" rel="noopener">Ver ↗</a>']
        };
      }), vacio || 'Ningún espacio.');
  };

  V.espacios = function () {
    var html = '<h1>Espacios</h1><p class="sub">Páginas privadas para tus clientes: propuestas, seguimiento de proyectos y entregables. ' +
      'Cada persona entra con su enlace.</p>';
    html += tablaEspacios(D.espacios || [], 'Aún no hay espacios.');
    return html + pista('Dile a tu agente <code>hazle a Acme un espacio con la propuesta</code> o ' +
      '<code>dale acceso a Ana al espacio de Acme</code>. «Ver» abre tu copia, dentro del admin; ' +
      'tu cliente la ve en /c/… con su enlace.');
  };

  V.proyectos = function (filtro) {
    var grupos = [['activo', 'Activos'], ['propuesta', 'Propuestas'], ['pausado', 'Pausados'], ['terminado', 'Terminados'], ['perdido', 'Perdidos']];
    var cuenta = function (e) { return D.proyectos.filter(function (p) { return p.estado === e; }).length; };
    if (!grupos.some(function (g) { return g[0] === filtro; })) filtro = '';
    var html = '<h1>Proyectos</h1><p class="sub">' + D.proyectos.length + ' en total</p>';
    // Menú de estados: Todos y cada estado con su número (#proyectos/terminado)
    html += '<div class="filtros" role="navigation" aria-label="Filtrar por estado">' +
      '<a href="#proyectos"' + (filtro ? '' : ' class="on" aria-current="page"') + '>Todos <small>' + D.proyectos.length + '</small></a>' +
      grupos.map(function (g) {
        var n = cuenta(g[0]);
        return '<a href="#proyectos/' + g[0] + '"' + (filtro === g[0] ? ' class="on" aria-current="page"' : '') + (n ? '' : ' data-vacio') + '>' +
          g[1] + ' <small>' + n + '</small></a>';
      }).join('') + '</div>';
    grupos.forEach(function (g) {
      if (filtro && filtro !== g[0]) return;
      var lista = D.proyectos.filter(function (p) { return p.estado === g[0]; });
      if (filtro || lista.length || g[0] === 'activo') html += '<h2>' + g[1] + ' <small>' + lista.length + '</small></h2>' + tablaProyectos(lista, 'Ninguno.');
    });
    return html + pista('Dile a tu agente <code>nuevo proyecto para Acme</code>, o pásale la propuesta y sacará de ahí los hitos y el precio.');
  };

  V.proyecto = function (slug) {
    var p = proyecto(slug);
    if (!p) return '<h1>No existe</h1>';
    var fact = facturado(p), pct = p.precio ? Math.min(100, Math.round(fact / p.precio * 100)) : 0;
    var html = '<h1>' + esc(p.nombre) + '</h1><p class="sub">' + linkCliente(p.cliente) + ' · ' + estado(p.estado) + '</p>';
    html += ficha([
      ['Precio', p.pro_bono ? 'Pro bono, no se factura' : p.precio ? eur(p.precio) + ' + IVA' : ''],
      ['Facturado', eur(fact) + (p.precio ? ' (' + pct + '%)<div class="barra"><i style="width:' + pct + '%"></i></div>' : '')],
      ['Inicio', fecha(p.inicio)], ['Fin', fecha(p.fin)]
    ]);
    if (Admin.bloqueProyecto) html += Admin.bloqueProyecto(slug);
    var esp = (D.espacios || []).filter(function (e) { return e.proyecto === slug; });
    if (esp.length) html += '<h2>Espacio del cliente</h2>' + tablaEspacios(esp);
    if ((p.enlaces || []).length) {
      html += '<h2>Enlaces</h2>' + tabla([{ t: 'Qué' }, { t: 'Dirección', cls: 'opc' }], p.enlaces.map(function (e) {
        return { celdas: ['<a href="' + esc(e.url) + '" target="_blank" rel="noopener">' + esc(e.nombre) + ' ↗</a>',
          '<span class="muted">' + esc(e.url.replace(/^https:\/\/[^/]+/, '').replace(/\?k=.*/, '')) + '</span>'] };
      }));
    }
    if ((p.hitos || []).length) {
      html += '<h2>Hitos</h2>' + tabla([{ t: 'Hito' }, { t: 'Fecha', cls: 'opc' }, { t: 'Importe', cls: 'n' }, { t: 'Estado', cls: 'n' }],
        p.hitos.map(function (h) {
          return {
            href: h.factura ? '#factura/' + h.factura : null,
            celdas: [esc(h.nombre), fecha(h.fecha), eur(h.importe), estado(h.estado) + (h.factura ? ' <span class="muted">' + esc(h.factura) + '</span>' : '')]
          };
        }));
    }
    var hr = p.horas_resumen || {};
    if ((p.horas || []).length || p.horas_semana) {
      var hh = function (x) { return (x || 0).toLocaleString('es-ES') + ' h'; };
      html += '<h2>Horas <small>' + hh(hr.total) + ' en total</small></h2>';
      html += kpis([
        [hh(hr.mes), 'Este mes' + (hr.presupuesto_mes ? ' (de unas ' + Math.round(hr.presupuesto_mes) + ' h previstas)' : '')],
        [hr.por_hora ? eur(hr.por_hora) : '—', 'Por hora, sobre lo facturado']
      ]);
      if (hr.presupuesto_mes) {
        var pc = Math.min(100, Math.round((hr.mes || 0) / hr.presupuesto_mes * 100));
        html += '<div class="barra"><i style="width:' + pc + '%"></i></div>';
      }
      html += tabla([{ t: 'Fecha' }, { t: 'Nota', cls: 'opc' }, { t: 'Horas', cls: 'n' }],
        (p.horas || []).slice().reverse().slice(0, 10).map(function (h) { return { celdas: [fecha(h.fecha), esc(h.nota || ''), hh(h.horas)] }; }),
        'Aún no hay horas. Dile a tu agente: hoy 3 h con este cliente.');
    }
    if (p.enviada && p.estado === 'propuesta') {
      html += '<p class="pista">Propuesta enviada el ' + fecha(p.enviada) + (p.ultimo_contacto ? ', último contacto el ' + fecha(p.ultimo_contacto) : '') + '.</p>';
    }
    if ((p.tareas || []).length) {
      html += '<h2>Tareas <small>' + p.tareas.filter(function (t) { return t.hecha; }).length + '/' + p.tareas.length + '</small></h2>' +
        tabla([{ t: '', cls: 'chk' }, { t: 'Tarea' }], p.tareas.map(function (t) {
          return { celdas: [t.hecha ? '●' : '○', t.hecha ? '<s class="muted">' + esc(t.texto) + '</s>' : esc(t.texto)] };
        }));
    }
    var fs = D.facturas.filter(function (f) { return f.proyecto === slug; });
    html += '<h2>Facturas</h2>' + tabla(COLS_FACTURA, fs.map(filaFactura), 'Sin facturas.');
    if (p.notas) html += '<h2>Notas</h2><p class="notas">' + esc(p.notas) + '</p>';
    return html;
  };

  var tablaBorradores = function () {
    var bs = D.borradores || [];
    if (!bs.length) return '';
    return '<h2>Borradores <small>sin número, aún no emitidos</small></h2>' + tabla(
      [{ t: 'Borrador' }, { t: 'Cliente' }, { t: 'Concepto', cls: 'opc' }, { t: 'Base', cls: 'n opc' }, { t: 'Total', cls: 'n' }],
      bs.map(function (b) {
        return {
          href: b.proyecto ? '#proyecto/' + b.proyecto : '#cliente/' + b.cliente,
          celdas: [estado('borrador'), esc(cliente(b.cliente).nombre), esc((b.conceptos[0] || {}).descripcion || ''),
            eur(b.base), b.error ? estado(b.error) : eur(b.total)]
        };
      })) + '<p class="pista" style="margin-top:12px">Para emitirlo: <code>emite el borrador de ' + esc(cliente(bs[0].cliente).nombre) + '</code></p>';
  };

  V.facturas = function (anyo) {
    var anyos = D.facturas.map(function (f) { return f.fecha.slice(0, 4); })
      .concat([hoy.slice(0, 4)]).filter(function (a, i, l) { return l.indexOf(a) === i; }).sort().reverse();
    anyo = anyo || anyos[0];
    var lista = D.facturas.filter(function (f) { return f.fecha.slice(0, 4) === anyo; })
      .sort(function (a, b) { return a.fecha < b.fecha || (a.fecha === b.fecha && a.numero < b.numero) ? 1 : -1; });
    var html = '<h1>Facturas</h1><p class="sub">' + anyos.map(function (a) {
      return a === anyo ? '<b>' + a + '</b>' : '<a href="#facturas/' + a + '">' + a + '</a>';
    }).join(' · ') + '</p>';
    html += tablaBorradores();
    html += kpis([
      [eur(suma(lista, 'base')), 'Base imponible'],
      [eur(suma(lista, 'iva')), 'IVA repercutido'],
      [eur(suma(lista, 'irpf')), 'IRPF retenido'],
      [eur(suma(lista, 'total')), 'Total facturado']
    ]);
    html += '<h2>' + lista.length + ' facturas</h2>' + tabla(COLS_FACTURA, lista.map(filaFactura), 'Ninguna factura en ' + anyo + '.');
    return html + pista('Las rectificativas restan y anulan la original, así que las cifras de arriba ya son netas. ' +
      'Para el trimestre: <code>python backoffice.py resumen ' + trimestre(hoy) + '</code>');
  };

  V.factura = function (n) {
    var f = factura(n);
    if (!f) return '<h1>No existe</h1>';
    var html = '<h1>' + esc(f.tipo === 'rectificativa' ? 'Rectificativa ' : 'Factura ') + esc(f.numero) + '</h1>' +
      '<p class="sub">' + linkCliente(f.cliente) + (f.proyecto && proyecto(f.proyecto) ? ' · <a href="#proyecto/' + esc(f.proyecto) + '">' +
        esc(proyecto(f.proyecto).nombre) + '</a>' : '') + ' · ' + estadoFactura(f) + '</p>';
    html += '<div class="acciones"><a href="pdf/' + esc(f.numero) + '.pdf" target="_blank">Abrir PDF ↗</a>' +
      '<a href="pdf/' + esc(f.numero) + '.pdf" download>Descargar</a></div>';
    html += ficha([
      ['Fecha', fecha(f.fecha)], ['Vence', fecha(f.vence)], ['Cobrada', f.cobrada ? fecha(f.cobrada) : ''],
      ['Base', eur(f.base)], ['IVA ' + f.iva_pct + '%', eur(f.iva)], ['IRPF ' + f.irpf_pct + '%', f.irpf ? '−' + eur(f.irpf) : eur(0)],
      ['Total', '<b>' + eur(f.total) + '</b>'],
      ['Rectifica a', f.rectifica ? '<a href="#factura/' + esc(f.rectifica) + '">' + esc(f.rectifica) + '</a>' : ''],
      ['Rectificada por', f.rectificada_por ? '<a href="#factura/' + esc(f.rectificada_por) + '">' + esc(f.rectificada_por) + '</a>' : ''],
      ['Mención', esc(f.mencion)]
    ]);
    html += '<h2>Conceptos</h2>' + tabla([{ t: 'Descripción' }, { t: 'Cant.', cls: 'n opc' }, { t: 'Precio', cls: 'n opc' }, { t: 'Importe', cls: 'n' }],
      f.conceptos.map(function (c) { return { celdas: [esc(c.descripcion), c.cantidad, eur(c.precio), eur(c.importe)] }; }));
    if (f.estado === 'emitida' && f.tipo !== 'rectificativa') html += pista('Cuando te paguen: <code>me han pagado la ' + esc(f.numero) + '</code>');
    return html;
  };

  var linkArchivo = function (g) {
    if (g.archivo) return '<a href="gastos/' + esc(g.archivo) + '" target="_blank">factura ↗</a>';
    return g.sin_factura ? '<span class="muted">sin factura</span>' : estado('falta factura');
  };

  V.gastos = function (anyo) {
    var anyos = D.gastos.map(function (g) { return g.fecha.slice(0, 4); })
      .concat([hoy.slice(0, 4)]).filter(function (a, i, l) { return l.indexOf(a) === i; }).sort().reverse();
    anyo = anyo || anyos[0];
    var lista = D.gastos.filter(function (g) { return g.fecha.slice(0, 4) === anyo; })
      .sort(function (a, b) { return a.fecha < b.fecha ? 1 : -1; });
    var html = '<h1>Gastos</h1><p class="sub">' + anyos.map(function (a) {
      return a === anyo ? '<b>' + a + '</b>' : '<a href="#gastos/' + a + '">' + a + '</a>';
    }).join(' · ') + '</p>';
    html += kpis([
      [eur(suma(lista, 'base')), 'Base'],
      [eur(suma(lista, 'iva_deducible')), 'IVA que te deduces'],
      [eur(suma(lista, 'gasto_irpf')), 'Gasto para el IRPF'],
      [eur(suma(lista, 'amortizable')), 'Equipos por amortizar']
    ]);
    var cats = {};
    lista.forEach(function (g) { cats[g.categoria] = (cats[g.categoria] || 0) + g.base; });
    var orden = Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; });
    if (orden.length) {
      html += '<h2>Por categoría</h2>' + tabla([{ t: 'Categoría' }, { t: 'Base', cls: 'n' }],
        orden.map(function (c) { return { celdas: [esc(D.categorias[c] || c), eur(cats[c])] }; }));
    }
    // Previsión por meses: los gastos de cada mes, qué ha llegado ya con factura y el ZIP para la gestoría
    var pg = (D.prevision_gastos || []).filter(function (x) { return x.fecha.slice(0, 4) === anyo || (anyo === hoy.slice(0, 4) && x.fecha > hoy); });
    var MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
    var nombreMes = function (m) { var n = MESES[+m.slice(5, 7) - 1]; return n.charAt(0).toUpperCase() + n.slice(1) + ' ' + m.slice(0, 4); };
    var meses = pg.map(function (x) { return x.mes; }).concat(lista.map(function (g) { return g.fecha.slice(0, 7); }))
      .filter(function (m, i, l) { return l.indexOf(m) === i; }).sort();
    if (meses.length) html += '<h2>Previsión por meses</h2>';
    meses.forEach(function (m) {
      var filas = pg.filter(function (x) { return x.mes === m; });
      var extra = lista.filter(function (g) { return g.fecha.slice(0, 7) === m && !g.recurrente; });
      var total = filas.reduce(function (s, x) { return s + x.base; }, 0) + suma(extra, 'base');
      var falta = filas.filter(function (x) { return x.estado === 'falta factura' || x.estado === 'pendiente'; }).length;
      var listo = filas.every(function (x) { return x.estado === 'confirmado'; });
      var zip = (D.meses_zip || []).indexOf(m) >= 0
        ? ' · <a href="meses/gestoria-' + m + '.zip" download>ZIP para la gestoría ↓</a>' : '';
      html += '<h3 class="mes">' + nombreMes(m) + ' <small>' + (listo ? '' : '≈ ') + eur(total) + ' · ' +
        (falta ? falta + ' por confirmar' : listo ? 'todo confirmado' : 'previsto') + zip + '</small></h3>';
      html += tabla([{ t: 'Fecha' }, { t: 'Proveedor' }, { t: 'Concepto', cls: 'opc' }, { t: 'Base', cls: 'n' }, { t: 'Estado', cls: 'n' }],
        filas.map(function (x) {
          var est = x.estado === 'confirmado' && x.archivo
            ? '<a href="gastos/' + esc(x.archivo) + '" target="_blank">' + estado('confirmado') + ' ↗</a>' : estado(x.estado);
          return { fecha: x.fecha, celdas: [fecha(x.fecha), esc(x.proveedor), esc(x.concepto),
            (x.estado === 'confirmado' ? '' : '<span class="muted">≈</span> ') + eur(x.base), est] };
        }).concat(extra.map(function (g) {
          return { fecha: g.fecha, celdas: [fecha(g.fecha), esc(g.proveedor), esc(g.concepto), eur(g.base), linkArchivo(g)] };
        })).sort(function (p, q) { return p.fecha < q.fecha ? -1 : 1; }));
    });
    if (meses.length) html += '<p class="pista">≈: importe aproximado hasta que llega la factura. El ZIP de cada mes lleva las facturas emitidas y recibidas en PDF y un resumen.csv para la gestoría.</p>';
    html += '<h2>' + lista.length + ' gastos</h2>' + tabla(
      [{ t: 'Fecha' }, { t: 'Proveedor' }, { t: 'Concepto', cls: 'opc' }, { t: 'Base', cls: 'n' }, { t: 'IVA deducible', cls: 'n opc' }, { t: '', cls: 'n' }],
      lista.map(function (g) {
        return {
          celdas: [fecha(g.fecha), esc(g.proveedor),
            esc(g.concepto) + (g.afectacion < 100 ? ' <span class="muted">(' + g.afectacion + '%)</span>' : ''),
            eur(g.base), eur(g.iva_deducible), linkArchivo(g)]
        };
      }), 'Ningún gasto en ' + anyo + '.');
    return html + pista('Pásale a tu agente el PDF o la foto de una factura: <code>apunta este gasto</code>. ' +
      'Los fijos (cuota de autónomos, suscripciones) se apuntan solos cada mes.');
  };

  V.trimestres = function () {
    var html = '<h1>Trimestres</h1><p class="sub">303 (IVA) y 130 (IRPF). Son estimaciones para la gestoría.</p>';
    html += tabla([{ t: 'Trimestre' }, { t: 'Plazo', cls: 'opc' }, { t: '303', cls: 'n opc' }, { t: '130', cls: 'n opc' }, { t: 'A pagar', cls: 'n' }, { t: '', cls: 'n' }],
      D.trimestres.map(function (r) {
        var e = r.presentado ? estado('presentado')
          : r.plazo < hoy ? estado('fuera de plazo')
          : '<span class="muted">' + (r.hasta < hoy ? 'por presentar' : 'en curso') + '</span>';
        return { href: '#trimestre/' + r.trimestre, celdas: [esc(r.trimestre), fecha(r.plazo), eur(r.m303['46']), eur(r.m130['07']), eur(r.a_pagar), e] };
      }));
    return html + pista('Para cerrar uno: <code>cierra el 4T</code>. Genera el resumen, los libros y un ZIP con todo para la gestoría.');
  };

  V.trimestre = function (t) {
    var r = tri(t), m = r.m303, n = r.m130;
    var html = '<h1>' + esc(t) + '</h1><p class="sub">Del ' + fecha(r.desde) + ' al ' + fecha(r.hasta) +
      ' · se presenta hasta el ' + fecha(r.plazo) +
      (r.presentado ? ' · ' + estado('presentado el ' + fecha(r.presentado.fecha)) : '') + '</p>';
    if ((r.archivos || []).length) {
      html += '<div class="acciones">' + r.archivos.map(function (a) {
        return '<a href="trimestres/' + esc(a) + '" target="_blank">' + (a.slice(-4) === '.pdf' ? 'Resumen PDF' : 'Libros Excel') + ' ↗</a>';
      }).join('') + '</div>';
    }
    html += kpis([[eur(m['46']), '303 · IVA'], [eur(n['07']), '130 · IRPF'], [eur(r.a_pagar), 'A pagar']]);
    var fila = function (c, txt, v) { return { celdas: ['<span class="muted">' + c + '</span>', txt, eur(v)] }; };
    html += '<h2>303 · IVA del trimestre</h2>' + tabla([{ t: 'Casilla', cls: 'cas' }, { t: '' }, { t: '', cls: 'n' }], [
      fila('07', 'Base de tus facturas al 21%', m['07']), fila('09', 'IVA que has cobrado', m['09']),
      fila('10–11', 'Servicios de la UE (autoliquidado)', m['11']),
      fila('12–13', 'Servicios de fuera de la UE (autoliquidado)', m['13']),
      fila('14–15', 'Rectificativas', m['15']), fila('27', '<b>IVA devengado</b>', m['27']),
      fila('28–29', 'IVA de tus gastos', m['29']), fila('36–37', 'IVA de servicios de la UE', m['37']),
      fila('45', '<b>IVA a deducir</b>', m['45']), fila('46', '<b>Resultado</b>', m['46']),
      fila('59', 'Servicios a empresas de la UE (informativa)', m['59']),
      fila('120', 'Servicios fuera de la UE (informativa)', m['120'])
    ]);
    html += '<h2>130 · IRPF, acumulado del año</h2>' + tabla([{ t: 'Casilla', cls: 'cas' }, { t: '' }, { t: '', cls: 'n' }], [
      fila('01', 'Ingresos', n['01']), fila('02', 'Gastos', n['02']), fila('03', 'Rendimiento', n['03']),
      fila('04', '20%', n['04']), fila('05', 'Pagado en trimestres anteriores', n['05']),
      fila('06', 'Retenciones que te han hecho', n['06']), fila('07', '<b>Resultado</b>', n['07'])
    ]);
    if (r.avisos.length) {
      html += '<h2>Ojo</h2><ul class="falta">' + r.avisos.map(function (a) { return '<li><span>' + esc(a) + '</span></li>'; }).join('') + '</ul>';
    }
    html += '<h2>Facturas emitidas <small>' + r.facturas.length + '</small></h2>' +
      tabla(COLS_FACTURA, r.facturas.map(function (x) { return filaFactura(factura(x)); }), 'Ninguna.');
    html += '<h2>Gastos <small>' + r.gastos.length + '</small></h2>' + tabla(
      [{ t: 'Fecha' }, { t: 'Proveedor' }, { t: 'Base', cls: 'n' }, { t: 'IVA deducible', cls: 'n opc' }, { t: '', cls: 'n' }],
      r.gastos.map(function (id) {
        var g = gasto(id);
        return { celdas: [fecha(g.fecha), esc(g.proveedor), eur(g.base), eur(g.iva_deducible), linkArchivo(g)] };
      }), 'Ninguno.');
    return html;
  };

  // ---- Router ----
  var pintar = function () {
    var partes = (location.hash.slice(1) || 'hoy').split('/');
    var vista = V[partes[0]] ? partes[0] : 'hoy';
    document.body.classList.remove('presentando');
    app.innerHTML = V[vista].apply(null, partes.slice(1).map(function (x) { return decodeURIComponent(x); }).concat(['', '']));
    var seccion = ({ cliente: 'clientes', proyecto: 'proyectos', factura: 'facturas', trimestre: 'trimestres' })[vista] || Admin.seccion[vista] || vista;
    document.querySelectorAll('nav a').forEach(function (a) { a.classList.toggle('on', a.dataset.v === seccion); });
    document.title = (app.querySelector('h1') || {}).textContent + ' · ' + ((D.negocio || {}).nombre || 'Backoffice');
    if (Admin.despues) Admin.despues(vista);
    if (!Admin.mantenerScroll) window.scrollTo(0, 0);
    Admin.mantenerScroll = false;
  };
  app.addEventListener('click', function (e) {
    var tr = e.target.closest('tr[data-href]');
    if (tr && !e.target.closest('a')) location.hash = tr.dataset.href;
  });
  window.addEventListener('hashchange', pintar);

  // Lo que necesita trabajo.js (y la página del cliente, con su propio cliente.js)
  var Admin = window.Admin = {
    V: V, esc: esc, fecha: fecha, hoy: hoy, pintar: pintar, seccion: {},
    datos: function () { return D; }, proyecto: proyecto
  };

  fetch('datos.json', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) {
    D = d;
    document.getElementById('pie').innerHTML = 'Datos del ' + esc(d.generado.replace('T', ' a las ')) +
      '<br>Las cifras de impuestos son estimaciones para tu gestoría. Revísalas antes de presentar nada.';
    if (d.negocio && d.negocio.nombre) document.querySelector('.brand').textContent = d.negocio.nombre;
    pintar();
  }).catch(function () {
    app.innerHTML = '<h1>Sin datos</h1><p class="sub">No encuentro datos.json. Móntalo con <code>python backoffice.py servir</code>.</p>';
  });
})();
