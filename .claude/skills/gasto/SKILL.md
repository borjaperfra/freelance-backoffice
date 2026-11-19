---
name: gasto
description: Apunta los gastos de la persona (autónomo) en su trastienda a partir de facturas en PDF o foto, lleva sus gastos fijos (cuota de autónomos, suscripciones) y cierra el trimestre para la gestoría (303 y 130). Úsala cuando la persona pase una factura o un ticket ("apunta este gasto", "te paso las facturas de noviembre", un PDF o una imagen de factura sin más), cuando hable de su cuota de autónomos o de un gasto que se repite, cuando pregunte cuánto tiene que pagar o apartar este trimestre, o cuando diga "cierra el 4T", "prepara lo de la gestoría" o "ya está presentado".
---

# Gastos y trimestres

Todo pasa por `python trastienda.py` desde la raíz del repo. El script calcula el IVA deducible, el IVA autoliquidado y el gasto para el IRPF; tú solo lees la factura y rellenas el borrador. El formato está en `docs/datos.md`.

Habla con la persona en su idioma y corto.

## Apuntar un gasto

1. **Lee la factura** (PDF o imagen) entera. Si es un archivo que acaba de pasar, cópialo antes a un directorio vacío del scratchpad y trabaja desde ahí.
2. **Escribe el borrador** en el scratchpad:
   ```json
   {
     "fecha": "2026-11-15",            // fecha de la factura, no la del pago
     "proveedor": "Anthropic",
     "nif_proveedor": "",               // si sale en la factura
     "pais": "US",                      // ISO del proveedor
     "numero_factura": "ABC-123",
     "concepto": "Claude Max noviembre",
     "categoria": "software",
     "tipo_iva": "isp_fuera",
     "base": 100,                       // sin IVA, en la moneda de la factura
     "moneda": "USD",                   // si no es EUR
     "iva_pct": 21,                     // solo nacional o ticket, si no es 21
     "afectacion": 100,                 // % que es del negocio
     "notas": ""
   }
   ```
3. **Apúntalo:** `python trastienda.py gasto <borrador.json> <factura.pdf|.jpg>`. Si es el gasto real de un gasto fijo, pon en el borrador `"recurrente": "<id>"` para que ese mes no se apunte también el aproximado. Si la moneda no es EUR, el script pasa a euros con el cambio del BCE de ese día. Si la persona te dice lo que le cobró el banco, pon `"base_eur"` y se usa eso.
4. **Dile en una línea** qué has apuntado y cualquier aviso del script.

Si pasa varias facturas, apúntalas todas y al final dale una tabla corta.

### tipo_iva: cómo elegirlo

| La factura | tipo_iva |
|---|---|
| Proveedor español, con IVA y **su NIF** (el de `negocio.json`) | `nacional` |
| Ticket o factura simplificada **sin tu NIF** | `ticket` (el IVA no se deduce; avísale de que pida factura completa) |
| Proveedor de la UE sin IVA (Figma, Google o Notion facturando desde Irlanda…), con tu NIF-IVA o "reverse charge" | `isp_ue` |
| Proveedor de fuera de la UE sin IVA (Anthropic, OpenAI, Vercel… de EEUU) | `isp_fuera` |
| Sin IVA por naturaleza: cuota de autónomos, seguros, comisiones del banco, formación reglada | `sin_iva` |

Si un proveedor de la UE te cobra IVA de su país (p. ej. 23% irlandés), es que no tiene tu NIF-IVA: apúntalo como `ticket` y dile a la persona que lo dé de alta como empresa en ese servicio.

### categoria

`software`, `equipo`, `formacion`, `seguridad_social`, `gestoria`, `telefono`, `viajes`, `comidas`, `oficina`, `publicidad`, `banco`, `seguros`, `colaboradores`, `otros`.

### afectacion

El % del gasto que es del negocio. 100 por defecto. Teléfono, fibra o algo que también usa en lo personal: pregúntale (lo normal es 50). Si duda, 50 y anótalo en `notas`.

### Lo que no hagas

- No inventes cifras: si la factura no se lee bien, pregúntale.
- No apuntes dos veces la misma factura (el script lo impide si hay número de factura).
- No edites a mano las cifras de un gasto ya apuntado. Si está mal, borra su `.json` y su archivo de `datos/gastos/<año>/` y apúntalo otra vez.
- Un equipo de más de 300 € (ordenador, cámara…) se apunta normal con `categoria: "equipo"`: el script lo deja aparte para que la gestoría lo amortice.

## "Revisa el Gmail" (o el correo que use)

Si la persona tiene un conector de correo (Gmail) en Claude, cuando diga "revisa los gastos" o "revisa el Gmail":

1. Busca las facturas recientes de sus proveedores: los de `recurrentes.json` y los de `datos/gastos/`, y su buzón de facturas si tiene uno (lo pone en `negocio.json`, `email_gastos`). Por ejemplo `(from:(stripe.com OR adobe.com) OR to:<email_gastos>) (receipt OR recibo OR invoice OR factura) newer_than:45d`. Solo lo emitido desde el alta (`alta` en `negocio.json`).
2. Descarta los que ya están apuntados: cada gasto apuntado desde el correo guarda su `gmail_id`. Mira con `grep -r "<id>" datos/gastos`.
3. Por cada uno nuevo: `get_message` para ver adjuntos y descarga el PDF de la **factura** (en Stripe hay dos: `Invoice-…pdf` es la factura, `Receipt-…pdf` el recibo; quédate con la factura). Léelo y apúntalo como siempre, con `"gmail_id": "<id del mensaje>"` en el borrador.
   Si la descarga de adjuntos no está permitida en su organización, pide el mensaje con `get_message` y `messageFormat: RAW`: el resultado se guarda en un archivo JSON y `python -I adjuntos.py <ese archivo> <carpeta del scratchpad>` saca los PDF.
