# Guía: BarberForge en Kubernetes con Argo CD y OpenTofu

Esta guía levanta BarberForge en un clúster local de **Minikube**. **OpenTofu** prepara la plataforma y **Argo CD**
despliega la aplicación leyendo este repositorio (GitOps). Está escrita para Windows con PowerShell, igual que la
guía de Minikube del diplomado; los comandos de Linux van al lado.

> ¿Solo quieres probar la app? No necesitas nada de esto: `docker compose up --build` y abre http://localhost:8080.

## Arquitectura

```
                    ┌──────────────── GitHub ────────────────┐
  git push main ──► │ Actions: pruebas, Trivy, build, SBOM,  │──► GHCR: barberforge-api / barberforge-web (firmadas)
                    │ firma ──► commit del tag en values-dev │
                    └───────────────────┬────────────────────┘
                                        │ Argo CD lee plataforma/ cada 60 s
┌─────────────────────────── Minikube ──▼──────────────────────────────────┐
│ argocd           Argo CD (instalado por OpenTofu)                         │
│ barberforge-dev  postgres · migraciones · api · worker · web · mailhog    │
│ barberforge-stg  lo mismo, 2 réplicas + autoescalado (sync manual)        │
│ observabilidad   Grafana + Prometheus + Tempo + Loki (otel-lgtm)          │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ http://host.minikube.internal:11434
                 Docker Desktop: barberforge-ollama (llama3 + nomic-embed-text, creado por OpenTofu)
```

| Qué | Dónde | Lo crea |
|---|---|---|
| Clúster | Minikube (driver Docker, CNI Calico) | `scripts/setup-minikube.ps1` |
| Namespaces, secretos, Argo CD, aplicaciones de Argo CD, Ollama | `plataforma/opentofu` | OpenTofu |
| Aplicación (Helm) | `plataforma/helm/barberforge` | Argo CD |
| Observabilidad (Helm) | `plataforma/helm/observabilidad` | Argo CD |

## Requisitos
- Windows 10/11 de 64 bits, **16 GB de RAM** (Minikube usa 6 GB y Ollama ~5 GB), virtualización habilitada.
- **Docker Desktop** abierto ("Engine running").
- `winget` (App Installer de Microsoft Store).

## 0. Una sola vez en GitHub (lo hace quien administra el repositorio)

1. Sube el repositorio con las ramas `main` y `develop` (ver `CONTRIBUTING.md`).
2. El primer push a `main` corre el pipeline y publica las imágenes en **Packages** del repositorio.
3. Deja las imágenes **públicas**, para que Minikube las descargue sin credenciales: en GitHub entra a tu perfil →
   **Packages** → `barberforge-api` → **Package settings** → **Change visibility** → **Public**. Repite con
   `barberforge-web`.
4. Si proteges la rama `main`, permite que **github-actions** haga push. Si no lo permites, el job `gitops` no podrá
   escribir el tag nuevo en `values-dev.yaml`.

> Si el repositorio o las imágenes deben ser privados, pon `github_usuario` y `github_token` en `terraform.tfvars` y
> agrega `pullSecrets: [{name: ghcr-credenciales}]` en `values.yaml`.

## 1. Instalar herramientas y crear el clúster (una vez por equipo)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup-minikube.ps1
```
Linux: `bash scripts/setup-minikube.sh`

Salida esperada al final:
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   1m    v1.3x.x
```

## 2. Configurar los secretos

```powershell
Copy-Item plataforma\opentofu\terraform.tfvars.ejemplo plataforma\opentofu\terraform.tfvars
notepad plataforma\opentofu\terraform.tfvars
```
Cambia `db_password` (mínimo 12 caracteres) y `jwt_secret` (mínimo 32). Este archivo **no** se sube a Git
(`.gitignore`); el estado de OpenTofu (`terraform.tfstate`) tampoco, porque contiene los secretos.

En Linux, cambia también `docker_host` por el de tu Docker. Por ejemplo
`unix:///home/<usuario>/.docker/desktop/docker.sock`, como en el Laboratorio 2.

## 3. Levantar la plataforma

```powershell
.\scripts\levantar-plataforma.ps1
```
Linux: `bash scripts/levantar-plataforma.sh`

