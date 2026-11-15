"""Identidad de la barbería editable desde «Ajustes»: nombre, dirección, horario, descripción y logo.

Mientras el administrador no la edite se siguen usando BARBERIA_NOMBRE y BARBERIA_DIRECCION del .env.

Idempotente. Revision ID: 006  Revises: 005
"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS shop_settings (
            id integer PRIMARY KEY,
            name text,
            address text,
            hours text,
            description text,
            logo bytea,
            logo_mime text,
            logo_updated_at timestamptz
        )""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS shop_settings")
