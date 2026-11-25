"""Festivos de la barbería (RF09) y ausencias de los barberos (RF17).

Un festivo cierra la barbería ese día: se quitan las franjas libres y las citas activas se cancelan con aviso por
correo. Una ausencia bloquea solo al barbero: sus citas pasan a otro barbero libre (o se cancelan si no hay nadie).
Mientras exista el bloqueo, la agenda automática no crea franjas y ni la web ni el chat ni la voz ofrecen esas horas.
"""
from datetime import date, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import db as bd
from app.config import get_settings
from app.core.tiempo import hora12, hoy
from app.models import AusenciaBarbero, Cita, DiaCerrado, Disponibilidad, Rol, Usuario
from app.models.cita import ESTADOS_ACTIVOS
from app.services import barberia, correo
from app.services import barberos as barberos_srv
from app.services import citas as citas_srv
from app.services.disponibilidad import generar_franjas
from app.services.errores import Conflicto, DatosInvalidos, NoEncontrado

DIAS_DE_AGENDA = 7          # igual que la agenda automática del arranque
MAX_DIAS_AUSENCIA = 180


# ---------- festivos de Colombia (Ley 51 de 1983, «Ley Emiliani») ----------

def _pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo gregoriano anónimo)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    mes = (h + m - 7 * n + 114) // 31
    dia = (h + m - 7 * n + 114) % 31 + 1
    return date(anio, mes, dia)


def _lunes(d: date) -> date:
    """Traslada el festivo al lunes siguiente (si ya es lunes, se queda)."""
    return d + timedelta(days=(7 - d.weekday()) % 7)


def festivos_colombia(anio: int) -> list[tuple[date, str]]:
    """Los 18 festivos nacionales de Colombia de un año, ordenados por fecha."""
    p = _pascua(anio)
    fijos = [(date(anio, 1, 1), "Año Nuevo"), (date(anio, 5, 1), "Día del Trabajo"),
             (date(anio, 7, 20), "Día de la Independencia"), (date(anio, 8, 7), "Batalla de Boyacá"),
             (date(anio, 12, 8), "Inmaculada Concepción"), (date(anio, 12, 25), "Navidad")]
    trasladables = [(date(anio, 1, 6), "Reyes Magos"), (date(anio, 3, 19), "San José"),
                    (date(anio, 6, 29), "San Pedro y San Pablo"), (date(anio, 8, 15), "Asunción de la Virgen"),
                    (date(anio, 10, 12), "Día de la Raza"), (date(anio, 11, 1), "Todos los Santos"),
                    (date(anio, 11, 11), "Independencia de Cartagena")]
    pascua = [(p - timedelta(days=3), "Jueves Santo"), (p - timedelta(days=2), "Viernes Santo"),
              (_lunes(p + timedelta(days=39)), "Ascensión del Señor"),
              (_lunes(p + timedelta(days=60)), "Corpus Christi"),
              (_lunes(p + timedelta(days=68)), "Sagrado Corazón")]
    return sorted(fijos + [(_lunes(d), m) for d, m in trasladables] + pascua)


# ---------- citas afectadas (se muestran antes de confirmar) ----------

def citas_afectadas(db: Session, desde: date, hasta: date | None = None, barbero_id: int | None = None) -> list[Cita]:
    q = select(Cita).where(Cita.status.in_(ESTADOS_ACTIVOS),
                           Cita.appointment_date.between(desde, hasta or desde)).order_by(Cita.appointment_date,
                                                                                         Cita.start_time)
    if barbero_id is not None:
        q = q.where(Cita.barber_id == barbero_id)
    return list(db.scalars(q).unique())


# ---------- festivos ----------

def listar_festivos(db: Session, todos: bool = False) -> list[DiaCerrado]:
    q = select(DiaCerrado).order_by(DiaCerrado.day)
    if not todos:
        q = q.where(DiaCerrado.day >= hoy())
    return list(db.scalars(q))


def _cerrar_dia(db: Session, dia: date) -> list[int]:
    """Quita las franjas libres de todos los barberos y cancela las citas activas de ese día.
    Devuelve los id de las citas canceladas (para avisar a los clientes)."""
    db.execute(delete(Disponibilidad).where(Disponibilidad.slot_date == dia))
    canceladas = []
    for c in db.scalars(select(Cita).where(Cita.appointment_date == dia, Cita.status.in_(ESTADOS_ACTIVOS))).unique():
        c.status, c.token_hash = "cancelada_admin", None
        canceladas.append(c.id)
    return canceladas


MAX_DIAS_CIERRE = 31


def crear_festivo(db: Session, dia: date, motivo: str, hasta: date | None = None) -> tuple[list[DiaCerrado], list[int]]:
    """Cierra un día o un rango de días (vacaciones colectivas). Devuelve (días creados, citas canceladas)."""
    hasta = hasta or dia
    if dia < hoy():
        raise DatosInvalidos("El festivo debe ser hoy o una fecha futura")
    if hasta < dia:
        raise DatosInvalidos("La fecha final debe ser igual o posterior a la inicial")
    if (hasta - dia).days + 1 > MAX_DIAS_CIERRE:
        raise DatosInvalidos(f"Se pueden cerrar máximo {MAX_DIAS_CIERRE} días seguidos")
    motivo = (motivo or "").strip()[:80] or "Festivo"
    existentes = {d.day for d in db.scalars(select(DiaCerrado).where(DiaCerrado.day.between(dia, hasta)))}
    if dia == hasta and dia in existentes:
        raise Conflicto("Ese día ya está marcado como festivo")
    creados, canceladas = [], []
    d = dia
    while d <= hasta:
        if d not in existentes:
            creados.append(DiaCerrado(day=d, motivo=motivo))
            canceladas += _cerrar_dia(db, d)
        d += timedelta(days=1)
    db.add_all(creados)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflicto("Alguno de esos días ya está marcado como festivo") from None
    return creados, canceladas


