#!/usr/bin/env bash
# setup-minikube.sh — Mac (Intel o Apple Silicon) y Ubuntu/Linux con Docker. Se corre UNA vez por equipo.
#   bash scripts/setup-minikube.sh
#   Equipos con poca RAM:  MEMORIA=3g CPUS=2 SIN_CALICO=1 bash scripts/setup-minikube.sh
set -euo pipefail
CPUS="${CPUS:-4}"
MEMORIA="${MEMORIA:-6g}"

echo "=== [1/4] Herramientas ==="
if [ "$(uname -s)" = "Darwin" ]; then
  # Mac: Homebrew (https://brew.sh) instala las versiones correctas para Intel o Apple Silicon.
  command -v brew >/dev/null || { echo "Instala Homebrew primero: https://brew.sh"; exit 1; }
  for paquete in minikube kubectl helm opentofu; do
    comando="$paquete"; [ "$paquete" = opentofu ] && comando=tofu
    command -v "$comando" >/dev/null || brew install "$paquete"
  done
else
  ARQ="$(uname -m)"; [ "$ARQ" = x86_64 ] && ARQ=amd64; [ "$ARQ" = aarch64 ] && ARQ=arm64
  if ! command -v minikube >/dev/null; then
    curl -fsSLo /tmp/minikube "https://storage.googleapis.com/minikube/releases/latest/minikube-linux-$ARQ"
    sudo install /tmp/minikube /usr/local/bin/minikube
  fi
  if ! command -v kubectl >/dev/null; then
    curl -fsSLo /tmp/kubectl "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/$ARQ/kubectl"
    sudo install /tmp/kubectl /usr/local/bin/kubectl
  fi
  if ! command -v helm >/dev/null; then
    curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  fi
  if ! command -v tofu >/dev/null; then   # método oficial, igual que en el Laboratorio 2
    curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh -o /tmp/install-opentofu.sh
    chmod +x /tmp/install-opentofu.sh && /tmp/install-opentofu.sh --install-method deb
  fi
fi

echo "=== [2/4] Docker ==="
docker info >/dev/null || { echo "Docker no responde"; exit 1; }

echo "=== [3/4] Clúster Minikube ==="
CNI="--cni=calico"; [ -n "${SIN_CALICO:-}" ] && CNI=""
minikube start --driver=docker --cpus="$CPUS" --memory="$MEMORIA" $CNI
minikube addons enable ingress
minikube addons enable metrics-server

echo "=== [4/4] Verificación ==="
kubectl get nodes
helm version --short
tofu version
echo "Listo. Copia plataforma/opentofu/terraform.tfvars.ejemplo como terraform.tfvars (en Mac y Linux: docker_host = "unix:///var/run/docker.sock") y corre: bash scripts/levantar-plataforma.sh"
