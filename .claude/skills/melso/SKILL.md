---
name: melso
description: Conecta el backoffice con Melso (la gestoría online melso.ai) y le manda las facturas emitidas, los gastos con su PDF y los cobros. Úsala cuando la persona diga "conecta Melso", "manda lo pendiente a Melso", "sube los gastos a Melso", "¿qué le falta a Melso?", "compara el 303 con Melso", o cuando el admin saque "Hay N cosas por mandar a Melso".
---

# Melso

Melso es una gestoría online con un servidor MCP para Claude: `https://mcp.melso.ai/mcp`, con OAuth y una empresa por conexión. Con él, Claude Code puede crear gastos a partir de un PDF, subir documentos, dar de alta contactos, marcar cobros y leer los impuestos que Melso ha calculado. Melso nunca presenta un impuesto ni emite una factura sin que la persona lo apruebe en Melso.

Este repo sigue siendo la fuente: aquí se emiten las facturas y se apuntan los gastos. Lo que ya se ha mandado se guarda en `datos/melso.json` (las facturas emitidas no se tocan, así que el id de Melso no va en ellas).

## Conectar (una vez)

1. Que la persona añada el servidor en su terminal:
   ```
   claude mcp add --transport http melso https://mcp.melso.ai/mcp
   ```
   y luego, dentro de Claude Code, `/mcp` → melso → autenticar. Se abre Melso en el navegador para que dé permiso.
2. Comprueba que tienes las herramientas de Melso (`expenses`, `invoices_read`, `documents`, `contacts`, `payments`, `taxes`…). Si no aparecen, que reinicie Claude Code.
3. Pregunta desde qué fecha lleva Melso sus impuestos. Lo anterior ya lo presentó otra gestoría y no se manda.
   ```
   python backoffice.py melso empezar 2026-10-01
   ```
4. Haz commit de `datos/melso.json`.

## Mandar lo pendiente

`python backoffice.py melso pendiente` da en JSON lo que falta: `facturas`, `gastos` y `cobros`, con las rutas de sus PDF.

**Antes de la primera vez, mira las herramientas de Melso.** Lee la descripción y los parámetros de cada una (no las conoces de memoria y pueden cambiar). Si una acción no tiene una herramienta clara, pregunta a la persona antes de improvisar.

Por cada **gasto**:
- Con PDF: súbelo con la acción de Melso para crear un gasto desde un documento (`expenses` → `from_document` o `upload`). Si Melso extrae cifras distintas de las nuestras (base, IVA), no lo corrijas tú: apúntalo para el resumen final.
- Sin PDF (`sin_factura`, la cuota de autónomos): créalo con `expenses` → `create` con los campos del JSON.
- Con el id que devuelve Melso: `python backoffice.py melso apuntar gasto <id> <id_melso>`.

Por cada **factura emitida**:
- Asegúrate de que el cliente existe en Melso (`contacts` → `upsert` con razón social, NIF, país y dirección).
- Sube el PDF como factura emitida fuera de Melso: busca en las herramientas la que registra ingresos o documentos de venta (`documents` → `upload`, o la que indique Melso para facturas emitidas en otro sistema). **No uses `invoices` → `issue`**: eso emitiría una factura nueva en Melso, con otro número.
- Las rectificativas (`tipo: rectificativa`) van igual, indicando la factura que rectifican.
- `python backoffice.py melso apuntar factura <número> <id_melso>`.

Por cada **cobro**: `payments` → `mark_paid` con la fecha de `cobrada`, y `python backoffice.py melso apuntar cobro <número> -`.

Hazlo de uno en uno: si algo falla a mitad, lo apuntado se queda apuntado y lo demás sale otra vez en `pendiente`. Al terminar, una tabla corta (qué, importe, resultado) con las diferencias de cifras que haya visto Melso, y haz commit de `datos/melso.json`.

## Comparar impuestos

«Compara el 303 con Melso»: `python backoffice.py resumen 2026-4T` y `taxes` → `get` del mismo trimestre en Melso. Enséñale las dos cifras y, si no cuadran, qué facturas o gastos faltan en un lado o en otro (`invoices_read`, `expenses_read`). La de Melso es la que presentará su gestor: la nuestra es una estimación.

## Lo que no se hace

- Emitir facturas en Melso, aprobar ni presentar impuestos: eso lo hace la persona en Melso.
- Borrar nada en Melso.
- Mandar lo que es anterior a `desde`.

## Si en el futuro factura con Melso

Melso emite facturas con Verifactu. Si la persona decide facturar desde Melso (por ejemplo, cuando Verifactu le sea obligatorio), este repo deja de emitir y pasa a importar. Eso aún no está hecho: ver `docs/melso.md`.