def cargar_colombia(db: Session, anio: int) -> tuple[int, list[int]]:
    """Agrega los festivos nacionales que faltan desde hoy hasta fin de año. Devuelve (creados, citas canceladas)."""
    if not 2000 <= anio <= 2100:
        raise DatosInvalidos("Año inválido")
    existentes = {d.day for d in db.scalars(select(DiaCerrado))}
    creados, canceladas = 0, []
    for dia, motivo in festivos_colombia(anio):
        if dia >= hoy() and dia not in existentes:
            db.add(DiaCerrado(day=dia, motivo=motivo))
            canceladas += _cerrar_dia(db, dia)
            creados += 1
    db.commit()
    return creados, canceladas


def _reabrir(db: Session, barberos: list[Usuario], desde: date, hasta: date) -> None:
    """Vuelve a crear la agenda habitual (9 a. m. – 5 p. m.) de los días que quedan dentro de la agenda automática.
    generar_franjas ya salta los días que sigan bloqueados por otro festivo o ausencia."""
    desde, hasta = max(desde, hoy()), min(hasta, hoy() + timedelta(days=DIAS_DE_AGENDA))
    if desde > hasta:
        return
    for b in barberos:
        if b.is_active:
            generar_franjas(db, b.id, desde, hasta, time(9), time(17), 30, set(b.work_days))


def borrar_festivo(db: Session, festivo_id: int) -> None:
    festivo = db.get(DiaCerrado, festivo_id)
    if not festivo:
        raise NoEncontrado("Festivo no encontrado")
    dia = festivo.day
    db.delete(festivo)
    db.commit()
    _reabrir(db, list(db.scalars(select(Usuario).where(Usuario.role == Rol.BARBERO))), dia, dia)


# ---------- ausencias de barberos ----------

def listar_ausencias(db: Session, barbero_id: int | None = None) -> list[AusenciaBarbero]:
    q = select(AusenciaBarbero).where(AusenciaBarbero.date_to >= hoy()).order_by(AusenciaBarbero.date_from)
    if barbero_id is not None:
        q = q.where(AusenciaBarbero.barber_id == barbero_id)
    return list(db.scalars(q))


def crear_ausencia(db: Session, barbero_id: int, desde: date, hasta: date,
                   motivo: str) -> tuple[AusenciaBarbero, list[dict]]:
    barbero = barberos_srv.obtener(db, barbero_id)
    if hasta < desde:
        raise DatosInvalidos("La fecha final debe ser igual o posterior a la inicial")
    if hasta < hoy():
        raise DatosInvalidos("La ausencia ya pasó")
    if (hasta - desde).days + 1 > MAX_DIAS_AUSENCIA:
        raise DatosInvalidos(f"Una ausencia puede durar máximo {MAX_DIAS_AUSENCIA} días")
    ausencia = AusenciaBarbero(barber_id=barbero.id, date_from=desde, date_to=hasta,
                               motivo=(motivo or "").strip()[:80] or "Ausencia")
    db.add(ausencia)
    db.execute(delete(Disponibilidad).where(Disponibilidad.barber_id == barbero.id,
                                            Disponibilidad.slot_date.between(desde, hasta)))
    db.commit()
    # Las citas de esos días pasan a otro barbero libre; si nadie puede, se cancelan.
    resumen = citas_srv.reasignar_de_barbero(db, barbero.id, desde, hasta)
    return ausencia, resumen


def borrar_ausencia(db: Session, ausencia_id: int) -> None:
    ausencia = db.get(AusenciaBarbero, ausencia_id)
    if not ausencia:
        raise NoEncontrado("Ausencia no encontrada")
    barbero, desde, hasta = db.get(Usuario, ausencia.barber_id), ausencia.date_from, ausencia.date_to
    db.delete(ausencia)
    db.commit()
    if barbero:
        _reabrir(db, [barbero], desde, hasta)


# ---------- avisos por correo (en segundo plano) ----------

def correos_por_festivo(cita_ids: list[int]) -> None:
    url = get_settings().public_url.rstrip("/")
    with bd.SessionLocal() as db:
        for cita_id in cita_ids:
            cita = db.get(Cita, cita_id)
            destino = cita and (cita.cliente.email if cita.cliente else cita.guest_email)
            if not destino:
                continue
            festivo = db.scalar(select(DiaCerrado).where(DiaCerrado.day == cita.appointment_date))
            motivo = f" ({festivo.motivo})" if festivo else ""
            correo.enviar(destino, f"Tu cita en {barberia.nombre(db)} fue cancelada",
                          f"La barbería no atenderá el {cita.appointment_date}{motivo}, así que tu cita de las "
                          f"{hora12(cita.start_time)} fue cancelada.\nAgenda un nuevo horario aquí: {url}/agendar\n"
                          "Disculpa los inconvenientes.")
