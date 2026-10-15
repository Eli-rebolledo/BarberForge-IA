from pydantic import BaseModel, ConfigDict


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    style_pref: str = ""
    photo_url: str | None = None


class RegistroIn(BaseModel):
    """Solo lo necesario para tener una cuenta: nombre, correo y contraseña (sin cédula)."""

    email: str
    full_name: str
    password: str
    accept_policy: bool = False


class LoginIn(BaseModel):
    email: str
    password: str


class SesionOut(BaseModel):
    token: str
    user: UsuarioOut


class CuentaIn(BaseModel):
    full_name: str | None = None
    email: str | None = None
    style_pref: str | None = None
    current_password: str | None = None
    new_password: str | None = None


class CuentaOut(BaseModel):
    user: UsuarioOut


class SetupOut(BaseModel):
    hay_admin: bool


class RecuperarIn(BaseModel):
    email: str


class RestablecerIn(BaseModel):
    token: str
    password: str


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
