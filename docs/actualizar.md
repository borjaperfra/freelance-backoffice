# Actualizar

Tu repo nació de la plantilla y no está enlazado con el original, así que las mejoras no te llegan solas. Para traerlas:

```
python backoffice.py actualizar --comprobar
```

Te dice si hay versión nueva y qué trae. Para instalarla:

```
python backoffice.py actualizar
```

O, más fácil, dile a Claude Code «¿hay versión nueva?» y que la instale si te convence.

## Qué hace

1. Se baja la última versión del repo original.
2. Copia encima el código nuevo y borra lo que ya no se usa. **No toca `datos/`** ni tu bandeja.
3. Si habías cambiado algún archivo del código, guarda tu versión en `.actualizar/<fecha>/` antes de pisarlo y te dice cuál.
4. Si el formato de los datos ha cambiado, los pone al día (`migrar`).
5. Pasa `revisar` para comprobar que todo cuadra.

Los cambios quedan preparados en git, sin subir. Míralos con `git diff --cached` si quieres y termina con:

```
git commit -m "Actualizado a la 0.3.0" && git push
```

## Los datos tienen versión

`datos/negocio.json` lleva un campo `version`. Cuando una versión nueva cambia cómo se guardan los datos, trae una migración que los convierte. `actualizar` la aplica sola, pero si alguna vez `revisar` te dice que los datos son de otra versión:

```
python backoffice.py migrar
```

Las migraciones solo añaden o reordenan; nunca tocan una factura emitida.

`python backoffice.py version` te dice en qué versión está el código y en cuál tus datos.

## Si has cambiado el código

Puedes cambiar lo que quieras: es tu repo. Ten en cuenta que al actualizar se pisa, aunque te quede la copia en `.actualizar/`. Si es una mejora que le sirve a más gente, mándala como pull request al repo original y te llegará de vuelta en la siguiente versión.

Lo único que deberías configurar en GitHub, nunca en el código, son las variables de Cloudflare Access. Así ninguna actualización las toca.
