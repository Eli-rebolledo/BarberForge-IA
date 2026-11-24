# Supuestos del generador de datos sintéticos (feature 011)

> **Importante.** BarberForge todavía no tiene citas reales suficientes para entrenar un modelo. Las 5.000 citas
> con las que se entrena el modelo inicial son **inventadas** por `generador.py`, siguiendo las reglas de este
> documento. El modelo aprende esas reglas: sus métricas demuestran que **el sistema funciona de principio a fin**
> (generar → entrenar → predecir → decidir el recordatorio → reentrenar), **no** que prediga bien en una barbería
> real. Para eso está `python -m app.tareas reentrenar`, que reemplaza el modelo cuando haya citas reales.

## De dónde salen las reglas

Casi toda la investigación sobre inasistencias es del sector salud (citas médicas), que es donde más se ha
medido. Se usa como referencia porque el problema es el mismo: una persona agenda y no llega sin avisar.

| Regla | Fuente o razón |
|---|---|
| Tasa general de inasistencia ≈ 18 % | En salud se reportan tasas de 10 % a 50 % según el entorno (Mohammadi et al., *Predictive Modeling for Appointment No-show in Community Health Centers*). Para una barbería se supone un valor bajo dentro de ese rango. |
| Más anticipación → más inasistencia | En 15 clínicas con más de un millón de citas, la anticipación con que se agenda fue el predictor más importante (Annals of Family Medicine, 2025, vol. 23 n.º 4). |
| Quien ha faltado antes, falta más | Los modelos de esos estudios usan el historial de citas cumplidas e inasistencias de cada persona como variable principal (ídem). Aquí cada cliente tiene una «propensión a faltar» oculta. |
| Olvidar la cita es la razón más común | Estudio sobre inasistencias en centros médicos (Journal of Medical Economics, 2017). Justifica el aviso extra de 60 minutos. |
| Invitados (sin cuenta) faltan un poco más y no tienen historial | Suposición del equipo: la app no puede saber si alguien sin cuenta ya faltó antes. |
| Primera hora de la mañana y la noche faltan más; el sábado menos | Suposición del equipo (el sábado es el día de más demanda en barberías). |
| Citas más caras (combos, varios servicios) se cumplen un poco más | Suposición del equipo: quien pide más servicios suele estar más comprometido con la cita. |

## Parámetros (en `generador.py`)

| Parámetro | Valor |
|---|---|
| Semilla | 2026 (mismas citas cada vez) |
| Citas / clientes | 5.000 citas de 600 clientes registrados + invitados (22 %) |
| Periodo | 300 días desde el 5 de enero de 2026 |
| Propensión de cada cliente | Beta(1,3; 7,5), media ≈ 15 % |
| Efecto de la anticipación | +0,55 por cada unidad de log(1 + días), en escala logit |
| Ruido | Normal(0; 0,25) en escala logit |
| Catálogo | Los 4 servicios de la migración 002, con sus precios |

## Qué ve el modelo (y qué no)

Solo lo que la app sabe **al agendar** (`caracteristicas.py`): día, franja y hora, anticipación, si es invitado,
citas y faltas previas del cliente, tasa de faltas suavizada, precio y número de servicios.

**No** usa «confirmó el recordatorio» (todavía no existe cuando se decide el aviso de 60 minutos), ni género, edad,
barrio o datos personales. La duración del servicio se dejó por fuera porque va casi pegada al precio y, con las dos,
los coeficientes de la regresión se vuelven difíciles de interpretar.

## Resultado del entrenamiento (semilla 2026)

División por fecha: entrena con las 4.000 citas más antiguas y evalúa con las 1.000 más recientes.

| Modelo | AUC | Recall (umbral 0,20) | Precisión | Citas con aviso extra |
|---|---|---|---|---|
| **Regresión logística (ganador)** | **0,71** | **0,59** | 0,32 | 35 % |
| XGBoost (solo experimento, profundidad 2) | 0,71 (0,707) | 0,48 | 0,34 | 27 % |
| Random Forest (200 árboles, profundidad 6) | 0,68 | 0,49 | 0,32 | 29 % |
| Árbol de decisión (profundidad 5) | 0,58 | 0,39 | 0,27 | 27 % |

**Por qué gana la regresión logística.** Con los mismos datos y la misma división, los modelos de bosques y boosting
no la superan: los datos sintéticos se generaron con una relación lineal (en escala logit) entre las variables y la
inasistencia, y eso es justo lo que una regresión logística aprende mejor. Además se explica variable por variable.
Con citas reales la relación puede no ser lineal: por eso el reentrenamiento vuelve a comparar logística, árbol y
Random Forest. XGBoost se probó en `app/ml/comparar_modelos.py` y no va en la imagen (más peso y no ganó).

**Por qué el umbral es 0,20 y no 0,30:** un correo extra no cuesta casi nada; una cita perdida, sí. Con 0,30 el
modelo solo detectaba 1 de cada 4 inasistencias; con 0,20 detecta unas 6 de cada 10, a cambio de mandar el aviso
extra a 1 de cada 3 citas. Se cambia con la variable `ML_UMBRAL_RIESGO`.

| Umbral | Inasistencias detectadas (recall) | Citas con aviso extra |
|---|---|---|
| 0,15 | 83 % | 61 % |
| 0,18 | 71 % | 44 % |
| **0,20** | **59 %** | **35 %** |
| 0,25 | 40 % | 20 % |
| 0,30 | 26 % | 11 % |

Variables con más peso en la regresión logística: faltas previas (+), sábado (−), anticipación (+),
citas previas cumplidas (−).

## Cómo reemplazar los datos sintéticos por reales

1. Cada vez que el barbero o el administrador marca una cita como **Completada** o **No asistió**, esa cita queda
   lista para entrenar.
2. `python -m app.tareas reentrenar` (en Kubernetes, un CronJob cada lunes a las 3 a. m.) entrena con las citas
   reales cuando hay al menos 200 cerradas, con 20 o más inasistencias y 20 o más cumplidas.
3. El modelo nuevo se guarda firmado en la tabla `ml_models` y **solo se activa si su AUC sobre las citas reales
   más recientes es igual o mejor que el del modelo en uso** (el sintético se evalúa con esas mismas citas reales).
