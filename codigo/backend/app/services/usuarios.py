"""Registro, inicio de sesión, cuenta y administrador inicial."""
import re
from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.seguridad import (
    hash_password,
    hash_token,
    nuevo_token_un_uso,
    verificar_password,
)
from app.core.tiempo import ahora_utc
from app.db import es_postgres
from app.models import Rol, Usuario
from app.schemas.usuario import CuentaIn, RegistroIn
from app.services.errores import Conflicto, CredencialesInvalidas, DatosInvalidos

CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MINUTOS_RECUPERACION = 30
LONGITUD_MINIMA_CLAVE = 8


def validar_correo(correo: str) -> str:
    correo = correo.strip().lower()
    if not CORREO_RE.match(correo):
        raise DatosInvalidos("El correo no es válido")
    return correo


def validar_clave(clave: str, mensaje: str = "La contraseña debe tener al menos 8 caracteres") -> None:
    if len(clave) < LONGITUD_MINIMA_CLAVE:
        raise DatosInvalidos(mensaje)


def hay_admin(db: Session) -> bool:
    return db.scalar(select(Usuario.id).where(Usuario.role == Rol.ADMIN).limit(1)) is not None


def registrar(db: Session, datos: RegistroIn) -> Usuario:
    nombre = datos.full_name.strip()
    if not nombre:
        raise DatosInvalidos("Escribe tu nombre completo")
    correo = validar_correo(datos.email)
    if not datos.accept_policy:
        raise DatosInvalidos("Debes aceptar la política de tratamiento de datos")
    validar_clave(datos.password)

    if es_postgres(db):
        # Evita que dos registros simultáneos queden ambos como administrador.
        db.execute(text("SELECT pg_advisory_xact_lock(7001)"))
    # RN02: la primera persona registrada queda como administrador; luego solo clientes.
    rol = Rol.CLIENTE if hay_admin(db) else Rol.ADMIN
    usuario = Usuario(email=correo, full_name=nombre, password_hash=hash_password(datos.password), role=rol, policy_accepted_at=ahora_utc())
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflicto("Ese correo ya está registrado") from None
    return usuario


def autenticar(db: Session, correo: str, clave: str) -> Usuario:
    usuario = db.scalar(select(Usuario).where(Usuario.email == correo.strip().lower()))
    if not usuario or not usuario.is_active or not verificar_password(clave, usuario.password_hash):
        raise CredencialesInvalidas("Correo o contraseña incorrectos")
    return usuario


def actualizar_cuenta(db: Session, usuario: Usuario, datos: CuentaIn) -> Usuario:
    if datos.full_name is not None and datos.full_name.strip():
        usuario.full_name = datos.full_name.strip()
    if datos.email is not None and datos.email.strip().lower() != usuario.email:
        usuario.email = validar_correo(datos.email)
    if datos.style_pref is not None and usuario.role == Rol.CLIENTE:
        usuario.style_pref = datos.style_pref.strip()[:200]
    if datos.new_password:
        validar_clave(datos.new_password, "La nueva contraseña debe tener al menos 8 caracteres")
        if not datos.current_password or not verificar_password(datos.current_password, usuario.password_hash):
            raise DatosInvalidos("La contraseña actual no es correcta")
        usuario.password_hash = hash_password(datos.new_password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflicto("Ese correo ya está registrado") from None
    db.refresh(usuario)
    return usuario


def asegurar_admin_inicial(db: Session) -> None:
    """Crea el administrador de ADMIN_EMAIL/ADMIN_PASSWORD si están definidos y aún no existe."""
    s = get_settings()
    if not s.admin_email or not s.admin_password:
        return
    correo = s.admin_email.strip().lower()
    if db.scalar(select(Usuario.id).where(Usuario.email == correo)):
        return
    db.add(Usuario(email=correo, full_name=s.admin_nombre, password_hash=hash_password(s.admin_password), role=Rol.ADMIN, policy_accepted_at=ahora_utc()))
    db.commit()


def solicitar_recuperacion(db: Session, correo: str) -> tuple[str, str] | None:
    """Crea un enlace de un solo uso (30 min). Devuelve (correo, token) o None si no existe la cuenta.
    El endpoint responde igual en ambos casos para no revelar qué correos están registrados."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == correo.strip().lower()))
    if not usuario or not usuario.is_active:
        return None
    token, hash_ = nuevo_token_un_uso()
    usuario.reset_token_hash = hash_
    usuario.reset_expires_at = ahora_utc() + timedelta(minutes=MINUTOS_RECUPERACION)
    db.commit()
    return usuario.email, token


def restablecer(db: Session, token: str, clave: str) -> None:
    validar_clave(clave)
    usuario = db.scalar(select(Usuario).where(Usuario.reset_token_hash == hash_token(token),
                                              Usuario.reset_expires_at > ahora_utc()))
    if not usuario:
        raise DatosInvalidos("El enlace venció o ya fue usado. Pide uno nuevo.")
    usuario.password_hash = hash_password(clave)
    usuario.reset_token_hash = usuario.reset_expires_at = None
    db.commit()
