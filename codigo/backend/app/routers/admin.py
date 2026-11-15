from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencias import require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.admin import AjustesOut, EstadisticasOut
from app.schemas.usuario import ClienteOut
from app.services import estadisticas

router = APIRouter(prefix="/api", tags=["administración"])


@router.get("/admin/stats", response_model=EstadisticasOut)
def estadisticas_panel(_: Usuario = Depends(require_roles(Rol.ADMIN)), db: Session = Depends(get_db)) -> EstadisticasOut:
    return estadisticas.resumen(db)


@router.get("/admin/settings", response_model=AjustesOut)
def ajustes(_: Usuario = Depends(require_roles(Rol.ADMIN)), db: Session = Depends(get_db)) -> AjustesOut:
    return estadisticas.ajustes(db)


@router.get("/clients", response_model=list[ClienteOut])
def clientes(_: Usuario = Depends(require_roles(Rol.ADMIN, Rol.BARBERO)), db: Session = Depends(get_db)) -> list[Usuario]:
    """Solo id y nombre: quien agenda en el local no necesita más datos personales."""
    return estadisticas.clientes(db)
