# Hoja de ruta

Las features siguen el orden en que se construyó el sistema: primero la identidad y el catálogo, luego la agenda y al final el asistente y la plataforma.

| # | Feature | Backend | Frontend | Estado |
|---|---|---|---|---|
| 001 | [Autenticación y cuentas](../features/001-autenticacion-y-cuentas/spec.md) | `auth`, `cuenta`, `usuarios` | `/login`, `/registro`, `/cuenta`, `Sesion`, `Panel` | 🟢 Implementada |
| 002 | [Barbería y catálogo de servicios](../features/002-barberia-y-servicios/spec.md) | `barberias`, `servicios` | `/`, `/barberia`, `/admin/servicios` | 🟢 Implementada; falta la sección “Barberías” del inicio |
| 003 | [Gestión de barberos](../features/003-gestion-de-barberos/spec.md) | `barberos` | `/admin/barberos`, `BarberoCard`, `FotoEditor` | 🟢 Implementada (con foto del barbero) |
| 004 | [Disponibilidad](../features/004-disponibilidad/spec.md) | `disponibilidad`, `arranque` | `/admin/disponibilidad` (solo administrador) | 🟢 Implementada; faltan festivos y ausencias |
| 005 | [Agendamiento de citas](../features/005-agendamiento-de-citas/spec.md) | `citas` | `/agendar`, `/citas` | 🟢 Implementada |
| 006 | [Recordatorios y confirmación](../features/006-recordatorios-y-confirmacion/spec.md) | `citas`, `correo`, `arranque` | `/citas` (enviar recordatorio, buzón) | 🟢 Implementada |
| 007 | [Asistente con IA y RAG](../features/007-asistente-ia-rag/spec.md) | `chat`, `rag`, `ia`, `aprendizaje`, `asistente` | `ChatAsistente`, `ChatFlotante`, `/asistente`, `/admin/asistente` | 🟢 Implementada: historial, asistente por rol, cancelar por chat y aprendizaje; falta evaluación |
| 008 | [Plataforma, despliegue y CI](../features/008-plataforma-y-despliegue/spec.md) | `health`, `arranque`, Alembic | Dockerfile + nginx | 🟢 Implementada |
| 009 | [Kubernetes, GitOps e IaC](../features/009-kubernetes-gitops-iac/spec.md) | `tareas` (Job de migraciones) | `plataforma/helm`, `plataforma/argocd`, `plataforma/opentofu` | 🟢 Implementada; falta ensayo de recuperación en otro equipo |
| 010 | [DevSecOps y observabilidad](../features/010-devsecops-y-observabilidad/spec.md) | `core/telemetria`, `core/metricas` | `ci.yml`, `plataforma/helm/observabilidad` | 🟢 Implementada; faltan alertas |
| 011 | [Predicción de inasistencias (ML)](../features/011-prediccion-inasistencias/spec.md) | `ml/`, `prediccion`, `citas`, `tareas` (migración 007) | `Riesgo`, `/admin` (tarjeta del modelo), `/citas` | 🟡 Implementada con datos sintéticos; falta evaluar con citas reales |

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
| 2026-11-18 | **Regresión logística, umbral 0,20** | Gana al árbol en AUC (0,71 vs. 0,58) y es explicable; con 0,20 se detectan ~6 de cada 10 inasistencias a cambio de un correo extra. |
| 2026-11-18 | **Modelos reentrenados en la base de datos, firmados con HMAC** | En Kubernetes el disco es de solo lectura y hay varias réplicas; la firma impide cargar un pickle alterado. |
| MVP | **Dokploy + Docker Compose** para el despliegue | Es lo que se usó en el Laboratorio 4. |
| MVP | **IA local con Ollama** (`nomic-embed-text` + `llama3`) y pgvector | Privacidad de los datos; sin dependencias de nube. |
| MVP | **MailHog** como servidor de correo | Probar recordatorios sin enviar correos reales. |

## Pendientes (backlog)
- **RF09:** días sin atención (festivos) que bloqueen la agenda → 004.
- **RF17:** ausencias de barberos → 004.
- Sección `#barberias` en el inicio: el enlace “Barberías” del `Navbar` apunta a un ancla que no existe → 002.
- Edición de barberos: los **días de trabajo** ya se editan; faltan nombre, correo y especialidades → 003.
- Conjunto de preguntas de evaluación del asistente → 007.
- Evaluar y reentrenar el modelo de inasistencias con citas reales; probar localidad y clima como variables → 011.
- Alertas de Grafana y ejercicio de incidente → 010.
- Correo de confirmación al agendar (hoy solo existe el recordatorio) → 006.
