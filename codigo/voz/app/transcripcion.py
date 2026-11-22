"""Audio a texto con Whisper (faster-whisper, en CPU)."""
import io
import logging
import os
import threading

from app.config import config

log = logging.getLogger(__name__)
_modelo = None
_candado = threading.Lock()

# Palabras del negocio: ayudan a Whisper a escribir bien los nombres de los servicios.
VOCABULARIO = ("Barbería BarberForge en Popayán. Corte clásico, barba perfilada, combo corte más barba, tratamiento "
               "capilar. Agendar, cancelar cita, mis citas, horario, precio, PQRS, queja, reclamo, sugerencia.")


class AudioInvalido(ValueError):
    pass


def modelo():
    global _modelo
    with _candado:
        if _modelo is None:
            from faster_whisper import WhisperModel
            c = config()
            log.info("cargando Whisper «%s»…", c.whisper_model)
            _modelo = WhisperModel(c.whisper_model, device="cpu", compute_type="int8", download_root=c.whisper_dir,
                                   cpu_threads=os.cpu_count() or 4)
        return _modelo


def cargado() -> bool:
    return _modelo is not None


def transcribir(audio: bytes) -> tuple[str, float]:
    """Devuelve el texto y la duración del audio en segundos."""
    c = config()
    if not audio:
        raise AudioInvalido("No llegó audio.")
    if len(audio) > c.max_bytes:
        raise AudioInvalido("El audio es demasiado largo. Graba un mensaje más corto.")
    try:
        segmentos, info = modelo().transcribe(io.BytesIO(audio), language="es", beam_size=1, vad_filter=True,
                                              initial_prompt=VOCABULARIO, without_timestamps=True,
                                              condition_on_previous_text=False)
        if info.duration > c.max_segundos:
            raise AudioInvalido(f"El audio dura más de {int(c.max_segundos)} segundos. Graba un mensaje más corto.")
        texto = " ".join(s.text.strip() for s in segmentos).strip()
    except AudioInvalido:
        raise
    except Exception as e:  # formato que PyAV no puede leer
        log.warning("no se pudo transcribir: %s", e)
        raise AudioInvalido("No pude leer el audio. Intenta grabar de nuevo.") from e
    return texto, float(info.duration)
