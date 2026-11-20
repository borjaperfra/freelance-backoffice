// Segunda cerradura del admin (/admin/...). La primera es la aplicación de Cloudflare Access sobre <tu dominio>/admin.
//
// Cada petición tiene que traer el token que firma Access (cabecera Cf-Access-Jwt-Assertion
// o cookie CF_Authorization). Aquí se comprueba la firma con las claves públicas de Access,
// que sea para esta aplicación (AUD), que no haya caducado y que el email esté en ADMIN_EMAIL (uno o varios, separados por comas).
// Sin eso, 403. Así la URL *.pages.dev, que Access no cubre, tampoco enseña nada, y si falta
// configuración el admin queda cerrado, no abierto.
//
// Las variables están en wrangler.toml.
//
// Con DEMO = "1" el admin queda abierto, pero solo si los datos publicados son los de la demo
// ("demo": true en negocio.json, que build deja en dist/modo.json). Con datos reales, DEMO no hace nada.

import MODO from '../../dist/modo.json';

let claves = { team: null, hasta: 0, keys: [] };

const b64url = (s) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));
const json = (s) => JSON.parse(new TextDecoder().decode(b64url(s)));

async function clavesDe(team) {
  if (claves.team !== team || Date.now() > claves.hasta) {
    const r = await fetch(`https://${team}.cloudflareaccess.com/cdn-cgi/access/certs`);
    if (!r.ok) throw new Error('No puedo leer las claves de Access');
    claves = { team, hasta: Date.now() + 3600e3, keys: (await r.json()).keys };
  }
  return claves.keys;
}

async function valido(token, env) {
  const partes = token.split('.');
  if (partes.length !== 3) return false;
  const [h, p, firma] = partes;
  const cabecera = json(h), datos = json(p);
  if (cabecera.alg !== 'RS256') return false;

  const jwk = (await clavesDe(env.ACCESS_TEAM)).find((k) => k.kid === cabecera.kid);
  if (!jwk) return false;
  const clave = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
  const ok = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', clave, b64url(firma), new TextEncoder().encode(`${h}.${p}`));
  if (!ok) return false;

  const ahora = Date.now() / 1000;
  const aud = Array.isArray(datos.aud) ? datos.aud : [datos.aud];
  return aud.includes(env.ACCESS_AUD)
    && datos.iss === `https://${env.ACCESS_TEAM}.cloudflareaccess.com`
    && datos.exp > ahora && (!datos.nbf || datos.nbf <= ahora + 60)
    && env.ADMIN_EMAIL.toLowerCase().split(',').map((e) => e.trim()).includes(String(datos.email || '').toLowerCase());
}

const fuera = (motivo) => new Response(`403 · ${motivo}\n`, {
  status: 403,
  headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' },
});

export async function onRequest({ request, env, next }) {
  if (env.DEMO === '1' && MODO.demo === true) return cabeceras(await next());
  if (!env.ACCESS_TEAM || !env.ACCESS_AUD || !env.ADMIN_EMAIL) return fuera('Falta configurar Access (variables ACCESS_TEAM, ACCESS_AUD y ADMIN_EMAIL en GitHub)');

  const cookie = (request.headers.get('cookie') || '').match(/(?:^|;\s*)CF_Authorization=([^;]+)/);
  const token = request.headers.get('cf-access-jwt-assertion') || (cookie && cookie[1]);
  if (!token) return fuera('Entra por tu dominio, no por la dirección de pages.dev');

  try {
    if (!(await valido(token, env))) return fuera('No eres tú');
  } catch (e) {
    return fuera('No he podido comprobar quién eres');
  }

  return cabeceras(await next());
}

function cabeceras(res) {
  const out = new Response(res.body, res);
  out.headers.set('cache-control', 'private, no-store');
  out.headers.set('x-robots-tag', 'noindex, nofollow');
  out.headers.set('referrer-policy', 'no-referrer');
  out.headers.set('x-frame-options', 'DENY');
  return out;
}
