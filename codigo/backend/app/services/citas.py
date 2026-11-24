"""Agendamiento, consulta, cancelación y cierre de citas; recordatorios y confirmación por correo."""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import db as bd
from app.config import get_settings
from app.core import metricas
from app.core.seguridad import hash_token, nuevo_token_un_uso
from app.core.tiempo import ahora_local, ahora_utc, hora12
from app.models import Cita, Rol, Servicio, Usuario
from app.models.cita import ESTADOS_ACTIVOS
from app.schemas.cita import CitaIn, CitaOut
from app.services import barberia, correo, prediccion
from app.services import disponibilidad as disp
from app.services.errores import Conflicto, DatosInvalidos, NoEncontrado

MINUTOS_RECORDATORIO = 40   # el correo sale 40 min antes de la cita
MINUTOS_AVISO_EXTRA = 60    # feature 011: aviso adicional solo para citas con riesgo alto de inasistencia
MINUTOS_PARA_CONFIRMAR = 15  # si no confirma en 15 min, se cancela y la franja queda libre
ESTADOS_CIERRE = ("completada", "inasistencia")


# ---------- agendar ----------

def agendar(db: Session, actor: Usuario, datos: CitaIn) -> Cita:
    """Un cliente agenda para sí mismo (queda pendiente de confirmar). Un barbero o el administrador pueden
    agendar para un cliente registrado o sin cuenta (cita en el local): queda confirmada."""
    ids = list(dict.fromkeys(datos.service_ids or ([datos.service_id] if datos.service_id else [])))
    if not ids:
        raise DatosInvalidos("Elige al menos un servicio")
    servicios = list(db.scalars(select(Servicio).where(Servicio.id.in_(ids), Servicio.is_active).order_by(Servicio.id)))
    if len(servicios) != len(ids):
        raise NoEncontrado("Servicio no disponible")
    barbero_id = actor.id if actor.role == Rol.BARBERO else datos.barber_id
    barbero = db.get(Usuario, barbero_id) if barbero_id else None
    if (not barbero or barbero.role != Rol.BARBERO or not barbero.is_active
            or not {s.id for s in servicios} <= set(barbero.service_ids)):
        raise DatosInvalidos("Ese barbero no ofrece los servicios elegidos")

    campos: dict = {}
    if actor.role == Rol.CLIENTE:
        campos, estado = {"client_id": actor.id}, "pendiente"
    else:
        estado = "confirmada"
        if datos.client_id:
            cliente = db.get(Usuario, datos.client_id)
            if not cliente or cliente.role != Rol.CLIENTE or not cliente.is_active:
                raise NoEncontrado("Cliente no encontrado")
            campos = {"client_id": cliente.id}
        elif datos.guest_name and datos.guest_name.strip():
            campos = {"guest_name": datos.guest_name.strip()[:80],
                      "guest_phone": (datos.guest_phone or "").strip()[:30] or None,
                      "guest_email": (datos.guest_email or "").strip().lower()[:120] or None}
        else:
            raise DatosInvalidos("Indica el cliente: elige uno registrado o escribe su nombre")

    minutos = sum(s.duration_minutes for s in servicios)
    cita = None
    if disp.esta_libre(db, barbero.id, datos.date, datos.time, minutos):
        cita = Cita(barber_id=barbero.id, service_id=servicios[0].id, servicios=servicios,
                    appointment_date=datos.date, start_time=datos.time, status=estado,
                    price_cop=sum(s.price_cop for s in servicios), duration_minutes=minutos,
                    created_by_id=actor.id, **campos)
        try:  # el índice único parcial impide la doble reserva aunque dos personas lleguen a la vez (RN08)
            with db.begin_nested():
                db.add(cita)
            db.commit()
        except IntegrityError:
            db.rollback()
            cita = None
    if cita is None:
        alternativas = [{"date": str(f.slot_date), "time": f"{f.start_time:%H:%M}"}
                        for f in disp.franjas_libres(db, barbero.id, limite=3, minutos=minutos)]
        raise Conflicto("Esa franja ya no está disponible", alternatives=alternativas)
    metricas.citas_creadas.add(1, {"rol": str(actor.role), "servicios": len(servicios)})
    prediccion.actualizar_riesgo(db, cita)  # feature 011; si el modelo falla, la cita queda igual (sin riesgo)
    return cita


def correo_de_creacion(cita_id: int) -> None:
    """Correo automático de «cita registrada». Abre su propia sesión (se ejecuta en segundo plano)."""
    with bd.SessionLocal() as db:
        cita = db.get(Cita, cita_id)
        destino = cita and (cita.cliente.email if cita.cliente else cita.guest_email)
        if not destino:
            return
        nombres = " + ".join(s.name for s in cita.servicios)
        extra = ("Te enviaremos un recordatorio automático por correo antes de la hora."
                 if cita.status == "pendiente" else "Tu cita ya está confirmada.")
        correo.enviar(destino, f"Tu cita en {barberia.nombre(db)}",
                      f"Servicios: {nombres}\nBarbero: {cita.barbero.full_name}\n"
                      f"Fecha: {cita.appointment_date} a las {hora12(cita.start_time)}\n"
                      f"Total: ${cita.price_cop:,}".replace(",", ".") + f"\n\n{extra}")


