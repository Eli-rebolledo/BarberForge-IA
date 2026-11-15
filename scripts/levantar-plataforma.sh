#!/usr/bin/env bash
# levantar-plataforma.sh — Minikube + OpenTofu (Ollama, namespaces, secretos, Argo CD). Argo CD despliega la app.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
TOFU="$RAIZ/plataforma/opentofu"

docker info >/dev/null || { echo "Docker no responde"; exit 1; }
minikube status >/dev/null 2>&1 || minikube start
kubectl config use-context minikube >/dev/null

if [ ! -f "$TOFU/terraform.tfvars" ]; then
  cp "$TOFU/terraform.tfvars.ejemplo" "$TOFU/terraform.tfvars"
  echo "Se creó plataforma/opentofu/terraform.tfvars: cambia las claves y el docker_host de Linux, y repite."
  exit 1
fi

cd "$TOFU"
tofu init -upgrade
tofu validate
tofu apply -auto-approve
tofu output
kubectl get applications -n argocd
echo "Modelos de IA descargándose: docker logs -f barberforge-ollama-modelos"
