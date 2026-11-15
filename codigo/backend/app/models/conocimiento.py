from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

DIMENSION_EMBEDDING = 768  # nomic-embed-text

NIVEL_PUBLICO = "public"
NIVEL_INTERNO = "internal"
NIVELES = (NIVEL_PUBLICO, NIVEL_INTERNO)

TIPO_DOCUMENTO = "documento"   # texto que escribe el administrador (políticas, procedimientos internos…)
TIPO_APRENDIDO = "aprendido"   # pregunta que el asistente no sabía y el administrador le enseñó


class DocumentoConocimiento(Base):
    """Lo que el asistente sabe. Se edita desde el panel del administrador y se indexa en fragmentos (RAG)."""

    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    access_level: Mapped[str] = mapped_column(Text, default=NIVEL_PUBLICO, server_default=NIVEL_PUBLICO)
    kind: Mapped[str] = mapped_column(Text, default=TIPO_DOCUMENTO, server_default=TIPO_DOCUMENTO)
    # Solo para lo aprendido: la pregunta original, para responder al instante si alguien la repite.
    question: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


class PreguntaPendiente(Base):
    """Pregunta que el asistente no supo responder (o cuya respuesta no sirvió). El administrador la enseña."""

    __tablename__ = "unanswered_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    normalized: Mapped[str] = mapped_column(Text, index=True)
    access_level: Mapped[str] = mapped_column(Text, default=NIVEL_PUBLICO)  # interno si la hizo el personal
    asked_by_role: Mapped[str] = mapped_column(Text, default="visitante")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(Text, default="sin_respuesta")  # sin_respuesta | no_util
    bot_answer: Mapped[str | None] = mapped_column(Text)
    times_asked: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(Text, default="pendiente")  # pendiente | respondida | descartada
    doc_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_docs.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


class FragmentoConocimiento(Base):
    """Fragmento de la base de conocimiento del asistente (RAG) con su embedding."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("kc_hnsw", "embedding", postgresql_using="hnsw",
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_docs.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(Text, default=TIPO_DOCUMENTO, server_default=TIPO_DOCUMENTO)
    source: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    access_level: Mapped[str] = mapped_column(Text)
    # En PostgreSQL es vector(768) con pgvector; en SQLite (pruebas) se guarda como JSON.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(DIMENSION_EMBEDDING).with_variant(JSON(), "sqlite"))
