# 012 · Asistente de voz con RAG y ML

**Depende de:** 007 (asistente RAG), 005 (agendamiento) y 011 (predicción de inasistencias)

## Descripción
El cliente puede hablarle al asistente en lugar de escribir. Un servicio nuevo, **bf-voz**, orquesta varios
modelos locales: **Whisper** convierte el audio en texto, el **modelo de lenguaje** de Ollama identifica la
intención (pregunta, agendar, cancelar, mis citas, PQRS o saludo) y el servicio llama a la **API existente**:
el chat (RAG, agendamiento y cancelación) o el registro de PQRS. Al agendar, la API calcula el **riesgo de
inasistencia con el modelo de ML** de la feature 011. La respuesta vuelve en texto y en voz (**Piper**, o la voz
del navegador si Piper no está disponible).

## Historias de usuario
- Como **cliente**, quiero preguntar o agendar hablando, para no tener que escribir.
- Como **cliente o visitante**, quiero presentar una queja, reclamo, petición o sugerencia de viva voz y recibir un
  número de radicado.
- Como **administrador**, quiero recibir un correo con cada PQRS y verlas en el panel, para responder a tiempo.
- Como **equipo**, queremos medir la voz con un Golden Dataset de audios y la misma meta del asistente de texto.

## Reglas
- El micrófono se usa solo después de que la persona acepta el aviso; la grabación dura como máximo 20 s.
- El audio se procesa en memoria y **no se guarda**; solo queda el texto en el historial del chat (RN21).
- La voz reutiliza la API: mismas reglas por rol, mismos horarios reales y mismas guardas contra la inyección de
  prompts que el chat. El servicio de voz no accede a la base de datos.
- Si Ollama no responde, la intención se detecta con reglas. Si Piper no está, el navegador lee la respuesta.
- Las PQRS tienen un plazo de respuesta de 15 días hábiles y se avisan por correo a los administradores.

## Criterios de aceptación
- [x] `POST /voz/` recibe una nota de voz (webm, ogg, m4a, mp3 o wav) y devuelve transcripción, intención, la
      respuesta del asistente (con sus opciones) y, si hay voz, el audio en WAV.
- [x] `POST /voz/texto` hace el mismo flujo con texto (pruebas y evaluación).
- [x] Agendar por voz pasa por `citas.agendar`, que guarda el riesgo de inasistencia (feature 011).
- [x] `POST /api/pqrs` (también para visitantes) y `GET /api/admin/pqrs`; correo a los administradores.
- [x] Botón de micrófono en el chat (flotante y página), con aviso de consentimiento y lectura en voz alta.
- [x] Página «PQRS» en el panel del administrador.
- [x] Docker Compose con el perfil `voz`; chart de Helm con `voz.enabled` (apagado por defecto, encendido en dev).
- [x] El administrador cambia el estado de cada PQRS y responde desde el panel; la respuesta llega por correo (`PATCH /api/admin/pqrs/{id}`).
- [x] Pruebas: intención por reglas, armado de los mensajes para el chat, servicio con Whisper y API simulados, PQRS.
- [x] Script de evaluación con WER, exactitud de la intención, palabras clave y latencia por etapa.
- [x] Evaluación lista: 30 frases en 12 categorías, `evaluar_voz.py` (WER, intención, palabras clave, latencia por etapa) y `--solo-texto` para medir intención y respuesta sin audios. Las grabaciones se hacen con el micrófono de cada integrante.
- [x] La imagen `barberforge-voz` se construye y escanea con Trivy en cada PR, y en `main` se publica en GHCR con SBOM y firma de Cosign (solo amd64). `voz.enabled: true` en dev; el job «gitops» actualiza su tag.

## Fuera de alcance
- WhatsApp y llamadas telefónicas.
