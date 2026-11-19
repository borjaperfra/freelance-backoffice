---
name: configurar
description: Pone en marcha la trastienda de un autónomo la primera vez — sus datos fiscales, la cuota de autónomos, las suscripciones que paga y la publicación en Cloudflare. Úsala cuando la persona diga "configura mi trastienda", "empecemos", "acabo de clonar esto" o cuando datos/negocio.json no exista o tenga campos PENDIENTE.
---

# Configurar la trastienda

Ve paso a paso y pregunta poco cada vez. Al final, la persona tiene sus datos en `datos/`, el admin funcionando en local y, si quiere, publicado.

## 1. Datos

1. Si no existe `datos/negocio.json`: `python trastienda.py init`.
2. Pide sus datos fiscales y rellena `datos/negocio.json`:
   - `nombre` (como sale en las facturas), `nif`, `direccion`, `cp`, `ciudad`, `provincia`, `email`, `iban`.
   - `alta`: fecha de alta como autónomo (AAAA-MM-DD). No se puede facturar antes.
   - `irpf`: 15 por defecto. Si se dio de alta hace menos de tres años, puede aplicar el 7%: pregunta, y si es así, pon `irpf: 7` e `irpf_hasta` con el 31 de diciembre del segundo año siguiente al alta.
   - `vence_dias` (30 por defecto) y `gestoria` (`nombre`, `email`) si tiene.
   - Si te pasa una factura antigua suya o su modelo 036, saca los datos de ahí y pide que los confirme.
3. Gastos fijos en `datos/gastos/recurrentes.json` (formato en la skill `gasto`): la cuota de autónomos (lo que le cobran de verdad) y las suscripciones que use para trabajar. Pregunta por ellas con una lista corta de ejemplos (diseño, correo, hosting, IA, teléfono). Luego `python trastienda.py recurrentes`.
4. Si quiere, sus clientes y proyectos en marcha (skill `backoffice`) y su voz para los textos a clientes en `datos/voz.md` (unos párrafos sobre cómo escribe, o textos suyos de ejemplo).
5. `python trastienda.py revisar` y `python trastienda.py servir`: que vea su admin en local.

## 2. Que el repo sea privado

Antes de hacer `git push` con sus datos, comprueba que el repo de GitHub es **privado** (`gh repo view --json visibility`). Si es público, para y díselo: sus datos fiscales y facturas quedarían a la vista.

## 3. Publicar en Cloudflare (opcional)

Sigue `docs/instalar.md` con la persona. Lo que hace falta:

1. Cuenta de Cloudflare (gratis) y un dominio o subdominio en ella.
2. Secretos en GitHub: `CLOUDFLARE_API_TOKEN` (permiso Cloudflare Pages: Edit) y `CLOUDFLARE_ACCOUNT_ID`.
3. El primer `git push` crea el proyecto de Pages `trastienda` y lo despliega.
4. Dominio propio en el proyecto de Pages, y `"dominio": "https://…"` en `negocio.json`.
5. Cloudflare Access (Zero Trust, gratis hasta 50 usuarios): una aplicación sobre `<dominio>/admin` con su email. Copia el nombre del equipo y el AUD a `wrangler.toml` (`ACCESS_TEAM`, `ACCESS_AUD`, `ADMIN_EMAIL`).
6. Comprueba que `<dominio>/admin/` pide el login de Access y que `<proyecto>.pages.dev/admin/` da 403.

Hasta que no estén las tres variables de Access, `/admin/` responde 403: nunca queda abierto.

## Lo que no hace

Verifactu: las facturas no se envían a Hacienda. Recuérdale que el sistema de facturación que use tiene que cumplirlo cuando le sea obligatorio, y que eso es responsabilidad suya.