4. Si ese mes había un gasto fijo aproximado del mismo proveedor (sin `archivo`, con `recurrente`), bórralo antes de apuntar el real.
5. Lo que no sea del negocio (supermercado, ocio, suministros que no quiera deducir), ignóralo sin preguntar. Si dudas, pregunta con una lista corta. Si la persona te dice que un proveedor no se apunta nunca, guárdalo en `negocio.json`, `no_apuntar`, y respétalo.

Al final, una tabla: proveedor, fecha, base, qué has hecho.

### La previsión de gastos fijos

En Gastos del admin sale cada gasto fijo mes a mes (`prevision_gastos()` en trastienda.py): *previsto* (aún no ha llegado su día), *pendiente* (ya pasó y no está apuntado: `recurrentes`), *falta factura* (apuntado con el importe aproximado) y *confirmado* (apuntado con su PDF). Confirmar uno = apuntar la factura real con `"recurrente": "<id>"` en el borrador, después de borrar el aproximado de ese mes si lo había. Si el importe real se aleja mucho del de `recurrentes.json`, actualiza su `base` para que la previsión acierte.

## El extracto del banco

La persona pasa el CSV que exporta su banco: el de Revolut tal cual, o cualquiera con columnas `fecha`, `importe` y `concepto` (si las columnas se llaman de otra forma, renómbralas en una copia). No lo guardes en el repo. Cópialo al scratchpad y:

```
python trastienda.py banco <extracto.csv>
```

- **Cobros que cuadran:** enséñaselos y, con su sí, márcalos con el `cobrar` que sugiere el script (con la fecha del banco).
- **Cargos SIN APUNTAR o con "falta la factura":** búscalos en Gmail (paso de arriba). Si no aparecen, díselo para que la descargue de la web del servicio.
- Si un proveedor sale en el banco con un texto que el script no reconoce, añádelo al campo `banco` de su gasto fijo en `recurrentes.json`.

## Gastos fijos

Están en `datos/gastos/recurrentes.json`:

```json
[
  { "id": "cuota-autonomos", "proveedor": "Seguridad Social", "concepto": "Cuota de autónomos",
    "categoria": "seguridad_social", "tipo_iva": "sin_iva", "base": 80, "desde": "2026-11", "sin_factura": true }
]
```

- `dia` (opcional) es el día del mes; sin él, el último. `hasta` (opcional, `AAAA-MM`) para cuando se acabe.
- `sin_factura: true` solo para lo que no tiene factura (la cuota de autónomos, comisiones del banco). Las suscripciones sí tienen factura: no lo pongas, y cada mes saldrá en "Lo que falta" hasta que la persona te pase la factura. Entonces borra el gasto generado y apúntalo con su factura.
- Después de añadir uno, y antes de cerrar un trimestre: `python trastienda.py recurrentes`.

La cuota de autónomos los primeros 12 meses es la tarifa plana; que la persona te diga lo que le cobran de verdad.

## Cuánto tengo que pagar / apartar

`python trastienda.py resumen` (trimestre actual) o `resumen 2026-4T`. Da la cifra primero: "Para el 4T, aparta unos 511 €: 100 de IVA y 411 de IRPF". Luego, si pregunta, el detalle.

## Cerrar un mes

A final de mes (o cuando diga "el ZIP del mes", "lo de la gestoría de noviembre"): si tiene conector de correo, revísalo como arriba para confirmar los gastos fijos de ese mes, y luego `python trastienda.py mes 2026-11`. Deja en `dist/meses/gestoria-2026-11.zip` las facturas emitidas y recibidas en PDF y un `resumen.csv`. El mismo ZIP sale en el admin, en Gastos, junto a cada mes (se rehace al publicar). Avisa de las facturas que falten.

## Cerrar un trimestre

Cuando diga "cierra el 4T" o "prepara lo de la gestoría":

1. `python trastienda.py recurrentes`
2. `python trastienda.py revisar`. Si hay problemas, arréglalos antes.
3. Mira "Lo que falta" (`python -c` sobre `pendientes()` o el admin): si faltan facturas de gastos del trimestre, díselo y pregunta si espera a tenerlas o cierra sin ellas.
4. `python trastienda.py trimestre 2026-4T`. Genera en `datos/trimestres/2026-4T/` el resumen PDF y los libros en Excel, y en `dist/trimestres/gestoria-2026-4T.zip` todo junto con las facturas.
5. Lee el resumen PDF y dale a la persona: lo que sale a pagar del 303 y del 130, los avisos, y la ruta del ZIP para mandárselo a la gestoría.
6. Publica (ver abajo).

Cuando diga que la gestoría ya lo ha presentado: `python trastienda.py presentado 2026-4T` y publica.

Lo que calcula es una estimación para la gestoría: no aplica la deducción del art. 110.3.c en el 130, ni gastos de difícil justificación, ni amortizaciones. Dilo si pregunta si es exacto.

Plazos: 1T, 2T y 3T hasta el día 20 del mes siguiente; 4T hasta el 30 de enero.

## Publicar

```
python trastienda.py revisar
git add datos && git commit -m "Gastos: …" && git push
```