def correo_de_cancelacion(cita_id: int) -> None:
    """Correo de «cita cancelada» al cliente: la canceló él, el barbero o el administrador, o se canceló sola porque no
    se confirmó a tiempo. Abre su propia sesión (segundo plano o worker)."""
    with bd.SessionLocal() as db:
        cita = db.get(Cita, cita_id)
        destino = cita and (cita.cliente.email if cita.cliente else cita.guest_email)
        if not destino or cita.status not in ("cancelada_cliente", "cancelada_admin", "cancelada_sin_confirmar"):
            return
        nombres = " + ".join(s.name for s in cita.servicios) or cita.servicio.name
        detalle = (f"tu cita de {nombres} con {cita.barbero.full_name} del {cita.appointment_date} "
                   f"a las {hora12(cita.start_time)}")
        if cita.status == "cancelada_sin_confirmar":
            texto = (f"Se canceló {detalle} porque no la confirmaste a tiempo. Te enviamos un recordatorio "
                     f"{MINUTOS_RECORDATORIO} minutos antes y el enlace para confirmar estuvo activo "
                     f"{MINUTOS_PARA_CONFIRMAR} minutos; como no se confirmó, el horario quedó libre para otro cliente.")
        else:
            texto = f"{'Cancelaste' if cita.status == 'cancelada_cliente' else 'La barbería canceló'} {detalle}."
        url = get_settings().public_url.rstrip("/")
        correo.enviar(destino, f"Tu cita en {barberia.nombre(db)} fue cancelada",
                      f"{texto}\nSi quieres otro horario, agenda aquí: {url}/agendar")


# ---------- consultar ----------

def _salida(c: Cita, ver_riesgo: bool = True) -> CitaOut:
    nombres = [s.name for s in c.servicios] or [c.servicio.name]
    riesgo = c.no_show_risk if ver_riesgo else None
    return CitaOut(id=c.id, date=c.appointment_date, time=f"{c.start_time:%H:%M}", status=c.status,
                   service=" + ".join(nombres), services=nombres, barber=c.barbero.full_name, barber_id=c.barber_id,
                   client=c.cliente.full_name if c.cliente else (c.guest_name or "Cliente"),
                   client_phone=c.guest_phone, walk_in=c.client_id is None,
                   price=c.price_cop or c.servicio.price_cop, duration=c.duration_minutes,
                   riesgo=riesgo, riesgo_alto=prediccion.es_alto(riesgo))


def listar_para(db: Session, usuario: Usuario, limite: int = 500) -> list[CitaOut]:
    """El cliente ve sus citas, el barbero su agenda y el administrador todas."""
    q = select(Cita).order_by(Cita.appointment_date.desc(), Cita.start_time).limit(limite)
    if usuario.role == Rol.CLIENTE:
        q = q.where(Cita.client_id == usuario.id)
    elif usuario.role == Rol.BARBERO:
        q = q.where(Cita.barber_id == usuario.id)
    return [_salida(c, ver_riesgo=usuario.role != Rol.CLIENTE) for c in db.scalars(q).unique()]


def _obtener(db: Session, cita_id: int) -> Cita:
    cita = db.get(Cita, cita_id)
    if not cita:
        raise NoEncontrado("Cita no encontrada")
    return cita


# ---------- cambiar estado ----------

def cancelar(db: Session, usuario: Usuario, cita_id: int) -> None:
    cita = _obtener(db, cita_id)
    if (usuario.role == Rol.CLIENTE and cita.client_id != usuario.id) or (
            usuario.role == Rol.BARBERO and cita.barber_id != usuario.id):
        raise NoEncontrado("Cita no encontrada")
    if cita.status not in ESTADOS_ACTIVOS:
        raise DatosInvalidos("La cita ya no está activa")
    cita.status = "cancelada_cliente" if usuario.role == Rol.CLIENTE else "cancelada_admin"
    cita.token_hash = None
    db.commit()
    metricas.citas_canceladas.add(1, {"estado": cita.status})


def cerrar(db: Session, usuario: Usuario, cita_id: int, estado: str) -> None:
    if estado not in ESTADOS_CIERRE:
        raise DatosInvalidos("Estado inválido")
    cita = _obtener(db, cita_id)
    if usuario.role == Rol.BARBERO and cita.barber_id != usuario.id:
        raise NoEncontrado("Cita no encontrada")
    if cita.status != "confirmada":
        raise DatosInvalidos("Solo se puede cerrar una cita confirmada")
    cita.status = estado
    db.commit()


