# 007 · Tareas

## Backend
- [x] Tabla `knowledge_chunks` con `vector(768)` e índice HNSW
- [x] Cliente de Ollama: embeddings y generación
- [x] Indexado con documentos fijos y catálogo
- [x] Búsqueda semántica con filtro por rol y respaldo por palabras clave
- [x] Guarda contra inyección de prompts
- [x] Intenciones: saludo, mis citas, agenda de hoy, agendar
- [x] Agendamiento guiado con botones y franjas reales
- [x] Indexado al arrancar con reintentos, al cambiar el catálogo y manual
- [x] Pruebas (`tests/test_chat.py`): saludo e inyección, visitante que quiere agendar, agenda guiada, RAG sin Ollama con filtro por rol, sin resultados

## Frontend
- [x] `ChatAsistente` con sugerencias, fuentes y botones
- [x] Chat incrustado en el inicio y flotante en las demás páginas
- [x] Reserva desde el chat con manejo del 409
- [x] Botón “Reindexar asistente”

## Evaluación (2026-11-19)
- [x] Golden Dataset (56 preguntas) y resultados de configA, configB y sin RAG en `docs/evaluacion-rag/`
- [x] `codigo/backend/evaluacion/evaluar_asistente.py`: el mismo dataset contra `POST /api/chat`
- [x] Historial de conversación (iteración 2)

## Iteración 2 (2026-11-13): asistente por rol, historial y aprendizaje
- [x] Historial por usuario en `chat_messages`; `GET/DELETE /api/chat/history`; la pregunta se guarda antes de responder (`pending` mientras piensa).
- [x] Asistente personal: cliente (agendar, ver y **cancelar** citas con confirmación) y barbero (procedimientos internos, agenda de hoy, próximas citas). Página `/asistente`.
- [x] Base de conocimiento editable (`knowledge_docs`) con niveles público/interno; procedimientos de limpieza de máquinas.
- [x] Preguntas sin respuesta y respuestas «no me sirvió» → `unanswered_questions`; el administrador las enseña en `/admin/asistente`.
- [x] Respuesta inmediata desde la base de datos para preguntas ya enseñadas; lo enseñado entra al RAG.
- [x] Pruebas: `tests/test_aprendizaje.py` y nuevos casos en `tests/test_chat.py`.
