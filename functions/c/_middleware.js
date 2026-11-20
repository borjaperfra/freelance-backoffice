// Cerradura de los espacios de cliente (/c/<slug>/...). La lógica está en lib/enlace-personal.js.
// Quién entra: dist/accesos.json, que monta "python backoffice.py build" (solo hashes).
//
// En la demo pública (DEMO = "1" y datos con "demo": true) los espacios se abren sin enlace, igual que el admin.
import ACCESOS from '../../dist/accesos.json';
import MODO from '../../dist/modo.json';
import { cerradura } from '../../lib/enlace-personal.js';

export const onRequest = (ctx) =>
  ctx.env.DEMO === '1' && MODO.demo === true ? ctx.next() : cerradura(ctx, { seccion: 'c', accesos: ACCESOS });
