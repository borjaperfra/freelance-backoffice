---
name: espacio
description: Crea y mantiene los espacios privados para clientes (una propuesta, el seguimiento de un proyecto, entregables) y da o quita acceso con enlaces personales. Úsala cuando la persona diga "hazle una propuesta a X", "monta el espacio de X", "actualiza el espacio de X con lo de esta semana", "dale acceso a Ana", "quítale el acceso a…", "¿quién ve el espacio de X?" o cuando quiera compartir algo con un cliente.
---

# Espacios de cliente

Un espacio es una página privada en `<dominio>/c/<slug>/`. Solo se abre con un enlace personal (`?k=<clave>`), uno por persona y revocable. En el repo solo queda el SHA-256 de cada clave; la clave se ve una vez, al crearla.

## Dónde vive

`datos/espacios/<slug>/index.md`, con una cabecera y el texto en Markdown. Cualquier otro archivo de esa carpeta (PDF, imágenes) se publica con él y sale en "Archivos".

```markdown
---
titulo: Web nueva de Acme Robótica
cliente: acme-robotica          # slug del cliente
proyecto: acme-robotica-web     # opcional: enseña sus hitos y facturas
tipo: proyecto                  # proyecto | propuesta
fecha: 2026-11-17
mostrar: hitos, facturas, archivos   # opcional; por defecto, todo
subtitulo:                      # opcional
aceptar:                        # opcional, solo propuestas: el texto de la caja final
---

Texto en Markdown: ## secciones, listas, **negrita**, [enlaces](https://…), tablas, > citas.
```

- `# ` y `## ` son secciones; `### ` subsecciones. El título grande es `titulo`.
- Con `proyecto`, el espacio enseña solo los hitos ("Cómo va") y las facturas de ese proyecto, con su PDF para descargar. Lo que no quieras enseñar, quítalo de `mostrar`.
- Una propuesta termina con una caja "¿Seguimos?" que abre un email a la persona.
- El slug: minúsculas, números y guiones. Normalmente el del cliente o el del proyecto.

## Escribir una propuesta

1. Pide lo que haya: notas de la reunión, el email del cliente, un presupuesto anterior. Si no está claro qué se vende, cuánto cuesta o en qué plazos, pregunta antes de escribir.
2. Estructura que funciona: qué has entendido de su problema, cómo lo harías (fases), inversión (tabla con fases, plazo y precio, siempre + IVA), y cuándo se empezaría.
3. Con la voz de `datos/voz.md` si existe. Concreto y corto: nada de "soluciones integrales" ni promesas que no se puedan cumplir. Sin cifras ni casos inventados.
4. Crea también el cliente y el proyecto en estado `propuesta` con sus hitos (skill `backoffice`), y pon `proyecto:` en el espacio. Cuando la envíe, `enviada` en el proyecto.
5. Enséñale el texto antes de publicarlo.

## Mantener un espacio de proyecto

"Actualiza el espacio de X": cambia la sección de la semana (qué se ha hecho, qué necesitas de ellos, próxima cita) y añade decisiones o archivos. Los hitos y facturas se actualizan solos al publicar.

## Dar y quitar acceso

Confirma siempre antes, con el nombre de la persona y el espacio.

- Dar: `python backoffice.py enlace <slug> "Nombre Apellido"`. Enseña el enlace a la persona **una vez**, en el chat. No lo guardes en ningún archivo ni lo mandes a ningún servicio. Si quiere, déjale un **borrador** de email con el enlace para su cliente (nunca lo envíes).
- Quitar: `python backoffice.py revocar <slug> "Nombre Apellido"`.
- Quién entra: el admin lo enseña en Espacios, o `datos/espacios/accesos.json` (nombres y fechas; los hashes no dicen nada).
- Si alguien pierde el enlace: revoca el suyo y crea uno nuevo.

Los cambios de acceso valen cuando se publica.

## Publicar

```
python backoffice.py revisar
git add datos && git commit -m "Espacio de <cliente>: …" && git push
```

En local, `python backoffice.py servir` y `http://127.0.0.1:8081/c/<slug>/` (en local no pide clave). Publicado, la persona lo ve sin clave en el admin: Espacios → Ver.
