"""El trabajo de un proyecto: fases, entregables, documentos, decisiones y pruebas.

Vive en datos/trabajo/<proyecto>/ (el slug de datos/proyectos/<proyecto>.json), un archivo por cosa:

    espacio.json               cabecera, fases, fase actual, próximo hito, resumen y si se comparte
    entregables/<01>.json      las carpetas del proyecto (01 · Investigación, 02 · Propuesta…)
    documentos/<id>.md         cada documento, en Markdown: una presentación o un documento para leer
    decisiones/<D-001>.json    el registro de decisiones
    pruebas/<P-001>.json       lo que se ha probado y lo que se ha aprendido
    generado/                  la página HTML y el PDF de cada documento (python backoffice.py documentos)

Cada documento es un .md con su cabecera:

    ---
    titulo: Lo que hemos aprendido de los clientes
    formato: presentacion       # presentacion (diapositivas 16:9) o documento (para leer, con índice)
    version: 1.0
    estado: en_revision
    fecha: 2026-11-20
    entregable: 01              # opcional: la carpeta donde va
    descripcion: Una frase.     # opcional
    subtitulo:                  # opcional
    etiqueta: 01 Resumen        # opcional: cómo se llama en las pestañas
    sustituye: 01-borrador      # opcional: el documento anterior, que pasa a «Sustituido»
    ---
    Primera diapositiva…
    ---
    [densa] Segunda diapositiva (entre corchetes, la clase de la diapositiva; opcional)

`python backoffice.py documentos <proyecto>` hace la página y el PDF (con Chrome) de los que han cambiado.
Las páginas y los PDF se guardan en el repo, como los de las facturas: GitHub Actions no los genera.

Con "compartir": {"slug": "acme"} en espacio.json, el cliente ve el proyecto entero, igual que en el admin
y en solo lectura, en /c/acme/, con los mismos enlaces personales que los espacios.
"""
import datetime as dt
import hashlib
import html as H
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import backoffice as bo

RAIZ = bo.DATOS / "trabajo"
PLANTILLAS = bo.ROOT / "web" / "trabajo"
WEB = bo.ROOT / "web" / "admin"

ESTADOS_ESPACIO = ["en_curso", "en_pausa", "cerrado"]
ESTADOS_FASE = ["pendiente", "en_curso", "hecha"]
ESTADOS_ENTREGABLE = ["sin_empezar", "en_curso", "en_revision", "revisado", "aprobado"]
TIPOS_ENTREGABLE = ["documentos", "pruebas"]
ESTADOS_DOC = ["borrador", "en_revision", "revisado", "aprobado", "sustituido"]
FORMATOS = ["presentacion", "documento"]
ESTADOS_DECISION = ["propuesta", "aprobada", "rechazada", "sustituida"]
ESTADOS_PRUEBA = ["prevista", "en_marcha", "hecha", "descartada"]
ETIQUETA_ESTADO = {"borrador": "Borrador", "en_revision": "En revisión", "revisado": "Revisado", "aprobado": "Aprobado",
                   "sustituido": "Sustituido"}
NOMBRE_FORMATO = {"presentacion": "Presentación", "documento": "Documento"}
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
VERSION = re.compile(r"^\d{1,3}(\.\d{1,3}){0,2}$")
MARCA = "La genera trabajo.py"   # va en la página del cliente: así sé que la carpeta es mía y puedo rehacerla


class Invalido(ValueError):
    """Datos que no valen. El mensaje se enseña tal cual."""


# ---- Leer ----

def proyectos_con_trabajo():
    if not RAIZ.exists():
        return []
    return sorted(d.name for d in RAIZ.iterdir() if d.is_dir() and (d / "espacio.json").exists())


def _coleccion(p, nombre):
    return [bo.leer(f) for f in sorted((RAIZ / p / nombre).glob("*.json"))]


