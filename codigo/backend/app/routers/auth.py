from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.seguridad import crear_token
from app.db import get_db
from app.schemas.comun import OkOut
from app.schemas.usuario import (
    LoginIn,
    RecuperarIn,
    RegistroIn,
    RestablecerIn,
    SesionOut,
    SetupOut,
    UsuarioOut,
)
from app.services import barberia, correo, usuarios

router = APIRouter(prefix="/api", tags=["autenticación"])


@router.get("/setup", response_model=SetupOut)
def setup(db: Session = Depends(get_db)) -> SetupOut:
    """Indica si ya existe un administrador (si no, el próximo registro lo será)."""
    return SetupOut(hay_admin=usuarios.hay_admin(db))


@router.post("/register", response_model=SesionOut)
def registrar(datos: RegistroIn, db: Session = Depends(get_db)) -> SesionOut:
    usuario = usuarios.registrar(db, datos)
    return SesionOut(token=crear_token(usuario.id), user=UsuarioOut.model_validate(usuario))


@router.post("/login", response_model=SesionOut)
def login(datos: LoginIn, db: Session = Depends(get_db)) -> SesionOut:
    usuario = usuarios.autenticar(db, datos.email, datos.password)
    return SesionOut(token=crear_token(usuario.id), user=UsuarioOut.model_validate(usuario))


@router.post("/password/forgot", response_model=OkOut)
def olvide(datos: RecuperarIn, tareas: BackgroundTasks, db: Session = Depends(get_db)) -> OkOut:
    """Siempre responde ok: no revela si el correo existe."""
    r = usuarios.solicitar_recuperacion(db, datos.email)
    if r:
        enlace = f"{get_settings().public_url.rstrip('/')}/restablecer?token={r[1]}"
        tareas.add_task(correo.enviar, r[0], f"Recupera tu contraseña de {barberia.nombre(db)}",
                        f"Usa este enlace para crear una contraseña nueva (vale {usuarios.MINUTOS_RECUPERACION} "
                        f"minutos y solo sirve una vez):\n{enlace}\n\nSi no lo pediste, ignora este mensaje.")
    return OkOut()


@router.post("/password/reset", response_model=OkOut)
def restablecer(datos: RestablecerIn, db: Session = Depends(get_db)) -> OkOut:
    usuarios.restablecer(db, datos.token, datos.password)
    return OkOut()
