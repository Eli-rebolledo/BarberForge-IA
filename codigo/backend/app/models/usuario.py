from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, LargeBinary, Text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.barbero_servicio import barbero_servicio


class Rol(StrEnum):
    CLIENTE = "cliente"
    BARBERO = "barbero"
    ADMIN = "administrador"


class Usuario(Base):
    """Clientes, barberos y administradores comparten la tabla; el rol los distingue."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True)
    full_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    policy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Recuperación de contraseña: solo se guarda el hash del enlace de un solo uso.
    reset_token_hash: Mapped[str | None] = mapped_column(Text)
    reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    specialties: Mapped[str] = mapped_column(Text, default="", server_default="")
    style_pref: Mapped[str] = mapped_column(Text, default="", server_default="")
    # Solo aplica a barberos: días de la semana que trabaja (0 = lunes … 6 = domingo), separados por comas.
    dias_csv: Mapped[str] = mapped_column("work_days", Text, default="0,1,2,3,4,5", server_default="0,1,2,3,4,5")

    # Foto del barbero (la gente lo reconoce más por su cara que por su nombre). Se carga solo cuando se pide.
    photo: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    photo_mime: Mapped[str | None] = mapped_column(Text)
    photo_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Solo aplica a barberos: servicios que ofrece.
    servicios: Mapped[list["Servicio"]] = relationship(  # noqa: F821
        secondary=barbero_servicio, lazy="selectin", order_by="Servicio.id")

    @property
    def work_days(self) -> list[int]:
        return [int(d) for d in self.dias_csv.split(",") if d.strip().isdigit()]

    @property
    def photo_url(self) -> str | None:
        """Ruta pública de la foto; el parámetro v evita que el navegador muestre una foto vieja en caché."""
        if not self.photo_mime:
            return None
        version = int(self.photo_updated_at.timestamp()) if self.photo_updated_at else 0
        return f"/api/barbers/{self.id}/photo?v={version}"

    @property
    def service_ids(self) -> list[int]:
        return [s.id for s in self.servicios]
