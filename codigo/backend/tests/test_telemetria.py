import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI

from app import db as bd
from app.core import metricas, telemetria

PRUEBA_ACTIVA = """
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import db as bd
from app.core import metricas, telemetria
app = FastAPI()

@app.get("/ping")
def ping():
    return {"ok": True}

assert telemetria.configurar(app, bd.engine, "test") is True
assert TestClient(app).get("/ping").json() == {"ok": True}
with metricas.cronometro_llm("llama3"):
    pass
print("TELEMETRIA_OK")
"""


def test_telemetria_apagada_sin_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert telemetria.configurar(FastAPI(), bd.engine, "test") is False
    metricas.citas_creadas.add(1)  # sin proveedor configurado no falla


def test_telemetria_activa_instrumenta_la_app():
    """Se prueba en otro proceso: OpenTelemetry instala proveedores globales que no deben afectar a las demás
    pruebas. Aunque el recolector no exista, la API responde normal (el envío va en segundo plano)."""
    entorno = {**os.environ, "OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:9", "OTEL_BSP_EXPORT_TIMEOUT": "500"}
    r = subprocess.run([sys.executable, "-c", PRUEBA_ACTIVA], cwd=Path(__file__).resolve().parents[1], env=entorno,
                       capture_output=True, text=True, timeout=120)
    assert "TELEMETRIA_OK" in r.stdout, r.stderr[-2000:]
