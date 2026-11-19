# ---------- clúster ----------

variable "kubeconfig" {
  description = "Archivo de configuración de kubectl (Minikube lo actualiza al arrancar)."
  type        = string
  default     = "~/.kube/config"
}

variable "contexto_kubernetes" {
  description = "Contexto de kubectl donde se instala la plataforma."
  type        = string
  default     = "minikube"
}

variable "entornos" {
  description = "Entornos a crear. Cada uno es un namespace barberforge-<entorno> con su propia base de datos."
  type        = list(string)
  default     = ["dev", "staging"]

  validation {
    condition     = length(var.entornos) > 0 && alltrue([for e in var.entornos : contains(["dev", "staging"], e)])
    error_message = "Los entornos permitidos son «dev» y «staging» (hay un values-<entorno>.yaml para cada uno)."
  }
}

# ---------- GitOps ----------

variable "repositorio_git" {
  description = "Repositorio que Argo CD vigila (fuente de verdad)."
  type        = string
  default     = "https://github.com/Eli-rebolledo/BarberForge-IA.git"

  validation {
    condition     = can(regex("^https://.+\\.git$", var.repositorio_git))
    error_message = "Usa la URL HTTPS del repositorio terminada en .git."
  }
}

variable "rama_git" {
  description = "Rama que se despliega."
  type        = string
  default     = "main"
}

variable "argocd_version_chart" {
  description = "Versión del chart argo-cd (https://argoproj.github.io/argo-helm). 10.18.1 = Argo CD v3.6.1."
  type        = string
  default     = "10.18.1"
}

variable "github_usuario" {
  description = "Usuario de GitHub. Solo hace falta si el repositorio o las imágenes de GHCR son privados."
  type        = string
  default     = ""
}

variable "github_token" {
  description = "Token de GitHub (permisos: repo de solo lectura y read:packages). Vacío si todo es público."
  type        = string
  default     = ""
  sensitive   = true
}

variable "observabilidad" {
  description = "Instalar Grafana + Prometheus + Tempo + Loki (otel-lgtm) en el namespace observabilidad."
  type        = bool
  default     = true
}

# ---------- secretos de la aplicación (nunca en Git: van en terraform.tfvars, que está en .gitignore) ----------

variable "db_password" {
  description = "Clave de PostgreSQL (cada entorno tiene su propia base, con esta clave)."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 12
    error_message = "La clave de la base de datos debe tener al menos 12 caracteres."
  }
}

variable "jwt_secret" {
  description = "Secreto para firmar las sesiones (JWT)."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.jwt_secret) >= 32
    error_message = "El secreto JWT debe tener al menos 32 caracteres."
  }
}

variable "admin_email" {
  description = "Correo del administrador inicial. Vacío: la primera cuenta registrada queda como administrador."
  type        = string
  default     = ""

  validation {
    condition     = var.admin_email == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.admin_email))
    error_message = "Escribe un correo válido o déjalo vacío."
  }
}

variable "admin_password" {
  description = "Clave del administrador inicial (solo si se define admin_email)."
  type        = string
  default     = ""
  sensitive   = true
}

# ---------- Ollama en Docker Desktop ----------

variable "docker_host" {
  description = "Conexión al Docker local. Windows: npipe:////.//pipe//docker_engine · Mac y Linux: unix:///var/run/docker.sock"
  type        = string
  default     = "npipe:////.//pipe//docker_engine"

  validation {
    condition     = can(regex("^(npipe|unix|tcp)://", var.docker_host))
    error_message = "docker_host debe empezar por npipe://, unix:// o tcp://."
  }
}

variable "ollama_con_opentofu" {
  description = "Crear el contenedor de Ollama con OpenTofu. Ponlo en false si ya lo levantas con docker compose."
  type        = bool
  default     = true
}

variable "ollama_puerto" {
  description = "Puerto publicado de Ollama. Los pods lo usan en http://host.minikube.internal:<puerto>."
  type        = number
  default     = 11434

  validation {
    condition     = var.ollama_puerto >= 1024 && var.ollama_puerto <= 65535
    error_message = "Usa un puerto entre 1024 y 65535."
  }
}

variable "ollama_imagen" {
  description = "Imagen de Ollama (versión fija: el laboratorio debe poder reconstruirse igual)."
  type        = string
  default     = "ollama/ollama:0.5.4"
}

variable "modelo_llm" {
  description = "Modelo de lenguaje. En equipos modestos: llama3.2:3b (más rápido)."
  type        = string
  default     = "llama3"
}

variable "modelo_embeddings" {
  description = "Modelo de embeddings para la búsqueda semántica del asistente."
  type        = string
  default     = "nomic-embed-text"
}
