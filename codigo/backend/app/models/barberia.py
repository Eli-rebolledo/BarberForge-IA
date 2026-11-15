from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AjustesBarberia(Base):
    """Identidad de la barbería, editable por el administrador: nombre, dirección, horario y logo.
    Hay una sola fila (id = 1). Si no existe, se usan los valores del archivo .env."""

    __tablename__ = "shop_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    hours: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    logo: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    logo_mime: Mapped[str | None] = mapped_column(Text)
    logo_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def logo_url(self) -> str | None:
        if not self.logo_mime:
            return None
        version = int(self.logo_updated_at.timestamp()) if self.logo_updated_at else 0
        return f"/api/brand/logo?v={version}"
