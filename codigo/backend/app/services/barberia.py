"""Ficha de la barbería: nombre, dirección, horario, descripción y logo. El administrador los edita desde
«Ajustes»; mientras no lo haga se usan los valores del archivo .env. El MVP atiende una sola barbería; la lista
se arma desde esta ficha para que sumar más barberías después no cambie la interfaz."""
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.tiempo import ahora_utc
from app.models import AjustesBarberia
from app.schemas.barbero import BarberoOut
from app.schemas.comun import BarberiaBase, BarberiaDetalle, BarberiaResumen, MarcaIn, MarcaOut
from app.schemas.servicio import ServicioOut
from app.services import barberos as barberos_srv
from app.services import imagenes
from app.services import servicios as servicios_srv
from app.services.errores import DatosInvalidos, NoEncontrado

ID_BARBERIA = 1
LOGO_MAX_BYTES = 1_000_000
HORARIO_INICIAL = "Lunes a sábado de 9:00 a 17:00 · domingos cerrado"
DESCRIPCION_INICIAL = ("Corte, barba y tratamiento capilar con agenda en línea, recordatorios por correo "
                       "y un asistente con IA que responde a cualquier hora.")


def _fila(db: Session) -> AjustesBarberia | None:
    return db.get(AjustesBarberia, ID_BARBERIA)


def _fila_o_nueva(db: Session) -> AjustesBarberia:
    fila = _fila(db)
    if fila is None:
        fila = AjustesBarberia(id=ID_BARBERIA)
        db.add(fila)
    return fila


def marca(db: Session) -> MarcaOut:
    s, f = get_settings(), _fila(db)
    return MarcaOut(nombre=(f and f.name) or s.barberia_nombre, direccion=(f and f.address) or s.barberia_direccion,
                    horario=(f and f.hours) or HORARIO_INICIAL, descripcion=(f and f.description) or DESCRIPCION_INICIAL,
                    logo_url=f.logo_url if f else None)


def nombre(db: Session) -> str:
    return marca(db).nombre


def ficha(db: Session) -> BarberiaBase:
    m = marca(db)
    return BarberiaBase(id=ID_BARBERIA, nombre=m.nombre, direccion=m.direccion, horario=m.horario,
                        descripcion=m.descripcion, logo_url=m.logo_url, buzon_url=get_settings().mailhog_url)


def actualizar(db: Session, datos: MarcaIn) -> MarcaOut:
    if not datos.nombre.strip():
        raise DatosInvalidos("Escribe el nombre de la barbería")
    fila = _fila_o_nueva(db)
    fila.name = datos.nombre.strip()[:80]
    fila.address = datos.direccion.strip()[:160] or None
    fila.hours = datos.horario.strip()[:160] or None
    fila.description = datos.descripcion.strip()[:400] or None
    db.commit()
    return marca(db)


def guardar_logo(db: Session, data_url: str) -> MarcaOut:
    datos, mime = imagenes.leer_data_url(data_url, LOGO_MAX_BYTES)
    fila = _fila_o_nueva(db)
    fila.logo, fila.logo_mime, fila.logo_updated_at = datos, mime, ahora_utc()
    db.commit()
    return marca(db)


def quitar_logo(db: Session) -> None:
    fila = _fila(db)
    if fila:
        fila.logo = fila.logo_mime = fila.logo_updated_at = None
        db.commit()


def leer_logo(db: Session) -> tuple[bytes, str]:
    fila = _fila(db)
    if not fila or not fila.logo_mime or not fila.logo:
        raise NoEncontrado("La barbería no tiene logo")
    return fila.logo, fila.logo_mime


def listar(db: Session) -> list[BarberiaResumen]:
    return [BarberiaResumen(**ficha(db).model_dump(), servicios=len(servicios_srv.listar(db)),
                            barberos=len(barberos_srv.listar(db)))]


def detalle(db: Session, barberia_id: int) -> BarberiaDetalle:
    if barberia_id != ID_BARBERIA:
        raise NoEncontrado("Barbería no encontrada")
    return BarberiaDetalle(
        **ficha(db).model_dump(),
        servicios=[ServicioOut.model_validate(s) for s in servicios_srv.listar(db)],
        barberos=[BarberoOut.model_validate(b) for b in barberos_srv.listar(db)])
