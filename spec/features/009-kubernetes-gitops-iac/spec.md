# 009 · Kubernetes, GitOps e infraestructura como código

## Descripción
BarberForge corre en un clúster de Kubernetes (Minikube) empaquetado con Helm, se despliega con Argo CD leyendo
el repositorio (GitOps) y la plataforma completa se reconstruye con OpenTofu. Responde a los módulos 2 y 4 del
diplomado CloudForge AI 5.0 y a los entregables «Manifests de Kubernetes y/o Helm», «Repositorio GitOps y
sincronización mediante Argo CD» e «Infraestructura como código».

## Historias de usuario
- Como **jurado**, quiero clonar el repositorio, correr dos scripts y ver la aplicación funcionando en Kubernetes.
- Como **desarrollador**, quiero hacer push a `main` y que el entorno dev se actualice solo, sin usar `kubectl`.
- Como **operador**, quiero que si alguien cambia el clúster a mano, Argo CD lo devuelva a lo que dice Git.
- Como **operador**, quiero volver a la versión anterior con un `git revert`.
- Como **equipo**, queremos un entorno staging que se promueva a mano, con más réplicas y autoescalado.

## Criterios de aceptación
- [x] Chart `plataforma/helm/barberforge` con PostgreSQL (StatefulSet + volumen), API, worker, Job de migraciones, web, MailHog, Ollama opcional, Ingress, HPA y NetworkPolicies.
- [x] Variantes `values-dev.yaml` (1 réplica, sincronización automática) y `values-staging.yaml` (2 réplicas + HPA, sincronización manual).
- [x] Health checks: `startupProbe` y `livenessProbe` en `/health`, `readinessProbe` en `/health/db`; actualización sin caída (`maxUnavailable: 0`).
- [x] Las migraciones corren en un Job (hook de Argo CD, ola 1) entre PostgreSQL (ola 0) y la API/web (ola 2).
- [x] Los recordatorios corren en un único `worker`: la API puede tener varias réplicas sin enviar correos repetidos.
- [x] Argo CD: AppProject `barberforge` restringido al repositorio y a sus namespaces; Applications `barberforge-dev` (prune + self-heal), `barberforge-staging` (manual) y `observabilidad`.
- [x] OpenTofu crea namespaces (con Pod Security Admission), secretos (desde `terraform.tfvars`, fuera de Git), Argo CD (chart oficial 10.18.1) y las aplicaciones; y el contenedor de Ollama en Docker Desktop con el proveedor de Docker (como en el Laboratorio 2).
- [x] Variables de OpenTofu con validaciones y salidas con los comandos para entrar a cada servicio.
- [x] Scripts `setup-minikube` y `levantar-plataforma` para Windows (PowerShell) y Linux (bash).
- [x] `docker compose up --build` sigue funcionando igual que antes.
- [x] Procedimiento de recuperación completa con objetivo < 30 min y ensayo guiado para un equipo distinto (`docs/runbook.md`, guía de laboratorio 19). El tiempo medido se anota en el registro de incidentes.
