"""Tests del motor: fiscalidad, numeración, facturas que no se tocan, migraciones, copias y conectores.

    python -m unittest discover -s tests -v

Cada clase trabaja sobre una copia de demo/ en una carpeta temporal: nunca toca datos/.
"""
import importlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def cargar(datos):
    """Importa backoffice (y sus módulos) apuntando a otra carpeta de datos."""
    os.environ["BACKOFFICE_DATOS"] = str(datos)
    import backoffice, conectores, mantenimiento, trabajo
    for m in (backoffice, conectores, mantenimiento, trabajo):
        importlib.reload(m)
    return backoffice, conectores, mantenimiento


class ConDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.datos = cls.tmp / "datos"
        shutil.copytree(ROOT / "demo", cls.datos)
        cls.bo, cls.con, cls.man = cargar(cls.datos)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def argv(self, *args):
        return mock.patch.object(sys, "argv", ["backoffice.py", *args])


class Regimen(ConDemo):
    neg = {"iva": 21, "irpf": 15}

    def test_espana_empresa_retiene(self):
        self.assertEqual(self.bo.regimen({"pais": "ES", "tipo": "empresa"}, self.neg), (Decimal(21), Decimal(15), None))

    def test_espana_particular_no_retiene(self):
        iva, irpf, _ = self.bo.regimen({"pais": "ES", "tipo": "particular"}, self.neg)
        self.assertEqual((iva, irpf), (21, 0))

    def test_ue_empresa_inversion_sujeto_pasivo(self):
        iva, irpf, mencion = self.bo.regimen({"pais": "FR", "tipo": "empresa"}, self.neg)
        self.assertEqual((iva, irpf), (0, 0))
        self.assertIn("sujeto pasivo", mencion)

    def test_ue_particular_paga_iva_espanol(self):
        iva, irpf, mencion = self.bo.regimen({"pais": "DE", "tipo": "particular"}, self.neg)
        self.assertEqual((iva, irpf, mencion), (21, 0, None))

    def test_fuera_de_la_ue_no_sujeta(self):
        iva, irpf, mencion = self.bo.regimen({"pais": "US", "tipo": "empresa"}, self.neg)
        self.assertEqual((iva, irpf), (0, 0))
        self.assertIn("no sujeta", mencion)

    def test_irpf_reducido(self):
        _, irpf, _ = self.bo.regimen({"pais": "ES"}, {"iva": 21, "irpf": 7})
        self.assertEqual(irpf, 7)


class Calcular(ConDemo):
    def test_redondeo_por_linea(self):
        lineas, t = self.bo.calcular([{"descripcion": "x", "cantidad": 3, "precio": 33.335}], Decimal(21), Decimal(15))
        self.assertEqual(lineas[0]["precio"], 33.34)
        self.assertEqual(t["base"], 100.02)
        self.assertEqual(t["iva"], 21.0)
        self.assertEqual(t["irpf"], 15.0)
        self.assertAlmostEqual(t["total"], 100.02 + 21.0 - 15.0)

    def test_varias_lineas(self):
        _, t = self.bo.calcular([{"descripcion": "a", "precio": 1000}, {"descripcion": "b", "cantidad": 2, "precio": 250}],
                                Decimal(21), Decimal(0))
        self.assertEqual((t["base"], t["iva"], t["total"]), (1500.0, 315.0, 1815.0))


