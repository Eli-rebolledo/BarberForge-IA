"""El asistente no pregunta por medios de pago: la base de conocimiento dice que la plataforma no maneja pagos.

Solo cambia el documento «Pagos y datos» si sigue con el texto original (si el administrador lo editó, se respeta).
El índice del asistente se reconstruye solo al arrancar la API. Revision ID: 010  Revises: 009
"""
import sqlalchemy as sa
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

ANTES = "No pedimos cédula para agendar: solo nombre y correo. Tus datos se tratan según la Ley 1581 de 2012."
AHORA = ("La plataforma no maneja pagos: agendar no cuesta nada y no se pide tarjeta, efectivo ni ningún medio de pago; "
         "el servicio se paga directamente en el local. No pedimos cédula para agendar: solo nombre y correo. "
         "Tus datos se tratan según la Ley 1581 de 2012.")


def _cambiar(de: str, a: str) -> None:
    op.get_bind().execute(sa.text("UPDATE knowledge_docs SET content = :a WHERE title = 'Pagos y datos' AND content = :de"),
                          {"a": a, "de": de})


def upgrade() -> None:
    _cambiar(ANTES, AHORA)


def downgrade() -> None:
    _cambiar(AHORA, ANTES)
