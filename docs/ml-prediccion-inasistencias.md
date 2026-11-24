# Predicción de inasistencias (feature 011): cómo correrla, verla y demostrarla

Spec: `spec/features/011-prediccion-inasistencias/` · Supuestos de los datos: `codigo/backend/app/ml/supuestos.md`

## 1. Qué hace
Al agendar, la API calcula la probabilidad de que el cliente no llegue. Si es de 0,20 o más, el worker envía un
correo extra **60 minutos antes** («Tu cita … es en una hora») además del recordatorio de **40 minutos** con
confirmación. Si es menor, solo sale el de 40, como antes.

## 2. El dataset
Las 5.000 citas sintéticas están en `docs/datos/`:
- `citas_sinteticas.csv`: el archivo exacto que usa el entrenamiento (lo mismo que produce `generar-datos`).
- `dataset_inasistencias_sintetico.xlsx`: el mismo dataset para abrir en Excel, con tres hojas: **Resumen** (tasas
  por anticipación, por faltas previas y por día), **Citas** y **Diccionario** (qué significa cada columna).

`probabilidad_real` es la probabilidad con la que el generador decidió si la persona faltaba: el modelo **no** la
ve, solo sirve para analizar. `inasistencia` (1 = no llegó) es lo que el modelo aprende a predecir.

## 3. Entrenar el modelo en tu equipo (opcional: el modelo ya viene entrenado)
```bash
cd codigo/backend
python -m venv .venv
# Windows: .venv\Scripts\activate        Mac/Linux: source .venv/bin/activate
pip install -r requirements-ml.txt

python -m app.tareas generar-datos        # datos/citas_sinteticas.csv (5.000 citas, ~18 % de inasistencia)
python -m app.tareas entrenar datos/citas_sinteticas.csv
#   regresion_logistica  AUC 0.711 · recall 0.59 · precisión 0.32 · alertas 35 %
#   arbol_decision       AUC 0.582 · recall 0.39 · precisión 0.27 · alertas 27 %
#   random_forest        AUC 0.682 · recall 0.49 · precisión 0.32 · alertas 29 %
#   ganador: regresion_logistica → app/ml/modelo_inasistencia.joblib

mlflow ui --backend-store-uri sqlite:///mlflow.db   # http://localhost:5000 → experimento «barberforge-inasistencias»
```
Experimento aparte con XGBoost (no va en la imagen de la API):
```bash
python -m app.ml.comparar_modelos     # → docs/evaluacion-ml/comparacion_modelos.csv
#   regresion_logistica  AUC 0.711 · xgboost 0.707 · random_forest 0.682 · arbol_decision 0.582
```

En MLflow se ven los tres candidatos con sus métricas, la matriz de confusión, la importancia de cada variable y el
modelo ganador. `datos/`, `mlflow.db` y `mlruns/` no se suben a Git (son regenerables).

> Si cambias `app/ml/caracteristicas.py` o la versión de scikit-learn, vuelve a correr `entrenar` y sube el nuevo
> `modelo_inasistencia.joblib`: la prueba `test_el_modelo_empaquetado_usa_las_variables_actuales` falla si se olvida.

## 4. Verlo funcionando con Docker Compose
```bash
docker compose up -d --build
# en el primer minuto (primer ciclo de recordatorios):
docker compose logs bf-api | grep -i "modelo de inasistencias"   # «modelo de inasistencias cargado: sintetico-…»
```
1. Entra como administrador → **Panel**: abajo aparece la tarjeta **Predicción de inasistencias** (modelo, AUC,
   recall, etiqueta «Entrenado con datos sintéticos» y citas próximas con riesgo alto).
2. Crea una cuenta de cliente y agenda una cita para dentro de varios días (más anticipación = más riesgo).
3. Como administrador, en **Citas** la cita aparece con la insignia roja **Riesgo N %** si supera el umbral.
   El cliente, en «Mis citas», no ve ninguna insignia.
4. Por la API: `GET /api/admin/ml` (con el token del administrador) devuelve lo mismo que la tarjeta.

### Demostrar el aviso de 60 minutos
1. Como cliente, agenda una cita que empiece **entre 45 y 55 minutos** desde ahora (si no hay franja, el
   administrador la abre en **Disponibilidad**).
