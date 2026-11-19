"""Freelance Backoffice: el backoffice de un autónomo en un repo.

Los datos son archivos JSON en datos/ (formato en docs/datos.md). Este script los valida,
emite las facturas (número, IVA, IRPF y PDF), lleva gastos y trimestres, y monta la web:
el admin (dist/sitio/admin/) y los espacios privados de cliente (dist/sitio/c/<slug>/).

    python backoffice.py init                    crea datos/ con lo mínimo para empezar
    python backoffice.py build                   monta dist/sitio/ (lo usa GitHub Actions)
    python backoffice.py servir [puerto]         monta y abre el admin en local (8081)
    python backoffice.py revisar                 comprueba que los datos están bien

    python backoffice.py emitir <borrador.json>  emite una factura desde un borrador
    python backoffice.py cobrar <número> [fecha] marca una factura como cobrada
    python backoffice.py rectificar <número> "<motivo>"
                                                 anula una factura con una rectificativa
    python backoffice.py pdf [número]            rehace el PDF de una factura (o de todas)

    python backoffice.py gasto <borrador.json> [factura.pdf]
                                                 apunta un gasto con su factura
    python backoffice.py recurrentes             apunta los gastos fijos de los meses que faltan
    python backoffice.py resumen [2026-4T]       cifras del 303 y el 130 del trimestre
    python backoffice.py trimestre [2026-4T]     paquete para la gestoría: resumen PDF, libros Excel y ZIP
    python backoffice.py presentado [2026-4T]    apunta que la gestoría ya lo presentó
    python backoffice.py mes [AAAA-MM]           ZIP del mes para la gestoría (por defecto, el pasado)
    python backoffice.py banco <extracto.csv>    cruza el extracto del banco con facturas y gastos
    python backoffice.py semana                  resumen de la semana en Markdown

    python backoffice.py enlace <espacio> "Nombre"   enlace personal a un espacio de cliente
    python backoffice.py revocar <espacio> "Nombre"  le quita el acceso

Con BACKOFFICE_DATOS=demo usa los datos de ejemplo de demo/ en vez de datos/.

Una factura emitida no se edita ni se borra: si está mal, se rectifica.
Las cifras de impuestos son una estimación para tu gestoría: revísalas antes de presentar nada.
Solo usa la biblioteca estándar de Python (y Chrome para los PDF).
"""
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal

ROOT = pathlib.Path(__file__).resolve().parent
DATOS = (ROOT / os.environ.get("BACKOFFICE_DATOS", "datos")).resolve()
WEB = ROOT / "web" / "admin"
PLANTILLA_ESPACIO = ROOT / "web" / "espacio.html"
SITIO = ROOT / "dist" / "sitio"
DIST = SITIO / "admin"
FACTURAS = DATOS / "facturas"
ESPACIOS = DATOS / "espacios"


def chrome():
    """Chrome o Chromium para imprimir los PDF (facturas y resumen del trimestre)."""
    if os.environ.get("CHROME") and pathlib.Path(os.environ["CHROME"]).exists():
        return os.environ["CHROME"]
    candidatos = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidatos:
        if pathlib.Path(c).exists():
            return c
    for nombre in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        if shutil.which(nombre):
            return shutil.which(nombre)
    sys.exit("No encuentro Chrome para generar el PDF. Instálalo o pon su ruta en la variable CHROME.")

