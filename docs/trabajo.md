# El trabajo de un proyecto

Para los proyectos que van por fases y producen documentos (investigación, propuestas, diseño, informes), el backoffice tiene una vista propia. Se abre desde la ficha del proyecto, en «Fases, entregables y documentos». Tiene:

- **Las fases**, con la actual marcada (el punto late).
- **Los entregables**, como carpetas. Lo que aún no ha empezado sale en una lista aparte, «Próximas fases».
- **Cómo seguir**: el resumen del proyecto, la presentación de la próxima reunión (o de la última) y el documento que la respalda.
- **El resumen**: el proyecto contado en capítulos, para leer en unos minutos, con enlaces a la parte exacta de cada documento.
- **Los documentos**, escritos en Markdown. Cada uno sale como página (presentación 16:9 o documento con índice) y como PDF, con sus versiones.
- **Las decisiones**, abiertas y tomadas.
- **Las pruebas**: lo que se ha probado con el producto o con clientes, y lo que se ha aprendido.
- **Un buscador** de documentos.

Todo se abre dentro del admin, en un visor con «Volver» y «Cerrar» siempre a la vista. Esc también cierra.

Si quieres, tu cliente ve exactamente lo mismo, en solo lectura, en `/c/<slug>/`, con su enlace personal.

Como el resto del backoffice, no se edita en la web: se lo pides a tu agente de código (la skill `trabajo`).

## Dónde vive

`datos/trabajo/<proyecto>/`, donde `<proyecto>` es el slug de `datos/proyectos/<proyecto>.json`:

```
espacio.json               cabecera, fases, próximo hito, reunión, resumen y si se comparte
entregables/01.json        cada carpeta
documentos/<id>.md         cada documento, en Markdown
decisiones/D-001.json      cada decisión
pruebas/P-001.json         cada prueba
generado/                  páginas, PDF e indice.json (los hace `python backoffice.py documentos`)
```

`demo/trabajo/acme-robotica-web/` es un ejemplo completo.

## espacio.json

```json
{
  "titulo": "Web nueva de Acme Robótica",
  "descripcion": "Una frase sobre el proyecto.",
  "estado": "en_curso",
  "fases": [
    { "id": "descubrimiento", "nombre": "Descubrimiento", "estado": "hecha" },
    { "id": "diseno", "nombre": "Diseño", "estado": "en_curso" }
  ],
  "fase_actual": "diseno",
  "proximo_hito": { "texto": "Aprobar el diseño", "fecha": "2026-12-02" },
  "reunion": { "fecha": "2026-12-02", "presentacion": "00-estado" },
  "dossier": "01-investigacion",
  "resumen": { "frase": "…", "entradilla": "…", "capitulos": [] },
  "compartir": { "slug": "acme-web" }
}
```

| Campo | Qué es |
|---|---|
| `estado` | `en_curso`, `en_pausa` o `cerrado` |
| `fases` | Las del proyecto, en orden. Cada una con `id`, `nombre` y `estado`: `pendiente`, `en_curso` o `hecha` |
| `fase_actual` | El `id` de la fase en la que estáis |
| `reunion` | La fecha de la próxima reunión (o de la última) y el documento que se presenta. Sale en «Cómo seguir» |
| `dossier` | Opcional: el documento «A fondo» de «Cómo seguir» |
| `resumen` | Opcional: el resumen por capítulos (ver abajo) |
| `compartir` | Opcional: `{"slug": "…"}` para que el cliente lo vea en `/c/<slug>/`. El slug no puede ser el de un espacio de `datos/espacios/` |

### El resumen

```json
{
  "frase": "La idea del proyecto en una frase.",
  "entradilla": "Cómo está el proyecto a 20 de noviembre de 2026.",
  "capitulos": [
    {
      "titulo": "Lo que sabemos",
      "entradilla": "Una línea.",
      "puntos": [
        { "titulo": "…", "texto": "…", "ref": { "doc": "01-investigacion", "ancla": "precio", "texto": "Investigación · Precio" } }
      ]
    },
    { "titulo": "Lo que falta decidir", "entradilla": "…", "decisiones": true,
      "aparte": { "titulo": "Lo que todavía no sabemos", "puntos": ["…"] } }
  ]
}
```

- `ref` lleva a un documento. Con `ancla`, a una sección suya: el `id` de un `##` del documento, que es su título en minúsculas, sin tildes y con guiones. La vista del documento las lista.
- `"decisiones": true` pone en ese capítulo las decisiones abiertas.
- `aparte` es una lista corta al final del capítulo.

## entregables/01.json

```json
{
  "codigo": "01",
  "titulo": "Investigación",
  "descripcion": "Entrevistas con clientes, analítica y competencia.",
  "fase": "descubrimiento",
  "estado": "aprobado",
  "tipo": "documentos"
}
```

