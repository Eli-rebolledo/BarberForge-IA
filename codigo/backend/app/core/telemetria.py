"""Observabilidad con OpenTelemetry: trazas, métricas y logs hacia un recolector OTLP (en el laboratorio,
grafana/otel-lgtm: Grafana + Tempo + Prometheus + Loki en un solo contenedor).

Solo se activa si existe la variable OTEL_EXPORTER_OTLP_ENDPOINT (por ejemplo http://otel-lgtm:4318).
Sin ella la API funciona igual y las métricas propias quedan como operaciones vacías."""
import logging
import os

from fastapi import FastAPI
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)


def activa() -> bool:
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))


def configurar(app: FastAPI, engine: Engine, version: str) -> bool:
    if not activa():
        return False
    # Importes aquí: si la telemetría está apagada no se carga nada de OpenTelemetry.
    from opentelemetry import metrics, trace
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    recurso = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "barberforge-api"),
        "service.namespace": "barberforge",
        "service.version": version,
        "deployment.environment": os.getenv("ENTORNO", "local"),
    })
    trazas = TracerProvider(resource=recurso)
    trazas.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(trazas)
    metrics.set_meter_provider(MeterProvider(resource=recurso, metric_readers=[
        PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=15000)]))
    registros = LoggerProvider(resource=recurso)
    registros.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(registros)
    logging.getLogger().addHandler(LoggingHandler(level=logging.INFO, logger_provider=registros))

    # Las sondas de Kubernetes no se trazan: generarían ruido cada pocos segundos.
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,health/db")
    SQLAlchemyInstrumentor().instrument(engine=engine)
    HTTPXClientInstrumentor().instrument()
    log.info("OpenTelemetry activo: enviando a %s", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
    return True
