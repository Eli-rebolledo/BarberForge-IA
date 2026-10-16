"""Importa todos los modelos para que queden registrados en Base.metadata (Alembic y pruebas)."""
from app.models.barberia import AjustesBarberia
from app.models.barbero_servicio import barbero_servicio
from app.models.chat import MensajeChat
from app.models.cita import Cita, cita_servicio
from app.models.conocimiento import DocumentoConocimiento, FragmentoConocimiento, PreguntaPendiente
from app.models.disponibilidad import Disponibilidad
from app.models.servicio import Servicio
from app.models.usuario import Rol, Usuario

__all__ = ["AjustesBarberia", "Cita", "Disponibilidad", "DocumentoConocimiento", "FragmentoConocimiento", "MensajeChat", "PreguntaPendiente",
           "Rol", "Servicio", "Usuario", "barbero_servicio", "cita_servicio"]
