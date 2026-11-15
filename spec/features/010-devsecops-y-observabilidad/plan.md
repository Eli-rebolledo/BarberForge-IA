# 010 · Plan técnico

## Pipeline (`.github/workflows/ci.yml`)
```
backend (ruff + pytest) ──┐
frontend (npm build) ─────┤
plataforma (helm lint,    ├─► imagenes [api, web]: build → Trivy image → (main) push GHCR → SBOM (Syft)
  kubeconform, tofu)      │                         → cosign sign → cosign attest → cosign verify
seguridad (Trivy fs +     ┘                                   │
  Trivy config)                                               ├─► gitops (main): yq → values-dev.yaml → commit
                                                              └─► dokploy (opcional)
```

## Telemetría
| Archivo | Contenido |
|---|---|
| `app/core/telemetria.py` | Proveedores de trazas, métricas y logs OTLP/HTTP; instrumenta FastAPI (sin `/health`), SQLAlchemy y httpx |
| `app/core/metricas.py` | Contadores e histograma de negocio; `cronometro_llm` |
| `plataforma/helm/observabilidad` | `grafana/otel-lgtm` + ConfigMap con el tablero |

## SLI/SLO
| SLI | Consulta (Prometheus) | SLO |
|---|---|---|
| Disponibilidad | 1 − peticiones 5xx / peticiones totales de `barberforge-api` | ≥ 99 % en 30 días |
| Latencia | p95 de `http_server_request_duration_seconds` sin `/api/chat` | < 500 ms |
| Peticiones rápidas | proporción < 500 ms sin el chat | ≥ 95 % |

El chat se excluye de la latencia: depende de llama3 (segundos) y tiene su propia métrica `barberforge_llm_duracion_seconds`.