# Países de la UE (ISO 3166-1), sin España
UE = set("AT BE BG CY CZ DE DK EE FI FR GR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split())

ESTADOS_CLIENTE = {"contacto", "propuesta", "activo", "pausado", "cerrado"}
ESTADOS_PROYECTO = {"propuesta", "activo", "pausado", "terminado", "perdido"}
ESTADOS_HITO = {"pendiente", "hecho", "facturado", "cobrado"}


# ---- Utilidades ----

def leer(f):
    return json.loads(pathlib.Path(f).read_text(encoding="utf-8"))


def escribir(f, datos):
    f = pathlib.Path(f)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def euros(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def hoy():
    return dt.date.today().isoformat()


def fecha(s, campo="fecha"):
    try:
        return dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        sys.exit(f"{campo} tiene que ir como AAAA-MM-DD (llegó {s!r})")


def pendiente(valor):
    return not valor or "PENDIENTE" in str(valor)


def negocio():
    return leer(DATOS / "negocio.json")


def clientes():
    return {f.stem: leer(f) | {"slug": f.stem} for f in sorted((DATOS / "clientes").glob("*.json"))}


def proyectos():
    return {f.stem: leer(f) | {"slug": f.stem} for f in sorted((DATOS / "proyectos").glob("*.json"))}


def facturas():
    return {f.stem: leer(f) for f in sorted(FACTURAS.glob("*/*.json")) if f.parent.name.isdigit()}


BORRADORES = FACTURAS / "borradores"


def borradores():
    """Facturas preparadas y sin emitir: datos/facturas/borradores/<slug>.json, con el formato de emitir."""
    return {f.stem: leer(f) | {"id": f.stem} for f in sorted(BORRADORES.glob("*.json"))}


def vista_borrador(b):
    """Cómo quedaría un borrador al emitirlo (cliente, IVA, IRPF, totales), para enseñarlo en el admin."""
    c = clientes().get(b.get("cliente"))
    if not c:
        return b | {"error": f"el cliente {b.get('cliente')!r} no existe"}
    iva, irpf, mencion = regimen(c, negocio())
    lineas, totales = calcular(b.get("conceptos", []), iva, irpf)
    return b | {"conceptos": lineas, **totales, "mencion": mencion}


def ruta_factura(numero):
    anyo = re.search(r"\d{4}", numero).group(0)
    return FACTURAS / anyo / f"{numero}.json"


# ---- Fiscalidad ----

def regimen(cliente, neg):
    """IVA y retención según dónde está el cliente y si es empresa o particular.

    Devuelve (iva %, irpf %, mención legal o None).
    """
    pais = cliente.get("pais", "ES").upper()
    empresa = cliente.get("tipo", "empresa") == "empresa"
    if pais == "ES":
        # Retención solo si quien paga es empresa o profesional en España
        return Decimal(neg["iva"]), Decimal(neg["irpf"]) if empresa else Decimal(0), None
    if pais in UE:
        if empresa:
            return Decimal(0), Decimal(0), "Inversión del sujeto pasivo (art. 84.Uno.2º y 69.Uno.1º Ley 37/1992)"
        return Decimal(neg["iva"]), Decimal(0), None
    return Decimal(0), Decimal(0), "Operación no sujeta a IVA por reglas de localización (art. 69 Ley 37/1992)"


def calcular(conceptos, iva, irpf):
    lineas, base = [], Decimal(0)
    for c in conceptos:
        cantidad = Decimal(str(c.get("cantidad", 1)))
        precio = euros(c["precio"])
        importe = euros(cantidad * precio)
        base += importe
        lineas.append({"descripcion": c["descripcion"], "cantidad": float(cantidad),
                       "precio": float(precio), "importe": float(importe)})
    cuota_iva = euros(base * iva / 100)
    cuota_irpf = euros(base * irpf / 100)
    return lineas, {
        "base": float(base), "iva_pct": float(iva), "iva": float(cuota_iva),
        "irpf_pct": float(irpf), "irpf": float(cuota_irpf),
        "total": float(base + cuota_iva - cuota_irpf),
    }


# ---- Revisar ----

def problemas():
    """Lista de cosas que no cuadran en los datos. Vacía si todo está bien."""
    errores = []
    cls, prs, fas = clientes(), proyectos(), facturas()
    for slug, c in cls.items():
        if c.get("estado") not in ESTADOS_CLIENTE:
            errores.append(f"cliente {slug}: estado {c.get('estado')!r} no es uno de {sorted(ESTADOS_CLIENTE)}")
    for slug, p in prs.items():
        if p.get("cliente") not in cls:
            errores.append(f"proyecto {slug}: el cliente {p.get('cliente')!r} no existe en datos/clientes/")
        if p.get("estado") not in ESTADOS_PROYECTO:
            errores.append(f"proyecto {slug}: estado {p.get('estado')!r} no es uno de {sorted(ESTADOS_PROYECTO)}")
        for h in p.get("hitos", []):
            if h.get("estado") not in ESTADOS_HITO:
                errores.append(f"proyecto {slug}, hito {h.get('nombre')!r}: estado {h.get('estado')!r} no vale")
            if h.get("factura") and h["factura"] not in fas:
                errores.append(f"proyecto {slug}, hito {h.get('nombre')!r}: la factura {h['factura']} no existe")
    # Numeración correlativa y fechas en orden dentro de cada serie
    series = {}
    for n, f in fas.items():
        m = re.fullmatch(r"(R?\d{4})-(\d{3})", n)
        if not m:
            errores.append(f"factura {n}: el número no tiene la forma 2026-001 o R2026-001")
            continue
        series.setdefault(m.group(1), []).append((int(m.group(2)), f["fecha"], n))
    for serie, lista in series.items():
        lista.sort()
        for i, (num, _, n) in enumerate(lista, 1):
            if num != i:
                errores.append(f"serie {serie}: falta el número {i:03d} (salta a {n})")
                break
        fechas = [f for _, f, _ in lista]
        if fechas != sorted(fechas):
            errores.append(f"serie {serie}: hay facturas con fecha anterior a la de un número más bajo")
    for n in fas:
        if not ruta_factura(n).with_suffix(".pdf").exists():
            errores.append(f"factura {n}: falta el PDF (python backoffice.py pdf {n})")
    for slug_p, p in prs.items():
        for h in p.get("horas", []):
            if not h.get("fecha") or not isinstance(h.get("horas"), (int, float)) or h["horas"] <= 0:
                errores.append(f"proyecto {slug_p}: hay un apunte de horas sin fecha o con horas que no valen")
                break
        for k in ("enviada", "ultimo_contacto"):
            if p.get(k):
                try:
                    dt.date.fromisoformat(p[k])
                except ValueError:
                    errores.append(f"proyecto {slug_p}: {k} tiene que ir como AAAA-MM-DD")
    for bid, b in borradores().items():
        if b.get("cliente") not in cls:
            errores.append(f"borrador {bid}: el cliente {b.get('cliente')!r} no existe")
        if not b.get("conceptos"):
            errores.append(f"borrador {bid}: no tiene conceptos")
        if b.get("proyecto") and b["proyecto"] not in prs:
            errores.append(f"borrador {bid}: el proyecto {b['proyecto']!r} no existe")
    for sid, e in espacios().items():
        if e.get("cliente") and e["cliente"] not in cls:
            errores.append(f"espacio {sid}: el cliente {e['cliente']!r} no existe")
        if e.get("proyecto") and e["proyecto"] not in prs:
            errores.append(f"espacio {sid}: el proyecto {e['proyecto']!r} no existe")
        if e.get("tipo", "proyecto") not in ("propuesta", "proyecto"):
            errores.append(f"espacio {sid}: tipo tiene que ser propuesta o proyecto")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", sid):
            errores.append(f"espacio {sid}: el nombre de la carpeta solo puede llevar minúsculas, números y guiones")
    for sid in accesos():
        if sid not in espacios():
            errores.append(f"accesos.json: hay enlaces a {sid!r}, que no existe")
    # Gastos: campos, que las cifras fiscales cuadren con lo que calcula el script y que el archivo exista
    vistos = {}
    iva_general = negocio().get("iva", 21)
    for gid, g in gastos().items():
        faltan = [k for k in ("fecha", "proveedor", "concepto", "categoria", "tipo_iva", "base") if g.get(k) in (None, "")]
        if faltan:
            errores.append(f"gasto {gid}: le falta {', '.join(faltan)}")
            continue
        if g["tipo_iva"] not in TIPOS_IVA:
            errores.append(f"gasto {gid}: tipo_iva {g['tipo_iva']!r} no vale")
            continue
        if g["categoria"] not in CATEGORIAS:
            errores.append(f"gasto {gid}: categoría {g['categoria']!r} no vale")
        if gid[:4] != g["fecha"][:4]:
            errores.append(f"gasto {gid}: está en la carpeta de otro año")
        bien = calcular_gasto(g, iva_general)
        if any(abs(bien[k] - g.get(k, -1)) > 0.005 for k in ("iva_deducible", "gasto_irpf", "iva_autoliquidado")):
            errores.append(f"gasto {gid}: las cifras no cuadran con su base y tipo de IVA (vuelve a apuntarlo con el script)")
        if g.get("archivo") and not (GASTOS / gid[:4] / g["archivo"]).exists():
            errores.append(f"gasto {gid}: no encuentro su factura {g['archivo']}")
        clave = (g["proveedor"], g.get("numero_factura"))
        if clave[1] and clave in vistos:
            errores.append(f"gasto {gid}: parece repetido con {vistos[clave]}")
        vistos[clave] = gid
    return errores


def revisar():
    errores = problemas()
    for e in errores:
        print("  ✗", e)
    print("Todo en orden" if not errores else f"{len(errores)} cosas que arreglar")
    return not errores


# ---- Emitir, cobrar, rectificar ----

def siguiente_numero(serie, fecha_nueva):
    existentes = [n for n in facturas() if n.startswith(serie + "-")]
    if existentes:
        ultima = max(existentes)
        fecha_ultima = leer(ruta_factura(ultima))["fecha"]
        if fecha_nueva < fecha_ultima:
            sys.exit(f"La {ultima} es del {fecha_ultima}: no puedo emitir una con fecha anterior ({fecha_nueva}). "
                     "Las facturas van en orden de número y fecha.")
        return f"{serie}-{int(ultima.split('-')[1]) + 1:03d}"
    return f"{serie}-001"


def datos_emisor(neg):
    return {k: neg[k] for k in ("nombre", "nif", "direccion", "cp", "ciudad", "provincia", "pais", "email")}


def datos_receptor(c):
    return {k: c.get(k, "") for k in ("razon_social", "nif", "direccion", "cp", "ciudad", "provincia", "pais", "tipo")}


def emitir():
    if len(sys.argv) < 3:
        sys.exit("Uso: python backoffice.py emitir <borrador.json>")
    b = leer(sys.argv[2])
    neg = negocio()
    faltan = [k for k in ("nombre", "nif", "direccion", "cp", "ciudad", "iban") if pendiente(neg.get(k))]
    if faltan:
        sys.exit(f"Antes de facturar, completa en datos/negocio.json: {', '.join(faltan)}")
    if neg.get("irpf_hasta") and hoy() > neg["irpf_hasta"] and neg["irpf"] < 15:
        sys.exit(f"El IRPF reducido del {neg['irpf']}% acabó el {neg['irpf_hasta']}. Pon \"irpf\": 15 en negocio.json.")

    cls = clientes()
    if b.get("cliente") not in cls:
        sys.exit(f"El cliente {b.get('cliente')!r} no existe en datos/clientes/")
    c = cls[b["cliente"]]
    faltan = [k for k in ("razon_social", "nif", "direccion", "pais") if pendiente(c.get(k))]
    if faltan:
        sys.exit(f"Al cliente {b['cliente']} le faltan datos para facturar: {', '.join(faltan)}")
    if not b.get("conceptos"):
        sys.exit("El borrador no tiene conceptos")

    f_emision = b.get("fecha") or hoy()
    fecha(f_emision)
    if neg.get("alta") and f_emision < neg["alta"]:
        sys.exit(f"Te diste de alta el {neg['alta']}: no puedes facturar con fecha {f_emision}.")
    numero = siguiente_numero(f_emision[:4], f_emision)
    iva, irpf, mencion = regimen(c, neg)
    lineas, totales = calcular(b["conceptos"], iva, irpf)
    dias = int(b.get("vence_dias", c.get("vence_dias", neg.get("vence_dias", 30))))

    factura = {
        "numero": numero,
        "tipo": "ordinaria",
        "fecha": f_emision,
        "vence": (fecha(f_emision) + dt.timedelta(days=dias)).isoformat(),
        "cliente": b["cliente"],
        "proyecto": b.get("proyecto"),
        "hito": b.get("hito"),
        "emisor": datos_emisor(neg),
        "receptor": datos_receptor(c),
        "conceptos": lineas,
        **totales,
        "mencion": mencion,
        "pago": {"forma": "Transferencia bancaria", "iban": neg["iban"]},
        "notas": b.get("notas", ""),
        "estado": "emitida",
        "cobrada": None,
    }
    escribir(ruta_factura(numero), factura)
    marcar_hito(factura, "facturado")
    origen = pathlib.Path(sys.argv[2]).resolve()
    if origen.parent == BORRADORES.resolve():
        origen.unlink()
        print(f"  Borrador {origen.stem} emitido y borrado")
    pdf_factura(numero)
    print(f"Factura {numero} emitida a {c['razon_social']}: base {totales['base']:.2f} €, "
          f"IVA {totales['iva']:.2f} €, IRPF −{totales['irpf']:.2f} €, total {totales['total']:.2f} €")
    print(f"  {ruta_factura(numero).with_suffix('.pdf')}")
    if c.get("pais", "ES").upper() in UE and c.get("tipo", "empresa") == "empresa":
        print("  Ojo: cliente de la UE. Comprueba su NIF-IVA en VIES y que tú estás en el ROI; va en el modelo 349.")


def marcar_hito(factura, estado):
    if not factura.get("proyecto") or not factura.get("hito"):
        return
    f = DATOS / "proyectos" / f"{factura['proyecto']}.json"
    if not f.exists():
        print(f"  Aviso: el proyecto {factura['proyecto']} no existe; no marco el hito")
        return
    p = leer(f)
    for h in p.get("hitos", []):
        if h.get("nombre") == factura["hito"]:
            h["estado"] = estado
            h["factura"] = factura["numero"]
            escribir(f, p)
            return
    print(f"  Aviso: el proyecto {factura['proyecto']} no tiene un hito {factura['hito']!r}")


def cobrar():
    if len(sys.argv) < 3:
        sys.exit("Uso: python backoffice.py cobrar <número> [AAAA-MM-DD]")
    numero = sys.argv[2]
    f = ruta_factura(numero)
    if not f.exists():
        sys.exit(f"No existe la factura {numero}")
    factura = leer(f)
    if factura["estado"] != "emitida":
        sys.exit(f"La {numero} está {factura['estado']}; no se puede cobrar")
    factura["estado"] = "cobrada"
    factura["cobrada"] = sys.argv[3] if len(sys.argv) > 3 else hoy()
    fecha(factura["cobrada"], "la fecha de cobro")
    escribir(f, factura)
    marcar_hito(factura, "cobrado")
    print(f"{numero} cobrada el {factura['cobrada']} ({factura['total']:.2f} €)")


def rectificar():
    if len(sys.argv) < 4:
        sys.exit('Uso: python backoffice.py rectificar <número> "<motivo>"')
    numero, motivo = sys.argv[2], sys.argv[3]
    f = ruta_factura(numero)
    if not f.exists():
        sys.exit(f"No existe la factura {numero}")
    original = leer(f)
    if original["estado"] == "rectificada":
        sys.exit(f"La {numero} ya está rectificada")

    f_emision = hoy()
    nuevo = siguiente_numero("R" + f_emision[:4], f_emision)
    negativo = [{"descripcion": c["descripcion"], "cantidad": -c["cantidad"], "precio": c["precio"]}
                for c in original["conceptos"]]
    lineas, totales = calcular(negativo, Decimal(str(original["iva_pct"])), Decimal(str(original["irpf_pct"])))
    rect = {
        **{k: original[k] for k in ("cliente", "proyecto", "hito", "emisor", "receptor", "mencion", "pago")},
        "numero": nuevo, "tipo": "rectificativa", "fecha": f_emision, "vence": f_emision,
        "rectifica": numero, "fecha_rectificada": original["fecha"],
        "motivo": motivo, "conceptos": lineas, **totales,
        "notas": "",
        "estado": "emitida", "cobrada": None,
    }
    escribir(ruta_factura(nuevo), rect)
    original["estado"] = "rectificada"
    original["rectificada_por"] = nuevo
    escribir(f, original)
    marcar_hito(original | {"numero": None}, "hecho")
    pdf_factura(nuevo)
    print(f"{nuevo} anula la {numero} ({totales['total']:.2f} €). Si hay que volver a facturar, emite una nueva.")


# ---- Gastos ----
#
# Cada gasto es datos/gastos/<año>/<id>.json con su factura al lado (<id>.pdf / .jpg / .png).
# Lo que importa para Hacienda (IVA deducible, IVA autoliquidado, gasto para el IRPF) lo calcula
# calcular_gasto() a partir de la base, el tipo de IVA y el % de afectación. Nunca se escribe a mano.

GASTOS = DATOS / "gastos"
RECURRENTES = GASTOS / "recurrentes.json"
TRIMESTRES = DATOS / "trimestres"

TIPOS_IVA = {
    "nacional": "Factura española con IVA",
    "ticket": "Ticket o factura sin tu NIF: el IVA no se deduce",
    "isp_ue": "Proveedor de la UE sin IVA (inversión del sujeto pasivo)",
    "isp_fuera": "Proveedor de fuera de la UE sin IVA (inversión del sujeto pasivo)",
    "sin_iva": "Sin IVA (cuota de autónomos, seguros, comisiones del banco…)",
}
CATEGORIAS = {
    "software": "Software y suscripciones", "equipo": "Equipos", "formacion": "Formación y libros",
    "seguridad_social": "Cuota de autónomos", "gestoria": "Gestoría y asesoría", "telefono": "Teléfono e internet",
    "viajes": "Viajes y transporte", "comidas": "Comidas con clientes", "oficina": "Oficina y material",
    "publicidad": "Publicidad y marketing", "banco": "Banco y comisiones", "seguros": "Seguros",
    "colaboradores": "Colaboradores y subcontratas", "otros": "Otros",
}
EXTENSIONES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic"}
# Un equipo de más de 300 € no se deduce entero en el IRPF: se amortiza en varios años.
LIMITE_AMORTIZAR = 300


def gastos():
    return {f.stem: leer(f) | {"id": f.stem} for f in sorted(GASTOS.glob("*/*.json"))}


def slug(texto):
    import unicodedata
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "gasto"


def calcular_gasto(g, iva_general=21):
    """Las cifras fiscales de un gasto a partir de base, tipo de IVA y % de afectación."""
    base = euros(g["base"])
    ded = Decimal(str(g.get("afectacion", 100))) / 100
    tipo = g["tipo_iva"]
    pct = Decimal(str(g.get("iva_pct", iva_general if tipo == "nacional" else 0)))
    iva = euros(base * pct / 100) if tipo in ("nacional", "ticket") else Decimal(0)
    autoliquidado = euros(base * Decimal(iva_general) / 100) if tipo in ("isp_ue", "isp_fuera") else Decimal(0)
    if tipo == "nacional":
        iva_deducible = euros(iva * ded)
    elif tipo in ("isp_ue", "isp_fuera"):
        iva_deducible = euros(autoliquidado * ded)
    else:
        iva_deducible = Decimal(0)
    # En el IRPF, el IVA que no se puede deducir (ticket) es más gasto
    gasto_irpf = euros((base + (iva if tipo == "ticket" else 0)) * ded)
    amortizable = g.get("categoria") == "equipo" and base > LIMITE_AMORTIZAR
    return {
        "base": float(base), "iva_pct": float(pct), "iva": float(iva), "total": float(base + iva),
        "afectacion": float(ded * 100), "iva_deducible": float(iva_deducible),
        "iva_autoliquidado": float(autoliquidado),
        "gasto_irpf": 0.0 if amortizable else float(gasto_irpf),
        "amortizable": float(gasto_irpf) if amortizable else 0.0,
    }


def tipo_cambio(moneda, dia):
    """Unidades de <moneda> por euro según el BCE, el día hábil más cercano anterior."""
    import urllib.request

    desde = (fecha(dia) - dt.timedelta(days=10)).isoformat()
    url = (f"https://data-api.ecb.europa.eu/service/data/EXR/D.{moneda}.EUR.SP00.A"
           f"?startPeriod={desde}&endPeriod={dia}&format=csvdata")
    try:
        try:  # en Windows, Python no siempre encuentra los certificados del sistema
            import certifi, ssl
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = None
        with urllib.request.urlopen(url, timeout=20, context=ctx) as r:
            filas = r.read().decode().strip().splitlines()
    except OSError as e:
        sys.exit(f"No puedo leer el cambio del BCE ({e}). Pon \"base_eur\" en el borrador con lo que te cobró el banco.")
    cab = filas[0].split(",")
    i_fecha, i_valor = cab.index("TIME_PERIOD"), cab.index("OBS_VALUE")
    ultima = filas[-1].split(",")
    return Decimal(ultima[i_valor]), ultima[i_fecha]


def registrar_gasto():
    """python backoffice.py gasto <borrador.json> [archivo]"""
    if len(sys.argv) < 3:
        sys.exit("Uso: python backoffice.py gasto <borrador.json> [factura.pdf|.jpg]")
    b = leer(sys.argv[2])
    archivo = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
    neg = negocio()

    for k in ("fecha", "proveedor", "concepto", "categoria", "tipo_iva", "base"):
        if b.get(k) in (None, ""):
            sys.exit(f"Al borrador le falta \"{k}\"")
    fecha(b["fecha"])
    if b["tipo_iva"] not in TIPOS_IVA:
        sys.exit(f"tipo_iva tiene que ser uno de: {', '.join(TIPOS_IVA)}")
    if b["categoria"] not in CATEGORIAS:
        sys.exit(f"categoria tiene que ser una de: {', '.join(CATEGORIAS)}")
    if archivo and (not archivo.exists() or archivo.suffix.lower() not in EXTENSIONES):
        sys.exit(f"No encuentro la factura {archivo} o no es PDF/imagen")
    if not archivo and not b.get("sin_factura"):
        print("  Aviso: sin factura adjunta. Quedará en \"Lo que falta\" hasta que la pases.")

    # Otra moneda: la base en euros sale del BCE, salvo que venga lo que cobró el banco
    moneda = b.get("moneda", "EUR").upper()
    g = {k: v for k, v in b.items() if k not in ("base_eur",)}
    if moneda != "EUR":
        g["base_original"] = b["base"]
        if b.get("base_eur"):
            g["base"] = float(euros(b["base_eur"]))
            g["cambio"] = "importe cargado en el banco"
        else:
            tasa, dia = tipo_cambio(moneda, b["fecha"])
            g["base"] = float(euros(Decimal(str(b["base"])) / tasa))
            g["cambio"] = f"BCE {dia}: 1 EUR = {tasa} {moneda}"

    ya = [x for x in gastos().values()
          if (b.get("numero_factura") and x.get("numero_factura") == b["numero_factura"] and x["proveedor"] == b["proveedor"])
          or (b.get("gmail_id") and x.get("gmail_id") == b["gmail_id"])]
    if ya:
        sys.exit(f"Ese gasto ya está apuntado: {ya[0]['id']}")
    if neg.get("alta") and not pendiente(neg["alta"]) and b["fecha"] < neg["alta"]:
        print(f"  Aviso: es anterior a tu alta ({neg['alta']}). Pregunta a la gestoría si se puede deducir.")

    g.update(calcular_gasto(g, neg.get("iva", 21)))
    base_id = f"{b['fecha']}-{slug(b['proveedor'])}"
    gid, n = base_id, 2
    while (GASTOS / b["fecha"][:4] / f"{gid}.json").exists():
        gid, n = f"{base_id}-{n}", n + 1
    destino = GASTOS / b["fecha"][:4]
    if archivo:
        destino.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archivo, destino / f"{gid}{archivo.suffix.lower()}")
        g["archivo"] = f"{gid}{archivo.suffix.lower()}"
    escribir(destino / f"{gid}.json", g)
    print(f"Gasto {gid}: {g['proveedor']}, base {g['base']:.2f} €, IVA deducible {g['iva_deducible']:.2f} €, "
          f"gasto IRPF {g['gasto_irpf']:.2f} €")
    if g.get("cambio"):
        print(f"  {g['base_original']} {moneda} → {g['base']:.2f} € ({g['cambio']})")
    if g["amortizable"]:
        print(f"  Equipo de más de {LIMITE_AMORTIZAR} €: no entra entero en el IRPF, se amortiza. Lo calcula la gestoría.")
    if g["tipo_iva"] == "isp_ue":
        print("  Proveedor de la UE: va en el 303 (casillas 10-11 y 36-37) y en el modelo 349. Necesitas estar en el ROI.")
    if g["tipo_iva"] == "ticket":
        print("  Ticket: el IVA no se deduce. Si puedes, pide factura completa con tu NIF.")


def recurrentes():
    """Apunta los gastos fijos (recurrentes.json) de cada mes que ya ha pasado y aún no están."""
    if not RECURRENTES.exists():
        print("No hay gastos fijos en datos/gastos/recurrentes.json")
        return
    hechos = {(g.get("recurrente"), g["fecha"][:7]) for g in gastos().values()}
    neg, nuevos = negocio(), 0
    for r in leer(RECURRENTES):
        a, m = map(int, r["desde"].split("-"))
        while True:
            ultimo = (dt.date(a + m // 12, m % 12 + 1, 1) - dt.timedelta(days=1)).day
            dia = dt.date(a, m, min(r.get("dia", ultimo), ultimo)).isoformat()
            if dia > hoy() or (r.get("hasta") and dia[:7] > r["hasta"]):
                break
            if (r["id"], dia[:7]) not in hechos:
                g = {k: v for k, v in r.items() if k not in ("id", "desde", "hasta", "dia")}
                g.update(fecha=dia, recurrente=r["id"])
                g.update(calcular_gasto(g, neg.get("iva", 21)))
                gid = f"{dia}-{slug(r['id'])}"
                escribir(GASTOS / dia[:4] / f"{gid}.json", g)
                print(f"  {gid}: {g['concepto']} {g['base']:.2f} €")
                nuevos += 1
            a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    print(f"{nuevos} gastos fijos apuntados" if nuevos else "Gastos fijos al día")


# ---- Trimestre: 303 y 130 ----

def trimestre_de(iso):
    return f"{iso[:4]}-{(int(iso[5:7]) - 1) // 3 + 1}T"


def limites(t):
    anyo, q = int(t[:4]), int(t[5])
    ini = dt.date(anyo, 3 * q - 2, 1)
    fin = dt.date(anyo + (q == 4), (3 * q) % 12 + 1, 1) - dt.timedelta(days=1)
    plazo = dt.date(anyo + 1, 1, 30) if q == 4 else dt.date(anyo, 3 * q + 1, 20)
    return ini.isoformat(), fin.isoformat(), plazo.isoformat()


def calcular_trimestre(t, fas=None, gas=None):
    """Las casillas del 303 (solo el trimestre) y del 130 (acumulado del año) a partir de facturas y gastos.

    Es una estimación para dársela a la gestoría: no aplica prorrata, deducción del art. 110.3.c
    (rendimientos bajos el año anterior), gastos de difícil justificación ni amortizaciones.
    """
    fas = list((fas or facturas()).values())
    gas = list((gas or gastos()).values())
    ini, fin, plazo = limites(t)
    D = lambda x: Decimal(str(x))
    S = lambda lista, k: sum((D(x[k]) for x in lista), Decimal(0))

    # 303: lo del trimestre
    f_t = [f for f in fas if ini <= f["fecha"] <= fin]
    g_t = [g for g in gas if ini <= g["fecha"] <= fin]
    ordinarias = [f for f in f_t if f.get("tipo") != "rectificativa"]
    rect = [f for f in f_t if f.get("tipo") == "rectificativa"]
    es = [f for f in ordinarias if f["iva_pct"] > 0]
    ue = [f for f in ordinarias if f["iva_pct"] == 0 and f["receptor"].get("pais", "ES").upper() in UE]
    fuera = [f for f in ordinarias if f["iva_pct"] == 0 and f not in ue]
    nac = [g for g in g_t if g["tipo_iva"] == "nacional"]
    isp_ue = [g for g in g_t if g["tipo_iva"] == "isp_ue"]
    isp_fuera = [g for g in g_t if g["tipo_iva"] == "isp_fuera"]

    m303 = {
        "07": S(es, "base"), "09": S(es, "iva"),
        "10": S(isp_ue, "base"), "11": S(isp_ue, "iva_autoliquidado"),
        "12": S(isp_fuera, "base"), "13": S(isp_fuera, "iva_autoliquidado"),
        "14": S(rect, "base"), "15": S(rect, "iva"),
        "28": S(nac, "base"), "29": S(nac, "iva_deducible") + S(isp_fuera, "iva_deducible"),
        "36": S(isp_ue, "base"), "37": S(isp_ue, "iva_deducible"),
        "59": S(ue, "base"), "120": S(fuera, "base"),
    }
    # Las ISP de fuera de la UE se deducen en 28-29 junto a las interiores
    m303["28"] += S(isp_fuera, "base")
    m303["27"] = m303["09"] + m303["11"] + m303["13"] + m303["15"]
    m303["45"] = m303["29"] + m303["37"]
    m303["46"] = m303["27"] - m303["45"]

    # 130: acumulado desde el 1 de enero hasta el final del trimestre
    y0 = t[:4] + "-01-01"
    f_a = [f for f in fas if y0 <= f["fecha"] <= fin]
    g_a = [g for g in gas if y0 <= g["fecha"] <= fin]
    m130 = {"01": S(f_a, "base"), "02": S(g_a, "gasto_irpf")}
    m130["03"] = m130["01"] - m130["02"]
    m130["04"] = euros(max(m130["03"], Decimal(0)) * Decimal("0.20"))
    previos = Decimal(0)
    for q in range(1, int(t[5])):
        anterior = calcular_trimestre(f"{t[:4]}-{q}T", {f["numero"]: f for f in fas}, {g["id"]: g for g in gas})
        previos += max(D(anterior["m130"]["07"]), Decimal(0))
    m130["05"] = previos
    m130["06"] = S(f_a, "irpf")
    m130["07"] = m130["04"] - m130["05"] - m130["06"]

    a_pagar = max(m303["46"], Decimal(0)) + max(m130["07"], Decimal(0))
    avisos = []
    if isp_ue or ue:
        avisos.append("Hay operaciones con empresas de la UE: también va el modelo 349, y tienes que estar en el ROI.")
    if any(g["amortizable"] for g in g_a):
        avisos.append(f"Hay equipos por amortizar ({eur_es(S(g_a, 'amortizable'))}): no están en la casilla 02 del 130. "
                      "La gestoría calcula la amortización.")
    sin = [g for g in g_t if not g.get("archivo") and not g.get("sin_factura")]
    if sin:
        avisos.append(f"Faltan {len(sin)} facturas de gastos: {', '.join(g['proveedor'] for g in sin)}.")
    if m303["46"] < 0:
        avisos.append("El 303 sale a compensar." + (" En el 4T se puede pedir la devolución." if t.endswith("4T") else ""))
    avisos.append("Revisar con la gestoría: deducción del art. 110.3.c en el 130, gastos de difícil justificación y prorrata.")

    num = lambda d: {k: float(v) for k, v in d.items()}
    return {
        "trimestre": t, "desde": ini, "hasta": fin, "plazo": plazo,
        "m303": num(m303), "m130": num(m130), "a_pagar": float(a_pagar),
        "facturas": [f["numero"] for f in sorted(f_t, key=lambda f: (f["fecha"], f["numero"]))],
        "gastos": [g["id"] for g in sorted(g_t, key=lambda g: (g["fecha"], g["id"]))],
        "avisos": avisos,
        "presentado": leer(TRIMESTRES / t / "presentado.json") if (TRIMESTRES / t / "presentado.json").exists() else None,
    }


def eur_es(x):
    """1234.5 → '1.234,50 €'"""
    return f"{Decimal(str(x)):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def trimestres_con_datos():
    """Todos los trimestres con facturas o gastos, más el actual."""
    ts = {trimestre_de(x["fecha"]) for x in list(facturas().values()) + list(gastos().values())}
    ts.add(trimestre_de(hoy()))
    return sorted(ts, reverse=True)


def leer_trimestre():
    t = sys.argv[2] if len(sys.argv) > 2 else trimestre_de(hoy())
    if not re.fullmatch(r"\d{4}-[1-4]T", t):
        sys.exit("El trimestre va como 2026-4T")
    return t


def resumen():
    t = leer_trimestre()
    r = calcular_trimestre(t)
    m, n = r["m303"], r["m130"]
    print(f"Trimestre {t} ({r['desde']} a {r['hasta']}), se presenta hasta el {r['plazo']}")
    print(f"  {len(r['facturas'])} facturas emitidas, {len(r['gastos'])} gastos")
    print(f"  303  IVA repercutido {m['27']:>10.2f} €  − deducible {m['45']:>10.2f} €  = {m['46']:>10.2f} €")
    print(f"  130  rendimiento {n['03']:>10.2f} €  × 20% = {n['04']:.2f} €  − retenciones {n['06']:.2f} €"
          f"  − pagos previos {n['05']:.2f} € = {n['07']:.2f} €")
    print(f"  A apartar: {r['a_pagar']:.2f} €")
    for a in r["avisos"]:
        print("  ·", a)


def xlsx(dest, hojas):
    """Escribe un .xlsx mínimo sin dependencias: {nombre: [fila, fila…]}, la primera fila es la cabecera."""
    import zipfile
    from xml.sax.saxutils import escape

    def col(i):
        s = ""
        while i >= 0:
            s, i = chr(65 + i % 26) + s, i // 26 - 1
        return s

    def celda(ref, v, cab):
        estilo = ' s="1"' if cab else ""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f'<c r="{ref}"{estilo}><v>{v}</v></c>'
        return f'<c r="{ref}" t="inlineStr"{estilo}><is><t>{escape(str(v if v is not None else ""))}</t></is></c>'

    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        nombres = list(hojas)
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                             for i in range(len(nombres))) + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(n[:31])}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(nombres))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                             for i in range(len(nombres)))
                   + f'<Relationship Id="rId{len(nombres) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                   + "</Relationships>")
        z.writestr("xl/styles.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
                   '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
                   '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
                   '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                   '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                   '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
                   '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i, filas in enumerate(hojas.values()):
            xml = "".join(f'<row r="{r + 1}">' + "".join(celda(f"{col(c)}{r + 1}", v, r == 0) for c, v in enumerate(fila)) + "</row>"
                          for r, fila in enumerate(filas))
            anchos = [min(60, max(10, *(len(str(fila[c])) + 2 for fila in filas if c < len(fila)))) for c in range(len(filas[0]))]
            cols = "".join(f'<col min="{c + 1}" max="{c + 1}" width="{w}" customWidth="1"/>' for c, w in enumerate(anchos))
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml",
                       '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                       f'<cols>{cols}</cols><sheetData>{xml}</sheetData></worksheet>')


def libros(t, r, dest):
    """Libros registro de ingresos y gastos del trimestre, en Excel, como los suele pedir una gestoría."""
    fas, gas = facturas(), gastos()
    ingresos = [["Fecha", "Número", "Tipo", "Cliente", "NIF", "País", "Base", "% IVA", "IVA", "% IRPF", "IRPF", "Total",
                 "Estado", "Cobrada"]]
    for n in r["facturas"]:
        f = fas[n]
        ingresos.append([f["fecha"], n, f.get("tipo", "ordinaria"), f["receptor"]["razon_social"], f["receptor"]["nif"],
                         f["receptor"].get("pais", "ES"), f["base"], f["iva_pct"], f["iva"], f["irpf_pct"], f["irpf"],
                         f["total"], f["estado"], f.get("cobrada") or ""])
    salidas = [["Fecha", "Proveedor", "NIF", "País", "Nº factura", "Concepto", "Categoría", "Tipo de IVA", "Base",
                "% IVA", "IVA", "Total", "% afectación", "IVA deducible", "IVA autoliquidado", "Gasto IRPF",
                "Por amortizar", "Archivo"]]
    for gid in r["gastos"]:
        g = gas[gid]
        salidas.append([g["fecha"], g["proveedor"], g.get("nif_proveedor", ""), g.get("pais", ""), g.get("numero_factura", ""),
                        g["concepto"], CATEGORIAS.get(g["categoria"], g["categoria"]), TIPOS_IVA[g["tipo_iva"]], g["base"],
                        g["iva_pct"], g["iva"], g["total"], g["afectacion"], g["iva_deducible"], g["iva_autoliquidado"],
                        g["gasto_irpf"], g["amortizable"], g.get("archivo") or ("sin factura" if g.get("sin_factura") else "FALTA")])
    m, n = r["m303"], r["m130"]
    casillas = [["Modelo", "Casilla", "Concepto", "Importe"]] + [
        ["303", "07", "Base al 21%", m["07"]], ["303", "09", "Cuota al 21%", m["09"]],
        ["303", "10", "Adquisiciones intracomunitarias de servicios: base", m["10"]], ["303", "11", "… cuota", m["11"]],
        ["303", "12", "Otras operaciones con inversión del sujeto pasivo: base", m["12"]], ["303", "13", "… cuota", m["13"]],
        ["303", "14", "Modificación de bases (rectificativas)", m["14"]], ["303", "15", "… cuotas", m["15"]],
        ["303", "27", "Total cuota devengada", m["27"]],
        ["303", "28", "Operaciones interiores corrientes: base", m["28"]], ["303", "29", "… cuota deducible", m["29"]],
        ["303", "36", "Adquisiciones intracomunitarias: base", m["36"]], ["303", "37", "… cuota deducible", m["37"]],
        ["303", "45", "Total a deducir", m["45"]], ["303", "46", "Resultado régimen general", m["46"]],
        ["303", "59", "Entregas intracomunitarias de servicios", m["59"]],
        ["303", "120", "Operaciones no sujetas por reglas de localización", m["120"]],
        ["130", "01", "Ingresos computables (acumulado)", n["01"]], ["130", "02", "Gastos deducibles (acumulado)", n["02"]],
        ["130", "03", "Rendimiento neto", n["03"]], ["130", "04", "20% del rendimiento", n["04"]],
        ["130", "05", "Pagos fraccionados de trimestres anteriores", n["05"]],
        ["130", "06", "Retenciones e ingresos a cuenta (acumulado)", n["06"]], ["130", "07", "Resultado", n["07"]],
    ]
    xlsx(dest, {"Casillas": casillas, "Ingresos": ingresos, "Gastos": salidas})


def trimestre():
    """Paquete para la gestoría: resumen en PDF, libros en Excel y un ZIP con todas las facturas."""
    import zipfile

    t = leer_trimestre()
    r = calcular_trimestre(t)
    carpeta = TRIMESTRES / t
    carpeta.mkdir(parents=True, exist_ok=True)

    libros(t, r, carpeta / f"libros-{t}.xlsx")
    tmp = build(ROOT / "dist" / "admin-pdf")
    server = servidor(tmp)
    try:
        pdf = carpeta / f"resumen-{t}.pdf"
        args = [chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw", "--virtual-time-budget=10000",
                f"--print-to-pdf={pdf}", f"http://127.0.0.1:{server.server_address[1]}/trimestre.html?t={t}"]
        if sys.platform != "win32":
            args.insert(1, "--no-sandbox")
        subprocess.run(args, check=True, capture_output=True)
    finally:
        server.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    zdest = ROOT / "dist" / "trimestres" / f"gestoria-{t}.zip"
    zdest.parent.mkdir(parents=True, exist_ok=True)
    gas = gastos()
    with zipfile.ZipFile(zdest, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf, pdf.name)
        z.write(carpeta / f"libros-{t}.xlsx", f"libros-{t}.xlsx")
        for n in r["facturas"]:
            z.write(ruta_factura(n).with_suffix(".pdf"), f"facturas-emitidas/{n}.pdf")
        for gid in r["gastos"]:
            if gas[gid].get("archivo"):
                z.write(GASTOS / gid[:4] / gas[gid]["archivo"], f"facturas-recibidas/{gas[gid]['archivo']}")
    print(f"Paquete del {t} listo:")
    print(f"  {pdf}")
    print(f"  {carpeta / f'libros-{t}.xlsx'}")
    print(f"  {zdest}  ← esto es lo que se manda a la gestoría")
    resumen()


def zip_mes(mes, destino):
    """ZIP de un mes para la gestoría: las facturas emitidas y recibidas (PDF) y un resumen.csv con todo,
    también los gastos que no llevan factura (cuota de autónomos). Devuelve cuántos PDF lleva."""
    import csv
    import io
    import zipfile

    fas = [f for f in facturas().values() if f["fecha"][:7] == mes]
    gas = {gid: g for gid, g in gastos().items() if g["fecha"][:7] == mes}
    if not fas and not gas:
        return 0
    destino.parent.mkdir(parents=True, exist_ok=True)
    cls = clientes()
    filas = io.StringIO()
    w = csv.writer(filas, delimiter=";")
    w.writerow(["Tipo", "Fecha", "Número", "Cliente o proveedor", "Concepto", "Base", "IVA", "IRPF", "Total", "Archivo"])
    n = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(fas, key=lambda x: x["numero"]):
            pdf = ruta_factura(f["numero"]).with_suffix(".pdf")
            if pdf.exists():
                z.write(pdf, f"facturas-emitidas/{pdf.name}")
                n += 1
            w.writerow(["Emitida" + (" (rectificativa)" if f.get("tipo") == "rectificativa" else ""), f["fecha"], f["numero"],
                        cls.get(f["cliente"], {}).get("razon_social") or f["cliente"], f.get("hito") or "",
                        eur_es(f["base"]), eur_es(f["iva"]), eur_es(f.get("irpf", 0)), eur_es(f["total"]),
                        f"facturas-emitidas/{pdf.name}" if pdf.exists() else ""])
        for gid, g in sorted(gas.items(), key=lambda x: x[1]["fecha"]):
            if g.get("archivo"):
                z.write(GASTOS / gid[:4] / g["archivo"], f"facturas-recibidas/{g['archivo']}")
                arch, n = f"facturas-recibidas/{g['archivo']}", n + 1
            else:
                arch = "no lleva factura" if g.get("sin_factura") else "FALTA LA FACTURA"
            w.writerow(["Recibida", g["fecha"], g.get("numero_factura") or "", g["proveedor"], g["concepto"],
                        eur_es(g["base"]), eur_es(g.get("iva", 0)), "", eur_es(g.get("total", g["base"])), arch])
        z.writestr("resumen.csv", "\ufeff" + filas.getvalue())
    return n


def mes():
    """python backoffice.py mes [AAAA-MM]: el ZIP del mes para la gestoría (por defecto, el mes pasado)."""
    if len(sys.argv) > 2:
        m = sys.argv[2]
    else:
        primero = fecha(hoy()).replace(day=1)
        m = (primero - dt.timedelta(days=1)).isoformat()[:7]
    destino = ROOT / "dist" / "meses" / f"gestoria-{m}.zip"
    if not zip_mes(m, destino) and not destino.exists():
        sys.exit(f"No hay facturas ni gastos en {m}.")
    print(f"{destino}  <- facturas en PDF y resumen.csv")
    for x in prevision_gastos():
        if x["mes"] == m and x["estado"] in ("falta factura", "pendiente"):
            print(f"  Aviso: falta la factura de {x['proveedor']} ({x['fecha']})")


def presentado():
    """python backoffice.py presentado 2026-4T: apunta que la gestoría ya lo presentó, con lo que salió."""
    t = leer_trimestre()
    r = calcular_trimestre(t)
    escribir(TRIMESTRES / t / "presentado.json",
             {"fecha": hoy(), "m303_46": r["m303"]["46"], "m130_07": r["m130"]["07"], "a_pagar": r["a_pagar"]})
    print(f"{t} marcado como presentado ({r['a_pagar']:.2f} €)")


# ---- Banco: cuadrar con el extracto ----
#
# Lee el CSV del banco: el de Revolut tal cual (Completed Date, Description, Amount, Fee, State)
# o cualquier CSV con columnas fecha, importe y concepto (separado por comas o por punto y coma).
# No guarda el extracto en el repo: solo lo cruza con facturas y gastos y dice qué cuadra y qué falta.

def leer_extracto(ruta):
    import csv

    texto = pathlib.Path(ruta).read_text(encoding="utf-8-sig")
    sep = ";" if texto.splitlines()[0].count(";") > texto.splitlines()[0].count(",") else ","
    filas = list(csv.DictReader(texto.splitlines(), delimiter=sep))
    if not filas:
        sys.exit("El CSV está vacío")
    cab = {k.strip().lower(): k for k in filas[0]}
    num = lambda x: Decimal((x or "0").replace(".", "").replace(",", ".") if "," in (x or "") else (x or "0"))
    movs = []
    if "amount" in cab:  # Revolut
        for r in filas:
            if r.get("State", "COMPLETED").upper() not in ("COMPLETED", "COMPLETADO"):
                continue
            dia = (r.get("Completed Date") or r.get("Started Date") or "")[:10]
            movs.append({"fecha": dia, "importe": num(r["Amount"]) - num(r.get("Fee")),
                         "concepto": r.get("Description", ""), "moneda": r.get("Currency", "EUR")})
    elif {"fecha", "importe", "concepto"} <= set(cab):
        for r in filas:
            dia = r[cab["fecha"]].strip()
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}", dia):
                dia = f"{dia[6:]}-{dia[3:5]}-{dia[:2]}"
            movs.append({"fecha": dia[:10], "importe": num(r[cab["importe"]].strip()),
                         "concepto": r[cab["concepto"]], "moneda": "EUR"})
    else:
        sys.exit("No reconozco el CSV: tiene que ser el de Revolut o tener columnas fecha, importe y concepto")
    return movs


