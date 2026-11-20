"""Conectores: el correo del que salen los gastos y Melso.

Lo llama backoffice.py (python backoffice.py correo | melso). La conexión en sí la hace Claude Code
con sus conectores (Gmail, Microsoft 365, el MCP de Melso). Aquí está lo que tiene que ser exacto:
qué buscar, qué está ya apuntado y qué falta por mandar.
"""
import datetime as dt
import json
import sys

import backoffice as bo

REVISION = bo.GASTOS / "revision.json"
MELSO = bo.DATOS / "melso.json"


# ---- Correo ----

def remitentes():
    """Dominios de los que llegan facturas: los de los gastos fijos y los de gastos ya apuntados desde el correo."""
    dominios = set()
    for r in (bo.leer(bo.RECURRENTES) if bo.RECURRENTES.exists() else []):
        dominios.update(d.strip().lower() for d in r.get("remitentes", []) if d.strip())
    for g in bo.gastos().values():
        if g.get("remitente"):
            dominios.add(g["remitente"].lower())
    return sorted(dominios)


def busqueda(dias=45):
    """La búsqueda de Gmail para las facturas recientes."""
    neg = bo.negocio()
    # Lo de los remitentes conocidos y el buzón de facturas vale aunque no diga «factura»;
    # del resto, solo lo que lo parece. Así entran también los proveedores de una sola vez.
    partes = []
    if remitentes():
        partes.append("from:(" + " OR ".join(remitentes()) + ")")
    if neg.get("email_gastos"):
        partes.append(f"to:{neg['email_gastos']}")
    if neg.get("etiqueta_gastos"):
        partes.append(f"label:{neg['etiqueta_gastos']}")
    partes.append("factura OR invoice OR recibo OR receipt")
    q = "(" + " OR ".join(f"({p})" if " " in p else p for p in partes) + f") has:attachment newer_than:{dias}d"
    if neg.get("alta") and not bo.pendiente(neg["alta"]):
        q += f" after:{neg['alta'].replace('-', '/')}"
    for no in neg.get("no_apuntar", []):
        q += f" -from:{no}" if "." in no else ""
    return q


def correo():
    """python backoffice.py correo [hecho | días]: qué buscar en el correo, y apuntar que ya se ha revisado."""
    args = sys.argv[2:]
    if args and args[0] == "hecho":
        bo.escribir(REVISION, {"ultima": bo.hoy()})
        print(f"Apuntado: correo revisado el {bo.hoy()}.")
        return
    neg = bo.negocio()
    dias = int(args[0]) if args and args[0].isdigit() else 45
    ultima = bo.leer(REVISION).get("ultima") if REVISION.exists() else None
    ids = sorted({g["gmail_id"] for g in bo.gastos().values() if g.get("gmail_id")})
    print(json.dumps({
        "origen": neg.get("correo_gastos", "sin configurar"),
        "busqueda_gmail": busqueda(dias),
        "remitentes": remitentes(),
        "no_apuntar": neg.get("no_apuntar", []),
        "ultima_revision": ultima,
        "ya_apuntados": ids,
        "bandeja": [f.name for f in sorted(bo.BANDEJA.glob("*")) if f.suffix.lower() in bo.EXTENSIONES] if bo.BANDEJA.exists() else [],
    }, ensure_ascii=False, indent=2))


def aviso_correo(neg):
    """Para "Lo que falta": si el correo está configurado y hace tiempo que no se revisa."""
    if neg.get("correo_gastos") in (None, "", "no"):
        return None
    ultima = bo.leer(REVISION).get("ultima") if REVISION.exists() else None
    cada = int(neg.get("revisar_correo_dias", 14))
    dias = (dt.date.today() - dt.date.fromisoformat(ultima)).days if ultima else None
    if dias is None or dias >= cada:
        texto = (f"Hace {dias} días que no buscas facturas en el correo." if dias is not None
                 else "Todavía no has buscado facturas en el correo.")
        return {"texto": texto, "pide": "revisa los gastos del correo"}
    return None


# ---- Melso ----
#
# Melso (https://melso.ai) es una gestoría online con un servidor MCP (https://mcp.melso.ai/mcp, con
# OAuth). Si la persona lleva sus impuestos con Melso, Claude Code le manda desde aquí las facturas
# emitidas y los gastos con su PDF. Lo que ya se ha mandado se guarda en datos/melso.json, aparte,
# porque una factura emitida no se toca.
#
# datos/melso.json: {"desde": "AAAA-MM-DD", "facturas": {numero: {id, fecha}}, "gastos": {id: {id, fecha}}}

