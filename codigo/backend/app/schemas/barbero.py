from pydantic import BaseModel, ConfigDict


class BarberoIn(BaseModel):
    email: str
    full_name: str
    password: str
    specialties: str = ""
    service_ids: list[int] = []
    work_days: list[int] = [0, 1, 2, 3, 4, 5]


class BarberoDiasIn(BaseModel):
    work_days: list[int]


class BarberoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    is_active: bool
    specialties: str
    service_ids: list[int]
    work_days: list[int]
    photo_url: str | None = None


class BarberoEditarIn(BaseModel):
    """Edición por el administrador. La contraseña es opcional: vacía = no se cambia."""

    email: str
    full_name: str
    password: str = ""
    specialties: str = ""
    service_ids: list[int] = []


class BarberoDetalleOut(BarberoOut):
    """Solo para el administrador: incluye el correo con el que el barbero inicia sesión."""

    email: str


class BarberoAlternarOut(BaseModel):
    ok: bool = True
    reasignadas: int = 0  # citas que pasaron a otro barbero al desactivarlo
    canceladas: int = 0  # citas que no pudieron pasar a nadie y se cancelaron


class FotoIn(BaseModel):
    image: str  # data URL: data:image/jpeg;base64,…


class FotoOut(BaseModel):
    ok: bool = True
    photo_url: str | None


class BarberoCreadoOut(BaseModel):
    ok: bool = True
    id: int  # para subir la foto justo después de crearlo
