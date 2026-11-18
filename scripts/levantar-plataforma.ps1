# levantar-plataforma.ps1 - levanta (o actualiza) toda la plataforma: Minikube + OpenTofu.
# OpenTofu crea Ollama en Docker Desktop, los namespaces, los secretos y Argo CD; Argo CD despliega la app
# leyendo el repositorio de GitHub.
#   .\scripts\levantar-plataforma.ps1
$ErrorActionPreference = "Continue"   # ver nota en setup-minikube.ps1: se revisa $LASTEXITCODE
$raiz = Split-Path -Parent $PSScriptRoot
$tofuDir = Join-Path $raiz "plataforma\opentofu"

function Fallar($mensaje) {
  Write-Host "`n[ERROR] $mensaje" -ForegroundColor Red
  exit 1
}

cmd /c "docker info >nul 2>&1"
if ($LASTEXITCODE -ne 0) { Fallar "Abre Docker Desktop primero." }

Write-Host "`n=== Minikube ===" -ForegroundColor Cyan
cmd /c "minikube status >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
  minikube start
  if ($LASTEXITCODE -ne 0) { Fallar "minikube start fallo." }
} else {
  Write-Host "  [OK] ya esta corriendo" -ForegroundColor Green
}
kubectl config use-context minikube | Out-Null

$vars = Join-Path $tofuDir "terraform.tfvars"
if (-not (Test-Path $vars)) {
  Copy-Item (Join-Path $tofuDir "terraform.tfvars.ejemplo") $vars
  Write-Host "`nSe creo plataforma\opentofu\terraform.tfvars a partir del ejemplo." -ForegroundColor Yellow
  Write-Host "Abrelo, cambia las claves (db_password y jwt_secret) y vuelve a correr este script." -ForegroundColor Yellow
  exit 1
}

Write-Host "`n=== OpenTofu ===" -ForegroundColor Cyan
Push-Location $tofuDir
try {
  tofu init -upgrade
  if ($LASTEXITCODE -ne 0) { Fallar "tofu init fallo (revisa la conexion a Internet)." }
  tofu validate
  if ($LASTEXITCODE -ne 0) { Fallar "tofu validate encontro errores en la configuracion." }
  tofu apply -auto-approve
  if ($LASTEXITCODE -ne 0) { Fallar "tofu apply fallo. Lee el error de arriba y mira docs\runbook.md." }
  Write-Host "`n=== Como entrar ===" -ForegroundColor Cyan
  tofu output
} finally { Pop-Location }

Write-Host "`n=== Aplicaciones de Argo CD (pueden tardar unos minutos en quedar Synced/Healthy) ===" -ForegroundColor Cyan
kubectl get applications -n argocd
Write-Host "`nModelos de IA descargandose en segundo plano: docker logs -f barberforge-ollama-modelos" -ForegroundColor Yellow
