// Cerradura de los espacios de cliente (/c/<slug>/...): enlace personal con ?k=<clave>.
//
// Se calcula el SHA-256 de la clave y se busca en accesos (lo genera "python backoffice.py build"
// en dist/accesos.json a partir de datos/espacios/accesos.json). En el repo solo hay hashes.
// La primera visita deja una cookie con la clave, solo para esa ruta, así que después se navega
// y se descargan archivos sin arrastrar ?k=.
//
// Sin clave válida: 403 con una página que no enseña nada. Un espacio sin enlaces queda cerrado.
// Cubre también <proyecto>.pages.dev.

const sha256 = async (s) => {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
};

const cerrado = () => new Response(`<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Espacio privado</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;font:18px/1.55 Inter,system-ui,sans-serif;background:#fff;color:#0a0a0a;padding:24px;box-sizing:border-box}
@media (prefers-color-scheme:dark){body{background:#0a0a0a;color:#f2f2f2}}main{max-width:32em}h1{font-weight:400;font-size:32px;letter-spacing:-.02em;margin:0 0 .5em}</style></head>
<body><main><h1>Este espacio es privado</h1>
<p>Solo se abre con un enlace personal, y este no lo es o ya no funciona.</p>
<p>Si crees que deberías tener acceso, pide un enlace nuevo a quien te lo mandó.</p></main></body></html>`, {
  status: 403,
  headers: {
    'content-type': 'text/html; charset=utf-8',
    'cache-control': 'no-store',
    'x-robots-tag': 'noindex, nofollow, noarchive',
    'referrer-policy': 'no-referrer',
  },
});

// accesos: { slug: { hash: nombre } }
export async function cerradura({ request, next }, { seccion, accesos }) {
  const url = new URL(request.url);
  const slug = decodeURIComponent(url.pathname).split('/')[2] || '';
  const claves = Object.prototype.hasOwnProperty.call(accesos, slug) ? accesos[slug] : null;
  if (!claves || !Object.keys(claves).length) return cerrado();

  const nombreCookie = `${seccion}_${slug.replace(/[^a-z0-9]/gi, '_')}`;
  const deUrl = url.searchParams.get('k');
  const m = (request.headers.get('cookie') || '').match(new RegExp(`(?:^|;\s*)${nombreCookie}=([^;]+)`));
  const deCookie = m ? decodeURIComponent(m[1]) : null;

  let k = null;
  for (const c of [deUrl, deCookie]) {
    if (c && c.length >= 16 && c.length <= 128 && Object.prototype.hasOwnProperty.call(claves, await sha256(c))) { k = c; break; }
  }
  if (!k) return cerrado();

  const res = await next();
  const out = new Response(res.body, res);
  out.headers.set('cache-control', 'private, no-store');
  out.headers.set('x-robots-tag', 'noindex, nofollow, noarchive');
  out.headers.set('referrer-policy', 'no-referrer');
  if (k !== deCookie) {
    out.headers.append('set-cookie',
      `${nombreCookie}=${encodeURIComponent(k)}; Path=/${seccion}/${slug}/; Max-Age=31536000; HttpOnly; Secure; SameSite=Lax`);
  }
  return out;
}
