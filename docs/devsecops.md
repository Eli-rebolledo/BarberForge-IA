# DevSecOps: controles de seguridad de BarberForge

Referentes del módulo 3: NIST SSDF (SP 800-218), SLSA y Sigstore. Cada control está automatizado en
`.github/workflows/ci.yml` o en la configuración del clúster, y aquí se explica qué evidencia deja.

## Controles

| Riesgo | Control | Dónde | Evidencia |
|---|---|---|---|
| Dependencias con vulnerabilidades conocidas | Trivy `fs` bloquea con CRÍTICAS; las ALTAS quedan en un reporte | job `seguridad` | log del job |
| Secretos subidos por error (claves, tokens) | Trivy `fs` con el escáner `secret` | job `seguridad` | log del job |
| Dockerfiles, manifiestos o IaC inseguros | Trivy `config` bloquea con ALTAS y CRÍTICAS | job `seguridad` | log del job |
| Imagen con vulnerabilidades del sistema operativo | Trivy `image` **antes** de publicar | job `imagenes` | log del job |
| No saber qué contiene una imagen | SBOM SPDX con Syft | job `imagenes` | artefactos `sbom-api.spdx.json`, `sbom-web.spdx.json` |
| Imagen alterada o publicada fuera del pipeline | Firma sin llaves con Cosign + atestación del SBOM + `cosign verify` | job `imagenes` | Rekor (registro público de transparencia) |
| Código que no pasa pruebas | ruff + pytest + build del frontend como requisito para construir | jobs `backend`, `frontend` | log |
| YAML de Kubernetes inválido | `helm lint` + `kubeconform` (incluye los CRD de Argo CD) | job `plataforma` | log |
| IaC mal escrita | `tofu fmt -check` + `tofu validate` | job `plataforma` | log |
| Cambios manuales en el clúster | Argo CD con `selfHeal` y AppProject restringido | Argo CD | historial de sincronización |
| Secretos en Git | Secretos en `terraform.tfvars` (en `.gitignore`) → Secret de Kubernetes | OpenTofu | `git ls-files` no los muestra |
| Contenedor comprometido escala privilegios | `runAsNonRoot`, uid fijo, `readOnlyRootFilesystem`, `drop: [ALL]`, seccomp | chart `barberforge` | `kubectl get pod -o yaml` |
| Pods que no cumplen el estándar | Pod Security Admission: `restricted` en staging, `baseline` + aviso en dev | OpenTofu (etiquetas del namespace) | `kubectl get ns --show-labels` |
| Movimiento lateral dentro del clúster | NetworkPolicies: denegar todo + caminos mínimos (solo la API llega a PostgreSQL) | chart `barberforge` | prueba con `nc` (guía, paso 5) |
| Token de Kubernetes robado desde un pod | `automountServiceAccountToken: false` | chart `barberforge` | sin `/var/run/secrets/kubernetes.io` en los pods |
| Prompt injection al asistente | Guarda de entrada + contexto marcado como datos + acciones solo vía base de datos | `app/services/chat.py` | pruebas `test_chat.py` |

## Verificar una imagen (cualquiera puede hacerlo)

```bash
# ¿La imagen salió del workflow ci.yml de este repositorio?
cosign verify ghcr.io/eli-rebolledo/barberforge-api:<sha> \
  --certificate-identity-regexp "^https://github.com/Eli-rebolledo/BarberForge-IA/.github/workflows/ci.yml@" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# SBOM adjunto a la imagen
cosign verify-attestation --type spdxjson ghcr.io/eli-rebolledo/barberforge-api:<sha> \
  --certificate-identity-regexp "^https://github.com/Eli-rebolledo/BarberForge-IA/" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com | jq -r .payload | base64 -d | jq '.predicate.packages | length'
```

## Bitácora de hallazgos

Distinguimos entre vulnerabilidad conocida, mala configuración y riesgo contextual. Cada hallazgo aceptado va
también en `.trivyignore` con su justificación.

| Fecha | Hallazgo | Tipo | Severidad | Decisión |
|---|---|---|---|---|
| 2026-11-18 | Starlette 0.38 (arrastrada por FastAPI 0.115.0) con vulnerabilidades conocidas de denegación de servicio en formularios multipart | Vulnerabilidad conocida | Alta | **Corregido:** FastAPI 0.115.12 → Starlette 0.46.2; 68 pruebas pasan |
| 2026-11-18 | La web corría nginx como root en el puerto 80 | Mala configuración | Media | **Corregido:** `nginx-unprivileged`, uid 101, puerto 8080 |
| 2026-11-18 | `grafana/otel-lgtm` necesita escribir en su propio disco (KSV-0014) y corre como root (KSV-0012) | Riesgo contextual | Alta / Media | **Aceptado** solo en el laboratorio: namespace propio, sin datos de usuarios, sin capacidades, sin escalada, seccomp por defecto. En producción se usarían los charts oficiales de Grafana, Prometheus, Tempo y Loki |
| 2026-11-18 | Imágenes de terceros con etiqueta (`pgvector:pg16`, `mailhog:v1.0.1`, `otel-lgtm:0.8.1`) y no con digest | Riesgo contextual | Media | Aceptado: versión fija y escaneo en cada build. Mejora futura: fijar por `@sha256` |
| 2026-11-18 | MailHog (`v1.0.1`) ya no tiene mantenimiento | Riesgo contextual | Baja | Aceptado solo en dev/staging; no recibe tráfico de fuera del clúster (NetworkPolicy) |
| 2026-11-18 | PyJWT 2.9.0 (tokens de sesión) con vulnerabilidades conocidas, detectadas por Trivy `fs`: el job `seguridad` bloqueó el lanzamiento v1.0.0 | Vulnerabilidad conocida | Crítica | **Corregido:** PyJWT 2.15.1; `pip-audit` sin hallazgos y 68 pruebas pasan |
| 2026-11-18 | `tofu validate` rechazaba el `for_each` del Secret de GHCR porque la condición dependía de `github_token` (variable sensible) | Error de IaC | — | **Corregido:** `nonsensitive()` solo sobre el sí/no; el valor del token sigue oculto |
| 2026-11-18 | Imagen web sobre `nginx-unprivileged:1.27-alpine` (rama de nginx sin soporte) con vulnerabilidades críticas, detectadas por Trivy `image` antes de publicar | Vulnerabilidad conocida | Crítica | **Corregido:** `nginx-unprivileged:1.30-alpine` (rama estable con soporte) |
| 2026-11-18 | `brotli-libs` 1.2.0 en la imagen web (CVE-2026-111497, escritura fuera de límites en el descompresor Brotli); Alpine ya publicó 1.2.1 pero la imagen base aún no lo trae | Vulnerabilidad conocida | Crítica | **Corregido:** `apk upgrade` en el Dockerfile, así cada build toma los parches de Alpine aunque la imagen base se atrase |

## Revisión del código generado con IA

Gran parte de este repositorio se escribió con ayuda de un asistente de IA. Antes de integrar cualquier cambio:
- Pasa ruff, pytest (68 pruebas), el build de TypeScript, `helm lint`, `kubeconform`, `tofu validate`, actionlint y Trivy.
- Cada pull request lo revisa una persona del equipo distinta a quien lo abrió (`CODEOWNERS`).
- Quien sustenta una parte debe poder explicarla línea por línea. Si no puede, esa parte no está lista.