- `estado`: `sin_empezar`, `en_curso`, `en_revision`, `revisado` o `aprobado`. Si está sin empezar y no tiene documentos, sale en «Próximas fases» y no como carpeta.
- `tipo`: `documentos`, o `pruebas` para la carpeta que enseña el registro de pruebas (con `sintesis`, un texto con lo que dicen las pruebas en conjunto).
- `capitulos` (opcional): partes de esta carpeta que viven dentro de otro documento: `[{"doc": "00-dossier", "ancla": "mercado", "texto": "Dossier · Mercado"}]`.

## documentos/<id>.md

El nombre del archivo es el `id` (minúsculas, números y guiones). Arriba, la cabecera entre dos líneas `---`; debajo, el texto.

```markdown
---
titulo: Dónde está la web nueva
formato: presentacion
version: 1.0
estado: en_revision
fecha: 2026-11-20
entregable: 02
descripcion: Para la reunión del 2 de diciembre.
etiqueta: Reunión
sustituye: 02-diseno-borrador
---
# Dónde está la web nueva

La primera diapositiva es la portada.
---
## Segunda diapositiva

Texto, listas, **negrita**, tablas…
```

| Campo | Qué es |
|---|---|
| `formato` | `presentacion` (diapositivas 16:9, separadas por `---`) o `documento` (para leer, con índice de sus `##`) |
| `version` | `1`, `1.0` o `1.0.2`. Cada versión deja su PDF: `<id>-v<versión>.pdf` |
| `estado` | `borrador`, `en_revision`, `revisado` o `aprobado`. «Sustituido» lo pone solo el documento que lo sustituye |
| `entregable` | Opcional: el código de su carpeta. Sin él, es un documento del proyecto (para «Cómo seguir») |
| `etiqueta` | Opcional: el nombre corto en las pestañas de la carpeta |
| `sustituye` | Opcional: el `id` del documento al que sustituye, que se queda como «Sustituido» |

En las presentaciones:

- `[densa]` o `[frase]` al principio de una diapositiva le dan otra composición: más texto, o una sola frase grande.
- Columnas alineadas, aunque un título ocupe dos líneas:

```markdown
<div class="cols c3" markdown="1">
<div markdown="1">
### Título
Texto.

<p class="dato">Fuente o dato</p>
</div>
…
</div>
```

`c2` a `c5` es el número de columnas.

### Páginas y PDF

```
python backoffice.py documentos <proyecto> [id…]
```

Hace la página y el PDF de los documentos que han cambiado, con Chrome, y los deja en `generado/`. Van al repo como los PDF de las facturas, porque GitHub Actions no los genera. Si cambias un `.md` y no lo ejecutas, `revisar` te lo dice.

Para enviar una versión nueva, sube `version`: la anterior se queda en el historial con su PDF. Si cambias el texto sin subir la versión, se rehace el PDF de esa misma versión.

## decisiones/D-001.json

```json
{
  "codigo": "D-001", "titulo": "Quitar el catálogo en PDF", "estado": "propuesta",
  "fecha": "2026-11-18", "responsable": "Ana Ríos",
  "descripcion": "…", "justificacion": "…", "riesgos": "…",
  "documentos": ["01-investigacion"], "entregables": ["02"]
}
```

`estado`: `propuesta` (sale en «Decisiones abiertas»), `aprobada`, `rechazada` o `sustituida`.

## pruebas/P-001.json

```json
{
  "id": "P-001", "nombre": "Comparar tres modelos", "estado": "hecha", "fecha": "2026-11-14",
  "objetivo": "…", "hipotesis": "…", "esperado": "…", "observado": "…",
  "funciono": "…", "fricciones": "…", "implicaciones": "…", "notas": ""
}
```

`estado`: `prevista`, `en_marcha`, `hecha` o `descartada`. Lo que pongas en `funciono`, `fricciones` e `implicaciones` se junta arriba, en la carpeta de pruebas.

## Compartirlo con el cliente

1. Pon `"compartir": {"slug": "acme-web"}` en `espacio.json`.
2. `python backoffice.py enlace acme-web "Ana Ríos"` (vale también el slug del proyecto). Enseña el enlace una vez.
3. Publica (`revisar`, commit y push).

El cliente ve el trabajo entero, igual que tú y en solo lectura: fases, carpetas, resumen, documentos, decisiones y pruebas. No ve nada más del backoffice (ni facturas, ni otros clientes, ni a quién has dado acceso). En el admin, «Ver como el cliente» te lo enseña tal cual.

Ojo: ve también las decisiones con sus riesgos y los documentos sustituidos. Si algo no debe verlo, no lo pongas en este proyecto.
