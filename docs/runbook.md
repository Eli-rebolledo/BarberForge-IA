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
| Respuestas muy lentas | Grafana → «Tiempo de respuesta del modelo de lenguaje» | Revisa que el modelo sea `llama3.2:3b` (`LLM_MODEL` en `.env`, `modelo_llm` en tfvars y `ollama.modelo` en values); la primera respuesta tras arrancar tarda más porque Ollama carga el modelo |

## Los recordatorios no llegan
1. `kubectl logs deploy/barberforge-worker -n barberforge-dev` → ¿hay errores de SMTP?
2. Mira el buzón: `kubectl port-forward -n barberforge-dev svc/barberforge-mailhog 8025:8025`.
3. Debe haber **un solo** pod del worker (`kubectl get pods -l app.kubernetes.io/component=worker -n barberforge-dev`).

## Alertas de Grafana
Grafana carga cuatro reglas al arrancar (`plataforma/helm/observabilidad/grafana/alertas.yaml`), en **Alerting › Alert rules ›
BarberForge**. Con Docker Compose también llegan por correo a MailHog (http://localhost:8025). Cada alerta enlaza a su sección:

| Alerta | Se dispara cuando | Severidad |
|---|---|---|
| SLO disponibilidad | Más del 1 % de peticiones en 5xx durante 5 min | crítica |
| API transaccional lenta | p95 sin el chat > 500 ms durante 10 min | advertencia |
| Presupuesto de error | Queda < 25 % del presupuesto de 30 días | advertencia |
| Ollama fallando | Respuestas del modelo de lenguaje con error durante 2 min | advertencia |
| Asistente con IA lento / voz lenta | p95 del asistente (chat o voz) > 60 s durante 10 min | advertencia |
| Asistente: muchos «no sé» | más del 30 % de respuestas sin respuesta útil en 1 hora | advertencia |

### API con errores 5xx
1. `curl http://localhost:8080/api/health` (o el host del ingress): si dice `db: false`, el problema es PostgreSQL (tabla «La aplicación no carga»).
2. Grafana › Explore › Loki: `{service_name="barberforge-api"} |= "ERROR"` muestra la excepción.
3. Grafana › Explore › Tempo: busca trazas con `status=error` para ver qué consulta falló.
4. Si empezó con un despliegue, vuelve a la versión anterior en Argo CD (**History and rollback**).

### API lenta
1. En el tablero, «Duración por ruta» muestra qué endpoint se volvió lento.
2. `kubectl top pods -n barberforge-dev`: si la API está al límite de CPU, sube `api.replicas` o activa `api.autoescalado`.
3. Si es la base de datos, revisa la traza en Tempo: la consulta lenta aparece como un span de SQLAlchemy.

### Presupuesto de error
Política del SLO: se congelan los cambios no urgentes hasta que el presupuesto vuelva a superar el 25 %. Solo entran
correcciones de estabilidad, por pull request a `develop` y con su prueba.

### Ollama no responde
Mismos pasos que «El asistente no responde con IA». Mientras tanto el chat y la voz siguen funcionando con el respaldo
(texto guardado y detección de intención por reglas).

### Asistente lento
1. En el tablero, «Asistente: p95 por servicio» dice si es el chat, la voz o ambos.
2. «Tiempo de respuesta del modelo de lenguaje»: si también subió, el cuello es Ollama (RAM o CPU del equipo);
   `docker stats bf-ollama` o `kubectl top`. Cierra programas pesados o usa un modelo más liviano.
3. Si solo sube la voz, revisa `docker compose logs bf-voz` (la transcripción con Whisper) y corre
   `python scripts/prueba-servicios.py --solo voz` para ver cuánto tarda cada etapa.

### Asistente no sabe
1. Panel → «Por aprender»: mira qué preguntas se acumularon.
2. Si falta información de la barbería (conocimiento): publica la respuesta oficial; se reindexa sola y se avisa a quien preguntó.
3. Si la información existe y no la encontró (asistente): ajusta el documento o el prompt, corre el Golden Dataset
   (`codigo/backend/evaluacion`) y despliega por pull request.
4. Si son preguntas fuera de tema o abuso (usuario): no se cambia nada.

## El asistente de voz no responde
| Síntoma | Diagnóstico | Solución |
|---|---|---|
| No aparece el botón del micrófono | El navegador solo lo permite en `localhost` o con https | Abre `http://localhost:8080`, no la IP |
| «No pude entender el audio» | `docker compose logs bf-voz` | Habla más cerca del micrófono o sube a `WHISPER_MODEL=small` y reconstruye |
| `bf-voz` reiniciándose | `docker stats` → memoria | Docker Desktop necesita ≥ 8 GB; o usa `WHISPER_MODEL=tiny` e `INTENCION_CON_LLM=false` |
| Responde pero no habla | `http://localhost:8001/voz/health` → `"tts": false` | La voz de Piper no se descargó: el navegador lee la respuesta. Reconstruye con internet para tener Piper |

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

### Ensayo de recuperación (para la sustentación)
Se hace en un equipo distinto al habitual, con el cronómetro en marcha, y se anota en el registro de incidentes:
1. Clonar el repositorio y copiar `terraform.tfvars` desde el gestor de contraseñas.
2. `.\scripts\setup-minikube.ps1` y `.\scripts\levantar-plataforma.ps1`.
3. Esperar a que Argo CD muestre las aplicaciones `Synced` y `Healthy`.
4. Restaurar el último respaldo y comprobar: iniciar sesión, ver citas, preguntar al asistente.
5. Anotar el tiempo total y lo que hubo que corregir.

## Registro de incidentes
| Fecha | Qué pasó | Detección | Causa | Solución | Tiempo hasta recuperar |
|---|---|---|---|---|---|
| | | | | | |