def estado_melso():
    return bo.leer(MELSO) if MELSO.exists() else None


def pendientes_melso():
    m = estado_melso()
    if not m:
        return None
    desde = m.get("desde", "0000")
    facturas = [
        {"numero": n, "fecha": f["fecha"], "tipo": f.get("tipo"), "rectifica": f.get("rectifica"),
         "cliente": f["receptor"].get("razon_social"), "nif_cliente": f["receptor"].get("nif"),
         "pais_cliente": f["receptor"].get("pais"), "base": f["base"], "iva_pct": f["iva_pct"], "iva": f["iva"],
         "irpf_pct": f["irpf_pct"], "irpf": f["irpf"], "total": f["total"], "estado": f["estado"],
         "cobrada": f.get("cobrada"), "pdf": str(bo.ruta_factura(n).with_suffix(".pdf"))}
        for n, f in bo.facturas().items() if f["fecha"] >= desde and n not in m.get("facturas", {})]
    gastos = [
        {"id": gid, "fecha": g["fecha"], "proveedor": g["proveedor"], "nif_proveedor": g.get("nif_proveedor"),
         "pais": g.get("pais"), "numero_factura": g.get("numero_factura"), "concepto": g["concepto"],
         "categoria": g["categoria"], "tipo_iva": g["tipo_iva"], "base": g["base"], "iva_pct": g.get("iva_pct"),
         "iva": g.get("iva"), "total": g.get("total"), "afectacion": g.get("afectacion", 100),
         "archivo": str(bo.GASTOS / gid[:4] / g["archivo"]) if g.get("archivo") else None,
         "sin_factura": bool(g.get("sin_factura"))}
        for gid, g in bo.gastos().items()
        if g["fecha"] >= desde and gid not in m.get("gastos", {}) and (g.get("archivo") or g.get("sin_factura"))]
    # Cobros: facturas ya mandadas que se han cobrado después
    cobros = [{"numero": n, "melso_id": m["facturas"][n]["id"], "cobrada": f["cobrada"]}
              for n, f in bo.facturas().items()
              if n in m.get("facturas", {}) and f.get("cobrada") and not m["facturas"][n].get("cobrada")]
    return {"facturas": facturas, "gastos": gastos, "cobros": cobros}


def melso():
    """python backoffice.py melso <empezar AAAA-MM-DD | pendiente | apuntar factura|gasto|cobro <id> <id_melso>>"""
    args = sys.argv[2:]
    orden = args[0] if args else "pendiente"
    if orden == "empezar":
        if len(args) < 2:
            sys.exit("Uso: python backoffice.py melso empezar AAAA-MM-DD (desde qué fecha lleva Melso tus impuestos)")
        bo.fecha(args[1], "la fecha")
        m = estado_melso() or {"facturas": {}, "gastos": {}}
        m["desde"] = args[1]
        bo.escribir(MELSO, m)
        print(f"Melso: se mandará lo que sea del {args[1]} en adelante.")
    elif orden == "pendiente":
        p = pendientes_melso()
        if p is None:
            sys.exit("Melso no está configurado. Empieza con: python backoffice.py melso empezar AAAA-MM-DD")
        print(json.dumps(p, ensure_ascii=False, indent=2))
    elif orden == "apuntar":
        if len(args) < 4 or args[1] not in ("factura", "gasto", "cobro"):
            sys.exit("Uso: python backoffice.py melso apuntar factura|gasto|cobro <número o id> <id en Melso>")
        m = estado_melso()
        if m is None:
            sys.exit("Melso no está configurado.")
        tipo, local, remoto = args[1:4]
        if tipo == "cobro":
            if local not in m.get("facturas", {}):
                sys.exit(f"La {local} no se ha mandado a Melso todavía.")
            m["facturas"][local]["cobrada"] = bo.hoy()
        else:
            existe = local in (bo.facturas() if tipo == "factura" else bo.gastos())
            if not existe:
                sys.exit(f"No existe {'la factura' if tipo == 'factura' else 'el gasto'} {local}")
            m.setdefault(tipo + "s", {})[local] = {"id": remoto, "fecha": bo.hoy()}
        bo.escribir(MELSO, m)
        print(f"Apuntado en datos/melso.json: {tipo} {local} → {remoto}")
    else:
        sys.exit(melso.__doc__)


def aviso_melso():
    p = pendientes_melso()
    if not p:
        return None
    n = len(p["facturas"]) + len(p["gastos"]) + len(p["cobros"])
    return {"texto": f"Hay {n} cosas por mandar a Melso.", "pide": "manda lo pendiente a Melso"} if n else None
