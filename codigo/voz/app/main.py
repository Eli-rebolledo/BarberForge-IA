"""BarberForge AI · servicio de voz (feature 012).

Flujo: nota de voz → Whisper (texto) → modelo de lenguaje (intención en JSON) → API de BarberForge
(RAG, agendamiento con riesgo de inasistencia por ML, o PQRS) → respuesta en texto y, si hay voz, audio con Piper.
El audio se procesa en memoria y no se guarda."""
import base64
import logging
import threading
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import enrutador, intencion, sintesis, transcripcion
from app.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("barberforge.voz")


def _precargar() -> None:
    try:
        transcripcion.modelo()
        sintesis.voz()
    except Exception as e:  # sin el modelo descargado: se intentará con la primera petición
        log.warning("no se pudieron precargar los modelos: %s", e)
    try:  # deja el LLM en memoria para las frases ambiguas (las demás se resuelven con reglas)
        httpx.post(f"{config().ollama_url}/api/generate", json={"model": config().llm_model, "keep_alive": "30m"},
                   timeout=300)
    except httpx.HTTPError as e:
        log.info("Ollama aún no responde: %s", e)


@asynccontextmanager
async def ciclo(_: FastAPI):
    if config().precargar:
        threading.Thread(target=_precargar, daemon=True).start()
    yield


app = FastAPI(title="BarberForge AI · voz", version="0.1.0", lifespan=ciclo)


class TextoIn(BaseModel):
    texto: str = Field(min_length=1, max_length=500)
    responder_con_voz: bool = False


def _ms(desde: float) -> int:
    return int((time.perf_counter() - desde) * 1000)


def _procesar(texto: str, autorizacion: str | None, con_voz: bool, tiempos: dict) -> dict:
    t = time.perf_counter()
    intento, metodo = intencion.detectar(texto)
    tiempos["entender"] = _ms(t)
    t = time.perf_counter()
    try:
        respuesta, mensaje = enrutador.responder(texto, intento, autorizacion)
    except httpx.HTTPStatusError as e:
        detalle = "La plataforma no pudo atender la solicitud."
        try:
            d = e.response.json().get("detail")
            detalle = d if isinstance(d, str) else detalle
        except ValueError:
            pass
        raise HTTPException(status_code=e.response.status_code, detail=detalle) from e
    except httpx.HTTPError as e:
        log.warning("la API no respondió: %s", e)
        raise HTTPException(status_code=502, detail="La plataforma no está disponible en este momento.") from e
    tiempos["responder"] = _ms(t)
    audio = None
    if con_voz:
        t = time.perf_counter()
        wav = sintesis.sintetizar(respuesta.get("reply", ""))
        tiempos["sintetizar"] = _ms(t)
        audio = base64.b64encode(wav).decode() if wav else None
    return {"intencion": intento, "metodo_intencion": metodo, "mensaje": mensaje, "respuesta": respuesta,
            "audio": audio}


@app.get("/voz/health")
def salud() -> dict:
    c = config()
    return {"status": "ok", "whisper": c.whisper_model, "whisper_cargado": transcripcion.cargado(),
            "tts": sintesis.disponible(), "modelo_intencion": c.llm_model if c.intencion_con_llm else "reglas"}


@app.post("/voz/")
def voz(audio: UploadFile = File(...), responder_con_voz: bool = Form(True),
        authorization: str | None = Header(None)) -> dict:
    """Recibe una nota de voz (webm, ogg, wav o mp3) y responde como el asistente de texto."""
    inicio = time.perf_counter()
    tiempos: dict[str, int] = {}
    datos = audio.file.read(config().max_bytes + 1)
    t = time.perf_counter()
    try:
        texto, duracion = transcripcion.transcribir(datos)
    except transcripcion.AudioInvalido as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    tiempos["transcribir"] = _ms(t)
    if not texto:
        raise HTTPException(status_code=422, detail="No entendí el audio. Habla un poco más cerca del micrófono.")
    salida = _procesar(texto, authorization, responder_con_voz, tiempos)
    tiempos["total"] = _ms(inicio)
    return {"transcripcion": texto, "duracion_s": round(duracion, 1), **salida, "tiempos_ms": tiempos}


@app.post("/voz/texto")
def voz_texto(datos: TextoIn, authorization: str | None = Header(None)) -> dict:
    """Mismo flujo sin el micrófono: sirve para probar la intención y para la evaluación."""
    inicio = time.perf_counter()
    tiempos: dict[str, int] = {}
    salida = _procesar(datos.texto.strip(), authorization, datos.responder_con_voz, tiempos)
    tiempos["total"] = _ms(inicio)
    return {"transcripcion": datos.texto.strip(), **salida, "tiempos_ms": tiempos}
