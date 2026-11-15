# BarberForge AI (Diplomado CloudForge AI 5.0)

Plataforma de agendamiento para barberías con asistente RAG local (Ollama + pgvector). El cliente ve servicios y precios, consulta la disponibilidad real y agenda su cita por formulario o por chat.

Corre de dos formas:
- **Rápida:** `docker compose up --build` en cualquier equipo con Docker.
- **Plataforma completa del diplomado:** Kubernetes (Minikube), Helm, GitOps con Argo CD, infraestructura como
  código con OpenTofu, pipeline DevSecOps (Trivy, SBOM, Cosign) y observabilidad con OpenTelemetry y Grafana.
  Está en [docs/plataforma-kubernetes.md](docs/plataforma-kubernetes.md).

## Estructura

```
spec/                          ← documentación spec-driven (se escribe antes del código)
├── constitution/              misión, stack tecnológico y hoja de ruta
└── features/NNN-nombre/       spec.md (qué) → plan.md (cómo) → tasks.md (checklist)
codigo/
├── backend/                   API: FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── models/            tablas (SQLAlchemy)
│   │   ├── schemas/           validación de entrada y salida (Pydantic)
│   │   ├── routers/           endpoints HTTP delgados
│   │   ├── services/          reglas de negocio (+ errores.py: errores de dominio)
│   │   ├── core/              seguridad (JWT, bcrypt), dependencias y hora local
│   │   ├── config.py          configuración por variables de entorno
│   │   └── main.py            aplicación, manejo de errores y tareas de fondo
│   ├── app/core/telemetria.py OpenTelemetry (trazas, métricas, logs) · metricas.py: métricas de negocio
│   ├── app/tareas.py          python -m app.tareas migrar|indexar (Job de Kubernetes)
│   ├── alembic/versions/      001 esquema · 002 semilla · 003–006 cambios del esquema
│   └── tests/                 pytest sobre SQLite en memoria, un archivo por router
└── frontend/                  web: Next.js 16 (App Router) + React 19 + TypeScript
    ├── app/                   una carpeta por página (barberia, login, registro, agendar, citas, cuenta, admin/…)
    ├── components/            Navbar, ServicioCard, BarberoCard, ChatAsistente, Panel, Aviso…
    ├── lib/                   api.ts (tipos + fetch), auth.ts (token), formato.ts
    └── nginx.conf.template    nginx sin privilegios: sitio estático + /api hacia la API (upstream por variable)
plataforma/
├── helm/barberforge/          chart de la app: values.yaml + values-dev.yaml + values-staging.yaml
├── helm/observabilidad/       Grafana + Prometheus + Tempo + Loki (otel-lgtm) y tablero de SLI/SLO
├── argocd/                    AppProject y Applications de Argo CD (GitOps)
└── opentofu/                  namespaces, secretos, Argo CD y Ollama en Docker Desktop (IaC)
scripts/                       setup-minikube y levantar/destruir-plataforma (.ps1 Windows · .sh Linux)
docs/                          guía de Kubernetes, DevSecOps, observabilidad (SLI/SLO) y runbook
.github/workflows/ci.yml       pruebas → Trivy → imágenes en GHCR → SBOM → Cosign → GitOps
docker-compose.yml             PostgreSQL + pgvector, API, web, Ollama, MailHog (+ perfil «observabilidad»)
.env.example                   variables de entorno de ejemplo (el .env real no se versiona)
CONTRIBUTING.md                ramas, commits, pull requests y responsables de cada feature
```

Estado de cada feature: [spec/constitution/roadmap.md](spec/constitution/roadmap.md).

## Ejecutar en local (Docker)
    cp .env.example .env
    docker compose up -d --build
