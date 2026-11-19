# 011 · Predicción de inasistencias (ML)

**Responsable:** @MiyerACI · **Depende de:** 005 (agendamiento) y 006 (recordatorios)

## Descripción
Cuando se agenda una cita, un modelo de clasificación estima la probabilidad de que el cliente **no llegue**. Las
citas con riesgo alto reciben un aviso extra 60 minutos antes, además del recordatorio con confirmación de los 40
minutos que ya existía. El barbero y el administrador ven una insignia «Riesgo N %» en esas citas, y el panel
muestra qué modelo está en uso y qué tan bien funciona.

## Historias de usuario
- Como **administrador**, quiero saber qué citas próximas tienen más riesgo de que el cliente no llegue, para
  estar atento a esa franja.
- Como **barbería**, quiero que a los clientes con más riesgo les llegue un aviso adicional, porque la razón más
  común de inasistencia es olvidar la cita.
- Como **cliente**, no quiero ver una etiqueta de «riesgo» sobre mí; solo recibir el recordatorio.
- Como **equipo**, queremos que el modelo se reentrene solo cuando haya citas reales, y que nunca reemplace a uno
  mejor.

## Regla de decisión
| Riesgo estimado | Qué se envía |
|---|---|
| ≥ `ML_UMBRAL_RIESGO` (0,20 por defecto) | Aviso 60 min antes (sin confirmación) **y** recordatorio con confirmación 40 min antes |
| Menor, o no hay modelo | Solo el recordatorio de 40 min (igual que antes de esta feature) |

- El aviso de 60 minutos se manda a citas activas (pendientes o confirmadas) que tengan correo. Si la cita se agendó
  cuando ya faltaban menos de 40 minutos, no se envía.
- Las notificaciones push o por WhatsApp quedan fuera de esta feature: todo es por correo, como en la 006.

## Criterios de aceptación
- [x] Al agendar se calcula y guarda `appointments.no_show_risk`; si el modelo falla, la cita se crea igual (sin riesgo).
- [x] Solo el barbero y el administrador ven el riesgo (`riesgo`, `riesgo_alto` en `GET /api/appointments`); el cliente recibe `null`.
- [x] El worker envía el aviso de 60 minutos solo a citas de riesgo alto, una sola vez (`early_reminder_sent_at`).
- [x] Las citas creadas antes de la feature se evalúan en el ciclo de recordatorios.
- [x] `GET /api/admin/ml` (solo administrador): modelo, origen (sintético o real), AUC, recall, umbral y citas de riesgo alto.
- [x] Panel: insignia «Riesgo N %» en `/citas` y en «Próximas citas», y tarjeta «Predicción de inasistencias».
- [x] Generador de datos sintéticos reproducible (semilla fija) con los supuestos documentados en `app/ml/supuestos.md`.
- [x] Se comparan regresión logística y árbol de decisión con división por fecha; gana el de mayor AUC.
- [x] Experimentos registrados en MLflow cuando está instalado (`requirements-ml.txt`).
- [x] `python -m app.tareas reentrenar` entrena con citas reales cerradas y solo activa el modelo nuevo si su AUC es igual o mejor; CronJob semanal en Kubernetes.
- [x] Los modelos guardados en la base van firmados (HMAC); uno con firma alterada no se carga.
- [x] `ML_ACTIVO=false` apaga la predicción sin tocar el código.
- [ ] Evaluar el modelo con citas reales de una barbería (pendiente: no hay datos todavía).

## Datos sintéticos y limitaciones
**No hay datos reales todavía.** El modelo inicial se entrena con 5.000 citas inventadas por
`app/ml/generador.py`, con reglas tomadas de estudios sobre inasistencia a citas médicas (el sector donde más se ha
medido el problema) y de supuestos del equipo. Todo está explicado en `codigo/backend/app/ml/supuestos.md`.

Consecuencia: el modelo aprende las reglas con las que se generaron los datos. Sus métricas (AUC 0,71) demuestran
que **el sistema funciona de principio a fin**, no que prediga bien en una barbería real. El reentrenamiento con
citas reales existe justamente para reemplazarlo cuando haya datos. Mientras tanto el panel lo dice con una etiqueta
«Entrenado con datos sintéticos».

## Fuera de alcance
- Localidad y clima como variables: la app no pide el barrio del cliente ni consulta el clima. Se pueden agregar
  cuando se reentrene con datos reales.
- Género, edad u otros datos personales: no se usan para decidir.
