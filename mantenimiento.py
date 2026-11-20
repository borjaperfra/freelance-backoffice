"""Mantenimiento del backoffice: actualizar el código, migrar los datos, copias, doctor y Cloudflare.

Lo llama backoffice.py (python backoffice.py actualizar | migrar | copia | restaurar | doctor | cloudflare).
Solo biblioteca estándar.
"""
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

import backoffice as bo

UPSTREAM = os.environ.get("BACKOFFICE_UPSTREAM", "https://github.com/borjaperfra/freelance-backoffice.git")
LOCAL = bo.ROOT / ".backoffice.local.json"   # ajustes de este ordenador (fuera de git)


# ---- Utilidades ----

def git(*args, binario=False, check=True):
    r = subprocess.run(["git", *args], cwd=bo.ROOT, capture_output=True, check=False)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} ha fallado:\n{r.stderr.decode(errors='replace').strip()}")
    return r.stdout if binario else r.stdout.decode("utf-8", errors="replace")


def gh(*args, entrada=None):
    """(código, salida) de un comando de gh. (127, '') si gh no está instalado."""
    if not shutil.which("gh"):
        return 127, ""
    r = subprocess.run(["gh", *args], cwd=bo.ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", input=entrada, timeout=60)
    return r.returncode, (r.stdout + r.stderr).strip()


def ajustes_locales():
    return bo.leer(LOCAL) if LOCAL.exists() else {}


def guardar_ajuste(clave, valor):
    a = ajustes_locales()
    a[clave] = valor
    bo.escribir(LOCAL, a)


def igual(a, b):
    """Mismo contenido, sin contar los saltos de línea de Windows."""
    crlf, lf = bytes([13, 10]), bytes([10])
    return a == b or a.replace(crlf, lf) == b.replace(crlf, lf)


def version_de(texto):
    m = re.search(r'^VERSION = "([^"]+)"', texto, re.M)
    return m.group(1) if m else None


# ---- Migraciones de datos ----
#
# Cada migración lleva los datos de la versión n-1 a la n. Se añaden al final y no se tocan nunca:
# hay gente con datos en cualquier versión anterior. La versión está en datos/negocio.json ("version").

def migracion_1():
    """v0.1 → v0.2: los datos pasan a llevar versión. Las variables de Access salen de wrangler.toml."""
    # actualizar ya ha pisado wrangler.toml con el nuevo, pero el del último commit sigue siendo el suyo.
    toml = git("show", "HEAD:wrangler.toml", check=False) if (bo.ROOT / ".git").exists() else ""
    if (bo.ROOT / "wrangler.toml").exists():
        toml += "\n" + (bo.ROOT / "wrangler.toml").read_text(encoding="utf-8")
    valores = dict(re.findall(r'^(ACCESS_TEAM|ACCESS_AUD|ADMIN_EMAIL)\s*=\s*"([^"]+)"', toml, re.M))
    if valores:
        print("  Tus variables de Access estaban en wrangler.toml. Ahora van en GitHub (Settings → Variables):")
        for k, v in valores.items():
            codigo, _ = gh("variable", "set", k, "--body", v)
            print(f"    {k}: {'guardada en GitHub' if codigo == 0 else 'ponla a mano en GitHub, gh no ha podido'}")


MIGRACIONES = {1: migracion_1}


def migrar():
    """python backoffice.py migrar: pone los datos al día con la versión del código."""
    if not (bo.DATOS / "negocio.json").exists():
        sys.exit("No hay datos que migrar. Empieza con: python backoffice.py init")
    neg = bo.negocio()
    v = int(neg.get("version", 0))
    if v > bo.DATOS_VERSION:
        sys.exit(f"Tus datos son de una versión más nueva ({v}) que este código ({bo.DATOS_VERSION}). "
                 "Actualiza el código: python backoffice.py actualizar")
    if v == bo.DATOS_VERSION:
        print(f"Datos al día (versión {v})")
        return
    for n in range(v + 1, bo.DATOS_VERSION + 1):
        print(f"Migrando los datos a la versión {n}…")
        MIGRACIONES[n]()
        neg = bo.negocio()
        neg["version"] = n
        bo.escribir(bo.DATOS / "negocio.json", neg)
    print(f"Datos en la versión {bo.DATOS_VERSION}. Revisa con git diff y haz commit.")


# ---- Actualizar el código ----
#
# El repo de cada persona nace de la plantilla con "Use this template", sin historia común con el
# original. Por eso no se hace merge: se trae el árbol de la última versión publicada y se copia
# encima, archivo a archivo, sin tocar nunca datos/. Si la persona había cambiado algún archivo del
# código, se guarda una copia en .actualizar/ antes de pisarlo.

def es_suyo(ruta):
    """Archivos que son de la persona y nunca se tocan al actualizar."""
    return ruta.startswith(("datos/", "bandeja/", ".actualizar/")) or ruta in (".backoffice.local.json",)


def actualizar():
    """python backoffice.py actualizar [--comprobar]: trae la última versión del código."""
    solo_mirar = "--comprobar" in sys.argv
    if not (bo.ROOT / ".git").exists():
        sys.exit("Esto no es un repo de git. Actualizar necesita git.")
    sucio = [l for l in git("status", "--porcelain").splitlines() if not es_suyo(l[3:].strip('"'))]
    if sucio and not solo_mirar:
        sys.exit("Tienes cambios sin guardar en el código:\n  " + "\n  ".join(sucio) +
                 "\nHaz commit o descártalos antes de actualizar.")

    print(f"Buscando la última versión en {UPSTREAM}…")
    r = subprocess.run(["git", "fetch", "--quiet", "--no-tags", UPSTREAM,
                        "+refs/heads/main:refs/remotes/upstream/main", "+refs/tags/*:refs/tags/upstream/*"],
                       cwd=bo.ROOT, capture_output=True)
    if r.returncode:
        sys.exit("No llego al repo original. Mira tu conexión; si sigue fallando, puede que el repo se haya movido "
                 "(pon su dirección en la variable BACKOFFICE_UPSTREAM).\n"
                 f"git dice: {r.stderr.decode(errors='replace').strip()}")
    nueva_ref = "refs/remotes/upstream/main"
    nueva = version_de(git("show", f"{nueva_ref}:backoffice.py"))
    numeros = lambda v: tuple(int(x) for x in re.findall(r"\d+", v or "0"))
    if numeros(nueva) <= numeros(bo.VERSION):
        print(f"Ya tienes la última versión ({bo.VERSION}).")
        return
    print(f"Tienes la {bo.VERSION}; hay una nueva: {nueva}.")
    notas = cambios_de(git("show", f"{nueva_ref}:CHANGELOG.md", check=False), nueva)
    if notas:
        print("\n" + notas + "\n")
    if solo_mirar:
        print("Para instalarla: python backoffice.py actualizar")
        return

    vieja_ref = f"refs/tags/upstream/v{bo.VERSION}"
    hay_vieja = bool(git("rev-parse", "--verify", "--quiet", vieja_ref, check=False).strip())
    nuevos = {p for p in git("ls-tree", "-r", "--name-only", nueva_ref).splitlines() if not es_suyo(p)}
    viejos = {p for p in git("ls-tree", "-r", "--name-only", vieja_ref).splitlines() if not es_suyo(p)} if hay_vieja else set()

    respaldo = bo.ROOT / ".actualizar" / dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    tocados, respaldados = [], []

    def respaldar(p):
        destino = respaldo / p
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bo.ROOT / p, destino)
        respaldados.append(p)

    for p in sorted(nuevos):
        contenido = git("show", f"{nueva_ref}:{p}", binario=True)
        local = bo.ROOT / p
        if local.exists():
            actual = local.read_bytes()
            if igual(actual, contenido):
                continue
            # ¿Lo había cambiado la persona? Si conocemos la versión de la que viene, se compara con ella.
            if p not in viejos or not igual(actual, git("show", f"{vieja_ref}:{p}", binario=True)):
                respaldar(p)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(contenido)
        tocados.append(p)
    for p in sorted(viejos - nuevos):
        local = bo.ROOT / p
        if local.exists() and igual(local.read_bytes(), git("show", f"{vieja_ref}:{p}", binario=True)):
            local.unlink()
            tocados.append(p)

    if tocados:
        git("add", "-A", "--", *tocados)
    print(f"Actualizado a la {nueva}: {len(tocados)} archivos.")
    if respaldados and hay_vieja:
        print(f"  Habías cambiado {'un archivo' if len(respaldados) == 1 else str(len(respaldados)) + ' archivos'} del código. "
              f"Tu versión está en {respaldo.relative_to(bo.ROOT)}:")
        for p in respaldados:
            print(f"    {p}")
    elif respaldados:
        print(f"  Copia de los archivos anteriores en {respaldo.relative_to(bo.ROOT)} (por si habías cambiado alguno).")

    # Con el código nuevo: migrar y revisar
    sys.stdout.flush()
    py = sys.executable
    subprocess.run([py, "backoffice.py", "migrar"], cwd=bo.ROOT)
    ok = subprocess.run([py, "backoffice.py", "revisar"], cwd=bo.ROOT).returncode == 0
    print("\nPara terminar:")
    print(f'  git add -A && git commit -m "Actualizado a la {nueva}" && git push')
    if any(p.startswith(".github/workflows/") for p in tocados):
        print("  Ojo: cambia el workflow. Si git push falla por permisos, mira docs/problemas.md («workflow scope»).")
    if not ok:
        print("  Antes, arregla lo que ha salido en revisar.")


