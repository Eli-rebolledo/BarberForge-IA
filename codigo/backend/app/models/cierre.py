from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DiaCerrado(Base):
    """Día en que la barbería no atiende (festivo o cierre). Nadie puede agendar ese día (RF09)."""

    __tablename__ = "closed_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True)
    motivo: Mapped[str] = mapped_column(Text, default="Festivo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AusenciaBarbero(Base):
    """Rango de días en que un barbero no atiende: vacaciones, incapacidad, permiso (RF17)."""

    __tablename__ = "barber_absences"

    id: Mapped[int] = mapped_column(primary_key=True)
    barber_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    motivo: Mapped[str] = mapped_column(Text, default="Ausencia")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
