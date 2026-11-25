# Servicio de voz (feature 012): Whisper (audio a texto) + intención con Ollama + API de BarberForge + Piper (voz).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    WHISPER_DIR=/modelos/whisper PIPER_DIR=/modelos/piper HF_HUB_DISABLE_TELEMETRY=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Los modelos se descargan al construir la imagen, así el contenedor arranca sin internet.
#   WHISPER_MODEL: tiny (más rápido) · base (equilibrio, por defecto) · small (más preciso, más lento)
#   PIPER_VOZ: voz en español de https://huggingface.co/rhasspy/piper-voices (si falla, el navegador lee la respuesta)
ARG WHISPER_MODEL=base
ARG PIPER_VOZ=es_MX-claude-high
RUN mkdir -p /modelos/whisper /modelos/piper \
    && python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8', download_root='/modelos/whisper')" \
    && (python -m piper.download_voices --download-dir /modelos/piper "${PIPER_VOZ}" \
        || echo "AVISO: no se descargó la voz de Piper; el navegador leerá las respuestas")
ENV WHISPER_MODEL=${WHISPER_MODEL} PIPER_VOZ=${PIPER_VOZ} HF_HUB_OFFLINE=1

COPY app ./app
# Usuario sin privilegios.
RUN useradd --create-home --uid 10001 app && chown -R app /modelos
USER app
EXPOSE 8001
HEALTHCHECK --interval=20s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/voz/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