def leer_documento(f):
    """(cabecera, cuerpo) de un documento .md. Lanza Invalido si a la cabecera le falta algo."""
    f = pathlib.Path(f)
    texto = f.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not texto.startswith("---\n"):
        raise Invalido(f"{f.name}: tiene que empezar por una cabecera entre dos líneas ---")
    cabecera, _, cuerpo = texto[4:].partition("\n---\n")
    cab = {}
    for linea in cabecera.splitlines():
        if ":" in linea and not linea.lstrip().startswith("#"):
            k, v = linea.split(":", 1)
            cab[k.strip()] = v.split("  #")[0].strip().strip('"')
    faltan = [k for k in ("titulo", "formato", "version", "estado", "fecha") if not cab.get(k)]
    if faltan:
        raise Invalido(f"{f.name}: le falta {', '.join(faltan)} en la cabecera")
    if cab["formato"] not in FORMATOS:
        raise Invalido(f"{f.name}: formato tiene que ser presentacion o documento")
    if cab["estado"] not in ESTADOS_DOC:
        raise Invalido(f"{f.name}: el estado {cab['estado']!r} no vale ({', '.join(ESTADOS_DOC)})")
    if not VERSION.match(cab["version"]):
        raise Invalido(f"{f.name}: la versión va como 1, 1.0 o 1.0.2")
    try:
        dt.date.fromisoformat(cab["fecha"])
    except ValueError:
        raise Invalido(f"{f.name}: la fecha va como AAAA-MM-DD")
    return cab, cuerpo.strip("\n")


def indice(p):
    """generado/indice.json: {id: {huella, versiones: [{version, fecha, pdf, bytes}]}}."""
    f = RAIZ / p / "generado" / "indice.json"
    return bo.leer(f) if f.exists() else {}


