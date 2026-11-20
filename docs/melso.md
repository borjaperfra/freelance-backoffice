# Melso

[Melso](https://melso.ai) es una gestoría online: te llevan el IVA, el IRPF y la renta, y tienen un software detrás. Si llevas tus impuestos con ellos, el backoffice les puede mandar lo que haces aquí, para que no tengas que subirlo dos veces.

## Qué hace la conexión

- Manda a Melso cada **gasto** con su PDF. Melso lo lee y lo contabiliza.
- Manda cada **factura emitida** con su PDF, y da de alta al cliente si no existe.
- Marca como cobradas en Melso las facturas que cobras aquí.
- **Compara impuestos**: pones tu estimación del 303 al lado de la que ha calculado Melso, y si no cuadran busca qué falta en cada lado.

No emite facturas en Melso, no aprueba ni presenta impuestos y no borra nada allí. Eso lo haces tú en Melso, que es como funciona Melso de todas formas: ninguna integración puede presentar un impuesto sin que lo apruebes.

Las facturas se siguen emitiendo aquí, con tu numeración. Melso las recibe como facturas emitidas en otro sistema.

## Cómo se conecta

Melso tiene un servidor MCP (la forma estándar de conectar herramientas a Claude) en `https://mcp.melso.ai/mcp`. Entras con tu cuenta de Melso y das permiso para una empresa.

1. En una terminal:

   ```
   claude mcp add --transport http melso https://mcp.melso.ai/mcp
   ```

2. En Claude Code, escribe `/mcp`, elige **melso** y autentícate. Se abre Melso en el navegador.
3. Dile a Claude Code **«conecta Melso»**. Te preguntará desde qué fecha lleva Melso tus impuestos: lo anterior no se manda.

A partir de ahí, «manda lo pendiente a Melso». El admin te avisa en «Lo que falta» cuando hay algo por mandar, y la skill `gasto` lo propone antes de cerrar cada trimestre.

## Qué se guarda

`datos/melso.json` apunta qué se ha mandado y con qué id quedó en Melso:

```json
{
  "desde": "2026-10-01",
  "facturas": { "2026-002": { "id": "…", "fecha": "2026-11-20" } },
  "gastos": { "2026-10-05-adobe-systems-software-ireland": { "id": "…", "fecha": "2026-11-20" } }
}
```

Va en un archivo aparte porque una factura emitida no se toca, ni siquiera para añadirle el id de Melso.

`python backoffice.py melso pendiente` enseña lo que falta por mandar.

## Lo que hay que saber

**Está sin estrenar.** La conexión se ha hecho con la documentación pública de Melso y su servidor MCP, pero todavía no se ha probado con una cuenta real. Las herramientas de Melso cambian de nombre o de parámetros de vez en cuando, así que la skill le pide a Claude que las lea antes de usarlas y que pregunte si algo no encaja. La primera vez, mira con calma lo que hace.

**Facturas emitidas en otro sistema.** Melso documenta cómo registrar ingresos que no se han facturado con ellos, pero el detalle de cómo hacerlo por MCP hay que confirmarlo en la primera sincronización.

**Hay una API para programas.** Melso tiene también una API REST para partners, en beta privada (se pide acceso a hello@melso.ai). Con ella la sincronización podría hacerse sola en GitHub Actions, sin Claude Code de por medio. Ahora mismo no la usamos.

## Facturar con Melso (pendiente)

Melso emite facturas con Verifactu, que para los autónomos será obligatorio previsiblemente desde julio de 2027. Llegado ese momento, una opción es que las facturas se emitan en Melso y el backoffice las importe: preparar la factura aquí, que la apruebes en Melso y traer de vuelta el número y el PDF.

No está hecho. Obliga a cambiar cómo se numeran y se validan las facturas en este repo, y necesita probarse con una cuenta real. Si te interesa, abre un issue.