def cambios_de(changelog, version):
    """La sección de CHANGELOG.md de una versión."""
    m = re.search(rf"^## {re.escape(version or '')}\b.*?(?=^## |\Z)", changelog or "", re.M | re.S)
    return m.group(0).strip() if m else ""


# ---- Copias ----

def copia():
    """python backoffice.py copia [carpeta]: un ZIP con todos tus datos, fuera del repo."""
    if not (bo.DATOS / "negocio.json").exists():
        sys.exit("No hay datos que copiar.")
    carpeta = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("BACKOFFICE_COPIAS") or ajustes_locales().get("copias")
    if not carpeta:
        sys.exit("¿Dónde guardo la copia? Dime una carpeta fuera del repo (Google Drive, Dropbox, un disco):\n"
                 "  python backoffice.py copia \"C:/Users/tu/Google Drive/backoffice\"\n"
                 "La recuerdo para las próximas veces.")
    carpeta = pathlib.Path(carpeta).expanduser().resolve()
    if carpeta == bo.ROOT or bo.ROOT in carpeta.parents:
        sys.exit("La copia tiene que ir fuera del repo: si pierdes el repo, la pierdes con él.")
    carpeta.mkdir(parents=True, exist_ok=True)
    guardar_ajuste("copias", str(carpeta))

    hoy = bo.hoy()
    destino = carpeta / f"backoffice-{hoy}.zip"
    archivos = [f for f in bo.DATOS.rglob("*") if f.is_file()]
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for f in archivos:
            z.write(f, f.relative_to(bo.DATOS).as_posix())
    with zipfile.ZipFile(destino) as z:
        if z.testzip() is not None or len(z.namelist()) != len(archivos):
            sys.exit(f"La copia {destino} no ha salido bien. Vuelve a intentarlo.")
    bo.escribir(bo.DATOS / "copias.json", {"ultima": hoy, "archivos": len(archivos)})
    print(f"Copia en {destino}: {len(archivos)} archivos, {destino.stat().st_size // 1024} KB.")
    print("  Haz commit de datos/copias.json para que el admin sepa cuándo fue la última.")


