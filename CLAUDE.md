# Freelance Backoffice

El backoffice de un autónomo en este repo. Tú (Claude Code) eres quien mete los datos: clientes, proyectos, facturas, gastos, trimestres y espacios de cliente. La web (`/admin/`) solo los enseña.

- Datos: JSON en `datos/` (formato en `docs/datos.md`). Con `BACKOFFICE_DATOS=demo`, los de ejemplo de `demo/`.
- Motor: `python backoffice.py` (solo biblioteca estándar; Chrome para los PDF). Sin argumentos, lista los comandos.
- Skills: `configurar` (primera vez), `backoffice` (clientes, proyectos, horas, preguntas), `factura`, `gasto` (gastos, gastos fijos, trimestres, ZIP para la gestoría) y `espacio` (propuestas y espacios privados para clientes).

## Reglas

- Habla con la persona en su idioma y corto. Da la cifra primero.
- **No inventes datos fiscales ni cifras.** Si falta algo, déjalo como `"PENDIENTE"` y pregunta.
- **Una factura emitida no se edita ni se borra.** Se rectifica.
- **Confirma antes de emitir una factura** y antes de dar o quitar acceso a un espacio.
- Los emails (facturas, recordatorios, seguimientos, la gestoría) se dejan en **borrador**. Nunca los envíes.
- Las claves de los enlaces personales no se guardan en ningún sitio: se enseñan una vez. No las mandes a servicios externos.
- Las cifras de impuestos (303, 130) son una estimación para la gestoría, no asesoramiento. Dilo si preguntan si es exacto.
- Si existe `datos/voz.md`, escribe los textos para clientes (espacios, emails) con esa voz.

## Publicar

Después de cualquier cambio en `datos/`:

```
python backoffice.py revisar
git add datos && git commit -m "<qué ha cambiado>" && git push
```

GitHub Actions despliega en Cloudflare Pages al subir a `main`. Si `revisar` encuentra algo, arréglalo antes.
