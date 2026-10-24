from pydantic import BaseModel

from app.schemas.barbero import BarberoOut
from app.schemas.servicio import ServicioOut


class OkOut(BaseModel):
    ok: bool = True


class SaludOut(BaseModel):
    servicio: str
    estado: str
    base_de_datos: str


class ReindexOut(BaseModel):
    embeddings_ok: bool


class BarberiaBase(BaseModel):
    id: int
    nombre: str
    direccion: str
    horario: str
    descripcion: str
    buzon_url: str
    logo_url: str | None = None


class BarberiaResumen(BarberiaBase):
    servicios: int
    barberos: int


class BarberiaDetalle(BarberiaBase):
    servicios: list[ServicioOut]
    barberos: list[BarberoOut]


class MarcaOut(BaseModel):
    """Identidad pública de la barbería: la usa la web para el logo, el nombre y el ícono de la pestaña."""

    nombre: str
    direccion: str
    horario: str
    descripcion: str
    logo_url: str | None = None


class MarcaIn(BaseModel):
    nombre: str
    direccion: str = ""
    horario: str = ""
    descripcion: str = ""


class LogoIn(BaseModel):
    image: str  # data URL: data:image/png;base64,…
