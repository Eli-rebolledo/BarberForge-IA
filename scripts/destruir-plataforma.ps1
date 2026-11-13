# destruir-plataforma.ps1 — borra lo que creó OpenTofu (Argo CD, namespaces con sus bases de datos, Ollama).
# Los modelos descargados de Ollama se pierden también. Para solo apagar sin borrar: minikube stop
$ErrorActionPreference = "Stop"
$tofuDir = Join-Path (Split-Path -Parent $PSScriptRoot) "plataforma\opentofu"
Push-Location $tofuDir
try { tofu destroy } finally { Pop-Location }
