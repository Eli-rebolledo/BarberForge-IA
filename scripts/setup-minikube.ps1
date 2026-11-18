# setup-minikube.ps1 - se corre UNA vez por equipo (Windows 10/11 con Docker Desktop abierto).
# Instala Minikube, kubectl, Helm y OpenTofu con winget y crea el cluster de BarberForge.
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\setup-minikube.ps1
param(
  [int]$Cpus = 4,
  [string]$Memoria = "6g",       # Ollama corre fuera del cluster; 6 GB alcanzan para la app + Argo CD + Grafana
  [switch]$SinCalico             # Calico hace cumplir las NetworkPolicy; quitalo solo si el equipo es muy justo
)
# Los programas externos (docker, minikube) escriben avisos en stderr: Windows PowerShell 5.1 los tomaria como
# errores si usaramos "Stop". Por eso se revisa $LASTEXITCODE despues de cada paso importante.
$ErrorActionPreference = "Continue"

function Fallar($mensaje) {
  Write-Host "`n[ERROR] $mensaje" -ForegroundColor Red
  exit 1
}

function Instalar($id, $comando) {
  if (Get-Command $comando -ErrorAction SilentlyContinue) {
    Write-Host "  [OK] $comando ya esta instalado" -ForegroundColor Green
  } else {
    Write-Host "  -> Instalando $id..." -ForegroundColor Yellow
    winget install --id $id -e --accept-package-agreements --accept-source-agreements
  }
}

Write-Host "`n=== [1/4] Herramientas ===" -ForegroundColor Cyan
Instalar "Kubernetes.minikube" "minikube"
Instalar "Kubernetes.kubectl"  "kubectl"
Instalar "Helm.Helm"           "helm"
Instalar "OpenTofu.Tofu"       "tofu"
# winget actualiza el PATH solo en terminales nuevas: se recarga aqui mismo.
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
foreach ($c in "minikube", "kubectl", "helm", "tofu") {
  if (-not (Get-Command $c -ErrorAction SilentlyContinue)) {
    Fallar "No se encuentra '$c'. Cierra PowerShell, abrelo de nuevo y repite el script."
  }
}

Write-Host "`n=== [2/4] Docker Desktop ===" -ForegroundColor Cyan
cmd /c "docker info >nul 2>&1"
if ($LASTEXITCODE -ne 0) { Fallar "Docker Desktop no esta corriendo. Abrelo, espera a que diga 'Engine running' y repite." }
Write-Host "  [OK] Docker responde" -ForegroundColor Green

Write-Host "`n=== [3/4] Cluster Minikube ===" -ForegroundColor Cyan
$argumentos = @("start", "--driver=docker", "--cpus=$Cpus", "--memory=$Memoria")
if (-not $SinCalico) { $argumentos += "--cni=calico" }
minikube @argumentos
if ($LASTEXITCODE -ne 0) { Fallar "minikube start fallo. Revisa el mensaje de arriba (memoria de Docker Desktop, virtualizacion)." }
minikube addons enable ingress
minikube addons enable metrics-server

Write-Host "`n=== [4/4] Verificacion ===" -ForegroundColor Cyan
kubectl get nodes
minikube version
kubectl version --client
helm version --short
tofu version
Write-Host "`nListo. Ahora: copia plataforma\opentofu\terraform.tfvars.ejemplo como terraform.tfvars y corre .\scripts\levantar-plataforma.ps1" -ForegroundColor Green
