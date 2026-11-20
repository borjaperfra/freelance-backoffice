---
name: configurar
description: Pone en marcha el backoffice de un autónomo la primera vez — sus datos fiscales, la cuota de autónomos y las suscripciones, el correo del que salen los gastos, las copias de seguridad y la publicación en Cloudflare. Úsala cuando la persona diga "configura mi backoffice", "empecemos", "acabo de clonar esto", "configura los gastos del correo", o cuando datos/negocio.json no exista o tenga campos PENDIENTE.
---

# Configurar el backoffice

Ve paso a paso y pregunta poco cada vez: una o dos preguntas por mensaje. Al terminar cada bloque, di en una línea qué queda hecho. Si la persona ya tenía una parte configurada, sáltatela.

Empieza siempre con `python backoffice.py doctor`. Te dice qué falta y en qué orden.

## 1. Tus datos

1. Si no existe `datos/negocio.json`: `python backoffice.py init`.
2. Pide sus datos fiscales y rellena `datos/negocio.json`:
   - `nombre` (como sale en las facturas), `nif`, `direccion`, `cp`, `ciudad`, `provincia`, `email`, `iban`.
   - `alta`: fecha de alta como autónomo (AAAA-MM-DD). No se puede facturar antes.
   - `irpf`: 15 por defecto. Si se dio de alta hace menos de tres años, puede aplicar el 7%: pregunta, y si es así, pon `irpf: 7` e `irpf_hasta` con el 31 de diciembre del segundo año siguiente al alta.
   - `vence_dias` (30 por defecto) y `gestoria` (`nombre`, `email`) si tiene.
   - Lo más rápido: que te pase una factura antigua suya o su modelo 036. Saca los datos de ahí y pide que los confirme.
3. No toques `version`: la gestiona `backoffice.py`.

## 2. Gastos fijos

En `datos/gastos/recurrentes.json` (formato en la skill `gasto`): la cuota de autónomos (lo que le cobran de verdad, no la tabla) y las suscripciones que usa para trabajar. Pregunta con una lista corta de ejemplos: diseño, correo, hosting, IA, teléfono. Luego `python backoffice.py recurrentes`.

## 3. El correo del que salen los gastos

El objetivo: que «revisa los gastos» encuentre las facturas nuevas sin que la persona tenga que reenviar nada. Pregunta: **¿dónde te llegan las facturas de tus proveedores?**

**Gmail.** Mira si tienes las herramientas de Gmail (`search_threads`, `get_thread`). Si no, dile cómo conectarlo: en claude.ai, *Settings → Connectors → Gmail*, y vuelve a abrir Claude Code. Pon `"correo_gastos": "gmail"` en `negocio.json`.

**Outlook o Microsoft 365.** Igual, con el conector de Microsoft 365. `"correo_gastos": "outlook"`.

**Otro correo, o prefiere no conectar nada.** La carpeta `bandeja/` del repo (no se sube a GitHub): deja ahí los PDF y dile «apunta lo de la bandeja». `"correo_gastos": "bandeja"`. Créala si no existe.

Con Gmail u Outlook, sigue:

1. **Buzón.** Pregunta si tiene una dirección o etiqueta solo para facturas (un alias tipo `facturas@`, o un filtro que etiquete). Si la tiene, guárdala en `email_gastos` o `etiqueta_gastos`. Si no, no hace falta: recomiéndalo solo si recibe mucho correo.
2. **Remitentes.** Busca facturas de los últimos 90 días: `(factura OR invoice OR recibo OR receipt) has:attachment newer_than:90d`. Agrupa por dominio del remitente y enséñale una tabla corta: dominio, cuántas, ejemplo de asunto. Pregunta cuáles son del negocio.
   - Los del negocio que se repiten cada mes: añade el dominio a `remitentes` del gasto fijo que corresponda en `recurrentes.json` (o crea el gasto fijo si no estaba).
   - Los del negocio que no se repiten: no hace falta guardarlos; los encontrará la búsqueda general.
   - Los que no son del negocio (supermercado, ocio, la luz de casa): a `no_apuntar` en `negocio.json`.
