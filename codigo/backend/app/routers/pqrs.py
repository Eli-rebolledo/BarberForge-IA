from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.dependencias import get_current_user_opcional, require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.comun import OkOut
from app.schemas.pqrs import PqrsCreadaOut, PqrsGestionIn, PqrsIn, PqrsOut
from app.services import pqrs

router = APIRouter(prefix="/api", tags=["pqrs"])


@router.post("/pqrs", response_model=PqrsCreadaOut)
def radicar(datos: PqrsIn, tareas: BackgroundTasks, usuario: Usuario | None = Depends(get_current_user_opcional),
            db: Session = Depends(get_db)) -> PqrsCreadaOut:
    """Feature 012: registra una PQRS (también la pueden enviar visitantes) y avisa por correo al administrador."""
    p, salida = pqrs.crear(db, usuario, datos)
    tareas.add_task(pqrs.avisar_en_segundo_plano, p.id)
    return salida


@router.get("/admin/pqrs", response_model=list[PqrsOut])
def listar(_: Usuario = Depends(require_roles(Rol.ADMIN)), db: Session = Depends(get_db)) -> list[PqrsOut]:
    return pqrs.listar(db)


@router.patch("/admin/pqrs/{pqrs_id}", response_model=OkOut)
def gestionar(pqrs_id: int, datos: PqrsGestionIn, tareas: BackgroundTasks, _: Usuario = Depends(require_roles(Rol.ADMIN)),
              db: Session = Depends(get_db)) -> OkOut:
    """El administrador cambia el estado (abierta, en trámite, cerrada) y responde; la respuesta llega por correo."""
    p, avisar = pqrs.gestionar(db, pqrs_id, datos)
    if avisar:
        tareas.add_task(pqrs.enviar_respuesta, p.id)
    return OkOut()
