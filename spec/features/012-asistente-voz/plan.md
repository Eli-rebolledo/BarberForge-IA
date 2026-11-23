# 012 · Plan técnico

## Flujo
```
 Chat (web)  🎤 MediaRecorder (máx. 20 s) ─► POST /voz/ ─► nginx ─► bf-voz
   bf-voz:  1. Whisper (faster-whisper, CPU, int8) ............ audio → texto
            2. Ollama (LLM_MODEL, format=json, temperatura 0) .. texto → intención  (si falla: reglas)
            3. Enrutador ─► pregunta / agendar / cancelar / mis citas ─► POST /api/chat  (con el token del usuario)
                         └► pqrs ─────────────────────────────────────► POST /api/pqrs
               (agendar: citas.agendar ─► prediccion.actualizar_riesgo ─► no_show_risk · feature 011)
            4. Piper (opcional) ........................................ texto → WAV
   web:     muestra «🎤 transcripción», la respuesta con sus botones y la reproduce (Piper o speechSynthesis)
```

## Archivos
| Archivo | Contenido |
|---|---|
| `codigo/voz/app/main.py` | `POST /voz/`, `POST /voz/texto`, `GET /voz/health`; tiempos por etapa |
| `codigo/voz/app/transcripcion.py` | Whisper con vocabulario de la barbería; límites de tamaño y duración |
| `codigo/voz/app/intencion.py` | Prompt JSON para Ollama, validación de la salida y reglas de respaldo |
| `codigo/voz/app/enrutador.py` | Frases que entiende el chat de la API y llamada a `/api/pqrs` |
| `codigo/voz/app/sintesis.py` | Piper (si hay voz instalada) |
| `codigo/voz/Dockerfile` | Descarga Whisper y la voz de Piper al construir; usuario sin privilegios |
| `codigo/voz/evaluacion/` | `golden_voz.csv` (30 frases), `evaluar_voz.py` (WER, intención, latencia) |
| `codigo/backend/app/models/pqrs.py` + migración `008` | Tabla `pqrs` |
| `codigo/backend/app/routers/pqrs.py`, `services/pqrs.py` | Radicar, avisar por correo, listar |
| `codigo/frontend/components/ChatAsistente.tsx` | Botón de micrófono, consentimiento, lectura en voz alta |
| `codigo/frontend/app/admin/pqrs/page.tsx` | Lista de PQRS para el administrador |
| `codigo/frontend/nginx.conf.template` | `/voz/` → `VOZ_UPSTREAM` |
| `plataforma/helm/barberforge/templates/voz.yaml` | Deployment + Service (si `voz.enabled`), NetworkPolicy |

## Decisiones
- **Servicio aparte (ADR-17):** Whisper y Piper ocupan memoria que la API no necesita; separado se escala o se
  apaga sin tocarla, y reutiliza el RAG, el agendamiento y el ML por HTTP, sin duplicarlos.
- **Whisper local (ADR-16):** el audio no sale del servidor. `base` en CPU es el equilibrio; `tiny` o `small` con
  `WHISPER_MODEL`.
- **Intención con el mismo LLM:** no se agrega otro modelo; con `INTENCION_CON_LLM=false` se usan reglas.
