from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TipoPqrs = Literal["peticion", "queja", "reclamo", "sugerencia"]
EstadoPqrs = Literal["abierta", "en_tramite", "cerrada"]


class PqrsIn(BaseModel):
    tipo: TipoPqrs
    descripcion: str = Field(min_length=5, max_length=2000)
    resumen: str | None = Field(default=None, max_length=300)
    canal: Literal["voz", "chat", "formulario"] = "voz"


class PqrsCreadaOut(BaseModel):
    id: int
    radicado: str
    mensaje: str


class PqrsOut(BaseModel):
    id: int
    radicado: str
    tipo: TipoPqrs
    descripcion: str
    resumen: str | None
    canal: str
    estado: str
    quien: str
    correo: str | None = None  # a dónde llega la respuesta (solo si la radicó un usuario registrado)
    respuesta: str | None = None
    respondida_at: datetime | None = None
    created_at: datetime | None


class PqrsGestionIn(BaseModel):
    estado: EstadoPqrs
    respuesta: str | None = Field(default=None, max_length=2000)