def palabras(texto):
    return {p for p in re.split(r"[^a-z0-9]+", slug(texto).replace("-", " ")) if len(p) > 2} - {
        "s", "sl", "sa", "inc", "ltd", "corporation", "software", "the", "com", "www"}


def banco():
    """python backoffice.py banco <extracto.csv>: cobros que cuadran con facturas y cargos de proveedores sin factura."""
    if len(sys.argv) < 3:
        sys.exit("Uso: python backoffice.py banco <extracto.csv>")
    movs = leer_extracto(sys.argv[2])
    fas, gas = facturas(), gastos()
    fijos = leer(RECURRENTES) if RECURRENTES.exists() else []
    print(f"{len(movs)} movimientos, del {min(m['fecha'] for m in movs)} al {max(m['fecha'] for m in movs)}\n")

    # 1. Ingresos que cuadran con facturas pendientes (mismo importe total, después de emitirla)
    pendientes_cobro = [f for f in fas.values() if f["estado"] == "emitida" and f.get("tipo") != "rectificativa"]
    print("Cobros que cuadran con una factura:")
    hay = False
    for m in movs:
        if m["importe"] <= 0:
            continue
        for f in pendientes_cobro:
            if abs(m["importe"] - Decimal(str(f["total"]))) < Decimal("0.02") and m["fecha"] >= f["fecha"]:
                print(f"  {m['fecha']}  {m['importe']:>9.2f} €  {m['concepto'][:40]:40}  → {f['numero']} "
                      f"(python backoffice.py cobrar {f['numero']} {m['fecha']})")
                hay = True
    if not hay:
        print("  ninguno")

    # 2. Cargos de proveedores conocidos (de gastos o fijos)
    proveedores = {}
    for x in list(gas.values()) + fijos:
        pal = palabras(x["proveedor"]) | palabras(x.get("concepto", ""))
        for alias in x.get("banco", []) if isinstance(x.get("banco"), list) else [x.get("banco", "")]:
            pal |= palabras(alias)
        proveedores.setdefault(x["proveedor"], set()).update(pal)
    print("\nCargos de proveedores del negocio:")
    hay = False
    for m in movs:
        if m["importe"] >= 0:
            continue
        claves = palabras(m["concepto"])
        for prov, pal in proveedores.items():
            if not claves & pal:
                continue
            hay = True
            cerca = [g for g in gas.values() if g["proveedor"] == prov
                     and abs((fecha(g["fecha"]) - fecha(m["fecha"])).days) <= 7]
            real = [g for g in cerca if g.get("archivo")]
            if real:
                estado = f"apuntado ({real[0]['id']})"
            elif cerca:
                estado = f"apuntado aproximado ({cerca[0]['id']}, {cerca[0]['base']:.2f} € de base): falta la factura"
            else:
                estado = "SIN APUNTAR: busca la factura"
            print(f"  {m['fecha']}  {m['importe']:>9.2f} {m['moneda']}  {m['concepto'][:30]:30}  {prov}: {estado}")
            break
    if not hay:
        print("  ninguno")
    print("\nEl resto de movimientos no se toca.")


