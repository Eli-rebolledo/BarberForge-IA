from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReservaChat(BaseModel):
    barber_id: int
    service_id: int
    date: str
    time: str


class ChatIn(BaseModel):
    message: str
    # Al tocar un horario ofrecido por el asistente se envía la reserva junto con el texto del botón.
    book: ReservaChat | None = None
    # Por dónde llegó el mensaje: el servicio de voz manda «voz» (así una PQRS hablada queda con ese canal).
    channel: Literal["chat", "voz"] = "chat"


class OpcionChat(BaseModel):
    """Botón que el asistente ofrece: enviar un texto, abrir una página o reservar una franja."""

    label: str
    send: str | None = None
    action: str | None = None  # "registro" | "login"
    book: ReservaChat | None = None
    image: str | None = None  # foto del barbero, si la tiene


class ChatOut(BaseModel):
    reply: str
    sources: list[str] = []
    options: list[OpcionChat] | None = None
    id: int | None = None  # id del mensaje guardado (solo usuarios registrados)
    can_rate: bool = False  # respuesta de la base de conocimiento: se puede marcar si sirvió o no


class MensajeOut(BaseModel):
    id: int
    sender: str  # "me" | "bot"
    text: str
    sources: list[str] = []
    options: list[OpcionChat] | None = None
    can_rate: bool = False
    feedback: int | None = None
    created_at: datetime | None = None


class HistorialOut(BaseModel):
    messages: list[MensajeOut]
    pending: bool = False  # la última pregunta aún se está respondiendo (p. ej. la persona cambió de página)


class OpinionIn(BaseModel):
    useful: bool
    message_id: int | None = None
    # Para visitantes (sin historial): la pregunta y la respuesta que calificaron.
    question: str | None = None
    answer: str | None = None


class OpinionOut(BaseModel):
    ok: bool = True
    message: str