El script hace `minikube start` (si hace falta) y después `tofu init`, `tofu validate` y `tofu apply`. Al final
muestra `tofu output` y las aplicaciones de Argo CD:
```
NAME                  SYNC STATUS   HEALTH STATUS
barberforge-dev       Synced        Healthy
barberforge-staging   OutOfSync     Missing        ← staging se sincroniza a mano (paso 6)
observabilidad        Synced        Healthy
```
La primera vez tarda: se descargan Argo CD, las imágenes y los modelos de IA. Puedes seguir la descarga de los
modelos con `docker logs -f barberforge-ollama-modelos`.

## 4. Entrar a cada servicio

Cada `port-forward` ocupa su propia terminal.

| Servicio | Comando | URL |
|---|---|---|
| BarberForge (dev) | `kubectl port-forward -n barberforge-dev svc/barberforge-web 8080:8080` | http://localhost:8080 |
| Argo CD | `kubectl port-forward -n argocd svc/argocd-server 8081:80` | http://localhost:8081 (usuario `admin`) |
| Grafana | `kubectl port-forward -n observabilidad svc/otel-lgtm 3000:3000` | http://localhost:3000 (`admin` / `admin`) |
| Correos (MailHog) | `kubectl port-forward -n barberforge-dev svc/barberforge-mailhog 8025:8025` | http://localhost:8025 |

Clave inicial de Argo CD:
```powershell
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | % { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_)) }
```
Linux: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d`

**Con Ingress (opcional).** Corre `minikube tunnel` en una terminal como administrador y agrega
`127.0.0.1 barberforge.local` al archivo `C:\Windows\System32\drivers\etc\hosts`. Luego abre http://barberforge.local.

## 5. Demostraciones para la sustentación

### GitOps: un cambio en Git llega solo al clúster
1. Cambia algo visible (por ejemplo, un texto del frontend), crea un pull request a `develop` y luego de `develop` a `main`.
2. El pipeline publica las imágenes con el SHA del commit y hace el commit `chore(gitops): dev usa las imágenes …`.
3. En Argo CD, `barberforge-dev` pasa a *OutOfSync* y en ≤ 60 s vuelve a *Synced* con los pods nuevos.
   ```powershell
   kubectl get pods -n barberforge-dev -w
   kubectl rollout history deployment/barberforge-api -n barberforge-dev
   ```

### Drift: Argo CD deshace los cambios hechos a mano
```powershell
kubectl scale deployment/barberforge-web -n barberforge-dev --replicas=3
kubectl get deployment barberforge-web -n barberforge-dev -w   # vuelve a 1 en segundos (self-heal)
```

### Rollback
La forma GitOps es revertir el commit de versión: `git revert <commit-gitops>` y push. También se puede desde la
interfaz de Argo CD (**History and rollback**), pero mientras la sincronización automática esté activa, Argo CD
volverá a lo que diga Git.

### Promover a staging
Copia en `values-staging.yaml` los `tag` que ya funcionan en dev, haz el pull request y, cuando se fusione, pulsa
**Sync** en `barberforge-staging`. También puedes usar `kubectl -n argocd patch application barberforge-staging --type merge -p '{"operation":{"sync":{}}}'`.
```powershell
kubectl get pods,hpa -n barberforge-staging
```

### Network policies
```powershell
kubectl run prueba -n barberforge-dev --rm -it --image=busybox:1.36 --restart=Never -- nc -zv -w 3 barberforge-postgres 5432
# → timed out: solo la API, el worker y las migraciones pueden hablar con PostgreSQL
```

### Firma de la imagen
```powershell
cosign verify ghcr.io/eli-rebolledo/barberforge-api:<sha> `
  --certificate-identity-regexp "^https://github.com/Eli-rebolledo/BarberForge-IA/.github/workflows/ci.yml@" `
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## 6. Apagar o borrar

| Acción | Comando |
|---|---|
| Apagar sin perder nada | `minikube stop` (y `docker stop barberforge-ollama`) |
| Volver a encender | `.\scripts\levantar-plataforma.ps1` |
| Borrar todo lo de OpenTofu (bases de datos incluidas) | `.\scripts\destruir-plataforma.ps1` |
| Borrar el clúster | `minikube delete` |

Las fallas comunes y su solución están en [runbook.md](runbook.md).