class Gastos(ConDemo):
    def g(self, **k):
        return self.bo.calcular_gasto({"base": 100, "categoria": "software"} | k)

    def test_nacional(self):
        r = self.g(tipo_iva="nacional")
        self.assertEqual((r["iva"], r["iva_deducible"], r["gasto_irpf"]), (21.0, 21.0, 100.0))

    def test_nacional_afectado_al_50(self):
        r = self.g(tipo_iva="nacional", afectacion=50, categoria="telefono")
        self.assertEqual((r["iva_deducible"], r["gasto_irpf"]), (10.5, 50.0))

    def test_ticket_el_iva_es_gasto(self):
        r = self.g(tipo_iva="ticket", iva_pct=21)
        self.assertEqual((r["iva_deducible"], r["gasto_irpf"]), (0.0, 121.0))

    def test_inversion_sujeto_pasivo(self):
        for tipo in ("isp_ue", "isp_fuera"):
            r = self.g(tipo_iva=tipo)
            self.assertEqual((r["iva"], r["iva_autoliquidado"], r["iva_deducible"], r["gasto_irpf"]), (0.0, 21.0, 21.0, 100.0))

    def test_sin_iva(self):
        r = self.g(tipo_iva="sin_iva", categoria="seguridad_social")
        self.assertEqual((r["iva"], r["iva_deducible"], r["gasto_irpf"]), (0.0, 0.0, 100.0))

    def test_equipo_caro_se_amortiza(self):
        r = self.g(tipo_iva="nacional", categoria="equipo", base=1000)
        self.assertEqual((r["gasto_irpf"], r["amortizable"], r["iva_deducible"]), (0.0, 1000.0, 210.0))

    def test_equipo_barato_es_gasto(self):
        r = self.g(tipo_iva="nacional", categoria="equipo", base=300)
        self.assertEqual((r["gasto_irpf"], r["amortizable"]), (300.0, 0.0))


class Trimestres(ConDemo):
    def test_limites_y_plazos(self):
        self.assertEqual(self.bo.limites("2026-1T"), ("2026-01-01", "2026-03-31", "2026-04-20"))
        self.assertEqual(self.bo.limites("2026-3T"), ("2026-07-01", "2026-09-30", "2026-10-20"))
        self.assertEqual(self.bo.limites("2026-4T"), ("2026-10-01", "2026-12-31", "2027-01-30"))

    def test_trimestre_de(self):
        self.assertEqual([self.bo.trimestre_de(f"2026-{m:02d}-15") for m in (1, 3, 4, 9, 10, 12)],
                         ["2026-1T", "2026-1T", "2026-2T", "2026-3T", "2026-4T", "2026-4T"])

    def test_casillas_cuadran(self):
        r = self.bo.calcular_trimestre("2026-4T")
        m303, m130 = r["m303"], r["m130"]
        self.assertAlmostEqual(m303["46"], m303["27"] - m303["45"], places=2)
        self.assertAlmostEqual(m130["03"], m130["01"] - m130["02"], places=2)
        self.assertAlmostEqual(m130["04"], round(m130["03"] * 0.2, 2), places=2)
        self.assertAlmostEqual(m130["07"], m130["04"] - m130["05"] - m130["06"], places=2)

    def test_demo_no_cambia(self):
        # Si esto falla, ha cambiado el cálculo del 303 o el 130: compruébalo a mano antes de tocar la cifra.
        self.assertEqual(self.bo.calcular_trimestre("2026-4T")["a_pagar"], 2261.44)


class Facturas(ConDemo):
    def test_la_demo_esta_bien(self):
        self.assertEqual(self.bo.problemas(desde=None), [])

    def test_siguiente_numero(self):
        self.assertEqual(self.bo.siguiente_numero("2026", "2026-12-01"), "2026-004")
        self.assertEqual(self.bo.siguiente_numero("2027", "2027-01-02"), "2027-001")
        self.assertEqual(self.bo.siguiente_numero("R2026", "2026-12-01"), "R2026-001")

    def test_no_se_emite_con_fecha_anterior(self):
        with self.assertRaises(SystemExit):
            self.bo.siguiente_numero("2026", "2026-01-01")


class EmitirCobrarRectificar(ConDemo):
    def test_emitir_cobrar_rectificar(self):
        borrador = self.tmp / "borrador.json"
        borrador.write_text(json.dumps({"cliente": "acme-robotica", "fecha": "2026-12-15",
                                        "conceptos": [{"descripcion": "Prueba", "precio": 1000}]}), encoding="utf-8")
        falso_pdf = lambda n=None: self.bo.ruta_factura(n).with_suffix(".pdf").write_bytes(b"%PDF-1.4")
        with mock.patch.object(self.bo, "pdf_factura", falso_pdf), mock.patch.object(self.bo, "hoy", lambda: "2026-12-20"):
            with self.argv("emitir", str(borrador)):
                self.bo.emitir()
            f = self.bo.leer(self.bo.ruta_factura("2026-004"))
            self.assertEqual((f["base"], f["estado"]), (1000.0, "emitida"))
            with self.argv("cobrar", "2026-004", "2026-12-18"):
                self.bo.cobrar()
            self.assertEqual(self.bo.leer(self.bo.ruta_factura("2026-004"))["cobrada"], "2026-12-18")
            with self.argv("rectificar", "2026-004", "Prueba"):
                self.bo.rectificar()
            r = self.bo.leer(self.bo.ruta_factura("R2026-001"))
            self.assertEqual((r["base"], r["rectifica"]), (-1000.0, "2026-004"))
            self.assertEqual(self.bo.leer(self.bo.ruta_factura("2026-004"))["estado"], "rectificada")
        self.assertEqual(self.bo.problemas(desde=None), [])


