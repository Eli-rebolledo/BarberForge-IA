# setup-minikube.ps1 — se corre UNA vez por equipo (Windows 10/11 con Docker Desktop abierto).
# Instala Minikube, kubectl, Helm y OpenTofu con winget y crea el clúster de BarberForge.
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\setup-minikube.ps1
param(
  [int]$Cpus = 4,
  [string]$Memoria = "6g",       # Ollama corre fuera del clúster; 6 GB alcanzan para la app + Argo CD + Grafana
  [switch]$SinCalico             # Calico hace cumplir las NetworkPolicy; quítalo solo si el equipo es muy justo
)
$ErrorActionPreference = "Stop"

function Instalar($id, $comando) {
  if (Get-Command $comando -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ $comando ya está instalado" -ForegroundColor Green
  } else {
    Write-Host "  → Instalando $id..." -ForegroundColor Yellow
    winget install --id $id -e --accept-package-agreements --accept-source-agreements
  }
}

Write-Host "`n=== [1/4] Herramientas ===" -ForegroundColor Cyan
Instalar "Kubernetes.minikube" "minikube"
Instalar "Kubernetes.kubectl"  "kubectl"
Instalar "Helm.Helm"           "helm"
Instalar "OpenTofu.Tofu"       "tofu"
# winget actualiza el PATH solo en terminales nuevas: lo recargamos aquí mismo.
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "`n=== [2/4] Docker Desktop ===" -ForegroundColor Cyan
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Desktop no está corriendo. Ábrelo, espera a que diga 'Engine running' y repite." }
Write-Host "  ✓ Docker responde" -ForegroundColor Green

Write-Host "`n=== [3/4] Clúster Minikube ===" -ForegroundColor Cyan
$argumentos = @("start", "--driver=docker", "--cpus=$Cpus", "--memory=$Memoria")
if (-not $SinCalico) { $argumentos += "--cni=calico" }
minikube @argumentos
minikube addons enable ingress
minikube addons enable metrics-server

Write-Host "`n=== [4/4] Verificación ===" -ForegroundColor Cyan
kubectl get nodes
minikube version
kubectl version --client
helm version --short
tofu version
Write-Host "`nListo. Ahora: copia plataforma\opentofu\terraform.tfvars.ejemplo como terraform.tfvars y corre .\scripts\levantar-plataforma.ps1" -ForegroundColor Green
