# levantar-plataforma.ps1 — levanta (o actualiza) toda la plataforma: Minikube + OpenTofu.
# OpenTofu crea Ollama en Docker Desktop, los namespaces, los secretos y Argo CD; Argo CD despliega la app
# leyendo el repositorio de GitHub.
#   .\scripts\levantar-plataforma.ps1
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$tofuDir = Join-Path $raiz "plataforma\opentofu"

docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Abre Docker Desktop primero." }

Write-Host "`n=== Minikube ===" -ForegroundColor Cyan
minikube status *> $null
if ($LASTEXITCODE -ne 0) { minikube start } else { Write-Host "  ✓ ya está corriendo" -ForegroundColor Green }
kubectl config use-context minikube | Out-Null

$vars = Join-Path $tofuDir "terraform.tfvars"
if (-not (Test-Path $vars)) {
  Copy-Item (Join-Path $tofuDir "terraform.tfvars.ejemplo") $vars
  Write-Host "`nSe creó plataforma\opentofu\terraform.tfvars a partir del ejemplo." -ForegroundColor Yellow
  Write-Host "Ábrelo, cambia las claves (db_password y jwt_secret) y vuelve a correr este script." -ForegroundColor Yellow
  exit 1
}

Write-Host "`n=== OpenTofu ===" -ForegroundColor Cyan
Push-Location $tofuDir
try {
  tofu init -upgrade
  tofu validate
  tofu apply -auto-approve
  Write-Host "`n=== Cómo entrar ===" -ForegroundColor Cyan
  tofu output
} finally { Pop-Location }

Write-Host "`n=== Aplicaciones de Argo CD (pueden tardar unos minutos en quedar Synced/Healthy) ===" -ForegroundColor Cyan
kubectl get applications -n argocd
Write-Host "`nModelos de IA descargándose en segundo plano: docker logs -f barberforge-ollama-modelos" -ForegroundColor Yellow
