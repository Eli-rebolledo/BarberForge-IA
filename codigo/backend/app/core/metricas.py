"""Métricas de negocio (OpenTelemetry). Si la telemetría está apagada son operaciones vacías.

En Prometheus aparecen como barberforge_citas_creadas_total, barberforge_chat_respuestas_total, etc."""
import time
from contextlib import contextmanager

from opentelemetry import metrics

_medidor = metrics.get_meter("barberforge")

citas_creadas = _medidor.create_counter("barberforge.citas.creadas", description="Citas agendadas")
citas_canceladas = _medidor.create_counter("barberforge.citas.canceladas", description="Citas canceladas")
recordatorios = _medidor.create_counter(
    "barberforge.recordatorios.enviados", description="Recordatorios enviados (tipo: 40 = confirmación, 60 = aviso extra)")
predicciones = _medidor.create_counter(
    "barberforge.ml.predicciones", description="Citas evaluadas por el modelo de inasistencias (nivel: alto, bajo)")
chat_respuestas = _medidor.create_counter(
    "barberforge.chat.respuestas", description="Respuestas del asistente por tipo (llm, aprendida, accion, sin_respuesta)")
duracion_asistente = _medidor.create_histogram(
    "barberforge.asistente.duracion", unit="s",
    description="Tiempo total de una respuesta del asistente, de la pregunta a la respuesta (canal: chat, voz)")
duracion_llm = _medidor.create_histogram(
    "barberforge.llm.duracion", unit="s", description="Tiempo que tarda el modelo de lenguaje en responder")


@contextmanager
def cronometro_llm(modelo: str):
    inicio = time.perf_counter()
    estado = "ok"
    try:
        yield
    except Exception:
        estado = "error"
        raise
    finally:
        duracion_llm.record(time.perf_counter() - inicio, {"modelo": modelo, "estado": estado})