# ---------- recordatorio y confirmación ----------

def enviar_recordatorio(db: Session, cita_id: int) -> bool:
    """Envía el correo con el enlace de confirmación de un solo uso. Solo para citas pendientes."""
    cita = db.get(Cita, cita_id)
    if not cita or cita.status != "pendiente":
        return False
    token, token_hash = nuevo_token_un_uso()
    cita.token_hash, cita.reminder_sent_at = token_hash, ahora_utc()
    db.commit()
    url = get_settings().public_url.rstrip("/")
    correo.enviar(cita.cliente.email, f"Confirma tu cita en {barberia.nombre(db)}",
                  f"Tu cita de {cita.servicio.name} es el {cita.appointment_date} a las {hora12(cita.start_time)}.\n"
                  f"Confirma en los próximos {MINUTOS_PARA_CONFIRMAR} minutos: {url}/api/confirm/{token}\n"
                  "Si no confirmas, la cita se cancelará y la franja quedará libre.")
    metricas.recordatorios.add(1, {"tipo": "40"})
    return True


def enviar_aviso_previo(db: Session, cita: Cita) -> bool:
    """Feature 011: aviso extra 60 min antes, solo para citas con riesgo alto. No pide confirmar: la
    confirmación sigue llegando a los 40 min. Se marca como enviado aunque el correo falle (no se reintenta)."""
    destino = cita.cliente.email if cita.cliente else cita.guest_email
    cita.early_reminder_sent_at = ahora_utc()
    db.commit()
    if not destino:
        return False
    siguiente = (f"En unos minutos te llegará otro correo para confirmarla: confirma en los {MINUTOS_PARA_CONFIRMAR} "
                 "minutos siguientes o la franja quedará libre para otro cliente."
                 if cita.status == "pendiente" else "Tu cita ya está confirmada. ¡Te esperamos!")
    correo.enviar(destino, f"Tu cita en {barberia.nombre(db)} es en una hora",
                  f"Te recordamos tu cita de {' + '.join(s.name for s in cita.servicios) or cita.servicio.name} "
                  f"hoy a las {hora12(cita.start_time)} con {cita.barbero.full_name}.\n{siguiente}\n\n"
                  "Si ya no puedes ir, cancélala desde «Mis citas»: así otra persona puede usar el turno.")
    metricas.recordatorios.add(1, {"tipo": "60"})
    return True


def procesar_avisos_previos(db: Session) -> None:
    """Citas activas que empiezan entre 40 y 60 minutos desde ahora y tienen riesgo alto → aviso extra.
    Si la cita no tiene riesgo calculado (p. ej. se creó antes de esta feature), se calcula aquí."""
    prediccion.modelo_activo(db)  # carga el modelo en el primer ciclo y detecta uno nuevo cada 5 minutos
    ahora = ahora_local()
    desde, hasta = ahora + timedelta(minutes=MINUTOS_RECORDATORIO), ahora + timedelta(minutes=MINUTOS_AVISO_EXTRA)
    candidatas = db.scalars(select(Cita).where(
        Cita.status.in_(ESTADOS_ACTIVOS), Cita.early_reminder_sent_at.is_(None),
        Cita.appointment_date.between(ahora.date(), hasta.date())))
    for cita in list(candidatas.unique()):
        if not desde < datetime.combine(cita.appointment_date, cita.start_time) <= hasta:
            continue
        riesgo = cita.no_show_risk if cita.no_show_risk is not None else prediccion.actualizar_riesgo(db, cita)
        if prediccion.es_alto(riesgo):
            enviar_aviso_previo(db, cita)


def recordar(db: Session, cita_id: int) -> None:
    if not enviar_recordatorio(db, cita_id):
        raise DatosInvalidos("Solo se envía recordatorio a citas pendientes")


def confirmar_por_token(db: Session, token: str) -> bool:
    limite = ahora_utc() - timedelta(minutes=MINUTOS_PARA_CONFIRMAR)
    cita = db.scalar(select(Cita).where(Cita.token_hash == hash_token(token), Cita.status == "pendiente",
                                        Cita.reminder_sent_at > limite))
    if not cita:
        return False
    cita.status, cita.token_hash = "confirmada", None
    db.commit()
    return True


