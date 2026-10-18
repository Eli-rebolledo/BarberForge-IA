"""Lectura segura de imágenes enviadas como data URL (fotos de barberos y logo de la barbería).
Solo JPEG, PNG y WebP: se revisa la firma real del archivo (no se aceptan SVG, que pueden llevar scripts)."""
import base64
import binascii
import re

from app.services.errores import DatosInvalidos

_DATA_URL = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,(.+)$", re.S)
_FIRMAS = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n", "image/webp": b"RIFF"}


def leer_data_url(data_url: str, max_bytes: int) -> tuple[bytes, str]:
    m = _DATA_URL.match(data_url.strip())
    if not m:
        raise DatosInvalidos("La imagen debe ser JPG, PNG o WebP")
    mime = m.group(1)
    try:
        datos = base64.b64decode(m.group(2), validate=False)
    except (binascii.Error, ValueError):
        raise DatosInvalidos("No se pudo leer la imagen") from None
    if not datos or len(datos) > max_bytes:
        raise DatosInvalidos(f"La imagen es muy pesada (máximo {max_bytes / 1_000_000:.1f} MB)".replace(".", ","))
    if not datos.startswith(_FIRMAS[mime]) or (mime == "image/webp" and datos[8:12] != b"WEBP"):
        raise DatosInvalidos("El archivo no es una imagen válida")
    return datos, mime
