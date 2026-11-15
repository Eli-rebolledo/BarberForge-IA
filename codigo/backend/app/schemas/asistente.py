from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentoIn(BaseModel):
    title: str
    content: str
    access_level: str = "public"  # public = todos · internal = solo barberos y administrador
    question: str | None = None  # si viene, es una respuesta aprendida (pregunta → respuesta)
    is_active: bool = True


class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    access_level: str
    kind: str
    question: str | None
    is_active: bool
    updated_at: datetime | None = None


class PendienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    access_level: str
    asked_by_role: str
    reason: str
    bot_answer: str | None
    times_asked: int
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EnsenarIn(BaseModel):
    answer: str
    access_level: str | None = None
    question: str | None = None  # el administrador puede reescribir la pregunta para que quede más clara
    title: str | None = None
