# Prepara la plataforma sobre el clúster que crea Minikube:
#   1. Namespaces (argocd, barberforge-dev, barberforge-staging, observabilidad)
#   2. Secretos de la aplicación en cada entorno (desde terraform.tfvars: nunca en Git)
#   3. Argo CD (chart oficial) y el proyecto + aplicaciones de BarberForge (chart ../argocd)
#   4. Ollama en Docker Desktop (ollama.tf)
# Desde ahí, Argo CD despliega la aplicación leyendo el repositorio: OpenTofu no instala la app directamente.

locals {
  etiquetas = {
    "app.kubernetes.io/part-of"    = "barberforge"
    "app.kubernetes.io/managed-by" = "opentofu"
  }
  namespaces_app = { for e in var.entornos : e => "barberforge-${e}" }
  # nonsensitive: solo se usa el SI/NO (hay token o no), nunca el valor del token, para decidir si se crea el Secret.
  credenciales = nonsensitive(var.github_token != "" && var.github_usuario != "")
}

# ---------- namespaces ----------

resource "kubernetes_namespace_v1" "argocd" {
  metadata {
    name   = "argocd"
    labels = local.etiquetas
  }
}

resource "kubernetes_namespace_v1" "app" {
  for_each = local.namespaces_app

  metadata {
    name = each.value
    labels = merge(local.etiquetas, {
      "barberforge/entorno" = each.key
      # Pod Security Admission: Kubernetes rechaza pods que no cumplan el perfil «restricted» (dev solo avisa).
      "pod-security.kubernetes.io/enforce" = each.key == "dev" ? "baseline" : "restricted"
      "pod-security.kubernetes.io/warn"    = "restricted"
    })
  }
}

resource "kubernetes_namespace_v1" "observabilidad" {
  count = var.observabilidad ? 1 : 0

  metadata {
    name   = "observabilidad"
    labels = local.etiquetas
  }
}

# ---------- secretos de la aplicación ----------

resource "kubernetes_secret_v1" "app" {
  for_each = local.namespaces_app

  metadata {
    name      = "barberforge-secretos"
    namespace = kubernetes_namespace_v1.app[each.key].metadata[0].name
    labels    = local.etiquetas
  }

  data = {
    DB_PASSWORD    = var.db_password
    JWT_SECRET     = var.jwt_secret
    ADMIN_EMAIL    = var.admin_email
    ADMIN_PASSWORD = var.admin_password
  }
}

# Solo si las imágenes de GHCR son privadas: Secret para descargarlas (en values: imagenes.pullSecrets).
resource "kubernetes_secret_v1" "ghcr" {
  for_each = local.credenciales ? local.namespaces_app : {}

  metadata {
    name      = "ghcr-credenciales"
    namespace = kubernetes_namespace_v1.app[each.key].metadata[0].name
    labels    = local.etiquetas
  }

  type = "kubernetes.io/dockerconfigjson"
  data = {
    ".dockerconfigjson" = jsonencode({
      auths = {
        "ghcr.io" = {
          auth = base64encode("${var.github_usuario}:${var.github_token}")
        }
      }
    })
  }
}

# ---------- Argo CD ----------

resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_version_chart
  namespace  = kubernetes_namespace_v1.argocd.metadata[0].name
  wait       = true
  timeout    = 900

  # Configuración mínima para un laboratorio en un solo equipo: sin Dex ni notificaciones (ahorra RAM) y
  # servidor sin TLS propio (se accede con port-forward).
  values = [yamlencode({
    global = { domain = "argocd.local" }
    configs = {
      params = { "server.insecure" = true }
      cm     = { "timeout.reconciliation" = "60s" }
    }
    dex           = { enabled = false }
    notifications = { enabled = false }
  })]
}

# Credenciales del repositorio (solo si es privado).
resource "kubernetes_secret_v1" "repositorio" {
  count = local.credenciales ? 1 : 0

  metadata {
    name      = "barberforge-repositorio"
    namespace = kubernetes_namespace_v1.argocd.metadata[0].name
    labels    = merge(local.etiquetas, { "argocd.argoproj.io/secret-type" = "repository" })
  }

  data = {
    type     = "git"
    url      = var.repositorio_git
    username = var.github_usuario
    password = var.github_token
  }

  depends_on = [helm_release.argocd]
}

# Proyecto y aplicaciones de Argo CD (app of apps). Después de esto, todo cambio entra por Git.
resource "helm_release" "gitops" {
  name      = "barberforge-gitops"
  chart     = "${path.module}/../argocd"
  namespace = kubernetes_namespace_v1.argocd.metadata[0].name

  values = [yamlencode({
    repoURL        = var.repositorio_git
    rama           = var.rama_git
    observabilidad = var.observabilidad
    # Los entornos que no se piden van en null: Helm combina mapas con los valores por defecto del chart,
    # y null es la forma de quitar uno (si no, Argo CD crearia igual la aplicacion de staging).
    entornos = { for e in ["dev", "staging"] : e => contains(var.entornos, e) ? { automatico = e == "dev" } : null }
  })]

  depends_on = [
    helm_release.argocd,
    kubernetes_secret_v1.app,
    kubernetes_secret_v1.repositorio,
    kubernetes_namespace_v1.observabilidad,
  ]
}