# ---- Previsión, horas, seguimiento y resumen semanal ----

def meses_siguientes(n=6):
    a, m = int(hoy()[:4]), int(hoy()[5:7])
    out = []
    for _ in range(n):
        out.append(f"{a}-{m:02d}")
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return out


def prevision_gastos(adelante=2):
    """Los gastos fijos mes a mes, desde que empiezan hasta dentro de <adelante> meses, con su estado:

    - confirmado: ya está apuntado con su factura (o no lleva factura, como la cuota de autónomos)
    - falta factura: apuntado con el importe aproximado; falta el PDF real
    - pendiente: ya ha pasado su día y aún no está apuntado (python backoffice.py recurrentes)
    - previsto: todavía no ha llegado su día
    """
    fijos = leer(RECURRENTES) if RECURRENTES.exists() else []
    neg = negocio()
    apuntados = {}
    for gid, g in gastos().items():
        if g.get("recurrente"):
            apuntados[(g["recurrente"], g["fecha"][:7])] = g | {"id": gid}
    limite = meses_siguientes(adelante + 1)[-1]
    out = []
    for r in fijos:
        a, m = map(int, r["desde"].split("-"))
        while True:
            mes = f"{a}-{m:02d}"
            if mes > limite or (r.get("hasta") and mes > r["hasta"]):
                break
            ultimo = (dt.date(a + m // 12, m % 12 + 1, 1) - dt.timedelta(days=1)).day
            dia = dt.date(a, m, min(r.get("dia", ultimo), ultimo)).isoformat()
            g = apuntados.get((r["id"], mes))
            if g:
                estado = "confirmado" if (g.get("archivo") or g.get("sin_factura")) else "falta factura"
                base, fecha_real, gid = g["base"], g["fecha"], g["id"]
            else:
                estado = "pendiente" if dia <= hoy() else "previsto"
                base, fecha_real, gid = calcular_gasto(r, neg.get("iva", 21))["base"], dia, None
            out.append({"mes": mes, "fecha": fecha_real, "fijo": r["id"], "proveedor": r["proveedor"],
                        "concepto": r["concepto"], "base": float(base), "estado": estado, "gasto": gid,
                        "archivo": (g or {}).get("archivo")})
            a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return sorted(out, key=lambda x: (x["fecha"], x["proveedor"]))


def prevision():
    """Lo que entra, lo que hay que apartar y lo que queda, mes a mes, con los hitos fechados y los gastos fijos.

    Es orientativo: IVA = cobrado − deducible de los fijos; IRPF = 20% del rendimiento menos lo que retienen.
    """
    neg, cls = negocio(), clientes()
    fijos = leer(RECURRENTES) if RECURRENTES.exists() else []
    meses = {m: {"mes": m, "base": Decimal(0), "iva": Decimal(0), "retenido": Decimal(0), "gastos": Decimal(0),
                 "iva_gastos": Decimal(0), "detalle": []} for m in meses_siguientes()}
    sin_fecha = Decimal(0)

    def sumar(mes, base, cliente, texto):
        c = cls.get(cliente)
        if not c or mes not in meses:
            return
        iva, irpf, _ = regimen(c, neg)
        x = meses[mes]
        x["base"] += base
        x["iva"] += euros(base * iva / 100)
        x["retenido"] += euros(base * irpf / 100)
        x["detalle"].append(texto)

    for p in proyectos().values():
        if p.get("estado") in ("terminado", "perdido"):
            continue
        for h in p.get("hitos", []):
            if h.get("estado") not in ("pendiente", "hecho"):
                continue
            if not h.get("fecha"):
                sin_fecha += Decimal(str(h.get("importe", 0)))
                continue
            etiqueta = f"{clientes().get(p['cliente'], {}).get('nombre', p['cliente'])} · {h['nombre']}"
            if p["estado"] == "propuesta":
                etiqueta += " (propuesta)"
            sumar(h["fecha"][:7], Decimal(str(h.get("importe", 0))), p["cliente"], etiqueta)
    for b in borradores().values():
        base = sum((Decimal(str(c.get("cantidad", 1))) * Decimal(str(c["precio"])) for c in b.get("conceptos", [])), Decimal(0))
        sumar((b.get("fecha") or hoy())[:7], base, b.get("cliente"), f"Borrador · {clientes().get(b.get('cliente'), {}).get('nombre', '')}")
    for r in fijos:
        for mes in meses:
            if mes >= r["desde"] and (not r.get("hasta") or mes <= r["hasta"]):
                c = calcular_gasto(r, neg.get("iva", 21))
                meses[mes]["gastos"] += Decimal(str(c["gasto_irpf"]))
                meses[mes]["iva_gastos"] += Decimal(str(c["iva_deducible"])) - Decimal(str(c["iva_autoliquidado"]))

    out = []
    for x in meses.values():
        rendimiento = x["base"] - x["gastos"]
        irpf = max(euros(max(rendimiento, Decimal(0)) * Decimal("0.20")) - x["retenido"], Decimal(0))
        iva = max(x["iva"] - x["iva_gastos"], Decimal(0))
        out.append({"mes": x["mes"], "base": float(x["base"]), "gastos": float(x["gastos"]),
                    "apartar": float(iva + irpf), "queda": float(rendimiento - irpf - x["retenido"]),
                    "detalle": x["detalle"]})
    return {"meses": out, "sin_fecha": float(sin_fecha)}


def horas_proyecto(p):
    """Horas apuntadas y lo que sale por hora, con lo facturado (o el precio si aún no hay facturas)."""
    lista = p.get("horas", [])
    total = sum(Decimal(str(h["horas"])) for h in lista)
    facturado = sum((Decimal(str(f["base"])) for f in facturas().values()
                     if f.get("proyecto") == p.get("slug") and f["estado"] != "rectificada"
                     and f.get("tipo") != "rectificativa"), Decimal(0))
    mes = hoy()[:7]
    return {"total": float(total), "mes": float(sum(Decimal(str(h["horas"])) for h in lista if h["fecha"][:7] == mes)),
            "por_hora": float(euros(facturado / total)) if total and facturado else None,
            "presupuesto_mes": float(Decimal(str(p["horas_semana"])) * Decimal("4.33")) if p.get("horas_semana") else None}


def semana():
    """Resumen de la semana en Markdown: lo que hay que hacer, cobrar y apartar. Lo usa la tarea de los lunes."""
    neg = negocio()
    fas = facturas()
    lineas = [f"# Semana del {fecha_corta(hoy())}", ""]
    falta = pendientes(neg)
    if falta:
        lineas += ["## Lo que falta", ""] + [f"- {p['texto']} → «{p['pide']}»" for p in falta] + [""]
    por_cobrar = sorted((f for f in fas.values() if f["estado"] == "emitida" and f.get("tipo") != "rectificativa"),
                        key=lambda f: f["vence"])
    lineas += ["## Por cobrar", ""] + ([f"- {f['numero']} · {clientes().get(f['cliente'], {}).get('nombre', f['cliente'])} · "
                                        f"{eur_es(f['total'])} · vence el {fecha_corta(f['vence'])}" for f in por_cobrar]
                                       or ["- Nadie te debe nada."]) + [""]
    proximos = []
    limite = (fecha(hoy()) + dt.timedelta(days=14)).isoformat()
    for p in proyectos().values():
        for h in p.get("hitos", []):
            if h.get("fecha") and h["estado"] == "pendiente" and h["fecha"] <= limite:
                proximos.append(f"- {fecha_corta(h['fecha'])} · {clientes().get(p['cliente'], {}).get('nombre', '')} · {h['nombre']}")
            if h["estado"] == "hecho":
                proximos.append(f"- Hecho y sin facturar: {clientes().get(p['cliente'], {}).get('nombre', '')} · {h['nombre']}")
    lineas += ["## Próximas dos semanas", ""] + (sorted(proximos) or ["- Nada con fecha."]) + [""]
    r = calcular_trimestre(trimestre_de(hoy()))
    lineas += ["## Impuestos", "",
               f"- Para el {r['trimestre']}, aparta {eur_es(r['a_pagar'])}: {eur_es(max(r['m303']['46'], 0))} de IVA y "
               f"{eur_es(max(r['m130']['07'], 0))} de IRPF. Plazo: {fecha_corta(r['plazo'])}.", ""]
    for p in proyectos().values():
        if p.get("horas") and p["estado"] == "activo":
            h = horas_proyecto(p | {"slug": p["slug"]})
            lineas.append(f"- Horas este mes con {clientes().get(p['cliente'], {}).get('nombre', '')}: {h['mes']:g} h")
    texto = "\n".join(lineas).rstrip() + "\n"
    print(texto)
    return texto

CAMPOS_NEGOCIO = {"nif": "tu NIF", "direccion": "tu dirección", "cp": "tu código postal", "email": "tu email",
                  "iban": "el IBAN", "irpf_hasta": "hasta cuándo dura el IRPF reducido"}


def fecha_corta(iso):
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]
    a, m, d = iso.split("-")
    return f"{int(d)} {meses[int(m) - 1]} {a}"


def pendientes(neg):
    """Lo que falta para que el sistema funcione del todo, con lo que hay que decirle a Claude Code."""
    out = []
    for k, nombre in CAMPOS_NEGOCIO.items():
        if k == "irpf_hasta" and float(neg.get("irpf", 15)) >= 15:
            continue
        if pendiente(neg.get(k)):
            out.append({"texto": f"Falta {nombre} en tus datos fiscales. Sin eso no se puede facturar.",
                        "pide": f"mi {nombre.removeprefix('tu ').removeprefix('el ')} es …"})
    if neg.get("alta") and hoy() < neg["alta"]:
        out.append({"texto": f"Tu alta de autónomo es el {fecha_corta(neg['alta'])}. Antes de esa fecha no se puede facturar.",
                    "pide": "el alta al final es el …"})
    cls = clientes()
    if not cls:
        out.append({"texto": "Aún no hay clientes.", "pide": "nuevo cliente: …"})
    prs = proyectos().values()
    for slug, c in cls.items():
        # Un cliente pro bono (o con todos sus proyectos pro bono) no se factura: no hacen falta sus datos fiscales
        suyos = [p for p in prs if p.get("cliente") == slug]
        if c.get("pro_bono") or (suyos and all(p.get("pro_bono") for p in suyos)) or c.get("estado") in ("contacto", "propuesta"):
            continue
        faltan = [k for k in ("razon_social", "nif", "direccion") if pendiente(c.get(k))]
        if faltan:
            out.append({"texto": f"A {c.get('nombre', slug)} le faltan datos para facturarle ({', '.join(faltan)}).",
                        "pide": f"los datos fiscales de {c.get('nombre', slug)} son …"})
    if cls and not proyectos():
        out.append({"texto": "Aún no hay proyectos.", "pide": "nuevo proyecto para …"})
    fijos = leer(RECURRENTES) if RECURRENTES.exists() else []
    if not any(r.get("categoria") == "seguridad_social" for r in fijos):
        out.append({"texto": "No está apuntada tu cuota de autónomos. Sin ella el 130 te sale más caro.",
                    "pide": "mi cuota de autónomos es … € al mes"})
    for g in gastos().values():
        if not g.get("archivo") and not g.get("sin_factura"):
            out.append({"texto": f"Falta la factura de {g['proveedor']} del {fecha_corta(g['fecha'])} ({g['base']:.2f} €).",
                        "pide": "aquí va la factura de …"})
    # Plazo de presentación: el trimestre anterior, si estamos dentro de su plazo y no está presentado
    ini_actual = limites(trimestre_de(hoy()))[0]
    anterior = trimestre_de((fecha(ini_actual) - dt.timedelta(days=1)).isoformat())
    plazo = limites(anterior)[2]
    if hoy() <= plazo and not (TRIMESTRES / anterior / "presentado.json").exists() and (
            any(trimestre_de(x["fecha"]) == anterior for x in list(facturas().values()) + list(gastos().values()))):
        out.append({"texto": f"Toca presentar el {anterior}: el plazo acaba el {fecha_corta(plazo)}.",
                    "pide": f"cierra el {anterior}"})
    # Cobros vencidos
    for f in facturas().values():
        if f["estado"] == "emitida" and f.get("tipo") != "rectificativa" and f["vence"] < hoy():
            dias = (fecha(hoy()) - fecha(f["vence"])).days
            nombre = cls.get(f["cliente"], {}).get("nombre", f["cliente"])
            out.append({"texto": f"La {f['numero']} de {nombre} venció hace {dias} días ({eur_es(f['total'])}).",
                        "pide": f"prepárale el recordatorio a {nombre}"})
    # Propuestas sin respuesta
    for p in proyectos().values():
        ultimo = p.get("ultimo_contacto") or p.get("enviada")
        if p.get("estado") == "propuesta" and ultimo:
            dias = (fecha(hoy()) - fecha(ultimo)).days
            if dias >= int(p.get("seguimiento_dias", 7)):
                nombre = cls.get(p["cliente"], {}).get("nombre", p["cliente"])
                out.append({"texto": f"{nombre}: {dias} días sin respuesta a la propuesta.",
                            "pide": f"prepárame un seguimiento para {nombre}"})
    return out


# ---- Espacios de cliente ----
#
# Un espacio es una página privada para un cliente: una propuesta, el seguimiento de un proyecto,
# entregables. Vive en datos/espacios/<slug>/index.md (cabecera con clave: valor y el texto en
# Markdown); el resto de archivos de esa carpeta se publican con él. Se publica en /c/<slug>/ y
# solo se abre con un enlace personal (?k=<clave>). En el repo solo queda el SHA-256 de cada clave,
# en datos/espacios/accesos.json; la clave se enseña una vez, al crear el enlace.

ACCESOS = ESPACIOS / "accesos.json"
ESTADO_HITO_CLIENTE = {"pendiente": "Por hacer", "hecho": "Entregado", "facturado": "Facturado", "cobrado": "Pagado"}
ESTADO_FACTURA_CLIENTE = {"emitida": "Pendiente de pago", "cobrada": "Pagada", "rectificada": "Anulada"}


def leer_espacio(carpeta):
    """(cabecera, markdown) de datos/espacios/<slug>/index.md."""
    texto = (carpeta / "index.md").read_text(encoding="utf-8")
    cab = {}
    if texto.startswith("---"):
        _, bloque, texto = texto.split("---", 2)
        for linea in bloque.strip().splitlines():
            if ":" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split(":", 1)
                cab[k.strip()] = v.strip().strip('"')
    return cab, texto.strip()


def espacios():
    if not ESPACIOS.exists():
        return {}
    out = {}
    for c in sorted(ESPACIOS.iterdir()):
        if c.is_dir() and (c / "index.md").exists():
            cab, md = leer_espacio(c)
            out[c.name] = cab | {"slug": c.name, "markdown": md}
    return out


def accesos():
    return leer(ACCESOS) if ACCESOS.exists() else {}


def markdown(md):
    """Markdown sencillo a HTML: títulos, párrafos, listas, citas, tablas, código, separadores,
    negrita, cursiva, código en línea y enlaces. El HTML que ya venga en el texto se respeta."""
    import html as H

    def linea(t):
        partes = re.split(r"(`[^`]+`)", t)
        out = []
        for x in partes:
            if x.startswith("`") and x.endswith("`") and len(x) > 1:
                out.append("<code>" + H.escape(x[1:-1]) + "</code>")
                continue
            if not re.search(r"<[a-zA-Z/][^>]*>", x):
                x = H.escape(x, quote=False)
            x = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1">', x)
            x = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', x)
            x = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", x)
            x = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", x)
            x = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", x)
            out.append(x)
        return "".join(out)

    def celdas(f):
        return [c.strip() for c in f.strip().strip("|").split("|")]

    lineas, html, i = md.replace("\r\n", "\n").split("\n"), [], 0
    while i < len(lineas):
        l = lineas[i]
        if not l.strip():
            i += 1
        elif l.startswith("```"):
            j = i + 1
            while j < len(lineas) and not lineas[j].startswith("```"):
                j += 1
            html.append("<pre><code>" + H.escape("\n".join(lineas[i + 1:j])) + "</code></pre>")
            i = j + 1
        elif m := re.match(r"(#{1,4})\s+(.*)", l):
            n = max(2, len(m.group(1)))  # # y ## son secciones (h2); el h1 es el título del espacio
            ident = slug(m.group(2))
            html.append(f'<h{n} id="{ident}">{linea(m.group(2))}</h{n}>')
            i += 1
        elif re.fullmatch(r"\s*(-{3,}|\*{3,})\s*", l):
            html.append("<hr>")
            i += 1
        elif l.lstrip().startswith("<") and re.match(r"\s*</?[a-zA-Z]", l):
            j = i
            while j < len(lineas) and lineas[j].strip():
                j += 1
            html.append("\n".join(lineas[i:j]))
            i = j
        elif l.startswith(">"):
            j = i
            while j < len(lineas) and lineas[j].startswith(">"):
                j += 1
            html.append("<blockquote>" + markdown("\n".join(x[1:].lstrip() for x in lineas[i:j])) + "</blockquote>")
            i = j
        elif "|" in l and i + 1 < len(lineas) and re.fullmatch(r"\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*", lineas[i + 1]):
            cab = celdas(l)
            alin = ["n" if c.strip().endswith(":") else "" for c in celdas(lineas[i + 1])]
            j = i + 2
            filas = []
            while j < len(lineas) and "|" in lineas[j] and lineas[j].strip():
                filas.append(celdas(lineas[j]))
                j += 1
            th = "".join(f'<th class="{alin[k] if k < len(alin) else ""}">{linea(c)}</th>' for k, c in enumerate(cab))
            trs = "".join("<tr>" + "".join(f'<td class="{alin[k] if k < len(alin) else ""}">{linea(c)}</td>'
                                           for k, c in enumerate(f)) + "</tr>" for f in filas)
            html.append(f'<div class="tabla"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
            i = j
        elif re.match(r"\s*([-*]|\d+\.)\s+", l):
            ordenada = bool(re.match(r"\s*\d+\.", l))
            items = []
            while i < len(lineas) and lineas[i].strip():
                m = re.match(r"\s*([-*]|\d+\.)\s+(.*)", lineas[i])
                if m:
                    items.append(m.group(2))
                elif items:
                    items[-1] += " " + lineas[i].strip()
                i += 1
            tag = "ol" if ordenada else "ul"
            html.append(f"<{tag}>" + "".join(f"<li>{linea(x)}</li>" for x in items) + f"</{tag}>")
        else:
            j = i
            while j < len(lineas) and lineas[j].strip() and not re.match(r"(#{1,4}\s|```|>|\s*([-*]|\d+\.)\s+)", lineas[j]):
                j += 1
            j = max(j, i + 1)
            html.append("<p>" + linea(" ".join(x.strip() for x in lineas[i:j])) + "</p>")
            i = j
    return "\n".join(html)


def pagina_espacio(e, neg, cls, prs, fas):
    """El HTML de un espacio de cliente, con sus hitos, facturas y archivos si los pide."""
    import html as H

    esc = lambda x: H.escape(str(x or ""))
    c = cls.get(e.get("cliente"), {})
    p = prs.get(e.get("proyecto"), {})
    mostrar = {x.strip() for x in e.get("mostrar", "hitos, facturas, archivos").split(",")}
    cuerpo = [markdown(e["markdown"])]
    indice = [(h_id, H.unescape(re.sub(r"<[^>]+>", "", t))) for h_id, t in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', cuerpo[0])]

    if p and "hitos" in mostrar and p.get("hitos"):
        filas = "".join(
            f'<tr><td>{esc(h["nombre"])}</td><td>{fecha_corta(h["fecha"]) if h.get("fecha") else "—"}</td>'
            f'<td class="n">{"" if p.get("pro_bono") else eur_es(h.get("importe", 0)) + " + IVA"}</td>'
            f'<td class="n"><span class="estado {esc(h["estado"])}">{ESTADO_HITO_CLIENTE.get(h["estado"], esc(h["estado"]))}</span></td></tr>'
            for h in p["hitos"])
        titulo_h = "Fases y fechas" if e.get("tipo") == "propuesta" else "Cómo va"
        cuerpo.append(f'<section class="bloque" id="como-va"><h2>{titulo_h}</h2><div class="tabla"><table><thead><tr><th>Fase</th>'
                      f'<th>Fecha</th><th class="n">{"" if p.get("pro_bono") else "Importe"}</th><th class="n">Estado</th></tr></thead>'
                      f'<tbody>{filas}</tbody></table></div></section>')
        indice.append(("como-va", titulo_h))
    suyas = [f for f in fas.values() if p and f.get("proyecto") == e.get("proyecto")]
    if suyas and "facturas" in mostrar:
        filas = "".join(
            f'<tr><td><a href="facturas/{esc(f["numero"])}.pdf" download>{esc(f["numero"])}</a></td><td>{fecha_corta(f["fecha"])}</td>'
            f'<td class="n">{eur_es(f["total"])}</td><td class="n"><span class="estado {esc(f["estado"])}">'
            f'{ESTADO_FACTURA_CLIENTE.get(f["estado"], esc(f["estado"]))}</span></td></tr>'
            for f in sorted(suyas, key=lambda f: f["numero"]))
        cuerpo.append(f'<section class="bloque" id="facturas"><h2>Facturas</h2><div class="tabla"><table><thead><tr><th>Número</th>'
                      f'<th>Fecha</th><th class="n">Total</th><th class="n">Estado</th></tr></thead><tbody>{filas}</tbody></table></div></section>')
        indice.append(("facturas", "Facturas"))
    carpeta = ESPACIOS / e["slug"]
    archivos = sorted(f for f in carpeta.rglob("*") if f.is_file() and f.name != "index.md")
    if archivos and "archivos" in mostrar:
        filas = "".join(f'<li><a href="{esc(f.relative_to(carpeta).as_posix())}" download>{esc(f.name)}</a>'
                        f'<span>{max(1, f.stat().st_size // 1024)} KB</span></li>' for f in archivos)
        cuerpo.append(f'<section class="bloque" id="archivos"><h2>Archivos</h2><ul class="archivos">{filas}</ul></section>')
        indice.append(("archivos", "Archivos"))
    if e.get("tipo") == "propuesta":
        asunto = H.escape(f"Propuesta: {e.get('titulo', '')}", quote=True).replace(" ", "%20")
        cuerpo.append(f'<section class="bloque cierre"><h2>¿Seguimos?</h2><p>{esc(e.get("aceptar") or "Si te encaja, contéstame a este correo y preparamos el arranque. Si hay algo que cambiar, también.")}</p>'
                      f'<p><a class="boton" href="mailto:{esc(neg.get("email"))}?subject={asunto}">Escribir a {esc(neg.get("nombre"))}</a></p></section>')

    nav = "".join(f'<a href="#{esc(i)}">{esc(t)}</a>' for i, t in indice) if len(indice) > 2 else ""
    datos = {
        "TITULO": esc(e.get("titulo") or p.get("nombre") or e["slug"]),
        "SUBTITULO": esc(e.get("subtitulo") or (("Propuesta para " if e.get("tipo") == "propuesta" else "Espacio de ") + (c.get("nombre") or ""))),
        "MARCA": esc(neg.get("nombre")),
        "EMAIL": esc(neg.get("email")),
        "FECHA": fecha_corta(e.get("fecha") or hoy()),
        "INDICE": f'<nav class="indice">{nav}</nav>' if nav else "",
        "CUERPO": "\n".join(cuerpo),
    }
    out = PLANTILLA_ESPACIO.read_text(encoding="utf-8")
    for k, v in datos.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def build_espacios(dest):
    """dist/sitio/c/<slug>/: cada espacio con sus archivos y las facturas de su proyecto."""
    neg, cls, prs, fas = negocio(), clientes(), proyectos(), facturas()
    hechos = []
    for slug_e, e in espacios().items():
        d = dest / slug_e
        carpeta = ESPACIOS / slug_e
        shutil.copytree(carpeta, d, ignore=shutil.ignore_patterns("index.md"))
        (d / "index.html").write_text(pagina_espacio(e, neg, cls, prs, fas), encoding="utf-8")
        if e.get("proyecto") and "facturas" in e.get("mostrar", "hitos, facturas, archivos"):
            for f in fas.values():
                if f.get("proyecto") == e["proyecto"]:
                    pdf = ruta_factura(f["numero"]).with_suffix(".pdf")
                    if pdf.exists():
                        (d / "facturas").mkdir(exist_ok=True)
                        shutil.copy2(pdf, d / "facturas" / pdf.name)
        hechos.append(slug_e)
    return hechos


def build_sitio():
    """Todo lo que se publica: dist/sitio/ (admin y espacios) y dist/accesos.json para la cerradura."""
    shutil.rmtree(SITIO, ignore_errors=True)
    build(DIST)
    hechos = build_espacios(SITIO / "c")
    # Vista previa para ti, dentro del admin (detrás de Access): /admin/espacios/<slug>/
    for h in hechos:
        shutil.copytree(SITIO / "c" / h, DIST / "espacios" / h)
    SITIO.mkdir(parents=True, exist_ok=True)
    (SITIO / "index.html").write_text(
        '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex, nofollow"><title>Privado</title><style>body{margin:0;min-height:100vh;display:grid;'
        'place-items:center;font:18px/1.5 system-ui,sans-serif;background:#fff;color:#0a0a0a}@media (prefers-color-scheme:dark)'
        '{body{background:#0a0a0a;color:#f2f2f2}}</style></head><body><p>Aquí no hay nada público.</p></body></html>\n', encoding="utf-8")
    (SITIO / "_headers").write_text(
        "/*\n  X-Robots-Tag: noindex, nofollow, noarchive\n  Referrer-Policy: no-referrer\n  X-Content-Type-Options: nosniff\n",
        encoding="utf-8")
    # La cerradura de /c/ solo necesita los hashes: {slug: {hash: nombre}}
    escribir(ROOT / "dist" / "accesos.json",
             {k: {a["hash"]: a["nombre"] for a in lista} for k, lista in accesos().items() if k in hechos})
    print(f"dist/sitio/c/ listo: {len(hechos)} espacios")


def enlace():
    """python backoffice.py enlace <espacio> "Nombre": crea un enlace personal y lo enseña una vez."""
    import hashlib
    import secrets

    if len(sys.argv) < 4:
        sys.exit('Uso: python backoffice.py enlace <espacio> "Nombre de la persona"')
    esp, nombre = sys.argv[2], sys.argv[3]
    if esp not in espacios():
        sys.exit(f"No existe el espacio {esp!r} (datos/espacios/{esp}/index.md)")
    clave = secrets.token_urlsafe(18)
    todos = accesos()
    todos.setdefault(esp, []).append({"nombre": nombre, "hash": hashlib.sha256(clave.encode()).hexdigest(), "creado": hoy()})
    escribir(ACCESOS, todos)
    dominio = (negocio().get("dominio") or "").rstrip("/")
    url = f"{dominio}/c/{esp}/?k={clave}" if dominio else f"/c/{esp}/?k={clave}"
    print(f"Enlace para {nombre} (guárdalo: no se puede volver a ver):\n  {url}")
    if not dominio:
        print('  Pon "dominio": "https://…" en datos/negocio.json para que salga la dirección completa.')
    print("  Funciona cuando se publique (git push).")


def revocar():
    """python backoffice.py revocar <espacio> "Nombre": quita sus enlaces."""
    if len(sys.argv) < 4:
        sys.exit('Uso: python backoffice.py revocar <espacio> "Nombre"')
    esp, nombre = sys.argv[2], sys.argv[3]
    todos = accesos()
    antes = len(todos.get(esp, []))
    todos[esp] = [a for a in todos.get(esp, []) if a["nombre"].lower() != nombre.lower()]
    if len(todos[esp]) == antes:
        sys.exit(f"{nombre} no tiene enlace a {esp}. Tienen: {', '.join(a['nombre'] for a in todos.get(esp, [])) or 'nadie'}")
    escribir(ACCESOS, todos)
    print(f"{nombre} ya no entra en {esp} en cuanto se publique (git push).")


def init():
    """python backoffice.py init: crea datos/ a partir de plantilla/ (no toca nada si ya existe)."""
    if (DATOS / "negocio.json").exists():
        sys.exit(f"Ya tienes datos en {DATOS}. No toco nada.")
    shutil.copytree(ROOT / "plantilla", DATOS, dirs_exist_ok=True)
    print(f"Creado {DATOS}. Ahora abre Claude Code en este repo y dile: «configura mi backoffice».")


def build(dest=DIST):
    """Copia la web y junta todos los datos en datos.json. Las facturas van con su PDF."""
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(WEB, dest)
    neg = negocio()
    datos = {
        "generado": dt.datetime.now().isoformat(timespec="minutes"),
        "negocio": {k: v for k, v in neg.items() if k != "notas"},
        "clientes": list(clientes().values()),
        "proyectos": [p | {"horas_resumen": horas_proyecto(p)} for p in proyectos().values()],
        "prevision": prevision(),
        "prevision_gastos": prevision_gastos(),
        "facturas": list(facturas().values()),
        "borradores": [vista_borrador(b) for b in borradores().values()],
        "gastos": list(gastos().values()),
        "categorias": CATEGORIAS,
        "tipos_iva": TIPOS_IVA,
        "trimestres": [calcular_trimestre(t) for t in trimestres_con_datos()],
        "problemas": problemas(),
        "pendientes": pendientes(neg),
        "espacios": [{k: v for k, v in e.items() if k != "markdown"} | {
            "accesos": [{"nombre": a["nombre"], "creado": a.get("creado")} for a in accesos().get(e["slug"], [])]}
            for e in espacios().values()],
    }
    datos["meses_zip"] = []
    for m in sorted({x["fecha"][:7] for x in datos["facturas"] + datos["gastos"]}):
        if zip_mes(m, dest / "meses" / f"gestoria-{m}.zip") or (dest / "meses" / f"gestoria-{m}.zip").exists():
            datos["meses_zip"].append(m)
    for t in datos["trimestres"]:
        t["archivos"] = sorted(f.name for f in (TRIMESTRES / t["trimestre"]).glob("*.*") if f.suffix in (".pdf", ".xlsx"))
    escribir(dest / "datos.json", datos)
    for pdf in FACTURAS.glob("*/*.pdf"):
        (dest / "pdf").mkdir(exist_ok=True)
        shutil.copy2(pdf, dest / "pdf" / pdf.name)
    for f in GASTOS.glob("*/*.*"):
        if f.suffix.lower() in EXTENSIONES:
            (dest / "gastos").mkdir(exist_ok=True)
            shutil.copy2(f, dest / "gastos" / f.name)
    for f in TRIMESTRES.glob("*/*.*"):
        if f.suffix in (".pdf", ".xlsx"):
            (dest / "trimestres").mkdir(exist_ok=True)
            shutil.copy2(f, dest / "trimestres" / f.name)
    print(f"dist/sitio/admin/ listo: {len(datos['clientes'])} clientes, {len(datos['proyectos'])} proyectos, "
          f"{len(datos['facturas'])} facturas, {len(datos['gastos'])} gastos")
    return dest


def servidor(directorio, puerto=0):
    import functools
    import http.server
    import threading

    class Silencioso(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Silencioso, directory=str(directorio))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", puerto), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def pdf_factura(numero=None):
    """Imprime factura.html con Chrome. Sin número, rehace todas."""
    numeros = [numero] if numero else list(facturas())
    tmp = build(ROOT / "dist" / "admin-pdf")
    server = servidor(tmp)
    try:
        for n in numeros:
            dest = ruta_factura(n).with_suffix(".pdf")
            args = [chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=10000",
                    f"--print-to-pdf={dest}", f"http://127.0.0.1:{server.server_address[1]}/factura.html?n={n}"]
            if sys.platform != "win32":
                args.insert(1, "--no-sandbox")
            subprocess.run(args, check=True, capture_output=True)
            print(f"  PDF {dest} ({dest.stat().st_size // 1024} KB)")
    finally:
        server.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


def pdf():
    pdf_factura(sys.argv[2] if len(sys.argv) > 2 else None)


def servir():
    import time
    import webbrowser

    puerto = int(sys.argv[2]) if len(sys.argv) > 2 else 8081
    build_sitio()
    servidor(SITIO, puerto)
    url = f"http://127.0.0.1:{puerto}/admin/"
    print(f"Admin en {url} (Ctrl+C para parar; vuelve a lanzarlo para ver cambios)")
    print(f"Los espacios, en http://127.0.0.1:{puerto}/c/<slug>/ (en local se abren sin clave)")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tareas = {"init": init, "build": build_sitio, "servir": servir, "enlace": enlace, "revocar": revocar, "revisar": revisar, "emitir": emitir, "cobrar": cobrar,
              "rectificar": rectificar, "pdf": pdf, "resumen": resumen, "gasto": registrar_gasto,
              "recurrentes": recurrentes, "trimestre": trimestre, "presentado": presentado,
              "banco": banco, "semana": semana, "mes": mes}
    tarea = tareas.get(sys.argv[1] if len(sys.argv) > 1 else "")
    if not tarea:
        print(__doc__)
    elif tarea is revisar:
        sys.exit(0 if revisar() else 1)
    else:
        tarea()