def restaurar():
    """python backoffice.py restaurar <copia.zip>: recupera datos/ desde una copia."""
    if len(sys.argv) < 3:
        sys.exit("Uso: python backoffice.py restaurar <backoffice-AAAA-MM-DD.zip>")
    origen = pathlib.Path(sys.argv[2])
    if not origen.exists():
        sys.exit(f"No encuentro {origen}")
    # Primero se comprueba y se descomprime aparte; datos/ no se toca hasta que la copia está bien.
    try:
        with zipfile.ZipFile(origen) as z:
            nombres = z.namelist()
            for n in nombres:
                if n.startswith(("/", "\\")) or ".." in pathlib.PurePosixPath(n.replace("\\", "/")).parts or ":" in n:
                    sys.exit(f"La copia tiene una ruta rara ({n}). No la abro.")
            if "negocio.json" not in nombres:
                sys.exit(f"{origen.name} no parece una copia del backoffice (no lleva negocio.json).")
            if z.testzip() is not None:
                sys.exit(f"{origen.name} está dañado. Prueba con otra copia.")
            nuevo = bo.DATOS.with_name(f"{bo.DATOS.name}-restaurando")
            shutil.rmtree(nuevo, ignore_errors=True)
            z.extractall(nuevo)
    except zipfile.BadZipFile:
        sys.exit(f"{origen.name} no es un ZIP válido.")
    if bo.DATOS.exists():
        aparte = bo.DATOS.with_name(f"{bo.DATOS.name}-antes-de-restaurar-{dt.datetime.now():%Y%m%d-%H%M%S}")
        bo.DATOS.rename(aparte)
        print(f"  Tus datos actuales quedan en {aparte.name}/ por si acaso.")
    nuevo.rename(bo.DATOS)
    print(f"Datos recuperados de {origen.name}.", flush=True)
    subprocess.run([sys.executable, "backoffice.py", "revisar"], cwd=bo.ROOT)


