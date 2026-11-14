# Observabilidad: OpenTelemetry, SLI y SLO

Igual que en el Laboratorio 3, la telemetría va a **grafana/otel-lgtm**, que reúne en un contenedor el recolector
OpenTelemetry, Prometheus (métricas), Tempo (trazas), Loki (logs) y Grafana.

## Qué se mide
| Señal | Origen | Ejemplos |
|---|---|---|
| Trazas | FastAPI, SQLAlchemy y httpx (instrumentación automática) | `POST /api/chat` → consultas SQL → `POST http://…:11434/api/generate` (llama3) |
| Métricas HTTP | FastAPI | `http_server_request_duration_seconds` (por ruta, método y código) |
| Métricas de negocio | `app/core/metricas.py` | `barberforge_citas_creadas_total`, `barberforge_citas_canceladas_total`, `barberforge_recordatorios_enviados_total`, `barberforge_chat_respuestas_total{tipo}`, `barberforge_llm_duracion_seconds` |
| Logs | `logging` de Python → OTLP | errores de base de datos, recordatorios, indexado del asistente |

La telemetría se activa solo si existe `OTEL_EXPORTER_OTLP_ENDPOINT`. Las pruebas y quien no la use no notan nada.

## Cómo verla
- **Kubernetes:** ya viene activa en dev y staging. Abre Grafana con
  `kubectl port-forward -n observabilidad svc/otel-lgtm 3000:3000` (http://localhost:3000, `admin` / `admin`) y busca
  el tablero **BarberForge › BarberForge · SLI/SLO y operación**.
- **Docker Compose:** pon `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-lgtm:4318` en el `.env` y corre
  `docker compose --profile observabilidad up -d`. Grafana queda en http://localhost:3000. Si el tablero no aparece
  solo, impórtalo desde `plataforma/helm/observabilidad/dashboards/barberforge-slo.json` (Dashboards → New → Import).

## SLI y SLO

| SLI | Definición | SLO | Por qué |
|---|---|---|---|
| Disponibilidad | Peticiones a la API que no terminan en 5xx ÷ peticiones totales | **≥ 99 %** en 30 días | Una barbería pequeña tolera ~7 h de errores al mes; más que eso hace perder citas |
| Latencia | p95 de la duración de las peticiones, **sin** `/api/chat` | **< 500 ms** | Agendar y ver citas debe sentirse inmediato |
| Peticiones rápidas | Peticiones (sin chat) que responden en < 500 ms | **≥ 95 %** | Complementa el p95 y sirve como SLI de proporción |

El chat se mide aparte (`barberforge_llm_duracion_seconds`): llama3 en CPU tarda segundos y mezclarlo dañaría el SLI.

**Presupuesto de error.** Con un 99 %, el 1 % de las peticiones del mes puede fallar. El tablero muestra cuánto queda.
Si baja del 25 %, se congelan los cambios no urgentes y se prioriza la estabilidad.

## Ejercicio de diagnóstico (para la sustentación)
1. Detén Ollama: `docker stop barberforge-ollama`.
2. Pregunta algo al asistente. Responde con el texto guardado (respaldo sin IA).
3. En Grafana › Explore › Tempo, busca la traza de `POST /api/chat`: aparece el intento fallido a `:11434` y su error.
4. En el tablero, «Tiempo de respuesta de llama3» muestra el estado `error`.
5. Recupera el servicio con `docker start barberforge-ollama`. Anota tiempo de detección y de recuperación en el runbook.