- App: http://localhost:8080 · Correos (MailHog): http://localhost:8025
- El primer registro queda como **administrador** (RN02), salvo que definas `ADMIN_EMAIL` y `ADMIN_PASSWORD`. Barberos demo: `carlos@demo.co` / `luis@demo.co`, clave `Demo12345`.
- `ollama-init` descarga `nomic-embed-text` y `llama3` (~5 GB); sin ellos el asistente usa búsqueda por palabras clave. Para equipos modestos: `LLM_MODEL=llama3.2:3b`.
- Las migraciones de Alembic corren solas al arrancar la API.

## Desarrollo sin Docker
Backend (necesita un PostgreSQL con pgvector, por ejemplo `docker compose up -d bf-db` con el puerto 5432 publicado):

    cd codigo/backend
    python -m venv .venv && .venv/Scripts/activate      # Linux/Mac: source .venv/bin/activate
    pip install -r requirements-dev.txt
    set DATABASE_URL=postgresql://barber:barber@localhost:5432/barber   # Linux/Mac: export …
    uvicorn app.main:app --reload
    pytest            # pruebas (SQLite en memoria, no necesitan base de datos)
    ruff check .      # estilo

Frontend (reenvía `/api` a `http://localhost:8000`; se cambia con `API_URL`):

    cd codigo/frontend
    npm install
    npm run dev       # http://localhost:3000
    npm run build     # genera el sitio estático en out/

## Kubernetes + Argo CD + OpenTofu (resumen)
```powershell
.\scripts\setup-minikube.ps1          # una vez: minikube, kubectl, helm, tofu y el clúster
.\scripts\levantar-plataforma.ps1     # OpenTofu: Ollama, namespaces, secretos, Argo CD → Argo CD despliega la app
```
Paso a paso, demostraciones (GitOps, drift, rollback, staging) y comandos de acceso:
[docs/plataforma-kubernetes.md](docs/plataforma-kubernetes.md).
Seguridad: [docs/devsecops.md](docs/devsecops.md). Observabilidad y SLO: [docs/observabilidad.md](docs/observabilidad.md).
Fallas comunes: [docs/runbook.md](docs/runbook.md).

## Desplegar en Dokploy (igual que el Laboratorio 4)
1. Proyecto → Create Service → **Compose** (Docker Compose). Provider GitHub, repo, rama `main`, Compose Path `./docker-compose.yml`.
2. Pestaña Environment: `DB_PASSWORD`, `JWT_SECRET`, `PUBLIC_URL=http://<dominio-de-web>`, `MAILHOG_URL=http://<dominio-de-mailhog>` (botón «Abrir buzón» del administrador) y `SEED_DEMO=false` en producción real.
3. Pestaña Domains → Add Domain (dos veces): `web` puerto `8080` y `mailhog` puerto `8025`. Después, redespliega.
4. (Opcional) Desactiva **Autodeploy** y copia el Webhook URL (pestaña Deployments) en el secreto `DOKPLOY_WEBHOOK_URL` de GitHub: el job `dokploy` del pipeline lo llama después de que pasen las pruebas y los escaneos. Sin ese secreto el job se omite, porque el despliegue principal es Argo CD.

Una base de datos creada por la primera versión del MVP se migra sola: la migración `001` solo crea lo que falta y conserva los datos.

## Qué incluye
Registro/login con roles · catálogo · barberos · disponibilidad (con **días de trabajo por barbero**) · agendamiento por formulario y por chat · índice único parcial anti doble reserva · recordatorio por correo (40 min) con enlace de un solo uso y cancelación a los 15 min · asistente RAG con filtro por rol en SQL y guarda anti inyección de prompts · cancelación y cierre de citas · migraciones Alembic · pruebas automatizadas.

