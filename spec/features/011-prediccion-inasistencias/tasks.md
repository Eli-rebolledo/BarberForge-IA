# 011 · Tareas

## Datos y modelo
- [x] Variables comunes en `app/ml/caracteristicas.py`
- [x] Generador sintético reproducible y `supuestos.md` con fuentes
- [x] Entrenamiento: regresión logística vs. árbol de decisión vs. Random Forest, división por fecha
- [x] Experimento con XGBoost (`app/ml/comparar_modelos.py`), fuera de la imagen
- [x] Correo a los administradores al reentrenar (activado o conservado)
- [x] Métricas: AUC, recall, precisión, Brier, matriz de confusión; elección del umbral (0,20)
- [x] Registro en MLflow (opcional, `requirements-ml.txt`)
- [x] Modelo empaquetado `modelo_inasistencia.joblib`

## Integración
- [x] Migración 007 (`created_at`, `no_show_risk`, `early_reminder_sent_at`, `ml_models`)
- [x] Riesgo al agendar, sin bloquear la cita si el modelo falla
- [x] Aviso de 60 minutos para riesgo alto en el worker
- [x] `GET /api/admin/ml` y tarjeta en el panel
- [x] Insignia «Riesgo N %» para barbero y administrador
- [x] `python -m app.tareas reentrenar` con firma HMAC y comparación contra el modelo en uso
- [x] CronJob semanal en el chart de Helm y variables `ML_*` en Compose y ConfigMap

## Calidad
- [x] 15 pruebas en `tests/test_prediccion.py` (generador, entrenamiento, riesgo, 60/40, reentrenamiento, firma, panel)
- [x] `pip-audit` sin hallazgos para scikit-learn, numpy, joblib y mlflow

## Operación (sin código pendiente)
- [x] Reentrenamiento y evaluación con citas reales: automáticos (CronJob semanal y `python -m app.tareas reentrenar`) al llegar a 200 citas cerradas
- Mejora futura, cuando haya datos reales: probar localidad y clima como variables
