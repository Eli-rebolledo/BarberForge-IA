# Hoja de ruta

Las features siguen el orden en que se construyó el sistema: primero la identidad y el catálogo, luego la agenda y al final el asistente y la plataforma.

| # | Feature | Backend | Frontend | Estado |
|---|---|---|---|---|
| 001 | [Autenticación y cuentas](../features/001-autenticacion-y-cuentas/spec.md) | `auth`, `cuenta`, `usuarios` | `/login`, `/registro`, `/cuenta`, `Sesion`, `Panel` | 🟢 Implementada |
| 002 | [Barbería y catálogo de servicios](../features/002-barberia-y-servicios/spec.md) | `barberias`, `servicios` | `/`, `/barberia`, `/admin/servicios` | 🟢 Implementada |
| 003 | [Gestión de barberos](../features/003-gestion-de-barberos/spec.md) | `barberos` | `/admin/barberos`, `BarberoCard`, `FotoEditor` | 🟢 Implementada (alta, edición, foto, días de trabajo) |
| 004 | [Disponibilidad](../features/004-disponibilidad/spec.md) | `disponibilidad`, `cierres`, `arranque` (migración 009) | `/admin/disponibilidad`, `/admin/festivos` | 🟢 Implementada, con festivos (RF09) y ausencias (RF17) |
| 005 | [Agendamiento de citas](../features/005-agendamiento-de-citas/spec.md) | `citas` | `/agendar`, `/citas` | 🟢 Implementada |
| 006 | [Recordatorios y confirmación](../features/006-recordatorios-y-confirmacion/spec.md) | `citas`, `correo`, `arranque` | `/citas` (enviar recordatorio, buzón) | 🟢 Implementada (correos al agendar, recordar y cancelar) |
| 007 | [Asistente con IA y RAG](../features/007-asistente-ia-rag/spec.md) | `chat`, `rag`, `ia`, `aprendizaje`, `asistente` | `ChatAsistente`, `ChatFlotante`, `/asistente`, `/admin/asistente` | 🟢 Implementada y evaluada: 82,1 % con el Golden Dataset de 56 preguntas ([resultados](../../docs/evaluacion-rag/README.md)) |
| 008 | [Plataforma, despliegue y CI](../features/008-plataforma-y-despliegue/spec.md) | `health`, `arranque`, Alembic | Dockerfile + nginx | 🟢 Implementada |
| 009 | [Kubernetes, GitOps e IaC](../features/009-kubernetes-gitops-iac/spec.md) | `tareas` (Job de migraciones) | `plataforma/helm`, `plataforma/argocd`, `plataforma/opentofu` | 🟢 Implementada (recuperación total documentada en el runbook) |
| 010 | [DevSecOps y observabilidad](../features/010-devsecops-y-observabilidad/spec.md) | `core/telemetria`, `core/metricas` | `ci.yml`, `plataforma/helm/observabilidad` | 🟢 Implementada, con alertas de Grafana |
| 011 | [Predicción de inasistencias (ML)](../features/011-prediccion-inasistencias/spec.md) | `ml/`, `prediccion`, `citas`, `tareas` (migración 007) | `Riesgo`, `/admin` (tarjeta del modelo), `/citas` | 🟢 Implementada: modelo inicial con datos sintéticos y reentrenamiento automático con citas reales |
| 012 | [Asistente de voz con RAG y ML](../features/012-asistente-voz/spec.md) | `codigo/voz` (servicio aparte), `pqrs` (migraciones 008 y 009) | `ChatAsistente` (micrófono), `/admin/pqrs` | 🟢 Implementada y funcionando en Compose (perfil `voz`) y en Kubernetes dev |

