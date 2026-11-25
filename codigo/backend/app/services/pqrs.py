"""PQRS (feature 012): se registran, se avisa a los administradores y se responden desde el panel."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import db as bd
from app.core.tiempo import ahora_utc
from app.models import Pqrs, Rol, Usuario
from app.schemas.pqrs import PqrsCreadaOut, PqrsGestionIn, PqrsIn, PqrsOut
from app.services import barberia, correo
from app.services.errores import NoEncontrado

NOMBRES = {"peticion": "petición", "queja": "queja", "reclamo": "reclamo", "sugerencia": "sugerencia"}
PLAZO = "15 días hábiles"


def radicado(p: Pqrs) -> str:
    return f"PQRS-{p.id:05d}"


def crear(db: Session, usuario: Usuario | None, datos: PqrsIn) -> tuple[Pqrs, PqrsCreadaOut]:
    p = Pqrs(user_id=usuario.id if usuario else None, tipo=datos.tipo, descripcion=datos.descripcion.strip(),
             resumen=(datos.resumen or "").strip() or None, canal=datos.canal)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p, PqrsCreadaOut(id=p.id, radicado=radicado(p),
                            mensaje=f"Registré tu {NOMBRES[p.tipo]} con el radicado {radicado(p)}. La barbería te "
                                    f"responderá en un plazo máximo de {PLAZO}.")


def avisar_en_segundo_plano(pqrs_id: int) -> None:
    """Tarea de fondo con su propia sesión (la de la petición ya se cerró)."""
    with bd.SessionLocal() as db:
        avisar_administradores(db, pqrs_id)


def avisar_administradores(db: Session, pqrs_id: int) -> None:
    """Tarea de fondo: correo a cada administrador activo con la PQRS nueva."""
    p = db.get(Pqrs, pqrs_id)
    if not p:
        return
    quien = db.get(Usuario, p.user_id).full_name if p.user_id and db.get(Usuario, p.user_id) else "Visitante"
    cuerpo = (f"Nueva {NOMBRES[p.tipo]} ({radicado(p)}) recibida por el canal «{p.canal}».\n\n"
              f"De: {quien}\nResumen: {p.resumen or '—'}\n\nTexto completo:\n{p.descripcion}\n\n"
              f"Plazo para responder: {PLAZO}.")
    for admin in db.scalars(select(Usuario).where(Usuario.role == Rol.ADMIN, Usuario.is_active.is_(True))):
        correo.enviar(admin.email, f"[BarberForge] Nueva {NOMBRES[p.tipo]} {radicado(p)}", cuerpo)


def listar(db: Session) -> list[PqrsOut]:
    salida = []
    for p in db.scalars(select(Pqrs).order_by(Pqrs.id.desc()).limit(200)):
        u = db.get(Usuario, p.user_id) if p.user_id else None
        salida.append(PqrsOut(id=p.id, radicado=radicado(p), tipo=p.tipo, descripcion=p.descripcion,
                              resumen=p.resumen, canal=p.canal, estado=p.estado,
                              quien=u.full_name if u else "Visitante", correo=u.email if u else None,
                              respuesta=p.respuesta, respondida_at=p.respondida_at, created_at=p.created_at))
    return salida


def gestionar(db: Session, pqrs_id: int, datos: PqrsGestionIn) -> tuple[Pqrs, bool]:
    """Cambia el estado y, si se escribe, guarda la respuesta. Devuelve (pqrs, hay que avisar al usuario)."""
    p = db.get(Pqrs, pqrs_id)
    if not p:
        raise NoEncontrado("PQRS no encontrada")
    texto = (datos.respuesta or "").strip()
    nueva = bool(texto) and texto != (p.respuesta or "")
    p.estado = datos.estado
    if nueva:
        p.respuesta, p.respondida_at = texto, ahora_utc()
    db.commit()
    return p, nueva and p.user_id is not None


def enviar_respuesta(pqrs_id: int) -> None:
    """Tarea de fondo: correo con la respuesta al usuario que radicó la PQRS."""
    with bd.SessionLocal() as db:
        p = db.get(Pqrs, pqrs_id)
        u = p and p.user_id and db.get(Usuario, p.user_id)
        if not u or not p.respuesta:
            return
        estado = "quedó cerrada" if p.estado == "cerrada" else "sigue en trámite"
        correo.enviar(u.email, f"Respuesta a tu {NOMBRES[p.tipo]} {radicado(p)} · {barberia.nombre(db)}",
                      f"Hola, {u.full_name}.\n\nSobre tu {NOMBRES[p.tipo]}: «{p.resumen or p.descripcion[:120]}»\n\n"
                      f"{p.respuesta}\n\nTu solicitud {estado}.")