3. **Prueba en seco.** `python backoffice.py correo 45` te da la búsqueda exacta y lo que ya está apuntado. Haz la búsqueda y enséñale una tabla de lo que apuntarías: proveedor, fecha, importe, tipo de IVA. **No apuntes nada todavía.** Corrige con lo que te diga (afectación del teléfono, algo que no es del negocio) y, con su sí, apúntalo con la skill `gasto`.
4. **Cada cuánto.** Pregunta cada cuántos días quiere revisarlo (14 por defecto) y guárdalo en `revisar_correo_dias`. Cuando pase ese tiempo, el admin lo saca en «Lo que falta» con la frase para pedírtelo. Al terminar cada revisión: `python backoffice.py correo hecho`.

## 4. Clientes y voz

Si quiere, sus clientes y proyectos en marcha (skill `backoffice`) y su voz para los textos a clientes en `datos/voz.md`: unos párrafos sobre cómo escribe, o dos o tres emails suyos de ejemplo.

`python backoffice.py revisar` y `python backoffice.py servir`: que vea su admin en local.

## 5. Copias y repo privado

1. Comprueba que el repo de GitHub es **privado** (`gh repo view --json visibility`). Si es público, para y díselo antes de hacer `git push`: sus datos fiscales y facturas quedarían a la vista.
2. Pregunta dónde guardar las copias: una carpeta fuera del repo que se sincronice sola (Google Drive, Dropbox, iCloud, OneDrive). `python backoffice.py copia "<carpeta>"`. La recuerda para las siguientes.
3. `python backoffice.py proteger`. Con el plan gratuito de GitHub no funciona en repos privados: díselo sin dramatismo. `.claude/settings.json` ya impide que Claude Code reescriba la historia.

## 6. Publicar (opcional)

Para tener el admin en su dominio y los espacios de cliente. Lo que hace falta:

1. Una cuenta de Cloudflare (gratis) con un dominio, o un subdominio de uno que ya tenga allí. Pon `"dominio": "https://backoffice.sudominio.com"` en `negocio.json`.
2. Zero Trust activado una vez: Cloudflare → *Zero Trust* → elige un nombre de equipo y el plan Free.
3. Un token de Cloudflare: *My Profile → API Tokens → Create Token → Custom token* con estos permisos:
   - Account · Cloudflare Pages · Edit
   - Account · Access: Apps and Policies · Edit
   - Account · Access: Organizations, Identity Providers, and Groups · Read
   - Account · Account Settings · Read
   - Zone · DNS · Edit (en la zona de su dominio)
4. **Que ejecute él** en una terminal, fuera del chat: `python backoffice.py cloudflare`. Pide el token sin enseñarlo, crea el proyecto de Pages, el dominio, el DNS y la aplicación de Access, y guarda en GitHub los secretos y las variables. **No le pidas el token ni lo pegues en el chat.**
5. `git push` y, cuando el workflow salga en verde, `python backoffice.py doctor`: tiene que decir que `/admin/` pide login.

Si algo falla o prefiere hacerlo a mano, `docs/instalar.md` lo cuenta paso a paso. Hasta que estén las variables de Access, `/admin/` responde 403: nunca queda abierto.

## 7. Melso (opcional)

Si lleva sus impuestos con Melso, sigue la skill `melso`.

## Al terminar

`python backoffice.py doctor` otra vez, y un resumen de tres o cuatro líneas: qué está listo, qué queda y qué decirte para seguir.

Recuérdale lo de Verifactu: las facturas no se envían a Hacienda. Cuando le sea obligatorio, tendrá que facturar con un sistema que lo cumpla (Melso lo hace, por ejemplo). Es responsabilidad suya.
