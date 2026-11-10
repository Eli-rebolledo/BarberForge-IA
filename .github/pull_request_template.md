## Qué cambia
<!-- Una o dos frases. Enlaza la feature: spec/features/NNN-… -->

## Cómo se probó
- [ ] `ruff check .` y `pytest` (backend)
- [ ] `npm run build` (frontend)
- [ ] `helm lint` / `tofu validate` (si toca `plataforma/`)
- [ ] Probado a mano (describe cómo):

## Seguridad
- [ ] Sin secretos en el código (`.env`, `terraform.tfvars` y `*.tfstate` no se suben)
- [ ] Si agrega dependencias o imágenes, pasó Trivy en el pipeline

## Uso de IA
<!-- ¿Qué partes se generaron con IA y cómo se verificaron? («Ninguna» también vale) -->

## Checklist de la feature
- [ ] Actualicé `tasks.md` (y `spec.md`/`plan.md` si cambió el alcance o el diseño)
