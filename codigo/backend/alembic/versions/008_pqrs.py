"""PQRS (feature 012, asistente de voz): peticiones, quejas, reclamos y sugerencias.

Idempotente. Revision ID: 008  Revises: 007
"""
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS pqrs (
            id serial PRIMARY KEY,
            user_id integer REFERENCES users(id) ON DELETE SET NULL,
            tipo text NOT NULL,
            descripcion text NOT NULL,
            resumen text,
            canal text NOT NULL DEFAULT 'voz',
            estado text NOT NULL DEFAULT 'abierta',
            created_at timestamptz NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pqrs_creada ON pqrs (created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pqrs")
