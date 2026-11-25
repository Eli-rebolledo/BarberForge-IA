# Cómo contribuir a BarberForge

## Equipo y responsables

Cada feature (`spec/features/NNN-…`) tiene una persona responsable. Esa persona revisa los pull requests que
tocan su parte (ver `.github/CODEOWNERS`), mantiene al día su `spec.md`, `plan.md` y `tasks.md`, y la explica en la
sustentación.

| Integrante (GitHub) | Features a cargo |
|---|---|
| @Eli-rebolledo | 001 Autenticación y cuentas · 002 Barbería y catálogo · 008 Plataforma, Compose y CI |
| @victor1134 | 007 Asistente con IA y RAG · 009 Kubernetes, GitOps e IaC |
| @JavierGalindez | 003 Gestión de barberos · 004 Disponibilidad · 010 DevSecOps y observabilidad |
| @MiyerACI | 005 Agendamiento de citas · 006 Recordatorios y confirmación · 011 Predicción de inasistencias (ML) |

## Ramas

```
main      ← lo que está desplegado. Solo entra por pull request desde develop, con el CI en verde.
develop   ← integración. Aquí llegan los pull requests de cada feature.
feature/NNN-descripcion   ← trabajo nuevo (ej. feature/011-prediccion-inasistencias)
fix/NNN-descripcion       ← correcciones (ej. fix/005-doble-reserva)
```

1. `git switch develop && git pull`
2. `git switch -c feature/011-prediccion-inasistencias`
3. Commits pequeños (ver abajo) y `git push -u origin feature/011-prediccion-inasistencias`
4. Pull request **hacia `develop`**. Lo revisa el responsable de cada parte tocada (GitHub los asigna solo con
   `CODEOWNERS`) y no quien lo abrió; el CI debe pasar.
5. Cuando `develop` está estable: pull request de `develop` a `main`. Al fusionarlo, el pipeline publica las
   imágenes y Argo CD actualiza dev solo.

Si `main` recibe una corrección urgente directa, hay que traerla a `develop` (`git switch develop && git merge main`)
antes de abrir el siguiente pull request, o el CI de `develop` fallará por algo que ya estaba arreglado.

## Issues

Cada funcionalidad tiene su issue (`001 · Autenticación y cuentas` … `012 · Asistente de voz con RAG y ML`) y cada
error se reporta con la plantilla «Error» (`.github/ISSUE_TEMPLATE/`). El pull request menciona su issue
(`Cierra #12`) para que se cierre solo al fusionarlo. En un repositorio nuevo, los issues de las funcionalidades y
del trabajo futuro se crean con `.\scripts\crear-issues.ps1` (necesita GitHub CLI: `gh auth login`).

## Mensajes de commit

Formato *Conventional Commits*, en español, con el número de la feature como alcance:

```
feat(011): modelo de inasistencias y aviso de 60 minutos
fix(006): no enviar recordatorio a citas canceladas
docs(009): pasos para promover a staging
test(007): caso de respuesta aprendida
chore(gitops): dev usa las imágenes 1a2b3c4   ← lo escribe el pipeline
```

## Antes de abrir el pull request

```bash
cd codigo/backend && ruff check . && pytest              # 105 pruebas
cd codigo/voz && ruff check . && pytest                  # 18 pruebas (Whisper y Piper simulados)
cd codigo/frontend && npm run build                      # incluye TypeScript
helm lint plataforma/helm/barberforge -f plataforma/helm/barberforge/values-dev.yaml
cd plataforma/opentofu && tofu fmt -check && tofu validate
```

Si cambias el modelo de inasistencias (`codigo/backend/app/ml/`), vuelve a entrenarlo con
`python -m app.tareas entrenar` y sube el nuevo `modelo_inasistencia.joblib` (ver `docs/ml-prediccion-inasistencias.md`).

## Uso de IA

Se permite usar asistentes de IA para escribir código, pruebas y documentación (política del diplomado). Antes de
integrar el cambio hay que validarlo: debe pasar las pruebas y los escaneos, quien lo integra debe poder explicarlo, y
el pull request debe indicar qué partes se generaron con IA y cómo se verificaron.

## Secretos

Nunca subas `.env`, `terraform.tfvars` ni `*.tfstate`. Están en `.gitignore`, y Trivy revisa secretos en cada pipeline.