## Novedades (migración 005)
- **Calendario solo del administrador:** el barbero ve su agenda y crea citas en el local, pero ya no asigna su calendario.
- **Foto del barbero:** el administrador la sube al crear o editar un barbero (y el barbero desde «Mi cuenta»). Se ve al agendar, en la página de la barbería y en el chat.
- **Asistente personal por rol** (pestaña «Asistente»): el cliente consulta servicios, agenda y **cancela citas** conversando; el barbero pregunta por **procedimientos internos** (limpieza y desinfección de máquinas, cuchillas, cierre del puesto), su agenda de hoy y sus próximas citas.
- **Historial del chat:** la conversación de cada usuario se guarda en la base de datos; si cambias de página mientras piensa, al volver sigue ahí (y aparece la respuesta cuando llega). Los visitantes no tienen historial. Botón ↻ para empezar una conversación nueva.
- **El asistente aprende:** lo que no sabe responder, o lo que alguien marca con 👎, aparece en «Asistente IA → Por aprender». El administrador escribe la respuesta una vez: queda como *respuesta oficial* en la base de datos, llama3 la redacta cuando alguien vuelve a preguntar (si Ollama no responde, se usa el texto guardado) y se le avisa en su chat a quien preguntó. En «Conocimiento» se editan los documentos (públicos o solo para el personal).
- **IA para hablar, base de datos para actuar:** las preguntas de información las redacta llama3 con lo que encuentra la búsqueda (RAG). Agendar, cancelar y consultar citas se resuelven directo en la base de datos, para que el modelo nunca invente horarios ni confirme algo que no pasó.

## Novedades (migración 006)
- **Identidad de la barbería:** en «Ajustes» el administrador sube el **logo** (PNG, JPG o WebP) y edita nombre, dirección, horario y descripción. Se ven en la barra superior, el pie de página, el asistente, la página de la barbería, la confirmación de citas, los correos y el ícono de la pestaña. Sin logo se muestra el de BarberForge; sin datos se usan `BARBERIA_NOMBRE` y `BARBERIA_DIRECCION` del `.env`.
- **Agendar más claro:** el resumen y el botón «Confirmar cita» son ahora el paso final, debajo de la hora; al elegir la hora la página baja sola hasta ahí y, si falta algo, dice qué.

## Novedades (plataforma del diplomado)
- **Kubernetes con Helm** (spec 009): PostgreSQL con volumen persistente, Job de migraciones, API con varias réplicas, worker de recordatorios, web, Ingress, autoescalado en staging y NetworkPolicies.
- **GitOps con Argo CD**: dev se actualiza solo con cada push a `main` y corrige los cambios manuales; staging se promueve a mano.
- **OpenTofu**: reconstruye la plataforma (namespaces, secretos, Argo CD y Ollama en Docker Desktop) con un comando.
- **DevSecOps** (spec 010): Trivy (código, configuración e imágenes), SBOM con Syft, firma y verificación con Cosign, contenedores sin root y de solo lectura.
- **Observabilidad**: OpenTelemetry → Grafana con un tablero de SLI/SLO (disponibilidad 99 %, p95 < 500 ms).

## Pendiente
Predicción de inasistencias con ML (después de recolectar los datos), bot de WhatsApp, corte por referencia, días sin atención y ausencias de barberos (RF09, RF17), alertas de Grafana.

## Diagnóstico rápido
`GET /api/health` responde `{"servicio":"barberforge-ai","estado":"ok","base_de_datos":"ok"}`. Si la base falla, `base_de_datos` muestra el motivo (por ejemplo `password authentication failed`: la clave `DB_PASSWORD` no coincide con la del volumen `pgdata`; se corrige borrando ese volumen en Dokploy y redesplegando). Para Kubernetes: `GET /health` (liveness) y `GET /health/db` (readiness).

## Actualizar una instalación existente

```bash
docker compose up -d --build
```

La API aplica sola las migraciones pendientes al arrancar. La `005` agrega la foto de los barberos, el historial
del chat y la base de conocimiento editable (carga los documentos iniciales y los procedimientos de limpieza).
La `004`: conserva usuarios, citas y servicios; elimina la cédula
(`id_type`/`id_number`), agrega citas sin cuenta, varios servicios por cita y la recuperación de contraseña.
Para empezar de cero (borra solo la base de datos, no los modelos de IA):
`docker compose down && docker volume rm <carpeta>_pgdata && docker compose up -d --build`.
