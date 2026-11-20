---
name: mantener
description: Mantiene el backoffice — actualizar a una versión nueva, copias de seguridad, recuperar datos, y comprobar que todo funciona. Úsala cuando la persona diga "actualiza el backoffice", "¿hay versión nueva?", "haz una copia de mis datos", "recupera la copia", "¿está todo bien?", "algo no funciona", o cuando revisar diga que hay que migrar.
---

# Mantener el backoffice

## ¿Está todo bien?

`python backoffice.py doctor`. Repasa Python, Chrome, los datos, las copias, GitHub, Cloudflare y la versión. Por cada ✗ dice cómo arreglarlo: hazlo tú si es un comando, o explícale a la persona lo que tiene que hacer en una web. Si algo no encaja, `docs/problemas.md` tiene los casos frecuentes.

## Actualizar

1. `python backoffice.py actualizar --comprobar`: dice si hay versión nueva y qué trae (del CHANGELOG). Cuéntaselo en dos o tres líneas.
2. Con su sí: `python backoffice.py actualizar`. Trae el código nuevo sin tocar `datos/`, migra los datos si hace falta y pasa `revisar`.
3. Si dice que la persona había cambiado archivos del código, están en `.actualizar/<fecha>/`. Compara con la versión nueva y pregúntale si quiere recuperar algo.
4. `git add -A && git commit -m "Actualizado a la <versión>" && git push`.

Si `git push` falla al cambiar `.github/workflows/`, mira `docs/problemas.md`.

Si `revisar` dice que los datos son de otra versión: `python backoffice.py migrar`, y haz commit.

## Copias

- **Hacer una:** `python backoffice.py copia`. La primera vez pregunta dónde: una carpeta fuera del repo que se sincronice sola (Google Drive, Dropbox, iCloud, OneDrive). Después, haz commit de `datos/copias.json`.
- El admin avisa en «Lo que falta» si la última tiene más de 35 días. Propónla también al cerrar cada trimestre.
- **Recuperar:** confirma antes con la persona qué copia (fecha) y avisa de que sus datos actuales se apartan a `datos-antes-de-restaurar-…/`, no se borran. `python backoffice.py restaurar <ruta del zip>`. Luego `git status` y enséñale qué ha cambiado antes de hacer commit.
- El historial de git también es una copia: un archivo borrado por error se recupera con `git checkout <commit> -- <ruta>`.

## Lo que no hagas

- Reescribir la historia de git (`push --force`, `reset --hard`, `rebase`). Está bloqueado en `.claude/settings.json`, y con razón: ahí están las facturas.
- Tocar a mano una factura emitida para arreglar una actualización. Si `revisar` se queja de una factura, para y pregunta.
