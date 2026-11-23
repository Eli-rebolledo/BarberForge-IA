# 012 · Tareas

## Fase 1 · servicio de voz
- [x] FastAPI `bf-voz` con Whisper y vocabulario de la barbería
- [x] Intención con Ollama (JSON) y reglas de respaldo

## Fase 2 · conexión con la plataforma
- [x] Enrutador hacia `/api/chat` con el token del usuario (RAG, agendar con riesgo ML, cancelar, mis citas)
- [x] Botón de micrófono en el chat y ruta `/voz/` en nginx

## Fase 3 · PQRS y voz
- [x] Migración 008, `POST /api/pqrs`, `GET /api/admin/pqrs`, correo a los administradores, página del panel
- [x] Piper (opcional) y voz del navegador como respaldo

## Fase 4 · evaluación
- [x] `golden_voz.csv` (30 frases en 12 categorías) y `evaluar_voz.py`
- [x] Procedimiento de grabación y evaluación en `codigo/voz/evaluacion/README.md`

## Fase 5 · despliegue
- [x] Docker Compose (perfil `voz`) y chart de Helm (`voz.enabled`)
- [x] Job `voz` en el CI (ruff + pytest)
- [x] Imagen `barberforge-voz` en la matriz del CI (Trivy, SBOM, Cosign); encendida en dev
