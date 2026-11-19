# 011 · Plan técnico

## Flujo
```
                 ┌──────────── entrenamiento (en un equipo o en CI) ─────────────┐
 generador.py ─► 5.000 citas sintéticas ─► entrenamiento.py ─► modelo_inasistencia.joblib (va en la imagen)
                                               │  logística vs. árbol, división por fecha
                                               └► MLflow (sqlite:///mlflow.db)

 POST /api/appointments ─► citas.agendar ─► prediccion.actualizar_riesgo ─► appointments.no_show_risk
 worker cada 60 s ─► procesar_recordatorios
                       ├─ 40 < minutos para la cita ≤ 60 y riesgo ≥ umbral ─► correo «es en una hora»
                       └─ minutos ≤ 40 y pendiente ─► correo con confirmación (feature 006, sin cambios)

 CronJob (lunes 3 a. m.) ─► python -m app.tareas reentrenar ─► citas reales cerradas
                             ─► ¿AUC nuevo ≥ AUC actual? ─► ml_models (firmado, activo) ─► API y worker lo cargan
```

## Archivos
| Archivo | Contenido |
|---|---|
| `app/ml/caracteristicas.py` | Las 10 variables del modelo, iguales en generador, entrenamiento y API |
| `app/ml/generador.py` | Citas sintéticas reproducibles (semilla 2026) |
| `app/ml/supuestos.md` | Reglas del generador, fuentes, resultados y elección del umbral |
| `app/ml/entrenamiento.py` | Candidatos, división por fecha, métricas, importancia de variables, MLflow |
| `app/ml/modelo_inasistencia.joblib` | Modelo entrenado con datos sintéticos (≈ 3 KB) |
| `app/services/prediccion.py` | Carga del modelo (base firmada → archivo), características desde la base, riesgo, reentrenamiento |
| `app/services/citas.py` | `agendar` guarda el riesgo; `procesar_avisos_previos` envía el aviso de 60 min |
| `app/models/modelo_ml.py` + migración `007` | Tabla `ml_models`; columnas `created_at`, `no_show_risk`, `early_reminder_sent_at` |
| `app/routers/admin.py` | `GET /api/admin/ml` |
| `app/tareas.py` | `generar-datos`, `entrenar`, `reentrenar` |
| `codigo/frontend/components/Riesgo.tsx` | Insignia «Riesgo N %» |
| `codigo/frontend/app/admin/page.tsx` | Tarjeta «Predicción de inasistencias» |
| `plataforma/helm/.../reentrenamiento-cronjob.yaml` | CronJob semanal con el mismo endurecimiento que el worker |

## Variables del modelo
`dia_semana`, `franja`, `hora`, `anticipacion_horas`, `es_invitado`, `citas_previas`, `faltas_previas`,
`tasa_faltas` (suavizada), `precio_miles`, `num_servicios`. Solo datos conocidos al agendar; el historial cuenta
únicamente citas que terminaron antes de que se creara la cita (sin «ver el futuro»).

## Configuración
| Variable | Por defecto | Uso |
|---|---|---|
| `ML_ACTIVO` | `true` | `false` = sin predicción (solo recordatorio de 40 min) |
| `ML_UMBRAL_RIESGO` | `0.20` | Desde este riesgo se envía el aviso de 60 min |
| `ML_MINIMO_REENTRENAMIENTO` | `200` | Citas reales cerradas necesarias para reentrenar |

## Seguridad
- Los modelos de la base se cargan con `joblib` (pickle) **solo si su firma HMAC-SHA256 coincide**; la clave se
  deriva de `JWT_SECRET`, que no está en la base. El modelo empaquetado viene del repositorio y de la imagen firmada.
- La NetworkPolicy de PostgreSQL permite el componente `reentrenamiento`.
- El CronJob corre sin root, con disco de solo lectura y sin capacidades.

## Observabilidad
- `barberforge.ml.predicciones{nivel=alto|bajo}`: citas evaluadas.
- `barberforge.recordatorios.enviados{tipo=40|60}`: recordatorios por tipo.