# ---- Doctor ----

def doctor():
    """python backoffice.py doctor: comprueba que todo está en su sitio y dice cómo arreglar lo que no."""
    filas = []

    def fila(ok, texto, arreglo=""):
        filas.append((ok, texto, arreglo))

    v = sys.version_info
    fila(v >= (3, 10), f"Python {v.major}.{v.minor}", "Instala Python 3.10 o superior: https://www.python.org/downloads/")
    fila(bool(shutil.which("git")), "git", "Instala git: https://git-scm.com/downloads")
    fila(bo.buscar_chrome() is not None,"Chrome (para los PDF de las facturas)", "Instala Google Chrome, o pon su ruta en la variable CHROME")

    # Datos
    if not (bo.DATOS / "negocio.json").exists():
        fila(False, "Tus datos", "python backoffice.py init, y luego dile a Claude Code «configura mi backoffice»")
    else:
        neg = bo.negocio()
        faltan = [k for k in ("nombre", "nif", "direccion", "cp", "ciudad", "email", "iban") if bo.pendiente(neg.get(k))]
        fila(not faltan, "Datos fiscales completos" + (f" (faltan: {', '.join(faltan)})" if faltan else ""),
             "Dile a Claude Code tus datos que faltan")
        ver = int(neg.get("version", 0))
        fila(ver == bo.DATOS_VERSION, f"Versión de los datos ({ver})", "python backoffice.py migrar")
        errores = bo.problemas()
        fila(not errores, "Los datos cuadran" + (f" ({len(errores)} problemas)" if errores else ""), "python backoffice.py revisar")
        ultima = (bo.leer(bo.DATOS / "copias.json") if (bo.DATOS / "copias.json").exists() else {}).get("ultima")
        dias = (dt.date.today() - dt.date.fromisoformat(ultima)).days if ultima else None
        fila(dias is not None and dias <= 35,
             f"Copia de seguridad ({'hace ' + str(dias) + ' días' if dias is not None else 'ninguna todavía'})",
             "python backoffice.py copia <carpeta fuera del repo>")

    # GitHub
    neg = bo.negocio() if (bo.DATOS / "negocio.json").exists() else {}
    publica = bool(neg.get("dominio"))
    codigo, salida = gh("auth", "status")
    repo = {}
    if codigo == 127:
        fila(None, "gh (GitHub CLI): no está instalado; no puedo mirar GitHub", "https://cli.github.com")
    elif codigo != 0:
        fila(False, "Sesión de GitHub en gh", "gh auth login")
    else:
        codigo, salida = gh("repo", "view", "--json", "visibility,nameWithOwner")
        repo = json.loads(salida) if codigo == 0 and salida.startswith("{") else {}
        if not repo:
            fila(False, "Repo en GitHub (esta carpeta no está conectada a ninguno)",
                 "Crea tu repo con «Use this template», márcalo como privado y clónalo")
    if repo:
        fila(repo.get("visibility") == "PRIVATE", f"Repo privado ({repo['nameWithOwner']}: {repo.get('visibility', '?').lower()})",
             "GitHub → Settings → General → Danger Zone → Change visibility → Private. Hazlo antes de subir datos.")
        # Sin dominio, lo de Cloudflare es opcional: se avisa, pero no cuenta como fallo.
        grave = False if publica else None
        _, secretos = gh("secret", "list")
        faltan = [s for s in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID") if s not in secretos]
        fila(grave if faltan else True, "Secretos de Cloudflare en GitHub" + (f" (faltan: {', '.join(faltan)})" if faltan else ""),
             "python backoffice.py cloudflare (o docs/instalar.md, paso a paso)")
        _, variables = gh("variable", "list")
        faltan = [s for s in ("ACCESS_TEAM", "ACCESS_AUD", "ADMIN_EMAIL") if s not in variables]
        fila(grave if faltan else True, "Variables de Access en GitHub" + (f" (faltan: {', '.join(faltan)})" if faltan else ""),
             "python backoffice.py cloudflare. Mientras falten, /admin/ responde 403")
        codigo, salida = gh("run", "list", "--workflow", "publicar.yml", "--limit", "1", "--json", "conclusion,status,createdAt")
        runs = json.loads(salida) if codigo == 0 and salida.startswith("[") else []
        if runs:
            r = runs[0]
            fila(r.get("conclusion") == "success" or r.get("status") != "completed",
                 f"Última publicación: {r.get('conclusion') or r.get('status')} ({r.get('createdAt', '')[:10]})",
                 "gh run view --log-failed, o mira la pestaña Actions")
        codigo, prot = gh("api", f"repos/{repo['nameWithOwner']}/branches/main/protection")
        try:
            prot = json.loads(prot) if codigo == 0 else {}
        except json.JSONDecodeError:
            prot = {}
        if prot and prot.get("allow_force_pushes", {}).get("enabled") is False:
            fila(True, "main protegida contra force-push")
        else:
            fila(None, "main sin proteger. Con GitHub Pro: python backoffice.py proteger. "
                       "Sin él, .claude/settings.json ya bloquea el force-push de Claude Code")

    # Web publicada
    dominio = (neg.get("dominio") or "").rstrip("/")
    if dominio:
        estado, destino = sin_redirigir(f"{dominio}/admin/")
        if estado is None:
            fila(False, f"{dominio} no responde", "Mira en Cloudflare que el dominio esté en el proyecto de Pages y tenga su DNS")
        else:
            protegido = estado == 403 or (estado in (301, 302, 303, 307) and "cloudflareaccess.com" in destino)
            fila(protegido, f"{dominio}/admin/ pide login ({estado})",
                 "Revisa la aplicación de Access en Cloudflare Zero Trust (docs/instalar.md, paso 4)")
        # La dirección *.pages.dev (Access no la cubre: la cierra el middleware). La guarda "cloudflare".
        if neg.get("pages_dev"):
            estado, _ = sin_redirigir(f"https://{neg['pages_dev']}/admin/")
            if estado is None:
                fila(None, f"{neg['pages_dev']} no responde (aún no se ha publicado)")
            else:
                fila(estado == 403, f"{neg['pages_dev']}/admin/ cerrado ({estado})", "Revisa ACCESS_AUD y ADMIN_EMAIL en GitHub → Variables")
    else:
        fila(None, "Sin publicar todavía (no hay dominio en negocio.json)", "Cuando quieras: python backoffice.py cloudflare")

    # Versión del código
    if shutil.which("git") and (bo.ROOT / ".git").exists():
        r = subprocess.run(["git", "ls-remote", UPSTREAM, "refs/heads/main"], cwd=bo.ROOT, capture_output=True, text=True, timeout=30)
        fila(None if r.returncode else True, f"Código en la versión {bo.VERSION}",
             "python backoffice.py actualizar --comprobar para ver si hay una nueva")

    malos = 0
    for ok, texto, arreglo in filas:
        marca = {True: "✓", False: "✗", None: "·"}[ok]
        print(f"  {marca} {texto}")
        if ok is False:
            malos += 1
            print(f"      → {arreglo}")
    print("\nTodo en orden." if not malos else "\n1 cosa por arreglar." if malos == 1 else f"\n{malos} cosas por arreglar.")
    return malos == 0


class SinRedirigir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def sin_redirigir(url):
    """(código HTTP, Location) sin seguir redirecciones. (None, '') si no responde."""
    try:
        r = urllib.request.build_opener(SinRedirigir).open(urllib.request.Request(url, method="GET"), timeout=15)
        return r.status, r.headers.get("location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("location", "")
    except OSError:
        return None, ""


def proteger():
    """python backoffice.py proteger: protege main contra force-push y borrado (GitHub Pro en repos privados)."""
    codigo, salida = gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
    if codigo:
        sys.exit("No puedo leer el repo con gh. ¿Has hecho gh auth login?")
    cuerpo = json.dumps({"required_status_checks": None, "enforce_admins": False, "required_pull_request_reviews": None,
                         "restrictions": None, "allow_force_pushes": False, "allow_deletions": False})
    codigo, salida = gh("api", "-X", "PUT", f"repos/{salida}/branches/main/protection", "--input", "-", entrada=cuerpo)
    if codigo:
        if "Upgrade" in salida or "403" in salida:
            sys.exit("GitHub no deja proteger ramas en repos privados con el plan gratuito. "
                     "Las reglas de .claude/settings.json ya impiden que Claude Code haga force-push.")
        sys.exit(f"No he podido: {salida}")
    print("main protegida: no se puede reescribir la historia ni borrar la rama.")


# ---- Cloudflare: publicar en un paso ----
#
# Hace con la API de Cloudflare lo que docs/instalar.md cuenta a mano: el proyecto de Pages, el dominio,
# el registro DNS y la aplicación de Access del admin. Luego guarda en GitHub los secretos y las
# variables. El token se pide aquí, en la terminal; no pasa por el chat ni se guarda en el repo.

API = "https://api.cloudflare.com/client/v4"


class Cloudflare:
    def __init__(self, token):
        self.token = token

    def __call__(self, metodo, ruta, cuerpo=None, permitir=()):
        req = urllib.request.Request(API + ruta, method=metodo, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                datos = json.loads(e.read() or b"{}")
            except ValueError:
                datos = {}
            if e.code in permitir:
                return datos | {"_codigo": e.code}
            errores = "; ".join(f"{x.get('code')}: {x.get('message')}" for x in datos.get("errors", [])) or str(e)
            raise SystemExit(f"Cloudflare ha dicho que no ({metodo} {ruta}): {errores}\n"
                             "Mira que el token tenga los permisos de docs/instalar.md.")
        except OSError as e:
            raise SystemExit(f"No llego a Cloudflare ({e}). Mira tu conexión y vuelve a lanzarlo.")


def leer_token(pregunta, otro_igual=""):
    """Lee un token del portapapeles (copias y pulsas Enter) y lo borra de allí. Si no se puede, lo pide oculto.

    Pegar en una entrada oculta falla en algunas terminales de Windows; leer el portapapeles, no.
    otro_igual: un token ya leído; si el portapapeles sigue vacío o igual, se usa ese.
    """
    try:
        import tkinter
        raiz = tkinter.Tk()
        raiz.withdraw()
    except Exception:
        raiz = None
    if raiz is not None:
        try:
            if otro_igual:
                input(f"{pregunta}\n  Copia el otro token y pulsa Enter (o pulsa Enter sin copiar nada para usar el mismo): ")
            else:
                input(f"{pregunta}\n  Copia el token (botón de copiar de Cloudflare) y pulsa Enter aquí: ")
            try:
                leido = raiz.clipboard_get().strip()
            except tkinter.TclError:
                leido = ""
            if leido and leido != otro_igual:
                raiz.clipboard_clear()   # que no se quede en el portapapeles
                raiz.update()
                print(f"  Leído del portapapeles ({len(leido)} caracteres) y borrado de allí.")
                return leido
            if otro_igual:
                print("  Uso el mismo token.")
                return ""
            print("  El portapapeles está vacío. Pégalo aquí (no se verá):")
        finally:
            raiz.destroy()
    import getpass
    return getpass.getpass(f"{pregunta} ").strip()


def revisar_token(token):
    """Antes de llamar a Cloudflare: que lo leído parezca un token. Dice cuánto ha leído, nunca qué."""
    raro = [c for c in token if not (c.isascii() and (c.isalnum() or c in "-_."))]
    if not token or len(token) < 30 or raro:
        motivo = ("no he leído nada" if not token else
                  f"he leído {len(token)} caracteres y {'hay caracteres que no son de un token' if raro else 'un token tiene unos 40 o más'}")
        sys.exit(f"El token no se ha leído bien: {motivo}.\n"
                 "Vuelve a lanzarlo y pega con clic derecho o Ctrl+Shift+V. "
                 "O ponlo antes en la variable CLOUDFLARE_API_TOKEN de esa terminal.")


def cloudflare():
    """python backoffice.py cloudflare [--cuenta <id>] [--proyecto <nombre>]: publica en Cloudflare en un paso."""
    import getpass
    from urllib.parse import urlparse

    neg = bo.negocio()
    dominio = (neg.get("dominio") or "").rstrip("/")
    if not dominio.startswith("https://"):
        sys.exit('Primero pon tu dominio en datos/negocio.json: "dominio": "https://backoffice.tudominio.com"')
    host = urlparse(dominio).hostname
    emails = [e.strip() for e in (os.environ.get("ADMIN_EMAIL") or neg.get("email") or "").split(",") if e.strip()]
    if not emails or bo.pendiente(emails[0]):
        sys.exit("Necesito tu email (el de negocio.json o ADMIN_EMAIL) para dejarte entrar al admin.")
    args = sys.argv[2:]
    opcion = lambda n, d=None: args[args.index(n) + 1] if n in args and args.index(n) + 1 < len(args) else d
    proyecto = opcion("--proyecto", "freelance-backoffice")

    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        if not sys.stdin.isatty():
            sys.exit("Ejecuta este comando tú, en una terminal: python backoffice.py cloudflare\n"
                     "Te pedirá el token de Cloudflare sin que pase por el chat.")
        token = leer_token("Token de Cloudflare.")
    revisar_token(token)
    cf = Cloudflare(token)
    if cf("GET", "/user/tokens/verify", permitir=(400,)).get("_codigo") == 400:
        sys.exit("Cloudflare no reconoce lo que he leído como un token. Cópialo otra vez entero desde Cloudflare y vuelve a lanzarlo.")
    if cf("GET", "/user/tokens/verify").get("result", {}).get("status") != "active":
        sys.exit("El token no está activo (¿caducado o desactivado?).")

    cuentas = cf("GET", "/accounts")["result"]
    cuenta = opcion("--cuenta") or (cuentas[0]["id"] if len(cuentas) == 1 else None)
    if not cuenta:
        sys.exit("Tienes varias cuentas de Cloudflare. Elige una con --cuenta <id>:\n" +
                 "\n".join(f"  {c['id']}  {c['name']}" for c in cuentas))
    a = f"/accounts/{cuenta}"
    print(f"Cuenta: {next((c['name'] for c in cuentas if c['id'] == cuenta), cuenta)}")

    # 1. Proyecto de Pages. Si el nombre está cogido en pages.dev, Cloudflare le añade un sufijo: se usa el suyo.
    r = cf("GET", f"{a}/pages/projects/{proyecto}", permitir=(404,))
    if r.get("_codigo") == 404:
        r = cf("POST", f"{a}/pages/projects", {"name": proyecto, "production_branch": "main"})
        print(f"  ✓ Proyecto de Pages {proyecto} creado")
    else:
        print(f"  ✓ Proyecto de Pages {proyecto} (ya existía)")
    pages_dev = r["result"].get("subdomain") or f"{proyecto}.pages.dev"
    if neg.get("pages_dev") != pages_dev:
        neg["pages_dev"] = pages_dev
        bo.escribir(bo.DATOS / "negocio.json", neg)

    # 2. Dominio en el proyecto
    dominios = [d["name"] for d in cf("GET", f"{a}/pages/projects/{proyecto}/domains")["result"]]
    if host not in dominios:
        cf("POST", f"{a}/pages/projects/{proyecto}/domains", {"name": host})
    print(f"  ✓ {host} en el proyecto")

    # 3. DNS, si la zona está en esta cuenta
    partes = host.split(".")
    zona = None
    for i in range(len(partes) - 1):
        r = cf("GET", f"/zones?name={'.'.join(partes[i:])}&account.id={cuenta}")["result"]
        if r:
            zona = r[0]
            break
    if zona:
        if not cf("GET", f"/zones/{zona['id']}/dns_records?name={host}")["result"]:
            cf("POST", f"/zones/{zona['id']}/dns_records",
               {"type": "CNAME", "name": host, "content": pages_dev, "proxied": True})
            print(f"  ✓ DNS: {host} → {pages_dev}")
        else:
            print(f"  ✓ DNS: {host} ya tenía un registro (no lo toco)")
    else:
        print(f"  · {host} no está en esta cuenta de Cloudflare. Crea en tu DNS un CNAME {host} → {pages_dev}")

    # 4. Cloudflare Access sobre /admin
    org = cf("GET", f"{a}/access/organizations", permitir=(400, 403, 404))
    if org.get("_codigo") or not org.get("result", {}).get("auth_domain"):
        sys.exit("\nFalta activar Zero Trust (una vez, a mano): Cloudflare → Zero Trust → elige un nombre de equipo "
                 "y el plan Free. Luego vuelve a lanzar este comando: lo que ya está hecho no se repite.")
    equipo = org["result"]["auth_domain"].removesuffix(".cloudflareaccess.com")
    destino = f"{host}/admin"
    apps = cf("GET", f"{a}/access/apps")["result"]
    app = next((x for x in apps if x.get("domain") == destino), None)
    if not app:
        regla = {"name": "Solo yo", "decision": "allow", "include": [{"email": {"email": e}} for e in emails]}
        app = cf("POST", f"{a}/access/apps", {"name": "Freelance Backoffice", "domain": destino, "type": "self_hosted",
                                              "session_duration": "24h", "app_launcher_visible": False,
                                              "policies": [regla]})["result"]
        if not app.get("policies"):
            cf("POST", f"{a}/access/apps/{app['id']}/policies", regla | {"precedence": 1})
        print(f"  ✓ Access sobre {destino}, solo para {', '.join(emails)}")
    else:
        print(f"  ✓ Access sobre {destino} (ya existía; revisa en Zero Trust quién puede entrar)")

    # 5. GitHub: secretos y variables
    valores = {"ACCESS_TEAM": equipo, "ACCESS_AUD": app["aud"], "ADMIN_EMAIL": ",".join(emails)}
    if proyecto != "freelance-backoffice":
        valores["PROYECTO"] = proyecto
    if gh("auth", "status")[0] != 0:
        print("\nNo puedo guardar nada en GitHub (gh no está o no tiene sesión). Ponlo tú:")
        print("  Secrets: CLOUDFLARE_API_TOKEN (tu token) y CLOUDFLARE_ACCOUNT_ID =", cuenta)
        for k, v in valores.items():
            print(f"  Variable {k} = {v}")
        return
    # A GitHub solo le hace falta publicar. Mejor un token con solo Pages: si se filtrara, no toca Access ni el DNS.
    publicar = os.environ.get("CLOUDFLARE_DEPLOY_TOKEN")
    if not publicar and sys.stdin.isatty():
        import getpass
        print("\nPara GitHub conviene un token aparte con un solo permiso: Account · Cloudflare Pages · Edit.")
        publicar = leer_token("Token para GitHub (solo con permiso de Pages).", otro_igual=token)
    if publicar and publicar != token:
        revisar_token(publicar)
        Cloudflare(publicar)("GET", "/user/tokens/verify")
    fallos = []
    for k, v in (("CLOUDFLARE_API_TOKEN", publicar or token), ("CLOUDFLARE_ACCOUNT_ID", cuenta)):
        if gh("secret", "set", k, entrada=v)[0]:
            fallos.append(f"secret {k}")
    for k, v in valores.items():
        if gh("variable", "set", k, "--body", v)[0]:
            fallos.append(f"variable {k} = {v}")
    if fallos:
        print("  ✗ No he podido guardar en GitHub (¿permisos de gh?). Ponlo a mano en Settings → Secrets and variables:")
        for f in fallos:
            print(f"    {f}")
        return
    print("  ✓ Secretos y variables guardados en GitHub")
    print(f"\nListo. Publica con git push (o: gh workflow run publicar.yml) y abre {dominio}/admin/")
    print("Luego: python backoffice.py doctor, para comprobar que el admin pide login.")


def wrangler():
    """python backoffice.py wrangler: escribe en wrangler.toml las variables de GitHub (solo en GitHub Actions)."""
    ruta = bo.ROOT / "wrangler.toml"
    texto = ruta.read_text(encoding="utf-8")
    for k in ("ACCESS_TEAM", "ACCESS_AUD", "ADMIN_EMAIL", "DEMO"):
        v = os.environ.get(k)
        if v:
            texto = re.sub(rf'^{k}\s*=\s*"[^"]*"', f'{k} = "{v}"', texto, flags=re.M)
    if os.environ.get("PROYECTO"):
        texto = re.sub(r'^name\s*=\s*"[^"]*"', f'name = "{os.environ["PROYECTO"]}"', texto, flags=re.M)
    ruta.write_text(texto, encoding="utf-8")
    puestas = [k for k in ("ACCESS_TEAM", "ACCESS_AUD", "ADMIN_EMAIL") if re.search(rf'^{k}\s*=\s*"[^"]+"', texto, re.M)]
    print(f"wrangler.toml: {len(puestas)} de 3 variables de Access" + ("" if len(puestas) == 3 else " (el admin responderá 403)"))
