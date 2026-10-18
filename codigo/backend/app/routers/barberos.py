from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.orm import Session

from app.core.dependencias import get_current_user_opcional, require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.barbero import BarberoAlternarOut, BarberoCreadoOut, BarberoDetalleOut, BarberoDiasIn, BarberoEditarIn, BarberoIn, BarberoOut, FotoIn, FotoOut
from app.schemas.comun import OkOut
from app.services import barberos, citas

router = APIRouter(prefix="/api/barbers", tags=["barberos"])
solo_admin = require_roles(Rol.ADMIN)


@router.get("", response_model=list[BarberoOut])
def listar(service_id: int | None = None, usuario: Usuario | None = Depends(get_current_user_opcional),
           db: Session = Depends(get_db)) -> list[Usuario]:
    return barberos.listar(db, incluir_inactivos=bool(usuario and usuario.role == Rol.ADMIN), servicio_id=service_id)


@router.post("", response_model=BarberoCreadoOut)
def crear(datos: BarberoIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> BarberoCreadoOut:
    return BarberoCreadoOut(id=barberos.crear(db, datos).id)


@router.post("/{barbero_id}/toggle", response_model=BarberoAlternarOut)
def alternar(barbero_id: int, tareas: BackgroundTasks, _: Usuario = Depends(solo_admin),
             db: Session = Depends(get_db)) -> BarberoAlternarOut:
    barbero = barberos.alternar(db, barbero_id)
    resumen = [] if barbero.is_active else citas.reasignar_de_barbero(db, barbero.id)
    if resumen:
        tareas.add_task(citas.correos_por_cambio_de_barbero, resumen)
    return BarberoAlternarOut(reasignadas=sum(1 for r in resumen if r["nuevo"]),
                              canceladas=sum(1 for r in resumen if not r["nuevo"]))


@router.put("/{barbero_id}/days", response_model=OkOut)
def dias(barbero_id: int, datos: BarberoDiasIn, _: Usuario = Depends(solo_admin),
         db: Session = Depends(get_db)) -> OkOut:
    barberos.actualizar_dias(db, barbero_id, datos.work_days)
    return OkOut()


@router.get("/{barbero_id}", response_model=BarberoDetalleOut)
def detalle(barbero_id: int, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> Usuario:
    return barberos.obtener(db, barbero_id)


@router.put("/{barbero_id}", response_model=OkOut)
def editar(barbero_id: int, datos: BarberoEditarIn, _: Usuario = Depends(solo_admin),
           db: Session = Depends(get_db)) -> OkOut:
    barberos.editar(db, barbero_id, datos)
    return OkOut()


@router.delete("/{barbero_id}", response_model=OkOut)
def eliminar(barbero_id: int, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> OkOut:
    barberos.eliminar(db, barbero_id)
    return OkOut()


@router.get("/{barbero_id}/photo", response_class=Response, responses={200: {"content": {"image/jpeg": {}}}})
def foto(barbero_id: int, db: Session = Depends(get_db)) -> Response:
    """Pública: la ven los clientes al elegir barbero. La URL lleva ?v=… y cambia con cada foto nueva."""
    datos, mime = barberos.leer_foto(db, barbero_id)
    return Response(content=datos, media_type=mime, headers={"Cache-Control": "public, max-age=604800"})


@router.put("/{barbero_id}/photo", response_model=FotoOut)
def subir_foto(barbero_id: int, datos: FotoIn,
               usuario: Usuario = Depends(require_roles(Rol.ADMIN, Rol.BARBERO)),
               db: Session = Depends(get_db)) -> FotoOut:
    return FotoOut(photo_url=barberos.guardar_foto(db, usuario, barbero_id, datos.image).photo_url)


@router.delete("/{barbero_id}/photo", response_model=OkOut)
def quitar_foto(barbero_id: int, usuario: Usuario = Depends(require_roles(Rol.ADMIN, Rol.BARBERO)),
                db: Session = Depends(get_db)) -> OkOut:
    barberos.quitar_foto(db, usuario, barbero_id)
    return OkOut()
