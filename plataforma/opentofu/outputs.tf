output "namespaces" {
  description = "Namespaces de la aplicación por entorno."
  value       = local.namespaces_app
}

output "argocd" {
  description = "Cómo entrar a Argo CD (usuario: admin)."
  value = {
    abrir                  = "kubectl port-forward -n argocd svc/argocd-server 8081:80   →   http://localhost:8081"
    clave_admin_powershell = "kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | % { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_)) }"
    clave_admin_bash       = "kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
  }
}

output "aplicacion" {
  description = "Cómo abrir BarberForge en cada entorno."
  value = { for e, ns in local.namespaces_app :
    e => "kubectl port-forward -n ${ns} svc/barberforge-web ${e == "dev" ? 8080 : 8082}:8080   →   http://localhost:${e == "dev" ? 8080 : 8082}"
  }
}

output "grafana" {
  description = "Tablero de observabilidad (usuario admin / clave admin)."
  value       = var.observabilidad ? "kubectl port-forward -n observabilidad svc/otel-lgtm 3000:3000   →   http://localhost:3000" : "desactivado"
}

output "ollama" {
  description = "URL de Ollama vista desde los pods de Minikube."
  value       = "http://host.minikube.internal:${var.ollama_puerto}"
}