## Decisiones tomadas
| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-11-03 | Backend en **FastAPI + SQLAlchemy + Alembic** con arquitectura en capas | Sustituye el `main.py` único del primer MVP; permite pruebas por capa y migraciones versionadas. |
| 2026-11-03 | Frontend en **Next.js 16 con exportación estática servida por nginx** | Una página por carpeta y tipos compartidos con la API; sin servidor Node en producción. |
| 2026-11-03 | **Sin gateway aparte:** nginx del frontend hace de proxy inverso de `/api` | Un servicio menos que mantener; la API no necesita CORS. |
| 2026-11-03 | **Migraciones dentro de la API** con reintentos y `pg_advisory_lock` | `/api/health` explica por qué la base no está lista y varias réplicas no migran a la vez. |
| 2026-11-03 | **Agenda de 7 días generada al arrancar** (no en la semilla) | Depende de la fecha; la semilla solo carga datos fijos. |
| 2026-11-11 | **Días de trabajo por barbero** (`users.work_days`, migración 003) y **tema oscuro** azul noche + rojo oscuro | El administrador define qué días atiende cada barbero; la agenda automática y la generación manual respetan esos días. |
| 2026-11-13 | **El calendario de atención solo lo asigna el administrador** | El barbero ya no tiene la pestaña «Mi calendario»; la API devuelve 403 si intenta generarlo, cerrarlo o consultarlo. |
| 2026-11-13 | **Foto del barbero** en la base de datos (`users.photo`, migración 005), reducida a 480 px en el navegador | Los clientes reconocen al barbero por la cara; se muestra en tarjetas, agenda, chat y cabecera. |
| 2026-11-13 | **Historial del chat en la base de datos** (`chat_messages`) solo para usuarios registrados | La conversación sobrevive al cambiar de página o recargar; la pregunta se guarda antes de responder, así una respuesta lenta no se pierde. Los visitantes no tienen historial. |
| 2026-11-13 | **Aprendizaje supervisado del asistente** (`knowledge_docs`, `unanswered_questions`) | Lo que no sabe (o lo que alguien marca como «no me sirvió») llega al administrador; lo que él enseña se responde al instante desde la base de datos y entra al RAG. El modelo no se reentrena. |
| 2026-11-13 | **llama3 para hablar, base de datos para actuar** | Toda pregunta de información la redacta llama3 (incluidas las respuestas enseñadas, como «respuesta oficial»); agendar, cancelar y consultar citas van directo a la base de datos para evitar alucinaciones. |
| 2026-11-13 | **Identidad de la barbería editable** (`shop_settings`, migración 006): logo, nombre, dirección y horario | Cada barbería independiente se personaliza desde «Ajustes» sin tocar el `.env`. |
| 2026-11-18 | **Kubernetes (Minikube) + Helm + Argo CD + OpenTofu** como despliegue principal; Dokploy queda opcional | Entregables del módulo 2 y 4 del diplomado: despliegue declarativo, GitOps e infraestructura reproducible. |
| 2026-11-18 | **Ollama fuera del clúster** (Docker Desktop, gestionado por OpenTofu) | llama3 necesita ~8 GB; en equipos de 16 GB no cabe junto a Minikube. |
| 2026-11-18 | **Worker separado y Job de migraciones** | Varias réplicas de la API sin correos duplicados; el esquema se migra antes de actualizar la API. |
| 2026-11-18 | **Imágenes firmadas con Cosign (sin llaves) y SBOM con Syft** | Procedencia verificable (SLSA / Sigstore) sin administrar llaves privadas. |
| 2026-11-18 | **OpenTelemetry opcional por variable de entorno** hacia `grafana/otel-lgtm` | Mismo stack del Laboratorio 3; sin variable, cero impacto en pruebas y en Compose. |
| 2026-11-18 | **Datos sintéticos para el modelo de inasistencias** (feature 011), con supuestos documentados | No hay tiempo de recolectar citas reales antes de la entrega; el sistema queda listo para reentrenar cuando existan. |
| 2026-11-21 | **llama3.2:3b como modelo por defecto**; la intención de voz se decide primero con reglas y el LLM solo entra si la frase es ambigua | Es el modelo con el que se evaluó el RAG y en CPU responde más rápido que llama3 8B (menos de la mitad de parámetros); las frases claras de voz ya no esperan al LLM. |
| 2026-11-21 | **PQRS también por el chat escrito** | Antes solo se creaban por voz; ahora «Quiero poner una queja: …» radica la PQRS con canal `chat`, número de radicado y aviso al administrador. |
| 2026-11-18 | **Regresión logística, umbral 0,20** | Gana al árbol en AUC (0,71 vs. 0,58) y es explicable; con 0,20 se detectan ~6 de cada 10 inasistencias a cambio de un correo extra. |
| 2026-11-18 | **Modelos reentrenados en la base de datos, firmados con HMAC** | En Kubernetes el disco es de solo lectura y hay varias réplicas; la firma impide cargar un pickle alterado. |
| 2026-11-20 | **Asistente de voz como servicio aparte (`bf-voz`) que usa la API** | Whisper y Piper ocupan memoria que la API no necesita; la voz reutiliza el RAG, el agendamiento y el riesgo ML sin duplicarlos. |
| 2026-11-21 | **Festivos y ausencias como bloqueos, no como borrado de franjas** (migración 009) | Las franjas se borran al bloquear, pero el bloqueo queda guardado: la agenda automática, el chat y la voz lo respetan aunque se regenere el calendario. |
| 2026-11-21 | **Un festivo cancela las citas del día; una ausencia las reasigna** | Si la barbería cierra no hay a quién pasarlas; si falta un barbero, otro puede atender a la misma hora (misma lógica que al desactivarlo). |
| 2026-11-21 | **Alertas de Grafana como archivo versionado** (`grafana/alertas.yaml`) | Las mismas reglas en Kubernetes y en Compose, revisables por pull request, con enlace al runbook. |
| 2026-11-21 | **Imagen de voz solo amd64** | Whisper y Piper bajo emulación ARM alargan el pipeline sin necesidad: los equipos del curso son Windows/Linux. |
| 2026-11-20 | **Whisper local (faster-whisper, `base`) y Piper; intención con el mismo LLM de Ollama** | El audio no sale del servidor; sin modelos de pago y sin agregar otro LLM. Si Ollama falla, la intención se detecta con reglas. |
| MVP | **Dokploy + Docker Compose** para el despliegue | Es lo que se usó en el Laboratorio 4. |
| MVP | **IA local con Ollama** (`nomic-embed-text` + `llama3`) y pgvector | Privacidad de los datos; sin dependencias de nube. |
| MVP | **MailHog** como servidor de correo | Probar recordatorios sin enviar correos reales. |

## Pendientes (backlog)
Ninguno dentro del alcance del diplomado. Trabajo futuro: bot de WhatsApp, sugerencia de corte a partir de una foto de
referencia, y probar localidad y clima como variables del modelo de inasistencias cuando haya citas reales.
