# Copias de seguridad

Tus datos ya están en dos sitios: tu ordenador y GitHub, con todo el historial. Para la mayoría de los sustos basta con eso: un archivo borrado por error se recupera de git.

Lo que no cubre es perder la cuenta de GitHub, o un error que se suba a GitHub y se borre de tu ordenador a la vez. Y las facturas hay que guardarlas años: cuatro por Hacienda, seis por el Código de Comercio. Por eso conviene una tercera copia, fuera de los dos.

## Hacer una copia

```
python backoffice.py copia "C:/Users/tu/Google Drive/backoffice"
```

Crea `backoffice-AAAA-MM-DD.zip` con todo lo que hay en `datos/`, comprueba que el ZIP se abre bien y apunta la fecha en `datos/copias.json`. La carpeta la recuerda, así que las siguientes veces basta con `python backoffice.py copia`. O dile a Claude Code «haz una copia de mis datos».

Elige una carpeta que se sincronice sola con la nube (Google Drive, Dropbox, iCloud, OneDrive). Tiene que estar fuera del repo: si no, se perdería con él.

El admin te avisa en «Lo que falta» si la última copia tiene más de 35 días. Un buen momento para hacerla es al cerrar cada trimestre.

## Recuperar una copia

```
python backoffice.py restaurar "C:/Users/tu/Google Drive/backoffice/backoffice-2026-11-20.zip"
```

Tus datos actuales no se borran: se apartan a `datos-antes-de-restaurar-<fecha>/`. Luego pasa `revisar`. Mira lo que ha cambiado con `git status` antes de hacer commit.

## Recuperar algo con git

Si solo se ha estropeado un archivo:

```
git log --oneline -- datos/clientes/acme.json
git checkout <commit> -- datos/clientes/acme.json
```

Claude Code lo sabe hacer: «recupera la ficha de Acme de ayer».

## Lo que protege tu historial

Claude Code tiene prohibido en este repo reescribir la historia de git (`push --force`, `reset --hard`, `rebase`) y editar a mano una factura emitida (`.claude/settings.json`). Además, si un push cambia o borra una factura emitida, GitHub no publica nada.

Con GitHub Pro, `python backoffice.py proteger` protege la rama `main` para que nadie pueda reescribirla. En el plan gratuito, GitHub no lo permite en repos privados.
