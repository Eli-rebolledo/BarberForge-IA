from datetime import date, datetime, time

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Table,
    Text,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ESTADOS_ACTIVOS = ("pendiente", "confirmada")
ESTADOS = (*ESTADOS_ACTIVOS, "completada", "inasistencia",
           "cancelada_cliente", "cancelada_admin", "cancelada_sin_confirmar")
_ACTIVA = text("status IN ('pendiente','confirmada')")

# Una cita puede incluir varios servicios (p. ej. corte + tratamiento).
cita_servicio = Table(
    "appointment_services", Base.metadata,
    Column("appointment_id", Integer, ForeignKey("appointments.id"), primary_key=True),
    Column("service_id", Integer, ForeignKey("services.id"), primary_key=True),
)


class Cita(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        # RN08: un barbero no puede tener dos citas activas en la misma franja.
        Index("uq_cita_activa", "barber_id", "appointment_date", "start_time", unique=True,
              postgresql_where=_ACTIVA, sqlite_where=_ACTIVA),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sin cliente registrado (cita creada en el local): client_id es nulo y se usa guest_*.
    client_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    guest_name: Mapped[str | None] = mapped_column(Text)
    guest_phone: Mapped[str | None] = mapped_column(Text)
    guest_email: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    barber_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))  # servicio principal
    appointment_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    price_cop: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # total al agendar
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, server_default="30")
    status: Mapped[str] = mapped_column(Text, default="pendiente", server_default="pendiente")
    token_hash: Mapped[str | None] = mapped_column(Text)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cliente: Mapped["Usuario | None"] = relationship(foreign_keys=[client_id], lazy="joined")  # noqa: F821
    barbero: Mapped["Usuario"] = relationship(foreign_keys=[barber_id], lazy="joined")  # noqa: F821
    servicio: Mapped["Servicio"] = relationship(lazy="joined")  # noqa: F821
    servicios: Mapped[list["Servicio"]] = relationship(  # noqa: F821
        secondary=cita_servicio, lazy="selectin", order_by="Servicio.id")