def huella(f):
    return hashlib.sha256(pathlib.Path(f).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _texto_plano(cuerpo):
    t = re.sub(r"<[^>]+>", " ", cuerpo)
    t = re.sub(r"[#>*_`|\[\]]|^-{3,}$", " ", t, flags=re.M)
    return re.sub(r"\s+", " ", t).strip()[:6000]


def documentos(p):
    """Los documentos de un proyecto, con lo generado (página, PDF y versiones) y quién sustituye a quién."""
    ind = indice(p)
    out = []
    for f in sorted((RAIZ / p / "documentos").glob("*.md")):
        cab, cuerpo = leer_documento(f)
        gen = ind.get(f.stem, {})
        versiones = gen.get("versiones", [])
        actual = next((v for v in reversed(versiones) if v["version"] == cab["version"]), None)
        pagina = f"{f.stem}.html" if (RAIZ / p / "generado" / f"{f.stem}.html").exists() else ""
        anclas = [{"id": i, "titulo": H.unescape(re.sub(r"<[^>]+>", "", t))}
                  for i, t in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', bo.markdown(cuerpo))] if cab["formato"] == "documento" else []
        out.append({
            "id": f.stem, "titulo": cab["titulo"], "formato": cab["formato"], "version": cab["version"],
            "estado": cab["estado"], "fecha": cab["fecha"], "entregable": cab.get("entregable", ""),
            "descripcion": cab.get("descripcion", ""), "subtitulo": cab.get("subtitulo", ""),
            "etiqueta": cab.get("etiqueta", ""), "sustituye": cab.get("sustituye", ""), "sustituido_por": "",
            "pagina": pagina, "pdf": actual["pdf"] if actual else "", "versiones": versiones,
            "al_dia": gen.get("huella") == huella(f), "anclas": anclas, "texto": _texto_plano(cuerpo),
        })
    ids = {d["id"]: d for d in out}
    for d in out:
        if d["sustituye"] in ids:
            ids[d["sustituye"]]["sustituido_por"] = d["id"]
            ids[d["sustituye"]]["estado"] = "sustituido"
    return out


def cargar(p):
    if p not in proyectos_con_trabajo():
        raise Invalido(f"El proyecto {p!r} no tiene trabajo (datos/trabajo/{p}/espacio.json)")
    base = RAIZ / p
    return {
        "proyecto": p,
        "espacio": bo.leer(base / "espacio.json"),
        "entregables": _coleccion(p, "entregables"),
        "documentos": documentos(p),
        "decisiones": _coleccion(p, "decisiones"),
        "pruebas": _coleccion(p, "pruebas"),
    }


def para_admin():
    """Lo que va en datos.json: cada proyecto con trabajo y si se comparte (sin las claves, claro)."""
    acc = bo.accesos()
    out = {}
    for p in proyectos_con_trabajo():
        try:
            e = cargar(p)
        except (Invalido, json.JSONDecodeError, OSError):
            continue   # revisar ya lo cuenta
        slug = (e["espacio"].get("compartir") or {}).get("slug")
        e["compartir"] = {"slug": slug, "accesos": [{"nombre": a["nombre"], "creado": a.get("creado")} for a in acc.get(slug, [])]} if slug else None
        out[p] = e
    return out


# ---- Revisar ----

def problemas():
    errores = []
    proyectos = bo.proyectos()
    espacios_md = set(bo.espacios())
    slugs = {}
    for p in proyectos_con_trabajo():
        q = f"trabajo {p}"
        if p not in proyectos:
            errores.append(f"{q}: no hay un proyecto {p!r} en datos/proyectos/")
        try:
            esp = bo.leer(RAIZ / p / "espacio.json")
            ents = _coleccion(p, "entregables")
            decs = _coleccion(p, "decisiones")
            prs = _coleccion(p, "pruebas")
            docs = documentos(p)
        except Invalido as ex:
            errores.append(f"{q}: {ex}")
            continue
        except (json.JSONDecodeError, OSError) as ex:
            errores.append(f"{q}: no puedo leer un archivo ({ex})")
            continue
        if not esp.get("titulo"):
            errores.append(f"{q}: falta el título en espacio.json")
        if esp.get("estado") not in ESTADOS_ESPACIO:
            errores.append(f"{q}: estado {esp.get('estado')!r} no vale ({', '.join(ESTADOS_ESPACIO)})")
        fases = esp.get("fases") or []
        ids_fase = [f.get("id") for f in fases]
        if not fases:
            errores.append(f"{q}: espacio.json necesita al menos una fase")
        for f in fases:
            if not f.get("id") or not f.get("nombre") or f.get("estado") not in ESTADOS_FASE:
                errores.append(f"{q}: la fase {f.get('id')!r} necesita id, nombre y un estado de {', '.join(ESTADOS_FASE)}")
        if esp.get("fase_actual") and esp["fase_actual"] not in ids_fase:
            errores.append(f"{q}: fase_actual {esp['fase_actual']!r} no es ninguna de sus fases")
        codigos = {x.get("codigo") for x in ents}
        ids_doc = {d["id"] for d in docs}
        for x in ents:
            qx = f"{q}, entregable {x.get('codigo')}"
            if not x.get("codigo") or not x.get("titulo"):
                errores.append(f"{qx}: le falta el código o el título")
            if x.get("estado") not in ESTADOS_ENTREGABLE:
                errores.append(f"{qx}: estado {x.get('estado')!r} no vale ({', '.join(ESTADOS_ENTREGABLE)})")
            if x.get("tipo", "documentos") not in TIPOS_ENTREGABLE:
                errores.append(f"{qx}: tipo {x.get('tipo')!r} no vale (documentos o pruebas)")
            if x.get("fase") not in ids_fase:
                errores.append(f"{qx}: la fase {x.get('fase')!r} no existe")
            for c in x.get("capitulos", []):
                if c.get("doc") not in ids_doc:
                    errores.append(f"{qx}: el capítulo apunta a {c.get('doc')!r}, que no existe")
        for d in docs:
            qd = f"{q}, documento {d['id']}"
            if not ID.match(d["id"]):
                errores.append(f"{qd}: el nombre del archivo va en minúsculas, números y guiones")
            if d["entregable"] and d["entregable"] not in codigos:
                errores.append(f"{qd}: el entregable {d['entregable']!r} no existe")
            if d["sustituye"] and d["sustituye"] not in ids_doc:
                errores.append(f"{qd}: sustituye a {d['sustituye']!r}, que no existe")
            if not d["al_dia"] or not d["pagina"] or not d["pdf"]:
                errores.append(f"{qd}: ha cambiado y falta su página o su PDF. Hazlos con: python backoffice.py documentos {p}")
        for ref in ((esp.get("reunion") or {}).get("presentacion"), esp.get("dossier")):
            if ref and ref not in ids_doc:
                errores.append(f"{q}: espacio.json apunta al documento {ref!r}, que no existe")
        for x in decs:
            if x.get("estado") not in ESTADOS_DECISION:
                errores.append(f"{q}, decisión {x.get('codigo')}: estado {x.get('estado')!r} no vale ({', '.join(ESTADOS_DECISION)})")
            for r in x.get("documentos", []):
                if r not in ids_doc:
                    errores.append(f"{q}, decisión {x.get('codigo')}: el documento {r!r} no existe")
            for r in x.get("entregables", []):
                if r not in codigos:
                    errores.append(f"{q}, decisión {x.get('codigo')}: el entregable {r!r} no existe")
        for x in prs:
            if x.get("estado") not in ESTADOS_PRUEBA:
                errores.append(f"{q}, prueba {x.get('id')}: estado {x.get('estado')!r} no vale ({', '.join(ESTADOS_PRUEBA)})")
        slug = (esp.get("compartir") or {}).get("slug")
        if slug:
            if not ID.match(slug):
                errores.append(f"{q}: el slug para compartir va en minúsculas, números y guiones")
            if slug in espacios_md:
                errores.append(f"{q}: ya hay un espacio datos/espacios/{slug}/; elige otro slug para compartir el proyecto")
            if slug in slugs:
                errores.append(f"{q}: el slug {slug!r} ya lo usa el proyecto {slugs[slug]}")
            slugs[slug] = p
    return errores


def compartidos():
    """{slug: proyecto} de los proyectos que se comparten con el cliente."""
    out = {}
    for p in proyectos_con_trabajo():
        try:
            slug = (bo.leer(RAIZ / p / "espacio.json").get("compartir") or {}).get("slug")
        except (json.JSONDecodeError, OSError):
            continue
        if slug:
            out[slug] = p
    return out


# ---- Páginas y PDF de los documentos ----

def fecha_larga(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _md(texto, h1=False):
    """El Markdown del backoffice, y además:
    - bloques <div … markdown="1"> … </div> con Markdown dentro (las columnas de las diapositivas);
    - con h1=True, «# Título» es un <h1> (la portada de una presentación) y no una sección."""
    trozos, out, lineas, i = [], [], texto.split("\n"), 0
    while i < len(lineas):
        l = lineas[i]
        m = re.match(r'\s*<div([^>]*?)\s+markdown="1"([^>]*)>\s*$', l)
        if m:
            prof, j = 1, i + 1
            while j < len(lineas) and prof:
                prof += len(re.findall(r"<div\b", lineas[j])) - len(re.findall(r"</div>", lineas[j]))
                j += 1
            trozos.append(f"<div{m.group(1)}{m.group(2)}>" + _md("\n".join(lineas[i + 1:j - 1]), h1).replace("\n", "") + "</div>")
            out += ["", f'<i data-t="{len(trozos) - 1}"></i>', ""]
            i = j
            continue
        if h1 and (m := re.match(r"#\s+(.+)$", l)):
            trozos.append("<h1>" + bo.markdown(m.group(1))[3:-4] + "</h1>")
            out += ["", f'<i data-t="{len(trozos) - 1}"></i>', ""]
        else:
            out.append(l)
        i += 1
    html = bo.markdown("\n".join(out))
    for k in range(len(trozos) - 1, -1, -1):
        html = html.replace(f'<i data-t="{k}"></i>', trozos[k])
    return html


def montar(p, cab, cuerpo, ident, pdf, hermanos, titulo_proyecto, marca):
    """La página de un documento: diapositivas 16:9 (presentacion) o texto con índice (documento)."""
    esc = lambda x: H.escape(str(x or ""), quote=True)
    etiqueta = ETIQUETA_ESTADO.get(cab["estado"], cab["estado"])
    kicker = (f'<p class="kicker-line"><span>{esc(NOMBRE_FORMATO[cab["formato"]])}</span><span>Versión {esc(cab["version"])}</span>'
              f'<span>{esc(fecha_larga(cab["fecha"]))}</span><span>{esc(etiqueta)}</span></p>')
    botones = "".join(f'<a class="btn ghost" href="{esc(r)}">{esc(t)}</a>' for t, r in hermanos)
    if pdf:
        botones += f'<a class="btn ghost" href="{esc(pdf)}" download>PDF</a>'
    pie = f"{titulo_proyecto} · {cab['titulo']}"
    if cab["formato"] == "presentacion":
        bloques = [b.strip("\n") for b in re.split(r"\n---\n", cuerpo) if b.strip()]
        slides = []
        for i, b in enumerate(bloques, 1):
            m = re.match(r"\[([a-z -]+)\]\s*\n?", b)
            clase = m.group(1) if m else ""
            b = b[m.end():] if m else b
            contenido = _md(b, h1=True)
            if i == 1:
                clase = (clase + " portada").strip()
                contenido += f'<p class="meta">Versión {esc(cab["version"])}, {esc(fecha_larga(cab["fecha"]))}. {esc(etiqueta)}.</p>'
            slides.append(f'<section class="slide {esc(clase)}" aria-label="Diapositiva {i}"><div class="in">{contenido}</div>'
                          f'<div class="pie"><span>{esc(pie)}</span><span class="n">{i} / {len(bloques)}</span></div></section>')
        cuerpo_html = (f'<div class="deck-head">{kicker}<p class="downloads"><button class="btn" type="button" data-presentar>Presentar</button>'
                       f'{botones}</p></div><div class="slides">{"".join(slides)}</div>'
                       '<button class="pres-cerrar" type="button" data-salir aria-label="Salir de la presentación">Cerrar <span aria-hidden="true">✕</span> <small>Esc</small></button>'
                       '<div class="pres-bar"><span class="pres-n"></span><button type="button" data-ir="-1" aria-label="Anterior">←</button>'
                       '<button type="button" data-ir="1" aria-label="Siguiente">→</button><button type="button" data-salir>Salir</button></div>')
        herramientas = '<button type="button" data-presentar>Presentar</button>'
    else:
        texto = _md(cuerpo)
        indice_html = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', texto))
        cuerpo_html = (f'<section class="hero">{kicker}<h1>{esc(cab["titulo"])}</h1>'
                       + (f'<p class="subtitle">{esc(cab.get("subtitulo"))}</p>' if cab.get("subtitulo") else "")
                       + f'<p class="downloads"><a class="btn" href="#leer">Empezar a leer</a>{botones}</p></section>'
                       f'<div class="reader"><nav class="toc" aria-label="Índice"><ol>{indice_html}</ol></nav>'
                       f'<div class="content prose" id="leer">{texto}</div></div>')
        herramientas = ""
    plantilla = (PLANTILLAS / "documento.html").read_text(encoding="utf-8")
    for k, v in {"TITULO": esc(cab["titulo"]), "PROYECTO": esc(titulo_proyecto), "VERSION": esc(cab["version"]),
                 "FORMATO": cab["formato"], "PIE": esc(pie).replace('"', "'"), "MARCA": esc(marca),
                 "ANYO": cab["fecha"][:4], "HERRAMIENTAS": herramientas, "CUERPO": cuerpo_html}.items():
        plantilla = plantilla.replace("{{" + k + "}}", v)
    return plantilla


def _hermanos(docs, d):
    """Los otros documentos con página de la misma carpeta, para saltar de la presentación al documento."""
    if not d["entregable"]:
        return []
    return [(f"Ver: {x['etiqueta'] or NOMBRE_FORMATO[x['formato']]}", x["id"] + ".html") for x in docs
            if x["id"] != d["id"] and x["entregable"] == d["entregable"] and x["estado"] != "sustituido"]


def imprimir(pagina, destino):
    """Imprime una página ya escrita en generado/ a PDF con Chrome, en claro."""
    args = [bo.chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
            f"--print-to-pdf={destino}", pathlib.Path(pagina).resolve().as_uri()]
    if sys.platform != "win32":
        args.insert(1, "--no-sandbox")
    subprocess.run(args, check=True, capture_output=True, timeout=180)


def generar(p, solo=None):
    """Hace la página y el PDF de los documentos que han cambiado. Devuelve el informe, línea a línea."""
    e = cargar(p)
    titulo = e["espacio"]["titulo"]
    marca = bo.negocio().get("nombre") or ""
    gen = RAIZ / p / "generado"
    a = gen / "assets"
    a.mkdir(parents=True, exist_ok=True)
    for f in ("documento.css", "documento.js"):
        shutil.copy2(PLANTILLAS / f, a / f)
    ind = indice(p)
    informe = []
    docs = [d for d in e["documentos"]]
    for d in docs:
        if solo and d["id"] not in solo:
            continue
        fuente = RAIZ / p / "documentos" / f"{d['id']}.md"
        cab, cuerpo = leer_documento(fuente)
        cab["estado"] = d["estado"]   # «sustituido» lo pone el documento que lo sustituye
        h = huella(fuente)
        entrada = ind.setdefault(d["id"], {"huella": "", "versiones": []})
        pdf = f"{d['id']}-v{cab['version']}.pdf"
        pagina = gen / f"{d['id']}.html"
        if entrada["huella"] == h and pagina.exists() and (gen / pdf).exists():
            informe.append(f"  = {d['id']} v{cab['version']}: sin cambios")
            continue
        pagina.write_text(montar(p, cab, cuerpo, d["id"], pdf, _hermanos(docs, d), titulo, marca), encoding="utf-8", newline="\n")
        imprimir(pagina, gen / pdf)
        datos = (gen / pdf).read_bytes()
        versiones = [v for v in entrada["versiones"] if v["version"] != cab["version"]]
        versiones.append({"version": cab["version"], "fecha": cab["fecha"], "pdf": pdf, "bytes": len(datos)})
        entrada.update({"huella": h, "versiones": versiones})
        informe.append(f"  ✓ {d['id']} v{cab['version']} ({ETIQUETA_ESTADO[cab['estado']]}, {len(datos) // 1024} KB)")
    # Las que ya no tienen .md se van, con sus PDF
    for ident in [i for i in ind if i not in {d["id"] for d in docs}]:
        for v in ind.pop(ident)["versiones"]:
            (gen / v["pdf"]).unlink(missing_ok=True)
        (gen / f"{ident}.html").unlink(missing_ok=True)
        informe.append(f"  - {ident}: borrado")
    bo.escribir(gen / "indice.json", ind)
    # Las páginas se rehacen todas (sin imprimir): así los enlaces entre documentos de la misma carpeta están al día
    for d in docs:
        if (gen / f"{d['id']}.html").exists():
            cab, cuerpo = leer_documento(RAIZ / p / "documentos" / f"{d['id']}.md")
            cab["estado"] = d["estado"]
            (gen / f"{d['id']}.html").write_text(
                montar(p, cab, cuerpo, d["id"], f"{d['id']}-v{cab['version']}.pdf", _hermanos(docs, d), titulo, marca),
                encoding="utf-8", newline="\n")
    return informe


def comando():
    """python backoffice.py documentos <proyecto> [id…]"""
    if len(sys.argv) < 3:
        sys.exit("Uso: python backoffice.py documentos <proyecto> [id…]\n"
                 f"Proyectos con trabajo: {', '.join(proyectos_con_trabajo()) or 'ninguno'}")
    try:
        informe = generar(sys.argv[2], sys.argv[3:] or None)
    except Invalido as ex:
        sys.exit(str(ex))
    except FileNotFoundError:
        sys.exit("No encuentro Google Chrome para imprimir los PDF. Instálalo o pon su ruta en CHROME.")
    print("\n".join(informe) or "  No hay documentos.")


# ---- Montar la web ----

def copiar(dest):
    """La carpeta generado/ de cada proyecto, a dist/sitio/admin/trabajo/<proyecto>/."""
    for p in proyectos_con_trabajo():
        if (RAIZ / p / "generado").exists():
            shutil.copytree(RAIZ / p / "generado", dest / "trabajo" / p, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("indice.json"))


def pagina_cliente(dest, p, todo):
    """/c/<slug>/: el trabajo del proyecto como en el admin, en solo lectura y sin nada más del backoffice."""
    e = todo[p]
    shutil.rmtree(dest, ignore_errors=True)
    (dest / "assets").mkdir(parents=True)
    for f in ("admin.css", "trabajo.css", "trabajo.js", "cliente.js"):
        shutil.copy2(WEB / f, dest / "assets" / f)
    if (RAIZ / p / "generado").exists():
        shutil.copytree(RAIZ / p / "generado", dest / "trabajo" / p, ignore=shutil.ignore_patterns("indice.json"))
    datos = json.loads(json.dumps(e))
    datos["espacio"].pop("compartir", None)
    datos["compartir"] = None
    neg = bo.negocio()
    bo.escribir(dest / "datos.json", {"generado": dt.datetime.now().isoformat(timespec="minutes"),
                                      "negocio": {"nombre": neg.get("nombre", "")}, "trabajo": {p: datos}})
    plantilla = (PLANTILLAS / "cliente.html").read_text(encoding="utf-8")
    for k, v in {"TITULO": H.escape(e["espacio"]["titulo"]), "PROYECTO": p, "MARCA": H.escape(neg.get("nombre") or "")}.items():
        plantilla = plantilla.replace("{{" + k + "}}", v)
    (dest / "index.html").write_text(plantilla, encoding="utf-8", newline="\n")
