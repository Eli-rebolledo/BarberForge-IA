from html import escape

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.dependencias import require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.cita import CitaCreadaOut, CitaIn, CitaOut, EstadoCitaIn
from app.schemas.comun import MarcaOut, OkOut
from app.services import barberia, citas

router = APIRouter(prefix="/api", tags=["citas"])
todos = require_roles(Rol.CLIENTE, Rol.BARBERO, Rol.ADMIN)


@router.post("/appointments", response_model=CitaCreadaOut)
def agendar(datos: CitaIn, tareas: BackgroundTasks, usuario: Usuario = Depends(todos),
            db: Session = Depends(get_db)) -> CitaCreadaOut:
    cita = citas.agendar(db, usuario, datos)
    tareas.add_task(citas.correo_de_creacion, cita.id)
    return CitaCreadaOut(id=cita.id)


@router.get("/appointments", response_model=list[CitaOut])
def listar(usuario: Usuario = Depends(todos), db: Session = Depends(get_db)) -> list[CitaOut]:
    return citas.listar_para(db, usuario)


@router.post("/appointments/{cita_id}/cancel", response_model=OkOut)
def cancelar(cita_id: int, usuario: Usuario = Depends(todos),
             db: Session = Depends(get_db)) -> OkOut:
    citas.cancelar(db, usuario, cita_id)
    return OkOut()


@router.patch("/appointments/{cita_id}/status", response_model=OkOut)
def cerrar(cita_id: int, datos: EstadoCitaIn, usuario: Usuario = Depends(require_roles(Rol.BARBERO, Rol.ADMIN)),
           db: Session = Depends(get_db)) -> OkOut:
    citas.cerrar(db, usuario, cita_id, datos.status)
    return OkOut()


@router.post("/appointments/{cita_id}/remind", response_model=OkOut)
def recordar(cita_id: int, _: Usuario = Depends(require_roles(Rol.ADMIN)), db: Session = Depends(get_db)) -> OkOut:
    citas.recordar(db, cita_id)
    return OkOut()


@router.get("/confirm/{token}", response_class=HTMLResponse)
def confirmar(token: str, db: Session = Depends(get_db)) -> str:
    """Enlace de un solo uso que llega en el correo de recordatorio."""
    return _pagina_confirmacion(citas.confirmar_por_token(db, token), barberia.marca(db))


def _pagina_confirmacion(ok: bool, marca: MarcaOut) -> str:
    nombre = escape(marca.nombre)
    logo = (f"<img src='{escape(marca.logo_url)}' alt='{nombre}' style='max-width:140px;max-height:70px;"
            "object-fit:contain;display:block;margin:0 auto 18px'>") if marca.logo_url else ""
    titulo = "Cita confirmada" if ok else "Enlace no válido"
    texto = "Gracias por confirmar. Te esperamos en la barbería." if ok else "El enlace venció o ya fue usado."
    color = "#16a34a" if ok else "#e11d2e"
    icono = ("<path d='M20 6 9 17l-5-5'/>" if ok else "<path d='M18 6 6 18M6 6l12 12'/>")
    return (
        "<!DOCTYPE html><html lang='es'><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'><title>{nombre}</title>"
        "<body style='margin:0;min-height:100vh;display:grid;place-items:center;padding:20px;box-sizing:border-box;"
        "background:linear-gradient(120deg,#0e1b4d,#1f3faf);font-family:Inter,system-ui,sans-serif'>"
        "<div style='text-align:center;background:#fff;padding:40px 34px;border-radius:22px;max-width:420px;width:100%;"
        "box-shadow:0 24px 60px rgba(5,10,40,.35)'>"
        f"{logo}<div style='width:64px;height:64px;border-radius:50%;background:{color};margin:0 auto 18px;display:grid;"
        "place-items:center'><svg width='30' height='30' viewBox='0 0 24 24' fill='none' stroke='#fff' "
        f"stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>{icono}</svg></div>"
        f"<h2 style='margin:0 0 8px;color:#0e1b4d;font-size:24px'>{titulo}</h2>"
        f"<p style='margin:0 0 24px;color:#667085'>{texto}</p>"
        "<a href='/' style='display:inline-block;background:#1f3faf;color:#fff;text-decoration:none;font-weight:600;"
        f"padding:11px 22px;border-radius:12px'>Ir a {nombre}</a></div></body></html>")
