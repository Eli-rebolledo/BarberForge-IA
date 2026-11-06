# Proveedores: Kubernetes y Helm hablan con el clúster de Minikube; Docker (como en el Laboratorio 2) maneja el
# contenedor de Ollama en Docker Desktop, fuera del clúster.
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "kubernetes" {
  config_path    = pathexpand(var.kubeconfig)
  config_context = var.contexto_kubernetes
}

# Helm 3.x del proveedor: «kubernetes» es un objeto (= { ... }), ya no un bloque.
provider "helm" {
  kubernetes = {
    config_path    = pathexpand(var.kubeconfig)
    config_context = var.contexto_kubernetes
  }
}

provider "docker" {
  host = var.docker_host
}
