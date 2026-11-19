// Cerradura de los espacios de cliente (/c/<slug>/...). La lógica está en lib/enlace-personal.js.
// Quién entra: dist/accesos.json, que monta "python trastienda.py build" (solo hashes).
import ACCESOS from '../../dist/accesos.json';
import { cerradura } from '../../lib/enlace-personal.js';

export const onRequest = (ctx) => cerradura(ctx, { seccion: 'c', accesos: ACCESOS });
