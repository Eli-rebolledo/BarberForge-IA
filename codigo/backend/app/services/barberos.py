"""Barberos: alta, edición, activación, eliminación, foto y servicios que ofrecen."""
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.seguridad import hash_password
from app.core.tiempo import ahora_utc, hoy
from app.models import AusenciaBarbero, Cita, Disponibilidad, MensajeChat, PreguntaPendiente, Rol, Servicio, Usuario
from app.models.cita import ESTADOS_ACTIVOS
from app.schemas.barbero import BarberoEditarIn, BarberoIn
from app.services import imagenes
from app.services.errores import Conflicto, DatosInvalidos, NoEncontrado, SinPermiso
from app.services.usuarios import validar_clave, validar_correo


def listar(db: Session, incluir_inactivos: bool = False, servicio_id: int | None = None) -> list[Usuario]:
    q = select(Usuario).where(Usuario.role == Rol.BARBERO).order_by(Usuario.id)
    if not incluir_inactivos:
        q = q.where(Usuario.is_active)
    barberos = list(db.scalars(q))
    if servicio_id is not None:
        barberos = [b for b in barberos if servicio_id in b.service_ids]
    return barberos


def obtener(db: Session, barbero_id: int) -> Usuario:
    barbero = db.get(Usuario, barbero_id)
    if not barbero or barbero.role != Rol.BARBERO:
        raise NoEncontrado("Barbero no encontrado")
    return barbero


def validar_dias(dias: list[int]) -> list[int]:
    """Días de la semana (0 = lunes … 6 = domingo): al menos uno, sin repetir y en rango."""
    unicos = sorted(set(dias))
    if not unicos or unicos[0] < 0 or unicos[-1] > 6:
        raise DatosInvalidos("Elige al menos un día de la semana válido")
    return unicos


def actualizar_dias(db: Session, barbero_id: int, dias: list[int]) -> Usuario:
    """Cambia los días de trabajo y retira las franjas libres futuras de los días que ya no trabaja."""
    barbero = obtener(db, barbero_id)
    dias = validar_dias(dias)
    barbero.dias_csv = ",".join(str(d) for d in dias)
    ocupadas = {(c.appointment_date, c.start_time) for c in db.scalars(
        select(Cita).where(Cita.barber_id == barbero.id, Cita.status.in_(ESTADOS_ACTIVOS)))}
    for f in db.scalars(select(Disponibilidad).where(Disponibilidad.barber_id == barbero.id,
                                                     Disponibilidad.slot_date >= hoy())):
        if f.slot_date.weekday() not in dias and (f.slot_date, f.start_time) not in ocupadas:
            db.delete(f)
    db.commit()
    return barbero


def crear(db: Session, datos: BarberoIn) -> Usuario:
    validar_clave(datos.password)
    correo = validar_correo(datos.email)
    if not datos.full_name.strip():
        raise DatosInvalidos("Escribe el nombre del barbero")
    if datos.service_ids:
        servicios = list(db.scalars(select(Servicio).where(Servicio.id.in_(set(datos.service_ids)))))
    else:  # sin selección, ofrece todos los servicios activos
        servicios = list(db.scalars(select(Servicio).where(Servicio.is_active)))
    barbero = Usuario(email=correo, full_name=datos.full_name.strip(),
                      password_hash=hash_password(datos.password),
                      role=Rol.BARBERO, specialties=datos.specialties.strip()[:200], servicios=servicios,
                      dias_csv=",".join(str(d) for d in validar_dias(datos.work_days)))
    db.add(barbero)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflicto("Ese correo ya está registrado") from None
    return barbero


def alternar(db: Session, barbero_id: int) -> Usuario:
    barbero = obtener(db, barbero_id)
    barbero.is_active = not barbero.is_active
    db.commit()
    return barbero


