"""Festivos (RF09) y ausencias de barberos (RF17). Los gestiona el administrador; la lista de festivos es pública
para que el calendario de «Agendar» los muestre cerrados."""
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.dependencias import require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.cierres import (
    AusenciaCreadaOut,
    AusenciaIn,
    AusenciaOut,
    CitaAfectadaOut,
    FestivoCreadoOut,
    FestivoIn,
    FestivoOut,
    FestivosCargadosOut,
    FestivosColombiaIn,
)
from app.schemas.comun import OkOut
from app.services import cierres, citas, rag

router = APIRouter(prefix="/api", tags=["festivos y ausencias"])
solo_admin = require_roles(Rol.ADMIN)


@router.get("/closed-days", response_model=list[FestivoOut])
def festivos(db: Session = Depends(get_db)) -> list[FestivoOut]:
    return [FestivoOut(id=f.id, date=f.day, motivo=f.motivo) for f in cierres.listar_festivos(db)]


def _afectadas(lista) -> list[CitaAfectadaOut]:
    return [CitaAfectadaOut(id=c.id, date=c.appointment_date, time=f"{c.start_time:%H:%M}",
                            client=c.cliente.full_name if c.cliente else (c.guest_name or "Cliente"),
                            barber=c.barbero.full_name, service=" + ".join(s.name for s in c.servicios) or c.servicio.name)
            for c in lista]


@router.get("/closed-days/preview", response_model=list[CitaAfectadaOut])
def vista_previa_festivo(date: date, date_to: date | None = None, _: Usuario = Depends(solo_admin),
                         db: Session = Depends(get_db)) -> list[CitaAfectadaOut]:
    """Citas activas que se cancelarían al cerrar esos días (se muestran antes de confirmar)."""
    return _afectadas(cierres.citas_afectadas(db, date, date_to))


@router.post("/closed-days", response_model=FestivoCreadoOut)
def crear_festivo(datos: FestivoIn, tareas: BackgroundTasks, _: Usuario = Depends(solo_admin),
                  db: Session = Depends(get_db)) -> FestivoCreadoOut:
    dias, canceladas = cierres.crear_festivo(db, datos.date, datos.motivo, datos.date_to)
    tareas.add_task(rag.reindexar_en_segundo_plano)  # el asistente aprende los días sin atención
    if canceladas:
        tareas.add_task(cierres.correos_por_festivo, canceladas)
    return FestivoCreadoOut(id=dias[0].id if dias else 0, dias=len(dias), canceladas=len(canceladas))


@router.post("/closed-days/colombia", response_model=FestivosCargadosOut)
def cargar_colombia(datos: FestivosColombiaIn, tareas: BackgroundTasks, _: Usuario = Depends(solo_admin),
                    db: Session = Depends(get_db)) -> FestivosCargadosOut:
    creados, canceladas = cierres.cargar_colombia(db, datos.year)
    tareas.add_task(rag.reindexar_en_segundo_plano)
    if canceladas:
        tareas.add_task(cierres.correos_por_festivo, canceladas)
    return FestivosCargadosOut(creados=creados, canceladas=len(canceladas))


@router.delete("/closed-days/{festivo_id}", response_model=OkOut)
def borrar_festivo(festivo_id: int, tareas: BackgroundTasks, _: Usuario = Depends(solo_admin),
                   db: Session = Depends(get_db)) -> OkOut:
    cierres.borrar_festivo(db, festivo_id)
    tareas.add_task(rag.reindexar_en_segundo_plano)
    return OkOut()


@router.get("/absences", response_model=list[AusenciaOut])
def ausencias(barber_id: int | None = None, _: Usuario = Depends(solo_admin),
              db: Session = Depends(get_db)) -> list[AusenciaOut]:
    salida = []
    for a in cierres.listar_ausencias(db, barber_id):
        barbero = db.get(Usuario, a.barber_id)
        salida.append(AusenciaOut(id=a.id, barber_id=a.barber_id, barber=barbero.full_name if barbero else "—",
                                  date_from=a.date_from, date_to=a.date_to, motivo=a.motivo))
    return salida


@router.get("/barbers/{barbero_id}/absences/preview", response_model=list[CitaAfectadaOut])
def vista_previa_ausencia(barbero_id: int, date_from: date, date_to: date, _: Usuario = Depends(solo_admin),
                          db: Session = Depends(get_db)) -> list[CitaAfectadaOut]:
    """Citas del barbero que habría que pasar a otro barbero o cancelar."""
    return _afectadas(cierres.citas_afectadas(db, date_from, date_to, barbero_id))


@router.post("/barbers/{barbero_id}/absences", response_model=AusenciaCreadaOut)
def crear_ausencia(barbero_id: int, datos: AusenciaIn, tareas: BackgroundTasks, _: Usuario = Depends(solo_admin),
                   db: Session = Depends(get_db)) -> AusenciaCreadaOut:
    ausencia, resumen = cierres.crear_ausencia(db, barbero_id, datos.date_from, datos.date_to, datos.motivo)
    if resumen:
        tareas.add_task(citas.correos_por_cambio_de_barbero, resumen)
    return AusenciaCreadaOut(id=ausencia.id, reasignadas=sum(1 for r in resumen if r["nuevo"]),
                             canceladas=sum(1 for r in resumen if not r["nuevo"]))


@router.delete("/absences/{ausencia_id}", response_model=OkOut)
def borrar_ausencia(ausencia_id: int, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> OkOut:
    cierres.borrar_ausencia(db, ausencia_id)
    return OkOut()
