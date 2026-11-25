# 004 · Tareas

## Backend
- [x] Modelo `Disponibilidad` con restricción única
- [x] Generación sin domingos ni duplicados
- [x] Consulta de franjas libres futuras de barberos activos
- [x] Agenda de 7 días al arrancar
- [x] Borrado de franjas antiguas
- [x] Pruebas (`tests/test_disponibilidad.py`): franjas libres futuras, sin domingos ni duplicados, validación del rango

## Frontend
- [x] `/admin/disponibilidad`: formulario de generación
- [x] Paso de horarios en `/agendar`, agrupado por día

## Iteración 2 (2026-11-21): festivos y ausencias
- [x] Migración 009: tablas `closed_days` y `barber_absences`
- [x] `dias_bloqueados()` en el servicio de disponibilidad: lo usan la generación de franjas y la consulta de libres
- [x] Servicio `cierres`: festivos de Colombia, cerrar un día, ausencias con reasignación de citas, reabrir al borrar
- [x] Correos al cliente por cita cancelada (festivo) o cambiada de barbero (ausencia)
- [x] Página `/admin/festivos` y días tachados en el calendario del administrador
- [x] Pruebas (`tests/test_cierres.py`): festivos 2026, cierre con cancelación, reapertura, carga sin duplicados, ausencia con y sin reemplazo, el chat no ofrece festivos
