# destruir-plataforma.ps1 - borra lo que creo OpenTofu (Argo CD, namespaces con sus bases de datos, Ollama).
# Los modelos descargados de Ollama se pierden tambien. Para solo apagar sin borrar: minikube stop
$ErrorActionPreference = "Continue"
$tofuDir = Join-Path (Split-Path -Parent $PSScriptRoot) "plataforma\opentofu"
Push-Location $tofuDir
try { tofu destroy } finally { Pop-Location }
