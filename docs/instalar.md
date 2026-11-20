# Publicar en Cloudflare

Hasta aquí tu backoffice funciona en tu ordenador. Al publicarlo tendrás dos cosas en tu dominio:

- `https://backoffice.tudominio.com/admin/`: tu admin. Solo entras tú, con un código que te llega por email.
- `https://backoffice.tudominio.com/c/<espacio>/?k=…`: los espacios de tus clientes, cada uno con su enlace.

Todo vive en un proyecto de Cloudflare Pages que se actualiza solo con cada `git push`. Es gratis.

## Lo que necesitas antes

- Una cuenta de Cloudflare con un dominio, o un subdominio de uno que ya tengas allí (`backoffice.tudominio.com`).
- [gh](https://cli.github.com), la herramienta de GitHub para la terminal, con sesión iniciada (`gh auth login`).
- Tu dominio en `datos/negocio.json`:

  ```json
  "dominio": "https://backoffice.tudominio.com"
  ```

## La forma rápida

### 1. Activa Zero Trust

Es lo único que Cloudflare no deja hacer desde fuera. En el panel de Cloudflare, entra en **Zero Trust**. La primera vez te pide un nombre de equipo (cualquiera, por ejemplo tu nombre) y un plan: elige **Free**. Puede que te pida una tarjeta aunque no cobre nada.

### 2. Crea un token

En Cloudflare: **My Profile → API Tokens → Create Token → Create Custom Token**. Ponle un nombre (`Freelance Backoffice`) y estos permisos:

| Tipo | Permiso | Nivel |
|---|---|---|
| Account | Cloudflare Pages | Edit |
| Account | Access: Apps and Policies | Edit |
| Account | Access: Organizations, Identity Providers, and Groups | Read |
| Account | Account Settings | Read |
| Zone | DNS | Edit |

En **Zone Resources**, elige tu dominio. Crea el token y déjalo copiado.

### 3. Lanza el comando

En una terminal, en la carpeta del repo (no en el chat de Claude Code):

```
python backoffice.py cloudflare
```

Te pide que copies el token (con el botón de copiar de Cloudflare) y pulses Enter: lo lee del portapapeles, lo borra de allí y hace lo demás. No hace falta pegarlo, y nunca lo pegues en la terminal ni en el chat. Después: crea el proyecto de Pages, le pone tu dominio, crea el registro DNS, protege `/admin` con Cloudflare Access para tu email y guarda en GitHub los secretos y variables que necesita la publicación. Al final te pide un segundo token para GitHub, con un solo permiso (**Account · Cloudflare Pages · Edit**). Es el que se queda guardado en GitHub para publicar; si algún día se filtrara, no daría acceso a tu Access ni a tu DNS. Si no copias otro y pulsas Enter, usa el mismo, pero no es lo recomendable.

Si algo falla, te dice qué, y puedes volver a lanzarlo: lo que ya está hecho no se repite.

Si tienes más de una cuenta de Cloudflare, te pedirá que elijas con `--cuenta <id>`.

### 4. Publica y comprueba

Haz commit de `datos/negocio.json` (el comando apunta ahí tu dirección de pages.dev) y `git push`. En la pestaña **Actions** de tu repo verás el workflow **Publicar**; cuando salga en verde:

```
python backoffice.py doctor
```

Tiene que decir que `/admin/` pide login y que la dirección de pages.dev está cerrada. Abre `https://backoffice.tudominio.com/admin/`: te pedirá tu email y un código.

## A mano

Si prefieres no darle a un comando tantos permisos, o algo no ha funcionado, estos son los mismos pasos en el panel.

1. **Token para GitHub.** Cloudflare → **My Profile → API Tokens → Create Custom Token**, con solo **Account · Cloudflare Pages · Edit**. Copia también tu **Account ID** (sale a la derecha en la portada de cualquier dominio).
2. **Secretos en GitHub.** En tu repo: **Settings → Secrets and variables → Actions → Secrets → New repository secret**. Crea `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`.
3. **Primer despliegue.** Haz `git push`. El workflow crea el proyecto de Pages `freelance-backoffice`. Si ese nombre ya lo tienes en tu cuenta, crea en GitHub la variable `PROYECTO` con otro nombre.
4. **Dominio.** Cloudflare → **Workers & Pages → freelance-backoffice → Custom domains → Set up a custom domain** → `backoffice.tudominio.com`.
5. **Access.** Cloudflare → **Zero Trust → Access → Applications → Add an application → Self-hosted**:
   - Nombre: `Freelance Backoffice`.
   - Dominio: `backoffice.tudominio.com`, ruta: `admin`.
   - Política: **Allow**, con la regla **Emails** y tu email.
   - Para entrar vale el código por email (One-time PIN), que viene activado.
6. **Variables en GitHub.** En **Settings → Secrets and variables → Actions → Variables**, crea:
   - `ACCESS_TEAM`: tu nombre de equipo, lo que va antes de `.cloudflareaccess.com`.
   - `ACCESS_AUD`: el **Application Audience (AUD) Tag**, en la pestaña Overview de la aplicación que acabas de crear.
   - `ADMIN_EMAIL`: tu email. Si entra más gente, sepáralos con comas.
7. `git push` otra vez y `python backoffice.py doctor`.

## Cómo funciona por dentro

- `python backoffice.py build` monta `dist/sitio/` con el admin, los PDF, los ZIP y los espacios, y `dist/accesos.json` con los hashes de los enlaces.
- El workflow escribe en `wrangler.toml` las variables de Access que tienes en GitHub. Por eso no tienes que tocar ese archivo, y las actualizaciones no chocan con tu configuración.
- `functions/admin/_middleware.js` comprueba en cada visita el token firmado de Access: firma, aplicación, caducidad y email. Si falta algo, responde 403. Así la dirección `*.pages.dev`, que Access no cubre, tampoco enseña nada.
- `functions/c/_middleware.js` calcula el SHA-256 de la clave del enlace y lo busca en `dist/accesos.json`. La primera visita deja una cookie válida solo para ese espacio.

## La demo pública

Para enseñar la demo sin login, publica `demo/` en otro proyecto de Pages con la variable `DEMO = "1"`. El admin solo se abre si los datos publicados son los de la demo (llevan `"demo": true`). Con tus datos reales, `DEMO` no hace nada.
