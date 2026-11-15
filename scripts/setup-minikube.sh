#!/usr/bin/env bash
# setup-minikube.sh — Ubuntu/Linux con Docker. Se corre UNA vez por equipo.
#   bash scripts/setup-minikube.sh
set -euo pipefail
CPUS="${CPUS:-4}"
MEMORIA="${MEMORIA:-6g}"

echo "=== [1/4] Herramientas ==="
if ! command -v minikube >/dev/null; then
  curl -fsSLo /tmp/minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
  sudo install /tmp/minikube /usr/local/bin/minikube
fi
if ! command -v kubectl >/dev/null; then
  curl -fsSLo /tmp/kubectl "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
  sudo install /tmp/kubectl /usr/local/bin/kubectl
fi
if ! command -v helm >/dev/null; then
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi
if ! command -v tofu >/dev/null; then   # método oficial, igual que en el Laboratorio 2
  curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh -o /tmp/install-opentofu.sh
  chmod +x /tmp/install-opentofu.sh && /tmp/install-opentofu.sh --install-method deb
fi

echo "=== [2/4] Docker ==="
docker info >/dev/null || { echo "Docker no responde"; exit 1; }

echo "=== [3/4] Clúster Minikube ==="
minikube start --driver=docker --cpus="$CPUS" --memory="$MEMORIA" --cni=calico
minikube addons enable ingress
minikube addons enable metrics-server

echo "=== [4/4] Verificación ==="
kubectl get nodes
helm version --short
tofu version
echo "Listo. Copia plataforma/opentofu/terraform.tfvars.ejemplo como terraform.tfvars (con docker_host de Linux) y corre: bash scripts/levantar-plataforma.sh"
