---
name: backoffice
description: Lleva los clientes, proyectos, hitos y tareas de la persona en su trastienda (datos/) y contesta preguntas sobre su negocio. Úsala cuando la persona diga "nuevo cliente…", "nuevo proyecto para X", "he terminado la Fase 1 de X", "apunta que…", "¿cuánto llevo facturado?", "¿qué me deben?", "¿cómo va el trimestre?", cuando quiera ver el admin, o cuando un cliente acepte una propuesta. Para emitir, cobrar o rectificar facturas, usa la skill factura; para gastos y trimestres, la skill gasto.
---

# Backoffice

El sistema de la persona para llevar su negocio de autónomo. Los datos son archivos JSON en `datos/` (el formato está en `docs/datos.md`: léelo antes de crear nada). La web (`/admin/`) solo los enseña; los cambios los haces tú.

Habla con la persona en su idioma y corto.

## Clientes

Un archivo por cliente: `datos/clientes/<slug>.json`. El slug es el nombre en minúsculas y con guiones (`acme`, `acme-labs`), el mismo que el de su propuesta si la hay.

- Rellena lo que la persona te dé: el nombre, la firma de un email, un PDF, la web.
- `pais` y `tipo` (empresa o particular) deciden el IVA y el IRPF de sus facturas: pregúntalos si no están claros. Un autónomo cuenta como `empresa`.
- Los datos fiscales (razón social, NIF, dirección) no se inventan. Si faltan, déjalos como `"PENDIENTE"` y díselo: hacen falta para facturar, no para tenerlo en el CRM.
- Estados: `contacto` → `propuesta` → `activo` → `pausado` / `cerrado`. Muévelos cuando pase algo (si firma, `activo`).

## Proyectos

Un archivo por proyecto: `datos/proyectos/<cliente>-<algo>.json`.

- **Si hay propuesta** (un espacio en `datos/espacios/<slug>/`, un PDF o un documento que te pase), saca de ahí el precio, las fases y las fechas. Cada fase con precio es un hito.
- Precios siempre en base, sin IVA.
- Estados del proyecto: `propuesta`, `activo`, `pausado`, `terminado`, `perdido`.
- Estados del hito: `pendiente` → `hecho` (terminado, falta facturar) → `facturado` → `cobrado`. Los dos últimos los pone `trastienda.py` al emitir y cobrar: no los toques a mano.
- "He terminado la Fase 1" → el hito pasa a `hecho` y pregúntale si lo facturas ya (skill factura).
- Tareas y notas: añade, marca o borra lo que diga. Las notas son texto libre (decisiones, contexto, lo que dijo el cliente).

**Después de una propuesta nueva** (skill espacio): crea el cliente en estado `propuesta` y el proyecto en estado `propuesta` con sus hitos. Si la aceptan, pasa los dos a `activo`.

## Horas

"Hoy 3 h con Acme", "ayer hora y media de Northwind": añade al proyecto activo de ese cliente, en `horas`:

```json
"horas": [{ "fecha": "2026-11-12", "horas": 3, "nota": "Entrevistas con el equipo" }]
```

Si el cliente tiene más de un proyecto activo, pregunta cuál. `horas_semana` (opcional) es la dedicación pactada: con ella el admin enseña cuánto lleva del mes. Si pregunta "¿cuánto me sale la hora con X?", es lo facturado entre las horas (el admin lo calcula).

## Seguimiento comercial

En los proyectos en `propuesta`:

- `enviada`: fecha en que se mandó la propuesta. Ponla cuando la persona diga que la ha enviado.
- `ultimo_contacto`: actualízala cuando diga que ha hablado con ellos o le han contestado.
- `seguimiento_dias` (7 por defecto): pasados esos días sin contacto, sale en "Lo que falta".

"Prepárame un seguimiento para X": crea un **borrador** en Gmail (nunca lo envíes) para el contacto del cliente, en la voz de la persona (`datos/voz.md`, si existe), corto y sin presión: retoma la propuesta y propone un siguiente paso concreto (una llamada esta semana). Si existe el hilo en que se mandó la propuesta, hazlo como respuesta (`replyToMessageId`).

"X ha aceptado": cliente y proyecto a `activo`, pon `inicio` y fechas a los hitos según la propuesta, y pregunta si deja en borrador la primera factura (skill factura).

## Resumen de la semana

`python trastienda.py semana` saca en Markdown lo que falta, lo que hay por cobrar, las entregas de las dos próximas semanas, lo que hay que apartar y las horas del mes. Úsalo cuando pregunte "¿qué tengo esta semana?" o "¿cómo voy?".

## Preguntas sobre el negocio

Contesta leyendo los JSON (con un script corto de Python si hay que sumar). Los datos están ahí:

- Facturado: suma `base` de `datos/facturas/*/*.json`. Las rectificativas tienen importes negativos, así que sumarlo todo da el neto.
- Pendiente de cobro: `estado == "emitida"` y `tipo == "ordinaria"`; vencidas si `vence` < hoy.
- Gastos: suma `base` (o `gasto_irpf` para el IRPF) de `datos/gastos/*/*.json`.
- Trimestre e impuestos: `python trastienda.py resumen 2026-4T` (ver la skill gasto).

Da la cifra primero, y luego el detalle si hace falta.

## Ver el admin

- En local: `python trastienda.py servir` (abre http://127.0.0.1:8081).
- Publicado: `<dominio>/admin/` (detrás de Cloudflare Access).

## Publicar

Después de cualquier cambio:

```
python trastienda.py revisar
git add datos && git commit -m "<qué ha cambiado>" && git push
```

GitHub Actions despliega el admin al subir a `main`. Si `revisar` encuentra algo, arréglalo antes.

## Lo que no hace

Editar desde el móvil: la web solo enseña. Los cambios pasan por Claude Code.
