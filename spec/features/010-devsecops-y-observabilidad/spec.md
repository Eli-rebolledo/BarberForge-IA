# 010 · DevSecOps y observabilidad

## Descripción
La cadena de entrega verifica la seguridad del código, de la configuración y de las imágenes, publica un SBOM y
firma cada imagen. La API emite trazas, métricas y logs con OpenTelemetry hacia Grafana, con un tablero de SLI/SLO.
Responde a los módulos 3 y 4 del diplomado.

## Historias de usuario
- Como **equipo**, queremos que el pipeline no deje publicar una imagen con vulnerabilidades críticas ni un manifiesto inseguro.
- Como **auditor**, quiero saber qué dependencias tiene cada imagen (SBOM) y comprobar que salió de nuestro pipeline (firma).
- Como **operador**, quiero ver en un tablero si la API cumple sus objetivos de disponibilidad y latencia.
- Como **operador**, quiero seguir una petición lenta del chat hasta la consulta a la base de datos o a llama3.

## Criterios de aceptación
- [x] CI: Trivy `fs` (vulnerabilidades y secretos, bloquea con CRÍTICAS), Trivy `config` (Dockerfiles, Helm y OpenTofu, bloquea con ALTAS) y Trivy `image` antes de publicar.
- [x] Imágenes publicadas en GHCR con tag del commit; SBOM SPDX generado con Syft y guardado como artefacto.
- [x] Firma sin llaves con Cosign (identidad OIDC del workflow), atestación del SBOM y verificación en el mismo pipeline.
- [x] Hallazgos aceptados en `.trivyignore` con justificación y bitácora en `docs/devsecops.md`.
- [x] Contenedores sin root (API uid 10001, web uid 101), disco de solo lectura y sin capacidades.
- [x] OpenTelemetry en la API: trazas de FastAPI, SQLAlchemy y httpx (llamadas a Ollama), métricas HTTP y de negocio, logs; se activa solo con `OTEL_EXPORTER_OTLP_ENDPOINT`.
- [x] Métricas propias: citas creadas/canceladas, recordatorios, respuestas del chat por tipo y duración de llama3.
- [x] SLO definidos (disponibilidad 99 %, p95 < 500 ms sin el chat) con presupuesto de error, en el tablero «BarberForge · SLI/SLO y operación».
- [x] Observabilidad disponible también en Compose: `docker compose --profile observabilidad up -d`.
- [ ] Alertas en Grafana para el consumo rápido del presupuesto de error.
