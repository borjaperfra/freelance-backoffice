# Los datos

Todo vive en `datos/` y es JSON (o Markdown, los espacios). El nombre del archivo es el identificador (slug). `python trastienda.py init` crea la estructura vacía; `demo/` tiene un ejemplo completo con datos inventados.

## negocio.json

Tus datos fiscales. Salen en cada factura.

| Campo | Qué es |
|---|---|
| `nombre`, `nif`, `direccion`, `cp`, `ciudad`, `provincia`, `pais`, `email` | Tus datos, tal como salen en la factura |
| `iban` | Donde te pagan; sale en la factura |
| `alta` | Fecha de alta como autónomo (AAAA-MM-DD). No se factura antes |
| `iva` | 21 |
| `irpf` | 15, o 7 los primeros años de actividad |
| `irpf_hasta` | Hasta cuándo dura el 7% (después avisa para pasar a 15) |
| `vence_dias` | Días para pagar una factura (30 por defecto) |
| `dominio` | `https://…` donde publicas; sirve para escribir los enlaces de los espacios |
| `gestoria` | `{nombre, email}`: a quién van los ZIP del mes y del trimestre |
| `email_gastos`, `no_apuntar` | Opcionales: tu buzón de facturas y proveedores que no quieres apuntar |

## clientes/<slug>.json

```json
{
  "nombre": "Acme",                  // cómo lo llamas tú
  "razon_social": "Acme S.L.",       // lo que sale en la factura
  "nif": "B12345678",                  // NIF o, en la UE, el NIF-IVA (FR..., DE...)
  "direccion": "Calle ...", "cp": "46001", "ciudad": "Valencia", "provincia": "Valencia",
  "pais": "ES",                        // ISO: ES, FR, US...
  "tipo": "empresa",                   // empresa | particular
  "estado": "activo",                  // contacto | propuesta | activo | pausado | cerrado
  "email_facturas": "",
  "contactos": [{ "nombre": "", "rol": "", "email": "", "telefono": "" }],
  "vence_dias": 30,                    // opcional; si no, el de negocio.json
  "desde": "2026-11",
  "notas": ""
}
```

El IVA y el IRPF salen solos de `pais` y `tipo`:

| Cliente | IVA | IRPF |
|---|---|---|
| España, empresa o autónomo | 21% | se retiene |
| España, particular | 21% | no |
| UE, empresa | 0% (inversión del sujeto pasivo) | no |
| UE, particular | 21% | no |
| Fuera de la UE | 0% (no sujeta) | no |

## proyectos/<slug>.json

```json
{
  "nombre": "Marca y web",
  "cliente": "acme",                 // slug del cliente
  "estado": "activo",                  // propuesta | activo | pausado | terminado | perdido
  "inicio": "2026-11-01", "fin": "2027-02-28",
  "precio": 12000,                     // base, sin IVA
  "hitos": [
    { "nombre": "Fase 0", "fecha": "2026-11-30", "importe": 3000, "estado": "pendiente", "factura": null }
  ],                                   // estado: pendiente | hecho | facturado | cobrado
  "tareas": [{ "texto": "", "hecha": false }],
  "notas": ""
}
```

## facturas/<año>/<número>.json

No se tocan a mano. Las crea `python trastienda.py emitir`, que también escribe el PDF al lado.
Lo único que cambia después es el estado (`cobrar`, `rectificar`).

## gastos/<año>/<id>.json

Cada gasto con su factura al lado (`<id>.pdf` o `.jpg`). Los crea `python trastienda.py gasto <borrador.json> <factura>`, que calcula las cifras fiscales:

| Campo | Qué es |
|---|---|
| `tipo_iva` | `nacional`, `ticket`, `isp_ue`, `isp_fuera` o `sin_iva` (ver `.claude/skills/gasto/SKILL.md`) |
| `afectacion` | % que es del negocio (100 por defecto) |
| `iva_deducible` | lo que se resta en el 303 |
| `iva_autoliquidado` | IVA de proveedores extranjeros: suma y resta en el 303 |
| `gasto_irpf` | lo que cuenta como gasto en el 130 |
| `amortizable` | equipos de más de 300 €: no van a `gasto_irpf`, los amortiza la gestoría |
| `recurrente` | si lo generó un gasto fijo |
| `sin_factura` | true si no tiene factura (cuota de autónomos) |

## gastos/recurrentes.json

Los gastos fijos de cada mes. `python trastienda.py recurrentes` apunta los que falten.

## trimestres/<2026-4T>/

El resumen PDF y los libros en Excel de cada trimestre cerrado (`python trastienda.py trimestre`), y `presentado.json` cuando la gestoría lo ha presentado.

## Campos opcionales

- **Clientes:** `pro_bono` (true: no se le factura; no pide datos fiscales en «Lo que falta»).
- **Proyectos:** `pro_bono` (true: no se factura), `enlaces` (`[{nombre, url}]`, enlaces útiles; salen en la ficha del proyecto), `horas` (`[{fecha, horas, nota}]`), `horas_semana` (dedicación pactada), `enviada` y `ultimo_contacto` (AAAA-MM-DD) y `seguimiento_dias` (7 por defecto) para avisar de propuestas sin respuesta.
- **Gastos:** `gmail_id` si salió de un email (evita apuntarlo dos veces).
- **Gastos fijos:** `banco`, lista de textos con los que aparece el cargo en el extracto ("Adobe", "Google *Workspace"…).
- **facturas/borradores/<slug>.json:** facturas preparadas sin emitir, con el formato del borrador de `emitir`. Se borran solas al emitirlas.

## espacios/<slug>/index.md

Un espacio privado para un cliente: cabecera `clave: valor` y el texto en Markdown. El resto de archivos de la carpeta se publican con él. Formato y uso en `.claude/skills/espacio/SKILL.md`.

## espacios/accesos.json

Quién entra en cada espacio: `{slug: [{nombre, hash, creado}]}`. Lo escriben `python trastienda.py enlace` y `revocar`. Solo guarda el SHA-256 de cada clave.