def editar(db: Session, barbero_id: int, datos: BarberoEditarIn) -> Usuario:
    """Actualiza nombre, correo, especialidades, servicios y (si se envía) la contraseña."""
    barbero = obtener(db, barbero_id)
    nombre = datos.full_name.strip()
    if not nombre:
        raise DatosInvalidos("Escribe el nombre del barbero")
    barbero.full_name = nombre
    barbero.email = validar_correo(datos.email)
    barbero.specialties = datos.specialties.strip()[:200]
    if datos.password:
        validar_clave(datos.password)
        barbero.password_hash = hash_password(datos.password)
        barbero.reset_token_hash = barbero.reset_expires_at = None
    if datos.service_ids:
        barbero.servicios = list(db.scalars(select(Servicio).where(Servicio.id.in_(set(datos.service_ids))).order_by(Servicio.id)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflicto("Ese correo ya está registrado") from None
    db.refresh(barbero)
    return barbero


def eliminar(db: Session, barbero_id: int) -> None:
    """Borra al barbero, su calendario y sus citas canceladas.
    No se puede si tiene citas pendientes/confirmadas (hay que cancelarlas o desactivarlo para pasarlas a otro
    barbero) ni citas ya atendidas (son el historial de ingresos: en ese caso se desactiva)."""
    barbero = obtener(db, barbero_id)
    citas = list(db.scalars(select(Cita).where(Cita.barber_id == barbero.id)).unique())
    if any(c.status in ESTADOS_ACTIVOS for c in citas):
        raise Conflicto("Este barbero tiene citas pendientes o confirmadas. Desactívalo para pasarlas a otro "
                        "barbero, o cancélalas primero.")
    if any(c.status in ("completada", "inasistencia") for c in citas):
        raise Conflicto("Este barbero ya atendió citas y forman parte del historial de ingresos, así que no se "
                        "puede eliminar. Desactívalo para que deje de recibir citas.")
    db.execute(delete(MensajeChat).where(MensajeChat.user_id == barbero.id))
    db.execute(update(PreguntaPendiente).where(PreguntaPendiente.user_id == barbero.id).values(user_id=None))
    for c in citas:  # solo quedan canceladas
        db.delete(c)
    db.execute(update(Cita).where(Cita.created_by_id == barbero.id).values(created_by_id=None))
    for f in db.scalars(select(Disponibilidad).where(Disponibilidad.barber_id == barbero.id)):
        db.delete(f)
    db.execute(delete(AusenciaBarbero).where(AusenciaBarbero.barber_id == barbero.id))
    barbero.servicios = []
    db.flush()
    db.delete(barbero)
    db.commit()


# ---------- foto ----------

FOTO_MAX_BYTES = 1_500_000  # el navegador la reduce a ~480 px antes de subirla; esto es solo un tope


def _puede_editar_foto(actor: Usuario, barbero_id: int) -> None:
    if actor.role != Rol.ADMIN and not (actor.role == Rol.BARBERO and actor.id == barbero_id):
        raise SinPermiso("Solo el administrador o el mismo barbero pueden cambiar esta foto")


def guardar_foto(db: Session, actor: Usuario, barbero_id: int, data_url: str) -> Usuario:
    """Recibe la imagen como data URL (JPEG, PNG o WebP) y la guarda en la base de datos."""
    _puede_editar_foto(actor, barbero_id)
    barbero = obtener(db, barbero_id)
    datos, mime = imagenes.leer_data_url(data_url, FOTO_MAX_BYTES)
    barbero.photo, barbero.photo_mime, barbero.photo_updated_at = datos, mime, ahora_utc()
    db.commit()
    return barbero


def quitar_foto(db: Session, actor: Usuario, barbero_id: int) -> None:
    _puede_editar_foto(actor, barbero_id)
    barbero = obtener(db, barbero_id)
    barbero.photo = barbero.photo_mime = barbero.photo_updated_at = None
    db.commit()


def leer_foto(db: Session, barbero_id: int) -> tuple[bytes, str]:
    barbero = db.get(Usuario, barbero_id)
    if not barbero or barbero.role != Rol.BARBERO or not barbero.photo_mime or not barbero.photo:
        raise NoEncontrado("Este barbero no tiene foto")
    return barbero.photo, barbero.photo_mime
