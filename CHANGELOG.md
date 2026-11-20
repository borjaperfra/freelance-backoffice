# Cambios

Cada versión, con lo que trae y si hay que hacer algo al actualizar. `python backoffice.py actualizar` enseña la sección de la versión nueva antes de instalarla.

## 0.2.1 · 2026-11-20

- `cloudflare`: si el token no se ha pegado bien (pasa en algunas terminales de Windows con Ctrl+V), lo dice en vez de hablar de permisos.
- Demo pública en backoffice.borjaperezfrances.com, con el admin y los espacios abiertos.

## 0.2.0 · 2026-11-20

Para actualizar desde la 0.1: copia los archivos de esta versión encima de los tuyos (la 0.1 no tenía `actualizar`), sin tocar `datos/`, y ejecuta `python backoffice.py migrar`. Si tenías las variables de Access en `wrangler.toml`, `migrar` las pasa a GitHub.

- **Actualizar** (`actualizar`): trae la última versión del código sin tocar tus datos, y guarda aparte lo que hubieras cambiado.
- **Migraciones** (`migrar`): los datos llevan versión y se ponen al día solos.
- **Copias de seguridad** (`copia`, `restaurar`), con aviso en el admin si la última tiene más de 35 días.
- **Doctor** (`doctor`): comprueba la instalación entera y dice cómo arreglar lo que falle.
- **Publicar en un paso** (`cloudflare`): crea el proyecto de Pages, el dominio, el DNS y Cloudflare Access, y guarda la configuración en GitHub.
- La configuración de Access va en las variables de GitHub, no en `wrangler.toml`.
- **Las facturas emitidas no se pueden cambiar**: `revisar` compara cada factura con la versión con la que entró en git y comprueba que no falte ninguna. GitHub no publica si una ha cambiado, aunque haya otros commits encima, ni si se ha reescrito la historia.
- **Gastos del correo**: configuración guiada, remitentes por gasto fijo, prueba en seco, carpeta `bandeja/` para quien no conecta el correo y recordatorio en el admin (`correo`).
- **Melso**: manda facturas, gastos y cobros a Melso por su servidor MCP (`melso`, skill `melso`). Sin probar todavía con una cuenta real.
- `.claude/settings.json` con permisos: Claude Code no puede reescribir la historia de git ni editar a mano una factura emitida.
- `DEMO = "1"` solo abre el admin si los datos son los de la demo.
- `pdf` sin número solo genera los PDF que faltan.
- `revisar` comprueba también `recurrentes.json`.
- `cloudflare` guarda en GitHub un token aparte, solo con permiso de Pages.
- Tests (`python -m unittest discover -s tests`), que se pasan en cada push.
- Documentación nueva: actualizar, copias, gastos del correo, Melso y problemas frecuentes.

## 0.1.0 · 2026-11-19

Primera versión.
