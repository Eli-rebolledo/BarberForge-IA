"""Cliente de Ollama (IA local): embeddings y generación de texto."""
import logging

import httpx

from app.config import get_settings
from app.core import metricas

log = logging.getLogger(__name__)


def embedding(texto: str) -> list[float] | None:
    """Vector del texto, o None si Ollama no responde o aún no descargó el modelo."""
    s = get_settings()
    try:
        r = httpx.post(f"{s.ollama_url}/api/embeddings", json={"model": s.embed_model, "prompt": texto, "keep_alive": "30m"}, timeout=30)
        r.raise_for_status()
        return r.json()["embedding"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        log.debug("embedding no disponible: %s", e)
        return None


def generar(prompt: str) -> str:
    s = get_settings()
    with metricas.cronometro_llm(s.llm_model):
        return _generar(s, prompt)


def _generar(s, prompt: str) -> str:
    r = httpx.post(f"{s.ollama_url}/api/generate", timeout=180,
                   json={"model": s.llm_model, "prompt": prompt, "stream": False, "keep_alive": "30m",
                         "options": {"temperature": 0.2, "num_predict": 200, "num_ctx": 2048}})
    r.raise_for_status()
    return r.json()["response"].strip()


def precalentar() -> None:
    """Carga en memoria el LLM y el modelo de embeddings al arrancar (y los deja 30 min). Sin esto, la primera
    pregunta del día espera además a que Ollama cargue el modelo desde el disco."""
    s = get_settings()
    for cuerpo in ({"model": s.llm_model, "keep_alive": "30m"}, ):
        try:
            httpx.post(f"{s.ollama_url}/api/generate", json=cuerpo, timeout=300).raise_for_status()
        except httpx.HTTPError as e:
            log.info("no se pudo precalentar %s: %s", cuerpo["model"], e)
    embedding("calentamiento")
