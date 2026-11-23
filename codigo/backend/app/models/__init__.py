"""Importa todos los modelos para que queden registrados en Base.metadata (Alembic y pruebas)."""
from app.models.barberia import AjustesBarberia
from app.models.barbero_servicio import barbero_servicio
from app.models.chat import MensajeChat
from app.models.cierre import AusenciaBarbero, DiaCerrado
from app.models.cita import Cita, cita_servicio
from app.models.conocimiento import DocumentoConocimiento, FragmentoConocimiento, PreguntaPendiente
from app.models.disponibilidad import Disponibilidad
from app.models.modelo_ml import ModeloML
from app.models.pqrs import Pqrs
from app.models.servicio import Servicio
from app.models.usuario import Rol, Usuario

__all__ = ["AjustesBarberia", "AusenciaBarbero", "Cita", "DiaCerrado", "Disponibilidad", "DocumentoConocimiento",
           "FragmentoConocimiento", "MensajeChat", "ModeloML", "PreguntaPendiente", "Pqrs", "Rol", "Servicio", "Usuario",
           "barbero_servicio", "cita_servicio"]
