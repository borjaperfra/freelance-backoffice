# Si algo falla

Lo primero, siempre:

```
python backoffice.py doctor
```

Repasa la instalación de arriba abajo y, por cada cosa que falla, dice cómo arreglarla. Si no basta, aquí están los casos que más se repiten.

## En tu ordenador

**«No encuentro Chrome para generar el PDF».** Instala Google Chrome, o pon la ruta de tu Chrome o Chromium en la variable `CHROME`. Solo hace falta para emitir facturas y cerrar trimestres.

**`python` no existe, o abre la Microsoft Store.** En Windows, instala Python desde python.org y marca «Add python.exe to PATH». Si tienes `py` pero no `python`, usa `py backoffice.py …`.

**Acentos raros en la terminal de Windows.** Es la terminal, no tus datos. En PowerShell: `[Console]::OutputEncoding = [Text.Encoding]::UTF8`.

**«No puedo leer el cambio del BCE».** El gasto está en otra moneda y no hay conexión con el Banco Central Europeo. Dile a Claude Code lo que te cobró el banco en euros y lo apunta con ese importe.

## Al publicar

**El workflow Publicar sale en rojo en «Revisar los datos».** Algo no cuadra en `datos/`. Ejecuta `python backoffice.py revisar` en tu ordenador: dice qué y dónde.

**«factura 2026-003: han cambiado…» o «se ha borrado».** Alguien ha tocado una factura emitida y GitHub se niega a publicar. Deshaz el cambio con `git checkout <commit anterior> -- datos/facturas/2026/2026-003.json` (o el PDF). Si la factura estaba mal, se rectifica: «la 2026-003 está mal».

**«tus datos son de la versión 0 y el código espera la 1».** Falta migrar: `python backoffice.py migrar` y haz commit.

**`git push` falla con «refusing to allow … to create or update workflow … without `workflow` scope».** Una actualización ha cambiado `.github/workflows/publicar.yml` y tu sesión de git no tiene permiso para tocar workflows. Con gh: `gh auth refresh -s workflow` y vuelve a hacer push.

**El workflow falla en «Desplegar» con un error de autenticación.** El token de `CLOUDFLARE_API_TOKEN` ha caducado o no tiene el permiso de Pages. Crea otro y guárdalo con `gh secret set CLOUDFLARE_API_TOKEN`.

## En la web

**`/admin/` responde «403 · Falta configurar Access».** Faltan las variables `ACCESS_TEAM`, `ACCESS_AUD` o `ADMIN_EMAIL` en GitHub (**Settings → Secrets and variables → Actions → Variables**). Después de crearlas, vuelve a publicar.

**`/admin/` responde «403 · No eres tú».** Has entrado con un email que no está en `ADMIN_EMAIL`, o el `ACCESS_AUD` no es el de la aplicación de Access. Compáralos en Cloudflare Zero Trust.

**«403 · Entra por tu dominio, no por la dirección de pages.dev».** Es lo esperado: la dirección `*.pages.dev` no pasa por Access y el admin no se enseña ahí.

**Un cliente dice que su enlace no funciona.** Puede que lo hayas revocado o que no se haya publicado todavía. Mira quién tiene acceso en el admin (Espacios) y, si hace falta, revoca el suyo y crea uno nuevo: «dale un enlace nuevo a Ana para el espacio de Acme».

**El dominio no carga.** Si tu dominio no está en Cloudflare, tienes que crear tú el registro CNAME en tu proveedor de DNS, apuntando a tu dirección de pages.dev. Los cambios de DNS pueden tardar un rato.

## Gastos y correo

**«revisa los gastos» no encuentra una factura.** Mira [gastos-correo.md](gastos-correo.md#cuando-no-encuentra-algo).

**Un gasto se ha apuntado mal.** No cambies las cifras a mano. Dile a Claude Code qué está mal: borra el gasto y lo vuelve a apuntar.

## Si nada de esto sirve

Abre un issue en el repo original con lo que sale en `python backoffice.py doctor` y el error exacto. No pegues datos fiscales, tokens ni enlaces de espacios.
