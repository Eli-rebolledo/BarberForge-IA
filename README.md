# BarberForge AI

Plataforma web para que una barbería maneje sus citas en línea, con tres piezas de inteligencia artificial que
corren en el propio equipo, sin servicios pagos:

- **Asistente con RAG:** responde con la información oficial de la barbería (precios, horarios, políticas), cita
  la fuente y aprende de lo que no sabe. Usa `llama3.2:3b` y `nomic-embed-text` en Ollama, y pgvector en PostgreSQL.
- **Predicción de inasistencias:** al agendar, un modelo de machine learning estima si el cliente podría no llegar
  y, si el riesgo es alto, le manda un aviso extra 60 minutos antes.
- **Asistente de voz:** el cliente habla y la plataforma transcribe (Whisper), entiende, actúa sobre la agenda o
  las PQRS, y responde en voz (Piper).

Proyecto integrador del Diplomado CloudForge AI 5.0 (Unicomfacauca). Corre de dos formas:

| Forma | Para qué | Cómo |
|---|---|---|
| **Docker Compose** | Probarlo y hacer la demostración en un solo computador | Esta guía, sección 2 |
| **Kubernetes** | El despliegue completo: Helm, Argo CD (GitOps), OpenTofu, DevSecOps y observabilidad | [docs/plataforma-kubernetes.md](docs/plataforma-kubernetes.md) |

---

## Contenido

