# Runbook de operación

Problemas frecuentes al operar BarberForge en Minikube, con su diagnóstico y solución. Primero mira el estado general:
```powershell
kubectl get applications -n argocd
kubectl get pods -A | Select-String -NotMatch "Running|Completed"
```

## La aplicación no carga

| Síntoma | Diagnóstico | Solución |
|---|---|---|
| Pods en `ImagePullBackOff` | `kubectl describe pod <pod> -n barberforge-dev` → `denied` o `not found` | Las imágenes de GHCR son privadas o el pipeline de `main` aún no corrió. Hazlas públicas (guía, paso 0) o configura `github_token` |
| API en `Running` pero `0/1 READY` | `kubectl logs deploy/barberforge-api -n barberforge-dev` → `esperando base de datos` | Revisa PostgreSQL (siguiente fila) |
| `barberforge-postgres-0` en `CrashLoopBackOff` | `kubectl logs barberforge-postgres-0 -n barberforge-dev` | Si dice `password authentication failed`: la clave de `terraform.tfvars` cambió y el volumen tiene la anterior. En dev: `kubectl delete pvc -l app.kubernetes.io/component=postgres -n barberforge-dev` y luego borra el pod |
| Job de migraciones fallido | `kubectl logs job/barberforge-migraciones -n barberforge-dev` | Corrige y vuelve a sincronizar. El Job se recrea en cada sync |
| `OutOfSync` permanente en Argo CD | Interfaz de Argo CD → **App diff** | Hay un cambio manual que el self-heal no puede corregir, o un campo que cambia siempre. Revisa `ignoreDifferences` |
| Argo CD no ve el repositorio | Argo CD → Settings → Repositories | Si el repositorio es privado, define `github_usuario` y `github_token` y corre `tofu apply` |

## El asistente no responde con IA

| Síntoma | Diagnóstico | Solución |
|---|---|---|
| Responde con el texto del documento, sin redactar | `docker ps` → ¿`barberforge-ollama` está `Up`? | `docker start barberforge-ollama` |
| Ollama arriba pero sin modelos | `docker exec barberforge-ollama ollama list` | `docker start -a barberforge-ollama-modelos` (vuelve a descargar) |
| Los pods no llegan a Ollama | `kubectl run t --rm -it --image=busybox:1.36 --restart=Never -n barberforge-dev -- wget -qO- http://host.minikube.internal:11434` | Puerto 11434 ocupado por el Ollama de `docker compose`: `docker compose down` y `tofu apply` |
| Respuestas muy lentas | Grafana → «Tiempo de respuesta de llama3» | Cambia a `llama3.2:3b` (`modelo_llm` en tfvars y `ollama.modelo` en values) |

## Los recordatorios no llegan
1. `kubectl logs deploy/barberforge-worker -n barberforge-dev` → ¿hay errores de SMTP?
2. Mira el buzón: `kubectl port-forward -n barberforge-dev svc/barberforge-mailhog 8025:8025`.
3. Debe haber **un solo** pod del worker (`kubectl get pods -l app.kubernetes.io/component=worker -n barberforge-dev`).

## Respaldo y restauración de la base de datos
El respaldo se genera dentro del pod y se copia con `kubectl cp`. No se redirige con `>` porque PowerShell
estropearía el archivo binario.
```powershell
# Respaldo
kubectl exec -n barberforge-dev barberforge-postgres-0 -- pg_dump -U barber -Fc -f /tmp/respaldo.dump barber
kubectl cp barberforge-dev/barberforge-postgres-0:/tmp/respaldo.dump .\respaldo.dump

# Restauración
kubectl cp .\respaldo.dump barberforge-dev/barberforge-postgres-0:/tmp/respaldo.dump
kubectl exec -n barberforge-dev barberforge-postgres-0 -- pg_restore -U barber -d barber --clean --if-exists /tmp/respaldo.dump
```

## Recuperación total (equipo nuevo o clúster perdido)
1. `.\scripts\setup-minikube.ps1`
2. Copia `terraform.tfvars` (guárdalo fuera del repositorio, por ejemplo en un gestor de contraseñas).
3. `.\scripts\levantar-plataforma.ps1`. Argo CD reconstruye todo desde Git.
4. Restaura el último respaldo de la base de datos (sección anterior).

Objetivo de recuperación: < 30 min sin contar las descargas de la primera vez.

## Registro de incidentes
| Fecha | Qué pasó | Detección | Causa | Solución | Tiempo hasta recuperar |
|---|---|---|---|---|---|
| | | | | | |
