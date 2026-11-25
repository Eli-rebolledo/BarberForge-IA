# Crea en GitHub las etiquetas y los issues del proyecto: uno por funcionalidad (ya implementadas, se cierran con un
# comentario que apunta a su especificación) y los de trabajo futuro (quedan abiertos).
#
# Requisitos: GitHub CLI (https://cli.github.com) con sesión iniciada:  gh auth login
# Uso, desde la raíz del repositorio:                                   .\scripts\crear-issues.ps1
# Para otro repositorio:                                                .\scripts\crear-issues.ps1 -Repo usuario/repo
param([string]$Repo = "")

$ErrorActionPreference = "Stop"
$r = @(); if ($Repo) { $r = @("--repo", $Repo) }

$etiquetas = @(
  @{n = "funcionalidad"; c = "1D76DB"; d = "Funcionalidad especificada en spec/features"},
  @{n = "plataforma"; c = "5319E7"; d = "Contenedores, Kubernetes, CI/CD, IaC"},
  @{n = "ia"; c = "0E8A16"; d = "RAG, machine learning o voz"},
  @{n = "error"; c = "D73A4A"; d = "Algo no funciona como dice la especificación"},
  @{n = "trabajo-futuro"; c = "FBCA04"; d = "Fuera del alcance de esta versión"}
)
foreach ($e in $etiquetas) { gh label create $e.n --color $e.c --description $e.d --force @r | Out-Null }

$funcionalidades = @(
  @{id = "001"; t = "Autenticación y cuentas"; a = "Eli-rebolledo"; l = "funcionalidad"
    d = "Registro, inicio de sesión con JWT y roles (cliente, barbero, administrador), gestión de la propia cuenta y protección de las páginas privadas según el rol."},
  @{id = "002"; t = "Barbería y catálogo de servicios"; a = "Eli-rebolledo"; l = "funcionalidad"
    d = "Ficha pública de la barbería, catálogo de servicios con precio y duración, y su administración. Cada cambio actualiza la base de conocimiento del asistente."},
  @{id = "003"; t = "Gestión de barberos"; a = "JavierGalindez"; l = "funcionalidad"
    d = "El administrador da de alta a los barberos con sus credenciales, especialidades, foto y servicios, y los activa o desactiva."},
  @{id = "004"; t = "Disponibilidad"; a = "JavierGalindez"; l = "funcionalidad"
    d = "Franjas de atención de cada barbero por rango de fechas, días de trabajo, festivos y ausencias."},
  @{id = "005"; t = "Agendamiento de citas"; a = "MiyerACI"; l = "funcionalidad"
    d = "Agendar con uno o varios servicios, sin doble reserva (índice único parcial), con vista por rol, cancelación, cierre y citas en el local sin cuenta."},
  @{id = "006"; t = "Recordatorios y confirmación"; a = "MiyerACI"; l = "funcionalidad"
    d = "Correo 40 minutos antes con enlace de confirmación de un solo uso; si no se confirma, la cita se cancela y la franja queda libre."},
  @{id = "007"; t = "Asistente con IA y RAG"; a = "victor1134"; l = "funcionalidad,ia"
    d = "Chat con RAG sobre pgvector y Ollama, filtro por rol, guardas contra inyección, bandeja «Por aprender», agendamiento, cancelación y PQRS por chat."},
  @{id = "008"; t = "Plataforma, despliegue y CI"; a = "Eli-rebolledo"; l = "funcionalidad,plataforma"
    d = "Contenedores, nginx, migraciones automáticas, health checks, configuración por variables de entorno y pipeline de GitHub Actions."},
  @{id = "009"; t = "Kubernetes, GitOps e infraestructura como código"; a = "victor1134"; l = "funcionalidad,plataforma"
    d = "Chart de Helm (dev y staging), despliegue con Argo CD leyendo el repositorio y reconstrucción de la plataforma con OpenTofu."},
  @{id = "010"; t = "DevSecOps y observabilidad"; a = "JavierGalindez"; l = "funcionalidad,plataforma"
    d = "Trivy, SBOM con Syft y firma con Cosign en el pipeline; OpenTelemetry hacia Grafana con tablero de SLI/SLO y cuatro alertas."},
  @{id = "011"; t = "Predicción de inasistencias (ML)"; a = "MiyerACI"; l = "funcionalidad,ia"
    d = "Regresión logística que estima el riesgo de inasistencia al agendar, aviso extra 60 minutos antes, registro en MLflow y reentrenamiento semanal."},
  @{id = "012"; t = "Asistente de voz con RAG y ML"; a = ""; l = "funcionalidad,ia"
    d = "Servicio bf-voz: Whisper transcribe, reglas (y el LLM si la frase es ambigua) detectan la intención, la API responde o actúa y Piper habla."}
)

$futuro = @(
  @{t = "Reentrenar el modelo de inasistencias con citas reales"; d = "Cuando haya al menos 200 citas reales cerradas, ejecutar el reentrenamiento y comparar contra el modelo sintético. Probar la localidad y el clima como variables."},
  @{t = "Canal de WhatsApp para el asistente"; d = "Conectar la API de WhatsApp Business al mismo endpoint del chat, sin duplicar reglas de negocio."},
  @{t = "Sugerencia de corte a partir de una foto"; d = "Requiere un modelo de visión; fuera del alcance de esta versión."},
  @{t = "Medir TTFT y TPS del modelo de lenguaje"; d = "Registrar prompt_eval_duration, eval_count y eval_duration de Ollama como métricas de OpenTelemetry."},
  @{t = "Limitar la tasa de peticiones y publicar con TLS"; d = "Rate limiting en la API y certificado TLS en el ingress antes de publicar en internet."}
)

foreach ($f in $funcionalidades) {
  $carpeta = (Get-ChildItem "spec/features" -Directory | Where-Object { $_.Name -like "$($f.id)-*" }).Name
  $cuerpo = @"
## Descripción
$($f.d)

## Especificación
- Spec: ``spec/features/$carpeta/spec.md``
- Plan: ``spec/features/$carpeta/plan.md``
- Tareas: ``spec/features/$carpeta/tasks.md``

## Rama
``feature/$carpeta`` → pull request hacia ``develop``
"@
  $argsIssue = @("issue", "create", "--title", "$($f.id) · $($f.t)", "--body", $cuerpo, "--label", $f.l) + $r
  if ($f.a) { $argsIssue += @("--assignee", $f.a) }
  $url = gh @argsIssue
  gh issue close $url --comment "Implementada y probada. Ver spec/features/$carpeta y sus pruebas en el pipeline." @r | Out-Null
  Write-Host "Creado y cerrado: $url"
}

foreach ($f in $futuro) {
  $url = gh issue create --title $f.t --body $f.d --label "trabajo-futuro" @r
  Write-Host "Creado (abierto): $url"
}
