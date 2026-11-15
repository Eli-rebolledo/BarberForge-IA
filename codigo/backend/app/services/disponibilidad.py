"""Franjas de atención de los barberos y consulta de franjas libres."""
from datetime import date, datetime, time, timedelta
from typing import NamedTuple

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.tiempo import ahora_local, hora12, hoy
from app.models import Cita, Disponibilidad, Rol, Usuario
from app.models.cita import ESTADOS_ACTIVOS
from app.schemas.disponibilidad import GenerarDisponibilidadIn
from app.services import barberos as barberos_srv
from app.services.errores import DatosInvalidos

DOMINGO = 6
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def generar_franjas(db: Session, barbero_id: int, desde: date, hasta: date,
                    inicio: time, fin: time, minutos: int, dias: set[int] | None = None) -> int:
    """Crea las franjas de los días de trabajo (por defecto lunes a sábado) sin duplicar. Devuelve cuántas creó."""
    dias = dias if dias is not None else set(range(DOMINGO))
    existentes = {(d.slot_date, d.start_time) for d in db.scalars(
        select(Disponibilidad).where(Disponibilidad.barber_id == barbero_id,
                                     Disponibilidad.slot_date.between(desde, hasta)))}
    nuevas = 0
    dia = desde
    while dia <= hasta:
        if dia.weekday() in dias:
            t, limite = datetime.combine(dia, inicio), datetime.combine(dia, fin)
            while t < limite:
                if (dia, t.time()) not in existentes:
                    db.add(Disponibilidad(barber_id=barbero_id, slot_date=dia, start_time=t.time()))
                    nuevas += 1
                t += timedelta(minutes=minutos)
        dia += timedelta(days=1)
    db.commit()
    return nuevas


def generar(db: Session, datos: GenerarDisponibilidadIn) -> int:
    if datos.minutes < 10 or datos.end <= datos.start:
        raise DatosInvalidos("Horas o duración inválidas")
    barbero = barberos_srv.obtener(db, datos.barber_id)
    if datos.dates:  # fechas concretas elegidas en el calendario
        nuevas = 0
        for d in sorted(set(datos.dates)):
            if d < hoy():
                continue
            nuevas += generar_franjas(db, barbero.id, d, d, datos.start, datos.end, datos.minutes, set(range(7)))
        return nuevas
    if datos.date_to < datos.date_from:
        raise DatosInvalidos("Rango de fechas inválido")
    dias = set(barberos_srv.validar_dias(datos.days)) if datos.days else set(barbero.work_days)
    return generar_franjas(db, barbero.id, datos.date_from, datos.date_to, datos.start, datos.end, datos.minutes, dias)


def _m(t: time) -> int:
    return t.hour * 60 + t.minute


class FranjaLibre(NamedTuple):
    slot_date: date
    start_time: time


