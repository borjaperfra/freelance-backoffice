# Publicar tu backoffice en Cloudflare

Al terminar tendrás:

- `https://<tu dominio>/admin/`: tu admin, solo para ti (Cloudflare Access).
- `https://<tu dominio>/c/<espacio>/?k=…`: los espacios de tus clientes, cada uno con su enlace.

Todo en un proyecto de Cloudflare Pages que se despliega solo cada vez que haces `git push`. Necesitas una cuenta de Cloudflare (gratis) con un dominio, o un subdominio de uno que ya tengas allí (`backoffice.tudominio.com`).

Claude Code puede guiarte paso a paso: «configura mi backoffice» (skill `configurar`).

## 1. El token de Cloudflare para GitHub

1. Cloudflare → **My Profile → API Tokens → Create Token → Custom token**.
2. Permiso: **Account · Cloudflare Pages · Edit**. Créalo y cópialo.
3. Copia también tu **Account ID** (sale en la portada de cualquier dominio, a la derecha).
4. En tu repo de GitHub: **Settings → Secrets and variables → Actions → New repository secret**:
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`

## 2. El primer despliegue

Haz `git push` con tus datos en `datos/`. El workflow **Publicar** (`.github/workflows/publicar.yml`) revisa los datos, monta el sitio y crea el proyecto de Pages `freelance-backoffice`. Mira que salga en verde en la pestaña **Actions**.

Si ya tienes un proyecto de Pages con ese nombre, cambia `name` en `wrangler.toml` y `PROYECTO` en el workflow.

## 3. Tu dominio

Cloudflare → **Workers & Pages → freelance-backoffice → Custom domains → Set up a custom domain** → `backoffice.tudominio.com` (o el que quieras).

Ponlo en `datos/negocio.json`:

```json
"dominio": "https://backoffice.tudominio.com"
```

## 4. Cloudflare Access para el admin

1. Cloudflare → **Zero Trust** (la primera vez te pide elegir un nombre de equipo y el plan Free).
2. **Access → Applications → Add an application → Self-hosted**:
   - Nombre: `Freelance Backoffice`.
   - Dominio: `backoffice.tudominio.com`, ruta: `admin`.
   - Política: **Allow**, regla **Emails** con tu email.
   - Método de login: el código de un solo uso por email (One-time PIN) vale.
3. Copia el **Application Audience (AUD) Tag** (en la aplicación, pestaña Overview).
4. Rellena `wrangler.toml`:

   ```toml
   ACCESS_TEAM = "tu-equipo"          # el de tu-equipo.cloudflareaccess.com
   ACCESS_AUD = "…"                    # el AUD Tag
   ADMIN_EMAIL = "tu@email.com"
   ```

5. `git push`.

## 5. Comprobar

- `https://backoffice.tudominio.com/admin/` te pide el código de Access y luego enseña tu admin.
- `https://freelance-backoffice.pages.dev/admin/` responde 403: Access no cubre esa dirección, pero la segunda cerradura sí.
- Crea un espacio de prueba y un enlace (`python backoffice.py enlace <espacio> "Prueba"`). Después del push, el enlace abre la página y la misma dirección sin `?k=` da 403.

## Cómo funciona por dentro

- `python backoffice.py build` monta `dist/sitio/` (el admin con `datos.json`, los PDF, los ZIP y los espacios) y `dist/accesos.json` (solo hashes).
- `functions/admin/_middleware.js` comprueba en cada petición el token firmado de Access: firma, AUD, caducidad y email. Si falta configuración, responde 403.
- `functions/c/_middleware.js` (con `lib/enlace-personal.js`) calcula el SHA-256 de la clave y lo busca en `dist/accesos.json`. La primera visita deja una cookie HttpOnly válida solo para ese espacio.

## La demo pública

Para enseñar la demo sin login, despliega `demo/` en otro proyecto de Pages con la variable `DEMO = "1"`. Con eso `/admin/` queda abierto, así que **nunca** lo hagas con datos reales.
