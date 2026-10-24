"""Panel del administrador para enseñarle al asistente: preguntas por aprender y base de conocimiento."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencias import require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.asistente import DocumentoIn, DocumentoOut, EnsenarIn, PendienteOut
from app.schemas.comun import OkOut
from app.services import aprendizaje

router = APIRouter(prefix="/api/assistant", tags=["aprendizaje del asistente"])
solo_admin = require_roles(Rol.ADMIN)


@router.get("/questions", response_model=list[PendienteOut])
def preguntas(status: str = "pendiente", _: Usuario = Depends(solo_admin),
              db: Session = Depends(get_db)) -> list:
    return aprendizaje.listar_pendientes(db, status)


@router.post("/questions/{pregunta_id}/answer", response_model=DocumentoOut)
def ensenar(pregunta_id: int, datos: EnsenarIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    return aprendizaje.ensenar(db, pregunta_id, datos)


@router.post("/questions/{pregunta_id}/discard", response_model=OkOut)
def descartar(pregunta_id: int, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> OkOut:
    aprendizaje.descartar(db, pregunta_id)
    return OkOut()


@router.get("/knowledge", response_model=list[DocumentoOut])
def documentos(_: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> list:
    return aprendizaje.listar_documentos(db)


@router.post("/knowledge", response_model=DocumentoOut)
def crear(datos: DocumentoIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    return aprendizaje.crear_documento(db, datos)


@router.put("/knowledge/{doc_id}", response_model=DocumentoOut)
def editar(doc_id: int, datos: DocumentoIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    return aprendizaje.editar_documento(db, doc_id, datos)


@router.delete("/knowledge/{doc_id}", response_model=OkOut)
def eliminar(doc_id: int, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)) -> OkOut:
    aprendizaje.eliminar_documento(db, doc_id)
    return OkOut()
