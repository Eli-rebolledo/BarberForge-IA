from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MensajeChat(Base):
    """Historial del asistente de cada usuario registrado (los visitantes no tienen historial).

    Se guarda en la base de datos para que la conversación siga ahí aunque la persona cambie de página,
    recargue o abra la app en otro dispositivo, y para que una respuesta lenta no se pierda."""

    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_usuario", "user_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    sender: Mapped[str] = mapped_column(Text)  # "me" (la persona) | "bot"
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSON)
    options: Mapped[list | None] = mapped_column(JSON)
    # Solo en respuestas del bot que vienen de la base de conocimiento: se pueden calificar.
    question: Mapped[str | None] = mapped_column(Text)
    can_rate: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    feedback: Mapped[int | None] = mapped_column(SmallInteger)  # 1 = me sirvió, -1 = no me sirvió
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