2. Si la insignia no salió (riesgo bajo), fuerza un riesgo alto para la demostración:
   ```bash
   docker compose exec bf-db psql -U barber -d barber -c \
     "UPDATE appointments SET no_show_risk = 0.9 WHERE id = (SELECT max(id) FROM appointments);"
   ```
3. En menos de un minuto llega a MailHog (http://localhost:8025) el correo **«… es en una hora»**. Cuando falten
   40 minutos llega el de **confirmación**. Con una cita de riesgo bajo solo llega el segundo.

### Apagarlo
`ML_ACTIVO=false` en el `.env` y `docker compose up -d`: la app vuelve a enviar solo el recordatorio de 40 minutos.

## 5. En Kubernetes (Minikube + Argo CD)
Cuando la feature llega a `main`, el pipeline publica la imagen nueva y Argo CD la despliega solo:
- El Job de migraciones aplica la **007** antes de actualizar la API.
- Aparece el CronJob **barberforge-reentrenamiento** (lunes 3 a. m.).

```bash
kubectl get cronjob -n barberforge-dev
kubectl logs deploy/barberforge-worker -n barberforge-dev | grep -i "modelo de inasistencias"

# Correr el reentrenamiento ya, sin esperar al lunes:
kubectl create job --from=cronjob/barberforge-reentrenamiento reentreno-manual -n barberforge-dev
kubectl logs job/reentreno-manual -n barberforge-dev
#   reentrenamiento: {"entrenado": false, "citas": 3, ... "motivo": "Faltan datos: ..."}   ← normal sin citas reales
kubectl delete job reentreno-manual -n barberforge-dev
```

## 6. Reentrenar con citas reales
Cada cita que el barbero o el administrador marca como **Completada** o **No asistió** queda lista para entrenar.
Con 200 o más (al menos 20 de cada tipo), `python -m app.tareas reentrenar`:
1. entrena los tres candidatos (logística, árbol y Random Forest) con esas citas (división por fecha),
2. evalúa también el modelo actual con las mismas citas recientes,
3. guarda el nuevo en la tabla `ml_models`, firmado, y **solo lo activa si su AUC es igual o mejor**,
4. la API y el worker lo cargan solos en menos de 5 minutos; el panel cambia a «Entrenado con citas reales»,
5. **avisa por correo a los administradores** qué pasó: «nuevo modelo activado» o «se conserva el actual», con los
   dos AUC. Así el que monitorea se entera, y si algo no le cuadra vuelve al modelo anterior activándolo en `ml_models`.

**«Firmado y recargado».** *Firmado*: el modelo se guarda con una firma HMAC (con la clave del servidor); si alguien
lo cambia en la base de datos, la firma no coincide y no se carga. *Recargado*: la API y el worker revisan cada pocos
minutos cuál es el modelo activo y lo toman sin reiniciar. **Criterio de activación:** el nuevo solo reemplaza al
actual si, evaluados los dos con las mismas citas recientes, su AUC es igual o mayor (hoy 0,71). Por eso «mejora
solo, pero nunca empeora».

## 7. Guion para la sustentación (2 minutos)
1. **Problema:** las citas perdidas cuestan turnos; la causa más común es olvidarlas.
2. **Decisión:** riesgo ≥ 0,20 → aviso a los 60 y a los 40 minutos; si no, solo a los 40.
3. **Datos:** «no tenemos citas reales todavía; generamos 5.000 sintéticas con reglas de la literatura, todas
   documentadas en `supuestos.md`».
4. **Modelo:** MLflow con tres candidatos más XGBoost en un experimento; ganó la regresión logística (AUC 0,71
   frente a 0,707 de XGBoost, 0,68 de Random Forest y 0,58 del árbol). Por qué umbral 0,20: detecta
   ~6 de cada 10 inasistencias a cambio de un correo extra a 1 de cada 3 citas.
5. **Demostración:** insignia en el panel, correo de 60 minutos en MailHog.
6. **MLOps:** CronJob de reentrenamiento, firma del modelo, el modelo nuevo solo reemplaza al anterior si es mejor.
7. **Honestidad:** «Las métricas demuestran que el sistema funciona de principio a fin, no que prediga bien en una
   barbería real. Para eso está el reentrenamiento con citas reales.»
