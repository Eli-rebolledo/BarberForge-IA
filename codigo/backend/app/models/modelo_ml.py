from datetime import datetime

from sqlalchemy import Boolean, DateTime, LargeBinary, Text, false, func
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.db import Base


class ModeloML(Base):
    """Modelos reentrenados con citas reales (feature 011).

    Se guardan en la base y no en disco porque en Kubernetes los contenedores tienen el disco de solo lectura y
    varias réplicas deben ver el mismo modelo. Cada modelo va firmado (HMAC con una clave derivada de JWT_SECRET):
    la app no carga un modelo cuya firma no coincida, así nadie puede colar un archivo malicioso solo con
    acceso de escritura a esta tabla.
    """

    __tablename__ = "ml_models"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, default="inasistencia", server_default="inasistencia")
    version: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)        # «sintetico» o «real»
    algorithm: Mapped[str] = mapped_column(Text)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    content: Mapped[bytes] = deferred(mapped_column(LargeBinary))
    signature: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
