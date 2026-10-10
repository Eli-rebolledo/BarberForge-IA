# 010 · Tareas

## DevSecOps
- [x] Trivy fs (vulnerabilidades + secretos) y reporte no bloqueante de ALTAS
- [x] Trivy config sobre Dockerfiles, charts y OpenTofu
- [x] Trivy image antes de publicar
- [x] Publicación en GHCR con etiquetas OCI de origen y revisión
- [x] SBOM SPDX con Syft
- [x] Firma, atestación y verificación con Cosign (sin llaves)
- [x] `.trivyignore` con justificación y bitácora
- [x] FastAPI 0.115.12 (Starlette 0.46) para cerrar vulnerabilidades conocidas de Starlette 0.38
- [x] nginx sin privilegios; contenedores con disco de solo lectura

## Observabilidad
- [x] Instrumentación OpenTelemetry opcional por variable de entorno
- [x] Métricas de negocio y de llama3
- [x] Chart de observabilidad y perfil de Compose
- [x] Tablero de SLI/SLO cargado automáticamente
- [x] Pruebas: telemetría apagada y encendida (en un proceso aparte)
- [ ] Reglas de alerta y ejercicio de incidente (latencia inducida en llama3)
