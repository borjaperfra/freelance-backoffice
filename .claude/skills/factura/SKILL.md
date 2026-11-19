---
name: factura
description: Emite, cobra y rectifica las facturas de la persona (autónomo) desde su trastienda. Úsala cuando la persona diga que quiere facturar algo ("factura a Acme la Fase 0", "hazle una factura a X por 2.000 €"), que le han pagado ("me ha pagado X", "cobrada la 2026-003") o que una factura está mal y hay que anularla o rectificarla.
---

# Facturas

Todo pasa por `python trastienda.py` (desde la raíz del repo). El script pone el número, calcula el IVA y el IRPF según el cliente y genera el PDF. Los datos están explicados en `docs/datos.md`.

Habla con la persona en su idioma y corto.

## Reglas que no se rompen

- **Una factura emitida no se edita ni se borra.** Ni el JSON ni el PDF. Si está mal, se rectifica y se emite otra.
- **Los números van seguidos y las fechas, en orden.** No emitas con fecha anterior a la última factura. El script ya lo impide: no intentes saltártelo.
- **No inventes datos fiscales.** Si al cliente le falta razón social, NIF o dirección, pídeselos a la persona o sácalos de un documento que te pase (una factura o un contrato suyos). Si los encuentras en la web, di de dónde salen y pide que los confirme.
- **Confirma antes de emitir.** Emitir gasta un número. Enséñale el resumen y espera un sí.

## Emitir

1. **Cliente.** Búscalo en `datos/clientes/` por nombre o razón social. Si no existe, créalo con la skill `backoffice` antes de seguir.
2. **Qué se factura.** Si habla de un hito ("la Fase 0"), búscalo en `datos/proyectos/` de ese cliente: el importe y el nombre salen de ahí. Si no, usa lo que diga. Los importes son siempre la base, sin IVA. Si dice "2.000 € con IVA" o "que me lleguen 2.000 €", calcula la base y enséñale la cuenta.
3. **Conceptos.** Escribe la descripción concreta y corta, como la diría la persona: "Fase 0: diagnóstico de marca y posicionamiento", no "Servicios de consultoría". Sin el nombre del cliente ni la fecha (ya salen en la factura).
4. **Borrador.** Escríbelo en el scratchpad (no en el repo):
   ```json
   {
     "cliente": "acme",
     "fecha": "2026-11-11",
     "proyecto": "acme-marca",
     "hito": "Fase 0",
     "conceptos": [{ "descripcion": "Fase 0: diagnóstico de marca", "cantidad": 1, "precio": 3000 }],
     "vence_dias": 30,
     "notas": ""
   }
   ```
   `fecha` es hoy salvo que diga otra. `proyecto` y `hito` son opcionales: si van, el hito pasa a "facturado" solo. `vence_dias` es opcional (por defecto, el del cliente o 30).
5. **Confirmación.** Enséñale en 4 o 5 líneas a quién, qué, la base, el IVA, el IRPF y el total. Para calcularlo sin emitir: el IVA es del 21% salvo para empresas de la UE y clientes de fuera de la UE (0%); se retiene el IRPF de `negocio.json` (15%, o 7% los primeros años) solo a empresas y autónomos de España.
6. **Emitir.** `python trastienda.py emitir <borrador.json>`. Si falla por datos de `negocio.json` o del cliente, dile exactamente qué falta.
7. **Revisa el PDF** (`datos/facturas/<año>/<número>.pdf`): léelo y comprueba que el total y los datos del cliente cuadran.
8. **Publica** (ver abajo). Si el script avisó de algo (cliente de la UE: VIES, ROI y modelo 349), díselo.
9. **Déjale el email listo en Gmail** (ver "Mandar la factura"). Si el cliente no tiene `email_facturas`, pregúntale a quién va y guárdalo en su ficha.

## Mandar la factura

Nunca envíes: crea un **borrador** en Gmail (`create_draft`) para que la persona lo revise y le dé a enviar.

- Para: el `email_facturas` del cliente (con copia al contacto si la persona lo pide).
- Asunto: `Factura <número> · la persona Pérez`.
- Cuerpo corto, en la voz de la persona (`datos/voz.md`, si existe): qué se factura, el total, el vencimiento y el IBAN. Sin frases de folleto. Firma "la persona".
- Adjunto: el PDF. Calcula su hash (`python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <pdf>`) y pásalo como `content: "sha256:<hash>:<ruta absoluta con />"`, `filename: "<número>.pdf"`, `mimeType: "application/pdf"`.

Dile que lo tiene en borradores y dale el enlace.

## Recordatorio de cobro

Cuando una factura vence sin cobrar, sale en "Lo que falta". Si la persona dice "prepárale el recordatorio a X":

- Busca en Gmail el email con el que se mandó la factura (`in:sent <número>`) y crea el borrador **como respuesta** (`replyToMessageId`), con la factura adjunta otra vez.
- Tono amable y corto: "Hola, X: te escribo por la factura <número> de <importe>, que venció el <fecha>. ¿Me confirmas cuándo la tenéis prevista? Gracias." Ajústalo a la voz de la persona.
- Si hace más de 30 días, un poco más directo, sin dejar de ser cordial.

## Borradores

Si la persona quiere dejar una factura preparada sin emitirla todavía ("déjala en borrador", "prepárame la factura de X"), guarda el borrador en `datos/facturas/borradores/<cliente>-<algo>.json` (mismo formato que arriba, normalmente sin `fecha`) y publica. Sale en el admin, en Hoy y en Facturas, con los totales calculados y sin número.

Para emitirlo ("emite el borrador de Northwind"): confirma igual que siempre y `python trastienda.py emitir datos/facturas/borradores/<archivo>.json`. Coge la fecha de hoy si no tiene, y el borrador se borra solo al emitir.

## Cobrar

`python trastienda.py cobrar <número> [AAAA-MM-DD]`. Sin fecha, hoy.

Si dice "me ha pagado Acme" y ese cliente tiene más de una factura emitida sin cobrar, busca la que coincide con el importe que diga o pregúntale cuál. El hito ligado pasa a "cobrado" solo.

## Rectificar o anular

`python trastienda.py rectificar <número> "<motivo>"` crea una rectificativa (serie `R2026-…`) que anula la factura entera, con importes en negativo. Si lo que había que cambiar era el importe o un dato, después se emite una factura nueva y correcta. Confirma antes, igual que al emitir.

## Publicar

```
python trastienda.py revisar
git add datos && git commit -m "Factura 2026-004 a Acme" && git push
```

Al subir a `main`, GitHub Actions despliega el admin y los espacios. Si `revisar` encuentra problemas, arréglalos antes.

## Qué no hace (todavía)

- **Verifactu.** Las facturas no van a Hacienda. Cuando le sea obligatorio (para autónomos, previsto para julio de 2027; que lo confirme), cumplirlo es responsabilidad de la persona: tendrá que usar un sistema que lo cumpla. Si pregunta, recuérdaselo.
- **Mandar el email.** Lo manda la persona con el PDF.
