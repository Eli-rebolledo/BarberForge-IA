"""Configuración del servicio de voz por variables de entorno."""
import os
from dataclasses import dataclass, field


def _bool(nombre: str, defecto: bool) -> bool:
    return os.getenv(nombre, str(defecto)).strip().lower() in ("1", "true", "si", "sí", "yes")


@dataclass(frozen=True)
class Config:
    api_url: str = field(default_factory=lambda: os.getenv("API_URL", "http://bf-api:8000").rstrip("/"))
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://bf-ollama:11434").rstrip("/"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama3.2:3b"))
    whisper_model: str = field(default_factory=lambda: os.getenv("WHISPER_MODEL", "base"))
    whisper_dir: str = field(default_factory=lambda: os.getenv("WHISPER_DIR", "/modelos/whisper"))
    piper_dir: str = field(default_factory=lambda: os.getenv("PIPER_DIR", "/modelos/piper"))
    piper_voz: str = field(default_factory=lambda: os.getenv("PIPER_VOZ", "es_MX-claude-high"))
    tts_activo: bool = field(default_factory=lambda: _bool("TTS_ACTIVO", True))
    intencion_con_llm: bool = field(default_factory=lambda: _bool("INTENCION_CON_LLM", True))
    max_bytes: int = field(default_factory=lambda: int(os.getenv("VOZ_MAX_BYTES", str(3 * 1024 * 1024))))
    max_segundos: float = field(default_factory=lambda: float(os.getenv("VOZ_MAX_SEGUNDOS", "45")))
    precargar: bool = field(default_factory=lambda: _bool("PRECARGAR_MODELOS", True))


def config() -> Config:
    return Config()
