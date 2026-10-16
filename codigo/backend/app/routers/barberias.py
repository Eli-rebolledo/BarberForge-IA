from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.orm import Session

from app.core.dependencias import require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.comun import BarberiaDetalle, BarberiaResumen, LogoIn, MarcaIn, MarcaOut, OkOut
from app.services import barberia, rag

router = APIRouter(prefix="/api", tags=["barberías"])
solo_admin = require_roles(Rol.ADMIN)


@router.get("/barberias", response_model=list[BarberiaResumen])
def listar(db: Session = Depends(get_db)) -> list[BarberiaResumen]:
    return barberia.listar(db)


@router.get("/barberias/{barberia_id}", response_model=BarberiaDetalle)
def detalle(barberia_id: int, db: Session = Depends(get_db)) -> BarberiaDetalle:
    return barberia.detalle(db, barberia_id)


# ---------- identidad de la barbería (nombre, datos y logo) ----------

@router.get("/brand", response_model=MarcaOut)
def marca(db: Session = Depends(get_db)) -> MarcaOut:
    return barberia.marca(db)


@router.put("/brand", response_model=MarcaOut)
def actualizar_marca(datos: MarcaIn, tareas: BackgroundTasks, _: Usuario = Depends(solo_admin),
                     db: Session = Depends(get_db)) -> MarcaOut:
    salida = barberia.actualizar(db, datos)
    tareas.add_task(rag.reindexar_en_segundo_plano)  # el asistente responde con el nombre, dirección y horario nuevos
    return salida


@router.get("/brand/logo", response_class=Response, responses={200: {"content": {"image/png": {}}}})
def logo(db: Session = Depends(get_db)) -> Response:
    datos, mime = barberia.leer_logo(db)
    return Response(content=datos, media_type=mime, headers={"Cache-Control": "public, max-age=604800"})


@router.put("/brand/logo", response_model=MarcaOut)
def subir_logo(datos: LogoIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> MarcaOut:
    return barberia.guardar_logo(db, datos.image)


@router.delete("/brand/logo", response_model=OkOut)
def quitar_logo(_: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> OkOut:
    barberia.quitar_logo(db)
    return OkOut()
