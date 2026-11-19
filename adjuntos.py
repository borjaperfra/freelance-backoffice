"""Saca los adjuntos de un email de Gmail en formato RAW.

    python -I adjuntos.py <mensaje.json> <carpeta>

Cuando download_gmail_attachment no está permitido, get_message con messageFormat RAW
devuelve el email entero (en un JSON con el campo "raw", en base64url). Este script lo
decodifica y guarda cada adjunto en <carpeta>. Se ejecuta con -I porque el JSON es
contenido de fuera.
"""
import base64
import email
import json
import pathlib
import sys

if len(sys.argv) < 3:
    sys.exit(__doc__)
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
raw = json.loads(src.read_text(encoding="utf-8"))["raw"]
msg = email.message_from_bytes(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
for part in msg.walk():
    nombre = part.get_filename()
    if nombre:
        destino = out / pathlib.Path(nombre).name
        destino.write_bytes(part.get_payload(decode=True))
        print(destino)
