# Gastos del correo

La mayoría de las facturas de un autónomo llegan por email: Adobe, Google, el hosting, la fibra. Si conectas tu correo, le dices a Claude Code «revisa los gastos del correo» y busca las facturas nuevas, se descarga los PDF, los lee y los apunta. Tú solo confirmas lo dudoso.

## Qué necesitas

Una de estas tres cosas:

- **Gmail**, conectado a Claude: en claude.ai, **Settings → Connectors → Gmail**. Después, reinicia Claude Code.
- **Outlook o Microsoft 365**, con su conector, de la misma forma.
- **Nada.** Si no quieres que Claude lea tu correo, deja los PDF en la carpeta `bandeja/` del repo y dile «apunta lo de la bandeja». Esa carpeta no se sube a GitHub, y cada factura sale de ella cuando queda apuntada.

## Configurarlo

Dile a Claude Code **«configura los gastos del correo»**. Te hará cuatro preguntas:

1. **Dónde te llegan las facturas**: Gmail, Outlook o la bandeja.
2. **Si tienes un buzón o una etiqueta solo para facturas.** No es obligatorio, pero si recibes mucho correo ayuda: un alias tipo `facturas@tudominio.com` o un filtro de Gmail que etiquete lo que lleva factura.
3. **Qué proveedores son del negocio.** Busca las facturas de los últimos tres meses, te enseña de qué dominios vienen y le dices cuáles cuentan. Los que se repiten cada mes quedan ligados a tus gastos fijos. Los que no son del negocio (el súper, la luz de casa) van a una lista de proveedores que no se apuntan nunca.
4. **Cada cuánto quieres revisarlo.** Cada 14 días por defecto. Cuando toque, el admin te lo recuerda en «Lo que falta».

Antes de apuntar nada, hace una prueba: te enseña una tabla con lo que apuntaría (proveedor, fecha, importe, tipo de IVA) y esperas a decirle que sí. Es el momento de corregir cosas como el porcentaje de la fibra que usas para trabajar.

## Después

«Revisa los gastos del correo» hace siempre lo mismo:

1. `python backoffice.py correo` le da la búsqueda exacta, construida con tus proveedores, tu buzón de facturas, tu fecha de alta y los proveedores excluidos, y la lista de correos ya apuntados.
2. Busca, descarta lo que ya está apuntado y abre cada correo nuevo.
3. Lee la factura (con Stripe, la factura y no el recibo) y la apunta con sus cifras fiscales.
4. Si ese mes había un gasto fijo apuntado con el importe aproximado, lo cambia por el real.
5. Te enseña una tabla con lo que ha hecho y apunta la fecha de la revisión.

No apunta nada dos veces: cada gasto que sale del correo guarda el id del mensaje.

## Lo que se guarda y dónde

| Dónde | Qué |
|---|---|
| `negocio.json` → `correo_gastos` | `gmail`, `outlook` o `bandeja` |
| `negocio.json` → `email_gastos`, `etiqueta_gastos` | Tu buzón o etiqueta de facturas, si tienes |
| `negocio.json` → `no_apuntar` | Proveedores que no se apuntan nunca |
| `negocio.json` → `revisar_correo_dias` | Cada cuántos días te lo recuerda (14) |
| `recurrentes.json` → `remitentes` | Dominios desde los que llega cada gasto fijo |
| `gastos/revision.json` | Cuándo fue la última revisión |

Claude no guarda tus correos. Solo los PDF de las facturas, junto a cada gasto, como si los hubieras pasado tú.

## Cuando no encuentra algo

- **Una factura que sabes que llegó.** Mira de qué dominio viene y dile «añade <dominio> a los remitentes de <gasto fijo>». O pásale el PDF directamente.
- **Facturas que solo están en la web del proveedor** (pasa con algunos bancos, Amazon y aerolíneas). Descárgala y déjala en `bandeja/`. El extracto del banco (`banco`) te dirá qué cargos siguen sin factura.
- **No puede descargar los adjuntos** en una cuenta de empresa con restricciones. La skill `gasto` usa entonces el correo en formato RAW y `adjuntos.py` para sacar los PDF.
