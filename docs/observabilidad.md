# Observabilidad: OpenTelemetry, SLI y SLO

Igual que en el Laboratorio 3, la telemetría va a **grafana/otel-lgtm**, que reúne en un contenedor el recolector
OpenTelemetry, Prometheus (métricas), Tempo (trazas), Loki (logs) y Grafana.

## Qué se mide
| Señal | Origen | Ejemplos |
|---|---|---|
| Trazas | FastAPI, SQLAlchemy y httpx (instrumentación automática) | `POST /api/chat` → consultas SQL → `POST http://…:11434/api/generate` (modelo de lenguaje) |
| Métricas HTTP | FastAPI | `http_server_request_duration_seconds` (por ruta, método y código) |
| Métricas de negocio | `app/core/metricas.py` | `barberforge_citas_creadas_total`, `barberforge_citas_canceladas_total`, `barberforge_recordatorios_enviados_total{tipo}` (40 o 60 min), `barberforge_ml_predicciones_total{nivel}` (alto o bajo, feature 011), `barberforge_chat_respuestas_total{tipo,canal}`, `barberforge_asistente_duracion_seconds{canal}` (chat o voz), `barberforge_llm_duracion_seconds` |
| Logs | `logging` de Python → OTLP | errores de base de datos, recordatorios, indexado del asistente |

La telemetría se activa solo si existe `OTEL_EXPORTER_OTLP_ENDPOINT`. Las pruebas y quien no la use no notan nada.

## Cómo verla
- **Kubernetes:** ya viene activa en dev y staging. Abre Grafana con
  `kubectl port-forward -n observabilidad svc/otel-lgtm 3000:3000` (http://localhost:3000, `admin` / `admin`) y busca
  el tablero **BarberForge › BarberForge · SLI/SLO y operación**.
- **Docker Compose:** pon `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-lgtm:4318` en el `.env` y corre
  `docker compose --profile observabilidad up -d`. Grafana queda en http://localhost:3000, con el tablero y las alertas ya
  cargados (carpeta «BarberForge»). Las alertas llegan por correo a MailHog (http://localhost:8025).

## SLI y SLO

| SLI | Definición | SLO | Por qué |
|---|---|---|---|
| Disponibilidad | Peticiones a la API que no terminan en 5xx ÷ peticiones totales | **≥ 99 %** en 30 días | Una barbería pequeña tolera ~7 h de errores al mes; más que eso hace perder citas |
| Latencia | p95 de la duración de las peticiones, **sin** `/api/chat` | **< 500 ms** | Agendar y ver citas debe sentirse inmediato |
| Peticiones rápidas | Peticiones (sin chat) que responden en < 500 ms | **≥ 95 %** | Complementa el p95 y sirve como SLI de proporción |
| Asistente escrito | p95 de una respuesta del chat, de la pregunta a la respuesta (`canal="chat"`) | **< 60 s** | El modelo corre en CPU: en la evaluación el p95 fue 47 s. No se mide con la vara de la API |
| Asistente de voz | p95 de la parte del asistente en una nota de voz (`canal="voz"`); Whisper y Piper se miden con `scripts/prueba-servicios.py` | **< 60 s** | Igual que el chat, más la transcripción |
| Respuestas útiles | Preguntas con respuesta ÷ preguntas, en 1 hora | **≥ 70 %** («no sé» ≤ 30 %) | Un «no sé» frecuente es un hueco en el conocimiento (LLMOps) |

**Umbrales separados por servicio.** Cada servicio tiene su propio criterio: la API transaccional (login, catálogo,
agendar) en milisegundos y el asistente con IA en segundos. Así una respuesta del modelo que tarda 30 s no dispara la
alerta de la API, y una API lenta no se esconde detrás del tiempo del modelo.

El chat se mide aparte (`barberforge_llm_duracion_seconds`): el modelo de lenguaje en CPU tarda segundos y mezclarlo dañaría el SLI.

**Presupuesto de error.** Con un 99 %, el 1 % de las peticiones del mes puede fallar. El tablero muestra cuánto queda.
Si baja del 25 %, se congelan los cambios no urgentes y se prioriza la estabilidad.

## Alertas
Las reglas están en `plataforma/helm/observabilidad/grafana/alertas.yaml` y se cargan solas, tanto en Kubernetes como
en Docker Compose. Se ven en **Grafana › Alerting › Alert rules** y llegan por correo al contacto `barberforge-correo`.

| Alerta | Expresión (resumida) | Umbral | Espera | Severidad |
|---|---|---|---|---|
| SLO disponibilidad | 1 − 5xx ÷ total, ventana de 10 min | < 99 % | 5 min | crítica |
| API transaccional lenta | p95 sin `/api/chat`, ventana de 10 min | > 500 ms | 10 min | advertencia |
| Presupuesto de error | presupuesto restante de 30 días | < 25 % | 15 min | advertencia |
| Ollama fallando | llamadas al modelo de lenguaje con `estado="error"` por minuto | > 0 | 2 min | advertencia |
| Asistente con IA lento | p95 de `barberforge_asistente_duracion_seconds{canal="chat"}`, 15 min | > 60 s | 10 min | advertencia |
| Asistente de voz lento | p95 de `barberforge_asistente_duracion_seconds{canal="voz"}`, 15 min | > 60 s | 10 min | advertencia |
| Asistente: muchos «no sé» | respuestas `sin_respuesta` ÷ total en 1 h (mínimo 10 preguntas) | > 30 % | 15 min | advertencia |

**Ejemplo (LLMOps).** Si en una hora más del 30 % de las preguntas quedan en «no sé», llega la alerta por correo. Se
revisa la bandeja «Por aprender»: si el problema es del conocimiento (falta un dato), el administrador publica la
respuesta y se reindexa; si es del asistente (entendió mal o el prompt falla), se ajusta, se vuelve a correr el Golden
Dataset y se despliega por pull request; si es el usuario (preguntas fuera de tema o abuso), no se cambia nada.

Cada alerta trae `runbook_url` hacia su sección en [runbook.md](runbook.md#alertas-de-grafana). En Kubernetes, para que
lleguen por correo, define `alertas.smtp.host` en el chart `observabilidad` (por ejemplo, el MailHog de dev).

## Ejercicio de diagnóstico (para la sustentación)
1. Detén Ollama: `docker stop barberforge-ollama`.
2. Pregunta algo al asistente. Responde con el texto guardado (respaldo sin IA).
3. En Grafana › Explore › Tempo, busca la traza de `POST /api/chat`: aparece el intento fallido a `:11434` y su error.
4. En el tablero, «Tiempo de respuesta del modelo de lenguaje» muestra el estado `error`.
5. En unos minutos (pregunta dos o tres veces seguidas) se dispara la alerta «El modelo de lenguaje (Ollama) está fallando» y llega el correo a MailHog.
6. Recupera el servicio con `docker start barberforge-ollama`. La alerta pasa a *Resolved* y llega el aviso de resolución.
   Anota tiempo de detección y de recuperación en el runbook.
