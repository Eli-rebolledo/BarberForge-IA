from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencias import require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.comun import OkOut
from app.schemas.disponibilidad import (
    CerrarDiasIn,
    DiaCalendarioOut,
    FranjaOut,
    GenerarDisponibilidadIn,
)
from app.services import disponibilidad

router = APIRouter(prefix="/api/availability", tags=["disponibilidad"])
# El calendario de atención solo lo asigna el administrador; el barbero ve su agenda en «Mi agenda».
solo_admin = require_roles(Rol.ADMIN)


@router.post("", response_model=OkOut)
def generar(datos: GenerarDisponibilidadIn, _: Usuario = Depends(solo_admin),
            db: Session = Depends(get_db)) -> OkOut:
    disponibilidad.generar(db, datos)
    return OkOut()


@router.post("/close", response_model=OkOut)
def cerrar(datos: CerrarDiasIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> OkOut:
    disponibilidad.cerrar_dias(db, datos.barber_id, datos.dates)
    return OkOut()


@router.get("/calendar", response_model=list[DiaCalendarioOut])
def calendario(barber_id: int, month: str, _: Usuario = Depends(solo_admin),
               db: Session = Depends(get_db)) -> list[dict]:
    return disponibilidad.calendario(db, barber_id, month)


@router.get("", response_model=list[FranjaOut])
def libres(barber_id: int, minutes: int = 30, db: Session = Depends(get_db)) -> list[FranjaOut]:
    return [FranjaOut(date=str(f.slot_date), time=f"{f.start_time:%H:%M}")
            for f in disponibilidad.franjas_libres(db, barber_id, limite=400, minutos=max(10, min(minutes, 480)))]