1. [Requisitos](#1-requisitos)
2. [Instalación paso a paso](#2-instalación-paso-a-paso)
3. [Comprobar que todo funciona](#3-comprobar-que-todo-funciona)
4. [Cuentas para probar](#4-cuentas-para-probar)
5. [Demostración paso a paso](#5-demostración-paso-a-paso)
6. [Pruebas automatizadas](#6-pruebas-automatizadas)
7. [Despliegue en Kubernetes](#7-despliegue-en-kubernetes)
8. [Estructura del repositorio](#8-estructura-del-repositorio)
9. [Documentación](#9-documentación)
10. [Solución de problemas](#10-solución-de-problemas)
11. [Detener, actualizar o empezar de cero](#11-detener-actualizar-o-empezar-de-cero)
12. [Equipo y contribución](#12-equipo-y-contribución)

---

## 1. Requisitos

| Requisito | Detalle |
|---|---|
| Sistema operativo | Windows 10/11, macOS o Linux. Los comandos de esta guía están en **PowerShell** (Windows); en macOS y Linux cambian solo donde se indica |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Versión 4.30 o superior, abierto y con el motor en marcha (ícono de la ballena en verde) |
| Memoria | 16 GB de RAM en el equipo; Docker Desktop debe poder usar al menos **8 GB** (Settings › Resources) |
| Disco | Unos **15 GB** libres: imágenes, modelos de IA (2,3 GB) y voz (1,5 GB) |
| [Git](https://git-scm.com/downloads) | Para clonar el repositorio |
| Navegador | Chrome o Edge. El micrófono solo funciona en `http://localhost` |
| Internet | Solo la primera vez, para descargar imágenes y modelos (unos 20 minutos con buena conexión) |

No hace falta instalar Python, Node.js ni PostgreSQL: todo corre dentro de contenedores.

---

## 2. Instalación paso a paso

### Paso 1. Clonar el repositorio

```powershell
git clone https://github.com/Eli-rebolledo/BarberForge-IA.git
cd BarberForge-IA
```

> Si la carpeta se llama distinto, los comandos funcionan igual; solo cambia el nombre de los volúmenes de Docker
> (por ejemplo `barberforge-ia_pgdata`).

### Paso 2. Crear el archivo `.env`

El archivo `.env` guarda las claves y la configuración. **No se sube a Git** (está en `.gitignore`).

```powershell
Copy-Item .env.example .env        # macOS / Linux: cp .env.example .env
notepad .env                       # macOS / Linux: nano .env
```

### Paso 3. Completar el `.env`

Cambien estas líneas. Las demás pueden quedar como vienen.

```dotenv
# Claves: valores largos y aleatorios, SIN espacios después del signo =
DB_PASSWORD=pongan-aqui-una-clave-larga
JWT_SECRET=pongan-aqui-otra-clave-larga-distinta

# Administrador que se crea al arrancar (si se dejan vacías, la primera cuenta registrada queda como administrador)
ADMIN_EMAIL=admin@barberforge.local
ADMIN_PASSWORD=una-clave-de-al-menos-8-caracteres

# Modelo de lenguaje: el mismo con el que se evaluó el asistente
LLM_MODEL=llama3.2:3b

# Levantar también la voz y la observabilidad (Grafana), y enviarle las métricas
COMPOSE_PROFILES=voz,observabilidad
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-lgtm:4318
```

Para generar claves aleatorias en PowerShell (copien cada resultado en su línea):

```powershell
[guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
```

En macOS o Linux: `openssl rand -hex 32`.

> **Importante:** `DB_PASSWORD` queda guardada en la base de datos la primera vez que arranca. Si después la
> cambian, la API no podrá conectarse; vean «password authentication failed» en la sección 10.

### Paso 4. Levantar la plataforma

```powershell
docker compose up -d --build
```

Con `COMPOSE_PROFILES` en el `.env`, este comando levanta todo. Si no lo pusieron, escriban los perfiles a mano:

```powershell
docker compose --profile voz --profile observabilidad up -d --build
```

La primera vez construye las imágenes y descarga los modelos: tarda entre 10 y 25 minutos según la conexión.

### Paso 5. Esperar la descarga de los modelos de IA

```powershell
docker compose logs -f ollama-init
```

Termina cuando aparece `success` dos veces (una por `nomic-embed-text` y otra por `llama3.2:3b`) y el contenedor
se detiene. Salgan con `Ctrl+C`. Para confirmarlo:

```powershell
docker compose exec bf-ollama ollama list
```

Deben aparecer `llama3.2:3b` y `nomic-embed-text`.

### Paso 6. Ver que los contenedores estén arriba

```powershell
docker compose ps
```

Deben estar en estado `running` (o `Up`): `bf-db`, `bf-api`, `web`, `bf-ollama`, `bf-voz`, `mailhog` y
`otel-lgtm`. `ollama-init` no aparece porque ya terminó: solo descarga los modelos. Con `docker compose ps -a` se ve
como `exited (0)`, que es lo normal.

---

## 3. Comprobar que todo funciona

| Qué | Dirección | Qué deben ver |
|---|---|---|
| Aplicación | http://localhost:8080 | La página de la barbería con servicios y barberos |
| Salud de la API | http://localhost:8080/api/health | `"estado":"ok"` y `"base_de_datos":"ok"` |
| Salud de la voz | http://localhost:8001/voz/health | `"status":"ok"` y `"tts": true` (Piper listo) |
| Correos (MailHog) | http://localhost:8025 | La bandeja de correos de prueba |
| Grafana | http://localhost:3000 (usuario `admin`, clave `admin`) | Dashboards › «BarberForge · SLI/SLO y operación» |

**Primera pregunta al asistente:** abran el chat y pregunten «¿Cuánto cuesta el corte?». La primera respuesta puede
tardar hasta un minuto porque el modelo se carga en memoria; las siguientes son más rápidas. El modelo queda cargado
30 minutos.

---

## 4. Cuentas para probar

| Rol | Correo | Clave | Cómo se obtiene |
|---|---|---|---|
| Administrador | El de `ADMIN_EMAIL` | El de `ADMIN_PASSWORD` | Se crea al arrancar |
| Barbero | `carlos@demo.co` | `Demo12345` | Datos de ejemplo (`SEED_DEMO=true`) |
| Barbero | `luis@demo.co` | `Demo12345` | Datos de ejemplo |
| Cliente | El que registren | La que elijan | Botón «Registrarse» |
| Visitante | — | — | Sin iniciar sesión |

---

## 5. Demostración paso a paso

Recorrido de unos 15 minutos que muestra las funciones principales con los cuatro roles. Tengan abiertas tres
pestañas: la aplicación (8080), los correos (8025) y Grafana (3000).

### 5.1 Visitante (sin iniciar sesión)
1. En la página de inicio, mostrar los servicios, los precios y los barberos.
2. Abrir el chat y escribir: **«¿Cuánto cuesta el corte clásico?»**. La respuesta sale de la información oficial y
   muestra su fuente.
3. Tocar el micrófono, aceptar el permiso del navegador y decir: **«¿A qué hora abren?»**. Responde en texto y en voz.
4. Preguntar algo que el asistente no sabe, por ejemplo **«¿Tienen parqueadero?»**: responde que todavía no lo sabe y
   guarda la pregunta para que el administrador se la enseñe (se ve en el paso 5.4).

### 5.2 Cliente
1. **Registrarse** con un correo cualquiera (por ejemplo `cliente@prueba.co`) y aceptar la política de datos.
2. **Agendar:** en «Agendar», elegir un servicio, un barbero (tocando su foto se ve en grande), el día y la hora, y
   confirmar.
3. En **MailHog** (8025) aparece el correo de la cita.
4. **Agendar por chat:** escribir «Quiero agendar un corte» y seguir los botones de horario.
5. **PQRS por chat:** escribir **«Tengo una queja»**. El asistente no la radica todavía: pregunta qué pasó. Responder
   **«El sábado esperé 40 minutos y nadie me avisó»** y el asistente contesta con el número de radicado (`PQRS-000NN`).
   También se puede grabar con el micrófono; si se habló mal, la **✕** roja cancela la grabación sin enviarla.
6. En «Mis citas», cancelar una de las dos citas. Llega el correo de cancelación.

### 5.3 Barbero
1. Cerrar sesión y entrar con `carlos@demo.co` / `Demo12345`.
2. Ver la agenda del día: cada cita muestra la insignia **«Riesgo N %»** calculada por el modelo de inasistencias.
3. Crear una cita para un cliente que llega al local (sin cuenta): queda confirmada de una vez.
4. Marcar una cita como **completada** o **inasistencia**: esa cita sirve después para reentrenar el modelo.

### 5.4 Administrador
1. Entrar con la cuenta de `ADMIN_EMAIL`.
2. **Festivos:** en la pestaña «Festivos», tocar «Cargar festivos de Colombia». Esos días ya no se ofrecen al agendar.
3. **Ausencias:** registrar una ausencia de Carlos en un día con citas. Las citas pasan a Luis y los clientes reciben
   un correo.
4. **PQRS:** en la pestaña «PQRS», abrir la queja del paso 5.2, cambiar el estado a «Cerrada» y escribir la respuesta.
   La respuesta le llega al cliente en MailHog.
5. **Por aprender:** en «Asistente IA», ver las preguntas que el asistente no supo responder, escribir una respuesta y
   publicarla. Si se vuelve a preguntar lo mismo en el chat, ahora responde con lo que se le enseñó.
6. **Panel del modelo:** en el panel, la tarjeta del modelo muestra el AUC, el umbral (0,20) y las citas con riesgo alto.

### 5.5 Observabilidad y una falla controlada
1. En **Grafana** (3000) abrir el dashboard **«BarberForge · SLI/SLO y operación»**: disponibilidad, latencia
   (percentil 95), presupuesto de error y respuestas del asistente.
2. Detener el modelo de lenguaje:
   ```powershell
   docker compose stop bf-ollama
   ```
3. Hacer 3 o 4 preguntas en el chat: el asistente sigue respondiendo con su respaldo sin IA.
4. En unos minutos, en Grafana › Alerting › Alert rules, la alerta **«El modelo de lenguaje (Ollama) está fallando»**
   pasa a *Firing* y llega un correo a MailHog.
5. Recuperar el servicio y hacer una pregunta más; la alerta vuelve a *Normal*:
   ```powershell
   docker compose start bf-ollama
   ```

### 5.6 (Opcional) Respaldo y recuperación de la base de datos
Paso a paso cronometrado en [docs/guia-pruebas-sustentacion.md](docs/guia-pruebas-sustentacion.md), sección 3.

---

## 6. Pruebas automatizadas

Corren en cada pull request en GitHub Actions. Para correrlas en el equipo se necesita Python 3.12 o superior:

```powershell
cd codigo/backend
pip install -r requirements-dev.txt
ruff check .
pytest                    # 105 pruebas (SQLite en memoria, no necesitan Docker)

cd ../voz
pip install -r requirements-dev.txt
pytest                    # 18 pruebas (Whisper, Piper y la API simulados)

cd ../frontend
npm install
npm run build             # compila las 21 páginas y revisa los tipos de TypeScript
```

Evaluaciones de los modelos:

| Evaluación | Dónde | Resultado |
|---|---|---|
| Asistente RAG (Golden Dataset de 56 preguntas) | [docs/evaluacion-rag/](docs/evaluacion-rag/) | 82,1 % de éxito (meta 70 %) |
| Modelo de inasistencias (5.000 citas sintéticas, división por fecha; logística vs. árbol, Random Forest y XGBoost) | [docs/ml-prediccion-inasistencias.md](docs/ml-prediccion-inasistencias.md) | AUC 0,71 · recall 0,59 |
| Asistente de voz (30 audios) | [codigo/voz/evaluacion/](codigo/voz/evaluacion/) | `python evaluar_voz.py` |

**Prueba de servicios (disponibilidad y latencia, cada servicio con su umbral).** Con la plataforma arriba:
```powershell
pip install httpx
python scripts/prueba-servicios.py      # web, API, login, catálogo, disponibilidad, asistente y voz
```
Deja en `resultados/` un CSV por petición y un resumen por servicio (disponibilidad, p50, p95 y si cumple su SLO:
500 ms la API normal, 60 s el asistente y la voz). No crea citas ni PQRS.

---

## 7. Despliegue en Kubernetes

Minikube + Helm + Argo CD (GitOps) + OpenTofu (infraestructura como código). En Windows, con PowerShell como
administrador la primera vez:

```powershell
.\scripts\setup-minikube.ps1          # una vez: instala minikube, kubectl, helm y tofu, y crea el clúster
Copy-Item plataforma\opentofu\terraform.tfvars.ejemplo plataforma\opentofu\terraform.tfvars
notepad plataforma\opentofu\terraform.tfvars   # completar los secretos (este archivo NO se sube a Git)
.\scripts\levantar-plataforma.ps1     # OpenTofu: Ollama, namespaces, secretos y Argo CD → Argo CD despliega la app
```

En macOS o Linux: `./scripts/setup-minikube.sh` y `./scripts/levantar-plataforma.sh`.

Guía completa, acceso a Argo CD y demostraciones (GitOps, corrección de cambios manuales, rollback, promoción a
staging): [docs/plataforma-kubernetes.md](docs/plataforma-kubernetes.md).

**Pipeline CI/CD** (`.github/workflows/ci.yml`): en cada pull request corren las pruebas, el análisis de estilo, la
validación de Helm, Kubernetes y OpenTofu, y Trivy. Al llegar a `main` construye las imágenes, las escanea, las
publica en GHCR con su SBOM (Syft), las firma y verifica con Cosign, y actualiza la versión en
`plataforma/helm/barberforge/values-dev.yaml`; Argo CD ve ese commit y despliega.

---

## 8. Estructura del repositorio

```
codigo/
├── backend/                   API: FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── models/            las 15 tablas de la base de datos
│   │   ├── schemas/           validación de entrada y salida (Pydantic)
│   │   ├── routers/           13 routers con los endpoints
│   │   ├── services/          reglas de negocio: citas, chat, RAG, PQRS, predicción…
│   │   ├── core/              seguridad (JWT, bcrypt), permisos, telemetría y hora local
│   │   ├── ml/                datos sintéticos, variables y entrenamiento del modelo (+ supuestos.md)
│   │   └── tareas.py          python -m app.tareas migrar | indexar | generar-datos | entrenar | reentrenar
│   ├── alembic/versions/      10 migraciones (001 esquema … 010 asistente sin pagos)
│   ├── evaluacion/            evaluar_asistente.py: Golden Dataset contra la aplicación
│   └── tests/                 105 pruebas (pytest)
├── voz/                       servicio de voz: transcripción, intención, enrutador y síntesis
│   ├── evaluacion/            Golden Dataset de 30 frases y evaluar_voz.py
│   └── tests/                 18 pruebas
└── frontend/                  web: Next.js + React + TypeScript, servida con nginx
plataforma/
├── helm/barberforge/          chart de la aplicación (values-dev.yaml y values-staging.yaml)
├── helm/observabilidad/       Grafana, Prometheus, Tempo y Loki, con el dashboard y las alertas
├── argocd/                    AppProject y Applications de Argo CD
└── opentofu/                  namespaces, secretos, Argo CD y Ollama
docs/                          arquitectura C4, Kubernetes, DevSecOps, observabilidad, runbook, evaluaciones, PQRS
spec/                          constitución del proyecto y las 12 funcionalidades (spec.md, plan.md, tasks.md)
scripts/                       setup-minikube y levantar/destruir la plataforma (.ps1 y .sh)
.github/                       pipeline, CODEOWNERS, plantillas de pull request y de issues
docker-compose.yml             todo el sistema en local (perfiles «voz» y «observabilidad»)
.env.example                   plantilla de configuración (el .env real no se sube)
```

---

## 9. Documentación

| Tema | Documento |
|---|---|
| Arquitectura (C4 niveles 1, 2 y 3, despliegue y voz) | [docs/arquitectura/](docs/arquitectura/) |
| Kubernetes, Argo CD y OpenTofu | [docs/plataforma-kubernetes.md](docs/plataforma-kubernetes.md) |
| Seguridad del pipeline (Trivy, SBOM, Cosign) | [docs/devsecops.md](docs/devsecops.md) |
| Observabilidad, SLI/SLO y alertas | [docs/observabilidad.md](docs/observabilidad.md) |
| Operación, respaldo, recuperación y fallas comunes | [docs/runbook.md](docs/runbook.md) |
| Modelo de inasistencias (MLOps) | [docs/ml-prediccion-inasistencias.md](docs/ml-prediccion-inasistencias.md) |
| Asistente de voz | [docs/asistente-voz.md](docs/asistente-voz.md) |
| PQRS | [docs/pqrs.md](docs/pqrs.md) |
| Evaluación del RAG | [docs/evaluacion-rag/](docs/evaluacion-rag/) |
| Guía de pruebas de la sustentación | [docs/guia-pruebas-sustentacion.md](docs/guia-pruebas-sustentacion.md) |
| Misión, tecnologías y decisiones | [spec/constitution/](spec/constitution/) |

---

## 10. Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `docker compose` dice que no encuentra el motor | Docker Desktop cerrado | Abrir Docker Desktop y esperar a que el ícono quede en verde |
| `port is already allocated` | Otro programa usa el 8080, 3000, 8025 u 8001 | Cerrar ese programa o cambiar el puerto en `docker-compose.override.yml` |
| `/api/health` dice `password authentication failed` | Se cambió `DB_PASSWORD` después del primer arranque | Volver a la clave anterior, o empezar de cero (sección 11) |
| El asistente responde sin IA o muy lento | Los modelos no se descargaron o el `.env` dice `LLM_MODEL=llama3` | `docker compose logs ollama-init`; poner `LLM_MODEL=llama3.2:3b` y `docker compose up -d` |
| La primera respuesta tarda casi un minuto | El modelo se está cargando en memoria | Es normal; las siguientes son más rápidas |
| No aparece el micrófono | El navegador solo lo permite en `localhost` | Abrir `http://localhost:8080`, no la IP del equipo |
| «El asistente de voz no está disponible» | `bf-voz` no se levantó | `docker compose --profile voz up -d --build` |
| `network … not found` al levantar la voz | Quedó un contenedor de una ejecución anterior | `docker compose --profile voz --profile observabilidad down` y volver a levantar |
| `bf-voz` se reinicia solo | Falta memoria | Darle 8 GB a Docker Desktop, o en el `.env` `WHISPER_MODEL=tiny` e `INTENCION_CON_LLM=false` y reconstruir |
| Grafana no muestra datos ni dispara alertas | Falta `OTEL_EXPORTER_OTLP_ENDPOINT` en el `.env` | Agregar la línea del paso 3 y `docker compose up -d` |
| No llegan correos | — | Todos los correos llegan a MailHog (http://localhost:8025), no a un correo real |

Más casos y cómo diagnosticarlos: [docs/runbook.md](docs/runbook.md).

---

## 11. Detener, actualizar o empezar de cero

```powershell
docker compose stop                  # detener sin borrar nada
docker compose up -d                 # volver a encenderlo

git pull                             # traer una versión nueva…
docker compose up -d --build         # …y reconstruir (las migraciones corren solas al arrancar la API)
```

Empezar de cero **solo con la base de datos** (conserva los modelos de IA ya descargados):

```powershell
docker compose down
docker volume ls                              # ver el nombre exacto del volumen
docker volume rm barberforge-ia_pgdata        # <carpeta>_pgdata
docker compose up -d --build
```

`docker compose down -v` borra **todo**, incluidos los modelos de Ollama (habría que volver a descargar 2,3 GB).

---

## 12. Equipo y contribución

| Integrante | GitHub |
|---|---|
| María Elizabeth Pinto Rebolledo | [@Eli-rebolledo](https://github.com/Eli-rebolledo) |
| Victor Andres Campo | [@victor1134](https://github.com/victor1134) |
| Javier Alejandro Guaca Galindez | [@JavierGalindez](https://github.com/JavierGalindez) |
| Miyer Arnulfo Cuetia | [@MiyerACI](https://github.com/MiyerACI) |

Ramas (`main`, `develop`, `feature/NNN-…`), mensajes de commit, pull requests, responsables de cada parte y uso de
IA: [CONTRIBUTING.md](CONTRIBUTING.md). Cada funcionalidad tiene su issue y su especificación en `spec/features/`.
