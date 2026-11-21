# 004 · Disponibilidad

## Descripción
Las franjas en que cada barbero atiende. El administrador las genera por rango de fechas, horas y duración; al arrancar, la API asegura una semana de agenda para cada barbero activo. Una franja está libre si es futura, su barbero está activo y no tiene una cita activa.

## Historias de usuario
- Como **cliente**, quiero ver los horarios libres de un barbero agrupados por día.
- Como **administrador**, quiero generar la agenda de un barbero para un rango de fechas con hora de inicio, fin y minutos por franja.
- Como **administrador**, quiero que la agenda de la próxima semana exista sin tener que generarla a mano.

## Criterios de aceptación
- [x] `GET /api/availability?barber_id=N` (público) devuelve hasta 80 franjas libres futuras, ordenadas, como `{date: AAAA-MM-DD, time: HH:MM}`.
- [x] Una franja con cita `pendiente` o `confirmada` no aparece; al cancelarse la cita vuelve a estar libre.
- [x] Las franjas de hoy anteriores a la hora local de la barbería no aparecen.
- [x] `POST /api/availability` (solo administrador) genera franjas de lunes a sábado; los domingos se omiten.
- [x] Generar dos veces el mismo rango no duplica franjas (restricción única por barbero, fecha y hora).
- [x] Se rechaza (400) una duración menor a 10 min, `date_to` anterior a `date_from` o `end` no posterior a `start`; un barbero inexistente responde 404.
- [x] Al arrancar se generan franjas de 30 min de 9:00 a 17:00 para los próximos 7 días de cada barbero activo.
- [x] Las franjas de antes de ayer se borran en el ciclo de recordatorios.
- [x] `/admin/disponibilidad` ofrece el formulario (por defecto hoy, 09:00–17:00, 30 min) con los barberos activos.
- [x] RF09: `POST /api/closed-days` (administrador) marca un día sin atención, o varios seguidos con `date_to` (máximo 31): se quitan las franjas libres de todos los barberos y las citas activas de ese día se cancelan con aviso por correo. `GET /api/closed-days` es público.
- [x] RF09: «Cargar festivos de Colombia» (`POST /api/closed-days/colombia`) agrega los 18 festivos nacionales (Ley Emiliani y fechas de Pascua) que faltan hasta fin de año, sin duplicar.
- [x] RF17: `POST /api/barbers/{id}/absences` registra una ausencia (máximo 180 días): sus citas de esos días pasan a otro barbero libre que haga el mismo servicio, o se cancelan si nadie puede; el cliente recibe un correo.
- [x] Mientras exista un festivo o una ausencia, ni la agenda automática ni `POST /api/availability` crean franjas esos días, y ni la web, ni el chat, ni la voz ofrecen esas horas.
- [x] Al quitar un festivo o una ausencia, los días que caen dentro de la agenda automática (7 días) se vuelven a abrir con el horario habitual.
- [x] `/admin/festivos` gestiona ambos; el calendario de `/admin/disponibilidad` muestra tachados los días bloqueados con su motivo.
