# 009 · Plan técnico

## Flujo
```
git push main ─► GitHub Actions ─► imágenes en GHCR (tag = SHA) ─► commit en values-dev.yaml
                                                                        │
Minikube ◄── Argo CD (vigila plataforma/helm cada 60 s) ◄───────────────┘
```

## Piezas
| Carpeta | Herramienta | Qué hace |
|---|---|---|
| `plataforma/helm/barberforge` | Helm | La aplicación: postgres, migraciones, api, worker, web, mailhog, ollama (opcional), ingress, hpa, networkpolicy |
| `plataforma/helm/observabilidad` | Helm | `grafana/otel-lgtm` + tablero de SLI/SLO (ver 010) |
| `plataforma/argocd` | Helm + Argo CD | AppProject y Applications (app of apps). Lo instala OpenTofu |
| `plataforma/opentofu` | OpenTofu | Namespaces, secretos, Argo CD, aplicaciones y Ollama en Docker Desktop |
| `scripts/` | PowerShell / bash | Instalar herramientas, crear el clúster, levantar y destruir |

## Orden de sincronización (olas de Argo CD)
| Ola | Recursos |
|---|---|
| 0 | ConfigMap, ServiceAccount, Services, PostgreSQL, MailHog, NetworkPolicies |
| 1 | Job `barberforge-migraciones` (hook `Sync`, se recrea en cada sincronización) |
| 2 | Deployments `api`, `worker`, `web` |

## Cambios en la aplicación
- `app/tareas.py`: `python -m app.tareas migrar|indexar` para el Job.
- `EJECUTAR_RECORDATORIOS` e `INDEXAR_AL_ARRANCAR` (`app/config.py`): la API los apaga y el worker los enciende.
- `codigo/frontend/nginx.conf.template`: `API_UPSTREAM` y `DNS_RESOLVER` por variable; nginx sin privilegios en el puerto 8080.

## Seguridad de los manifiestos
`runAsNonRoot`, usuario fijo, `readOnlyRootFilesystem`, `drop: [ALL]`, `seccompProfile: RuntimeDefault`,
`automountServiceAccountToken: false`, requests/limits en todo, NetworkPolicies de menor privilegio y Pod Security
Admission (`restricted` en staging). Ver 010.

## Decisiones
- **Ollama fuera del clúster** (`host.minikube.internal:11434`): llama3 necesita ~8 GB y el equipo tiene 16 GB.
- **Un solo repositorio** con la carpeta `plataforma/` como configuración GitOps: más simple para el equipo; el pipeline escribe solo en `values-dev.yaml`.
- **Calico** como CNI en Minikube para que las NetworkPolicies se cumplan.
- **Imágenes públicas en GHCR**: Argo CD y Minikube las descargan sin credenciales (OpenTofu soporta privadas con `github_token`).