def _hora(minutos: int) -> time:
    return time(minutos // 60, minutos % 60)


def franjas_libres(db: Session, barbero_id: int, limite: int = 80, fecha: date | None = None,
                   hora: time | None = None, minutos: int = 30) -> list[FranjaLibre]:
    """Horas futuras de un barbero activo donde cabe una cita de `minutos` sin cruzarse con otra.

    Las horas candidatas son las de la jornada (cada 30 min, por ejemplo) y además el momento en que
    termina cada cita activa: si un servicio dura menos que la franja, el tiempo sobrante se puede agendar.
    Si una cita de hoy se cerró antes de su hora de fin, el tiempo restante también queda disponible."""
    ahora = ahora_local()
    barbero = db.get(Usuario, barbero_id)
    if not barbero or not barbero.is_active or barbero.role != Rol.BARBERO:
        return []
    minutos = max(minutos, 1)
    hoy_ = ahora.date()

    qd = select(Disponibilidad).where(Disponibilidad.barber_id == barbero_id, Disponibilidad.slot_date >= hoy_)
    qc = select(Cita.appointment_date, Cita.start_time, Cita.duration_minutes, Cita.status).where(
        Cita.barber_id == barbero_id, Cita.status.in_((*ESTADOS_ACTIVOS, "completada")),
        Cita.appointment_date >= hoy_)
    if fecha is not None:
        qd, qc = qd.where(Disponibilidad.slot_date == fecha), qc.where(Cita.appointment_date == fecha)

    inicios: dict[date, set[int]] = {}
    for f in db.scalars(qd):
        inicios.setdefault(f.slot_date, set()).add(_m(f.start_time))

    ocupado: dict[date, list[tuple[int, int]]] = {}
    extremos: dict[date, set[int]] = {}
    liberado: set[date] = set()
    ahora_min = ahora.hour * 60 + ahora.minute
    for d, t, dur, estado in db.execute(qc):
        ini, fin = _m(t), _m(t) + max(dur or 30, 1)
        if estado in ESTADOS_ACTIVOS:
            ocupado.setdefault(d, []).append((ini, fin))
            extremos.setdefault(d, set()).add(fin)
        elif d == hoy_ and fin > ahora_min:  # cita completada antes de tiempo: lo que sobra queda libre
            liberado.add(d)

    libres: list[FranjaLibre] = []
    for dia in sorted(inicios):
        starts = sorted(inicios[dia])
        paso = min((b - a for a, b in zip(starts, starts[1:], strict=False)), default=30) or 30
        ventanas: list[list[int]] = []  # tramos continuos de atención
        for st in starts:
            if ventanas and st <= ventanas[-1][1]:
                ventanas[-1][1] = max(ventanas[-1][1], st + paso)
            else:
                ventanas.append([st, st + paso])
        candidatas = set(starts) | extremos.get(dia, set())
        if dia in liberado:
            candidatas.add((ahora_min // 5 + 1) * 5)  # el próximo múltiplo de 5 min
        for c in sorted(candidatas):
            if c >= 24 * 60 or (hora is not None and c != _m(hora)):
                continue
            if datetime.combine(dia, _hora(c)) <= ahora:
                continue
            if not any(v0 <= c and c + minutos <= v1 for v0, v1 in ventanas):
                continue  # no cabe dentro de la jornada
            if any(a < c + minutos and c < b for a, b in ocupado.get(dia, [])):
                continue
            libres.append(FranjaLibre(dia, _hora(c)))
            if len(libres) >= limite:
                return libres
    return libres


def esta_libre(db: Session, barbero_id: int, fecha: date, hora: time, minutos: int = 30) -> bool:
    return bool(franjas_libres(db, barbero_id, limite=1, fecha=fecha, hora=hora, minutos=minutos))


def calendario(db: Session, barbero_id: int, mes: str) -> list[dict]:
    """Franjas y citas activas por día de un mes (AAAA-MM)."""
    try:
        anio, m = (int(x) for x in mes.split("-"))
        desde = date(anio, m, 1)
    except ValueError:
        raise DatosInvalidos("Mes inválido, usa AAAA-MM") from None
    hasta = date(anio + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
    dias: dict[date, list[int]] = {}
    for f in db.scalars(select(Disponibilidad).where(Disponibilidad.barber_id == barbero_id,
                                                      Disponibilidad.slot_date.between(desde, hasta))):
        dias.setdefault(f.slot_date, [0, 0])[0] += 1
    for c in db.scalars(select(Cita).where(Cita.barber_id == barbero_id, Cita.status.in_(ESTADOS_ACTIVOS),
                                           Cita.appointment_date.between(desde, hasta))).unique():
        dias.setdefault(c.appointment_date, [0, 0])[1] += 1
    return [{"date": str(d), "total": v[0], "ocupadas": v[1]} for d, v in sorted(dias.items())]


def cerrar_dias(db: Session, barbero_id: int, fechas: list[date]) -> int:
    """Quita las franjas libres de esos días (las que ya tienen cita se conservan)."""
    ocupadas = {(c.appointment_date, c.start_time) for c in db.scalars(
        select(Cita).where(Cita.barber_id == barbero_id, Cita.status.in_(ESTADOS_ACTIVOS),
                           Cita.appointment_date.in_(fechas))).unique()}
    n = 0
    for f in db.scalars(select(Disponibilidad).where(Disponibilidad.barber_id == barbero_id,
                                                      Disponibilidad.slot_date.in_(fechas))):
        if (f.slot_date, f.start_time) not in ocupadas:
            db.delete(f)
            n += 1
    db.commit()
    return n


def etiqueta(franja: Disponibilidad) -> str:
    d = franja.slot_date
    return f"{DIAS[d.weekday()]} {d:%d/%m} · {hora12(franja.start_time)}"


def borrar_antiguas(db: Session) -> None:
    db.execute(delete(Disponibilidad).where(Disponibilidad.slot_date < hoy() - timedelta(days=1)))
    db.commit()