def procesar_recordatorios(db: Session) -> None:
    """Tarea periódica: aviso extra a las citas de riesgo alto (60 min), recordatorios con confirmación (40 min)
    y cancela las citas que no se confirmaron a tiempo."""
    procesar_avisos_previos(db)
    ahora = ahora_local()
    ventana = ahora + timedelta(minutes=MINUTOS_RECORDATORIO)
    pendientes = db.scalars(select(Cita).where(
        Cita.status == "pendiente", Cita.reminder_sent_at.is_(None),
        Cita.appointment_date.between(ahora.date(), ventana.date())))
    for cita in list(pendientes.unique()):
        if ahora <= datetime.combine(cita.appointment_date, cita.start_time) <= ventana:
            enviar_recordatorio(db, cita.id)

    limite = ahora_utc() - timedelta(minutes=MINUTOS_PARA_CONFIRMAR)
    vencidas = list(db.scalars(select(Cita.id).where(Cita.status == "pendiente", Cita.reminder_sent_at < limite)))
    if vencidas:
        db.execute(update(Cita).where(Cita.id.in_(vencidas))
                   .values(status="cancelada_sin_confirmar", token_hash=None))
    db.commit()
    for cita_id in vencidas:  # el cliente se entera de por qué perdió la cita
        correo_de_cancelacion(cita_id)
    disp.borrar_antiguas(db)


# ---------- barbero que deja de atender ----------

def reasignar_de_barbero(db: Session, barbero_id: int, desde: date | None = None,
                         hasta: date | None = None) -> list[dict]:
    """Pasa las citas futuras (pendientes o confirmadas) de un barbero inactivo o ausente (entre `desde` y `hasta`,
    RF17) a otro barbero activo que ofrezca los mismos servicios y esté libre a esa misma hora. Si nadie puede,
    la cita se cancela. Devuelve un resumen por cita para avisar a los clientes por correo."""
    ahora = ahora_local()
    anterior = db.get(Usuario, barbero_id)
    q = select(Cita).where(Cita.barber_id == barbero_id, Cita.status.in_(ESTADOS_ACTIVOS),
                           Cita.appointment_date >= max(ahora.date(), desde or ahora.date()))
    if hasta is not None:
        q = q.where(Cita.appointment_date <= hasta)
    pendientes = [c for c in db.scalars(q).unique() if datetime.combine(c.appointment_date, c.start_time) > ahora]
    pendientes.sort(key=lambda c: (c.appointment_date, c.start_time))
    otros = [b for b in db.scalars(select(Usuario).where(Usuario.role == Rol.BARBERO, Usuario.is_active,
                                                         Usuario.id != barbero_id).order_by(Usuario.id))]
    resumen: list[dict] = []
    for cita in pendientes:
        ids = {s.id for s in cita.servicios} or {cita.service_id}
        aptos = [b for b in otros if ids <= set(b.service_ids)]
        carga = {b.id: db.scalar(select(func.count(Cita.id)).where(
            Cita.barber_id == b.id, Cita.appointment_date == cita.appointment_date,
            Cita.status.in_(ESTADOS_ACTIVOS))) or 0 for b in aptos}
        elegido = None
        for b in sorted(aptos, key=lambda b: (carga[b.id], b.id)):  # primero quien tenga menos citas ese día
            if not disp.esta_libre(db, b.id, cita.appointment_date, cita.start_time, cita.duration_minutes):
                continue
            try:
                with db.begin_nested():
                    cita.barber_id = b.id
                    db.flush()
                elegido = b
                break
            except IntegrityError:
                cita.barber_id = barbero_id
        if elegido:
            nuevo = elegido.full_name
        else:
            cita.status, cita.token_hash = "cancelada_admin", None
            nuevo = None
        db.commit()
        resumen.append({"cita_id": cita.id, "anterior": anterior.full_name if anterior else "Tu barbero", "nuevo": nuevo})
    return resumen


def correos_por_cambio_de_barbero(resumen: list[dict]) -> None:
    """Avisa a cada cliente si su cita pasó a otro barbero o se canceló. Se ejecuta en segundo plano."""
    url = get_settings().public_url.rstrip("/")
    with bd.SessionLocal() as db:
        for r in resumen:
            cita = db.get(Cita, r["cita_id"])
            destino = cita and (cita.cliente.email if cita.cliente else cita.guest_email)
            if not destino:
                continue
            cuando = f"{cita.appointment_date} a las {hora12(cita.start_time)}"
            if r["nuevo"]:
                correo.enviar(destino, f"Tu cita en {barberia.nombre(db)} cambió de barbero",
                              f"{r['anterior']} ya no está disponible, así que pasamos tu cita a {r['nuevo']}.\n"
                              f"Se mantiene el mismo día y la misma hora: {cuando}.\n\n"
                              "Si prefieres otro horario, puedes cancelarla desde «Mis citas» y agendar de nuevo.")
            else:
                correo.enviar(destino, f"Tu cita en {barberia.nombre(db)} fue cancelada",
                              f"{r['anterior']} ya no está disponible y no encontramos otro barbero libre el {cuando}.\n"
                              f"Tu cita fue cancelada. Agenda un nuevo horario aquí: {url}/agendar\n"
                              "Disculpa los inconvenientes.")
