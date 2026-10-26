from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.dependencias import get_current_user, get_current_user_opcional, require_roles
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas.chat import ChatIn, ChatOut, HistorialOut, OpinionIn, OpinionOut
from app.schemas.comun import OkOut, ReindexOut
from app.services import chat, rag

router = APIRouter(prefix="/api", tags=["asistente"])


@router.post("/chat", response_model=ChatOut, response_model_exclude_none=True)
def conversar(datos: ChatIn, tareas: BackgroundTasks, usuario: Usuario | None = Depends(get_current_user_opcional),
              db: Session = Depends(get_db)) -> ChatOut:
    return chat.responder(db, usuario, datos.message, datos.book, tareas)


@router.get("/chat/history", response_model=HistorialOut, response_model_exclude_none=True)
def historial(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> HistorialOut:
    """Conversación guardada del usuario (los visitantes no tienen historial)."""
    return chat.historial(db, usuario)


@router.delete("/chat/history", response_model=OkOut)
def borrar_historial(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> OkOut:
    chat.borrar_historial(db, usuario)
    return OkOut()


@router.post("/chat/feedback", response_model=OpinionOut)
def opinar(datos: OpinionIn, usuario: Usuario | None = Depends(get_current_user_opcional),
           db: Session = Depends(get_db)) -> OpinionOut:
    return chat.opinar(db, usuario, datos)


@router.post("/admin/reindex", response_model=ReindexOut)
def reindexar(_: Usuario = Depends(require_roles(Rol.ADMIN)), db: Session = Depends(get_db)) -> ReindexOut:
    return ReindexOut(embeddings_ok=rag.reindexar(db))
