---
name: trabajo
description: Lleva el trabajo de un proyecto por fases en el backoffice (datos/trabajo/<proyecto>/) - fases, entregables en carpetas, documentos en Markdown que salen como presentación o documento con su PDF, decisiones, pruebas y un resumen - y lo comparte entero con el cliente. Úsala cuando la persona diga "monta las fases de X", "nuevo entregable", "escribe la presentación para la reunión", "pasa este documento a la web", "sube la versión", "marca el diseño como revisado", "apunta la decisión de…", "apunta esta prueba", "actualiza el resumen", "pasamos a la fase de…" o "comparte el proyecto con el cliente".
---

# El trabajo de un proyecto

El formato completo está en `docs/trabajo.md`. Léelo antes de crear o cambiar nada. `demo/trabajo/acme-robotica-web/` es un ejemplo entero.

Háblale a la persona en su idioma y corto.

## Reglas

- Todo vive en `datos/trabajo/<proyecto>/`, y `<proyecto>` tiene que existir en `datos/proyectos/`. Si no existe, créalo antes con la skill `backoffice`.
- **No inventes datos, cifras, citas ni resultados de pruebas.** Si falta algo, pregunta o déjalo fuera. Un documento con un hueco es mejor que uno con un dato falso.
- Escribe con la voz de `datos/voz.md` si existe. Concreto: qué se ha encontrado, qué significa y de dónde sale. Sin frases de folleto ni «no es X, es Y».
- Los estados van tal cual los lista `docs/trabajo.md` (`en_revision`, no «En revisión»).
- Confirma antes de compartir el proyecto con el cliente y antes de darle acceso a alguien.

## Empezar el trabajo de un proyecto

1. Pregunta (o saca de la propuesta) las fases del proyecto y qué se entrega en cada una.
2. Crea `espacio.json` con las fases y la actual, y una carpeta (`entregables/NN.json`) por entregable. Lo que aún no ha empezado va como `sin_empezar`.
3. Enséñale la estructura antes de seguir.

## Documentos

- Un `.md` por documento en `documentos/`, con su cabecera. `presentacion` para lo que se enseña en una reunión; `documento` para lo que se lee con calma.
- Presentaciones: pocas palabras por diapositiva, un mensaje por diapositiva y el título diciendo ese mensaje. Para comparar cosas, columnas (`<div class="cols c3" markdown="1">`) o una tabla.
- Después de crear o cambiar uno: `python backoffice.py documentos <proyecto>`. Hace la página y el PDF con Chrome. Abre el PDF y comprueba que no hay nada cortado ni montado. Si una diapositiva no cabe, recorta el texto o usa `[densa]`.
- Versión nueva para enviar al cliente: sube `version`. Un cambio pequeño antes de enviarlo no necesita versión nueva.
- «Márcalo como revisado»: cambia `estado` en la cabecera y vuelve a ejecutar `documentos`.
- Si un documento reemplaza a otro, pon `sustituye: <id del viejo>`. No borres el viejo.

## Fases, decisiones, pruebas y resumen

- «Pasamos a la fase de X»: la anterior a `hecha`, la nueva a `en_curso` y `fase_actual`. Actualiza `proximo_hito`.
- Decisión nueva: `decisiones/D-NNN.json` con el siguiente número, en `propuesta`. Cuando el cliente la cierre, `aprobada` o `rechazada`.
- Prueba nueva: `pruebas/P-NNN.json`. Lo observado, tal cual pasó.
- El resumen (`resumen` en `espacio.json`) cuenta el proyecto en tres o cuatro capítulos con enlaces a las secciones de los documentos. Actualízalo cuando cambie algo importante, no cada día.
- La reunión: `reunion.fecha` y `reunion.presentacion` (el documento que se va a presentar).

## Compartir con el cliente

1. Confirma con la persona. Ojo: el cliente ve todo el trabajo del proyecto, decisiones con sus riesgos incluidas.
2. `"compartir": {"slug": "<slug>"}` en `espacio.json`. El slug no puede ser el de un espacio de `datos/espacios/`.
3. Acceso para una persona: `python backoffice.py enlace <slug> "Nombre Apellido"`. Enseña el enlace una vez, en el chat. No lo guardes ni lo mandes a ningún servicio. Para quitarlo: `revocar`.

## Publicar

```
python backoffice.py revisar
git add datos && git commit -m "Acme: diseño v1.1 en revisión" && git push
```

En local: `python backoffice.py servir`, y en el admin, la ficha del proyecto → «Fases, entregables y documentos».
