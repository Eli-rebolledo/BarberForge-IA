"""Texto a voz con Piper (opcional). Si no hay voz instalada, el navegador lee la respuesta."""
import io
import logging
import os
import re
import threading
import wave

from app.config import config

log = logging.getLogger(__name__)
_voz = None
_intentado = False
_candado = threading.Lock()
MAX_CARACTERES = 600


def _ruta() -> str:
    c = config()
    return os.path.join(c.piper_dir, f"{c.piper_voz}.onnx")


def voz():
    global _voz, _intentado
    with _candado:
        if not _intentado:
            _intentado = True
            if config().tts_activo and os.path.exists(_ruta()):
                try:
                    from piper import PiperVoice
                    _voz = PiperVoice.load(_ruta())
                    log.info("voz de Piper cargada: %s", config().piper_voz)
                except Exception as e:
                    log.warning("no se pudo cargar la voz de Piper: %s", e)
            else:
                log.info("síntesis de voz con Piper desactivada o sin voz instalada")
        return _voz


def disponible() -> bool:
    return voz() is not None


def para_leer(texto: str) -> str:
    """Quita lo que suena raro en voz alta (comillas angulares, viñetas) y recorta."""
    t = re.sub(r"[«»*#•]", "", texto).replace("\n", ". ")
    return t[:MAX_CARACTERES]


def sintetizar(texto: str) -> bytes | None:
    v = voz()
    if v is None or not texto.strip():
        return None
    buf = io.BytesIO()
    try:
        with wave.open(buf, "wb") as wav:
            v.synthesize_wav(para_leer(texto), wav)
    except Exception as e:
        log.warning("no se pudo sintetizar: %s", e)
        return None
    return buf.getvalue()
