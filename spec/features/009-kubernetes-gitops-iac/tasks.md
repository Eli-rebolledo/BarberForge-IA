# 009 · Tareas

## Aplicación
- [x] Job de migraciones (`app/tareas.py`) y banderas `EJECUTAR_RECORDATORIOS` / `INDEXAR_AL_ARRANCAR`
- [x] nginx sin privilegios con upstream configurable por variable de entorno

## Helm
- [x] Chart `barberforge` con valores base, dev y staging
- [x] PostgreSQL como StatefulSet con volumen y `PGDATA` en subcarpeta
- [x] Worker separado de la API; HPA en staging
- [x] Ingress (`/api` → API con 180 s de timeout, `/` → web)
- [x] NetworkPolicies (denegar todo + caminos permitidos)
- [x] `helm lint` + `kubeconform` en CI

## Argo CD
- [x] Chart `plataforma/argocd` con AppProject y Applications
- [x] dev automático con prune y self-heal; staging manual
- [x] Validación de los CRD con el catálogo de esquemas en CI

## OpenTofu
- [x] Proveedores kubernetes, helm y docker
- [x] Namespaces con Pod Security Admission
- [x] Secretos desde `terraform.tfvars` (en `.gitignore`)
- [x] Argo CD con el chart oficial y las aplicaciones
- [x] Ollama en Docker Desktop (imagen, volumen, red, contenedor y descarga de modelos)
- [x] Validaciones en variables y salidas útiles
- [x] `tofu fmt -check` + `tofu validate` en CI

## Operación
- [x] Scripts de instalación y arranque (Windows y Linux)
- [x] Guía `docs/plataforma-kubernetes.md` y runbook `docs/runbook.md`
- [ ] Ensayo de recuperación en otro equipo y evidencia (capturas) para la sustentación
