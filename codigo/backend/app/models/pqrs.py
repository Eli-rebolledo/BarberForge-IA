from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Pqrs(Base):
    """Peticiones, quejas, reclamos y sugerencias (feature 012).

    Llegan por el asistente de voz (canal «voz») o por el chat. El administrador recibe un correo con cada una y
    las ve en GET /api/admin/pqrs; desde el panel cambia el estado y responde (PATCH /api/admin/pqrs/{id}).
    El plazo para responder es de 15 días hábiles (base de conocimiento, documento
    06-pqrs-procedimiento)."""

    __tablename__ = "pqrs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    tipo: Mapped[str] = mapped_column(Text)  # peticion | queja | reclamo | sugerencia
    descripcion: Mapped[str] = mapped_column(Text)
    resumen: Mapped[str | None] = mapped_column(Text)
    canal: Mapped[str] = mapped_column(Text, default="voz", server_default="voz")
    estado: Mapped[str] = mapped_column(Text, default="abierta", server_default="abierta")  # abierta | en_tramite | cerrada
    respuesta: Mapped[str | None] = mapped_column(Text)  # lo que respondió el administrador (migración 009)
    respondida_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