class FacturasQueNoSeTocan(unittest.TestCase):
    """facturas_tocadas() con un repo de git de verdad."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "demo", self.tmp / "datos")
        self.bo, _, _ = cargar(self.tmp / "datos")
        self.bo.ROOT = self.tmp
        g = lambda *a: subprocess.run(["git", *a], cwd=self.tmp, check=True, capture_output=True)
        g("init", "-q")
        g("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "inicio")
        self.g = g
        self.json = self.tmp / "datos/facturas/2026/2026-001.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cambiar(self, **k):
        d = json.loads(self.json.read_text(encoding="utf-8")) | k
        self.json.write_text(json.dumps(d), encoding="utf-8")

    def test_sin_cambios(self):
        self.assertEqual(self.bo.facturas_tocadas("HEAD"), [])

    def test_cobrar_se_puede(self):
        self.cambiar(estado="cobrada", cobrada="2026-12-01")
        self.assertEqual(self.bo.facturas_tocadas("HEAD"), [])

    def test_cambiar_el_importe_no(self):
        self.cambiar(base=1.0)
        errores = self.bo.facturas_tocadas("HEAD")
        self.assertEqual(len(errores), 1)
        self.assertIn("base", errores[0])

    def test_borrarla_no(self):
        self.json.unlink()
        self.assertIn("se ha borrado", self.bo.facturas_tocadas("HEAD")[0])

    def test_cambiar_el_pdf_no(self):
        self.json.with_suffix(".pdf").write_bytes(b"otro")
        self.assertIn("PDF", self.bo.facturas_tocadas("HEAD")[0])

    def test_otro_commit_encima_no_lo_tapa(self):
        self.cambiar(base=1.0)
        self.g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "cambio")
        self.g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "otro push")
        antes = subprocess.run(["git", "rev-parse", "HEAD~1"], cwd=self.tmp, capture_output=True, text=True).stdout.strip()
        self.assertIn("base", self.bo.facturas_tocadas(antes)[0])

    def test_borrada_en_un_commit_anterior(self):
        self.g("rm", "-q", str(self.json))
        self.g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "borra")
        self.assertIn("se ha borrado", self.bo.facturas_tocadas("HEAD")[0])

    def test_historia_reescrita(self):
        self.assertIn("reescrito", self.bo.facturas_tocadas("0123456789abcdef0123456789abcdef01234567")[0])

    def test_una_nueva_si(self):
        (self.tmp / "datos/facturas/2026/2026-099.json").write_text("{}", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True)
        self.assertEqual(self.bo.facturas_tocadas("HEAD"), [])


class Trabajo(ConDemo):
    """El trabajo de un proyecto (datos/trabajo/): revisar, el admin, la página del cliente y los enlaces."""

    def setUp(self):
        import trabajo
        self.tr = trabajo
        self.base = self.datos / "trabajo" / "acme-robotica-web"

    def test_la_demo_esta_bien(self):
        self.assertEqual(self.bo.problemas(desde=None), [])
        e = self.tr.cargar("acme-robotica-web")
        self.assertEqual(e["espacio"]["fase_actual"], "diseno")
        docs = {d["id"]: d for d in e["documentos"]}
        # 02-diseno sustituye al borrador: el borrador pasa a «sustituido» y apunta al nuevo
        self.assertEqual((docs["02-diseno-borrador"]["estado"], docs["02-diseno-borrador"]["sustituido_por"]), ("sustituido", "02-diseno"))
        self.assertTrue(all(d["al_dia"] and d["pagina"] and d["pdf"] for d in docs.values()))
        self.assertIn("que-hacen-antes-de-llamar", [a["id"] for a in docs["01-investigacion"]["anclas"]])

    def test_un_documento_cambiado_sin_regenerar_es_un_problema(self):
        f = self.base / "documentos" / "01-investigacion.md"
        antes = f.read_text(encoding="utf-8")
        try:
            f.write_text(antes + "\nUna línea más.\n", encoding="utf-8")
            self.assertTrue(any("01-investigacion" in x and "documentos acme-robotica-web" in x for x in self.tr.problemas()))
        finally:
            f.write_text(antes, encoding="utf-8")

    def test_cabecera_y_estados_que_no_valen(self):
        f = self.tmp / "malo.md"
        f.write_text("---\ntitulo: X\nformato: libro\nversion: 1\nestado: borrador\nfecha: 2026-11-20\n---\nHola", encoding="utf-8")
        with self.assertRaises(self.tr.Invalido):
            self.tr.leer_documento(f)
        x = self.base / "entregables" / "01.json"
        antes = x.read_text(encoding="utf-8")
        try:
            x.write_text(antes.replace('"aprobado"', '"approved"'), encoding="utf-8")
            self.assertTrue(any("entregable 01" in e for e in self.tr.problemas()))
        finally:
            x.write_text(antes, encoding="utf-8")

    def test_columnas_y_portada_en_las_diapositivas(self):
        html = self.tr._md('# Portada\n\n<div class="cols c2" markdown="1">\n<div markdown="1">\n### Uno\nTexto **fuerte**.\n</div>\n</div>', h1=True)
        self.assertIn("<h1>Portada</h1>", html)
        self.assertIn('<div class="cols c2"><div><h3 id="uno">Uno</h3><p>Texto <strong>fuerte</strong>.</p></div></div>', html)

    def test_admin_y_pagina_del_cliente(self):
        dest = self.tmp / "admin"
        with mock.patch("builtins.print"):
            self.bo.build(dest)
        datos = json.loads((dest / "datos.json").read_text(encoding="utf-8"))
        self.assertIn("acme-robotica-web", datos["trabajo"])
        self.assertIn("acme-web", [e["slug"] for e in datos["espacios"]])
        self.assertTrue((dest / "trabajo" / "acme-robotica-web" / "02-diseno.html").exists())
        c = self.tmp / "c" / "acme-web"
        self.tr.pagina_cliente(c, "acme-robotica-web", self.tr.para_admin())
        cliente = json.loads((c / "datos.json").read_text(encoding="utf-8"))
        # Solo ese proyecto, sin facturas, clientes ni a quién se ha dado acceso
        self.assertEqual(set(cliente), {"generado", "negocio", "trabajo"})
        self.assertEqual(list(cliente["trabajo"]), ["acme-robotica-web"])
        self.assertIsNone(cliente["trabajo"]["acme-robotica-web"]["compartir"])
        self.assertNotIn("compartir", cliente["trabajo"]["acme-robotica-web"]["espacio"])
        self.assertIn(self.tr.MARCA, (c / "index.html").read_text(encoding="utf-8"))
        for f in ("assets/trabajo.js", "assets/cliente.js", "trabajo/acme-robotica-web/00-estado-v1.0.pdf"):
            self.assertTrue((c / f).is_file(), f)
        self.assertFalse((c / "trabajo" / "acme-robotica-web" / "indice.json").exists())

    def test_enlace_al_proyecto_compartido(self):
        acc = self.datos / "espacios" / "accesos.json"
        antes = acc.read_text(encoding="utf-8")
        try:
            with self.argv("enlace", "acme-robotica-web", "Luis Gil"), mock.patch("builtins.print") as dijo:
                self.bo.enlace()
            self.assertIn("/c/acme-web/?k=", " ".join(str(a) for c in dijo.call_args_list for a in c.args))
            self.assertIn("Luis Gil", [a["nombre"] for a in self.bo.accesos()["acme-web"]])
            with self.argv("revocar", "acme-web", "Luis Gil"), mock.patch("builtins.print"):
                self.bo.revocar()
            self.assertNotIn("Luis Gil", [a["nombre"] for a in self.bo.accesos()["acme-web"]])
            self.assertEqual(self.bo.problemas(desde=None), [])
        finally:
            acc.write_text(antes, encoding="utf-8")


class Mantenimiento(ConDemo):
    def test_migrar_desde_la_01(self):
        # Sin tocar el wrangler.toml ni las variables de GitHub de este repo
        self.enterContext(mock.patch.object(self.man, "gh", return_value=(0, "")))
        self.enterContext(mock.patch.object(self.man, "git", return_value=""))
        self.enterContext(mock.patch.object(self.man.bo, "ROOT", self.tmp))
        neg = self.bo.negocio()
        neg.pop("version")
        self.bo.escribir(self.datos / "negocio.json", neg)
        self.assertTrue(any("migrar" in e for e in self.bo.problemas(desde=None)))
        self.man.migrar()
        self.assertEqual(self.bo.negocio()["version"], self.bo.DATOS_VERSION)
        self.assertEqual(self.bo.problemas(desde=None), [])

    def test_hay_una_migracion_por_version(self):
        self.assertEqual(sorted(self.man.MIGRACIONES), list(range(1, self.bo.DATOS_VERSION + 1)))

    def test_copia_y_restaurar(self):
        carpeta = self.tmp / "copias"
        with mock.patch.object(self.man, "LOCAL", self.tmp / "local.json"):
            with self.argv("copia", str(carpeta)):
                self.man.copia()
            zips = list(carpeta.glob("backoffice-*.zip"))
            self.assertEqual(len(zips), 1)
            (self.datos / "clientes" / "northwind.json").unlink()
            with self.argv("restaurar", str(zips[0])), mock.patch.object(self.man.subprocess, "run"):
                self.man.restaurar()
        self.assertTrue((self.datos / "clientes" / "northwind.json").exists())

    def test_restaurar_una_copia_mala_no_toca_nada(self):
        malo = self.tmp / "malo.zip"
        malo.write_bytes(b"esto no es un zip")
        with self.argv("restaurar", str(malo)), self.assertRaises(SystemExit):
            self.man.restaurar()
        self.assertTrue((self.datos / "negocio.json").exists())

    def test_migracion_1_rescata_access_del_ultimo_commit(self):
        viejo = 'name = "x"\n[vars]\nACCESS_TEAM = "equipo"\nACCESS_AUD = "aud123"\n'
        guardadas = {}
        def gh(*a, **k):
            guardadas[a[2]] = a[4]
            return 0, ""
        with mock.patch.object(self.man, "git", return_value=viejo), mock.patch.object(self.man, "gh", gh),              mock.patch.object(self.man.bo, "ROOT", self.tmp):
            (self.tmp / ".git").mkdir(exist_ok=True)
            self.man.migracion_1()
        self.assertEqual(guardadas, {"ACCESS_TEAM": "equipo", "ACCESS_AUD": "aud123"})

    def test_la_copia_no_va_dentro_del_repo(self):
        with mock.patch.object(self.man, "LOCAL", self.tmp / "local.json"), self.argv("copia", str(self.bo.ROOT / "copias")):
            with self.assertRaises(SystemExit):
                self.man.copia()

    def test_actualizar_no_toca_lo_suyo(self):
        for ruta in ("datos/negocio.json", "datos/voz.md", "bandeja/x.pdf", ".backoffice.local.json"):
            self.assertTrue(self.man.es_suyo(ruta), ruta)
        for ruta in ("backoffice.py", ".github/workflows/publicar.yml", "demo/negocio.json"):
            self.assertFalse(self.man.es_suyo(ruta), ruta)


class Conectores(ConDemo):
    def test_busqueda_de_correo(self):
        q = self.con.busqueda()
        self.assertIn("from:(adobe.com OR fibradeejemplo.es)", q)
        self.assertIn("newer_than:45d", q)

    def test_melso(self):
        with self.argv("melso", "empezar", "2026-10-01"):
            self.con.melso()
        p = self.con.pendientes_melso()
        self.assertEqual([f["numero"] for f in p["facturas"]], ["2026-002", "2026-003"])
        self.assertTrue(all(g["fecha"] >= "2026-10-01" for g in p["gastos"]))
        self.assertTrue(all(g["archivo"] or g["sin_factura"] for g in p["gastos"]))
        with self.argv("melso", "apuntar", "factura", "2026-002", "inv_123"):
            self.con.melso()
        self.assertEqual([f["numero"] for f in self.con.pendientes_melso()["facturas"]], ["2026-003"])


if __name__ == "__main__":
    unittest.main()
