"""Festivos (días sin atención, RF09), ausencias de barberos (RF17) y respuesta de las PQRS desde el panel.

Idempotente. Revision ID: 009  Revises: 008
"""
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS closed_days (
            id serial PRIMARY KEY,
            day date NOT NULL UNIQUE,
            motivo text NOT NULL DEFAULT 'Festivo',
            created_at timestamptz NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS barber_absences (
            id serial PRIMARY KEY,
            barber_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date_from date NOT NULL,
            date_to date NOT NULL,
            motivo text NOT NULL DEFAULT 'Ausencia',
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_ausencia_rango CHECK (date_to >= date_from)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ausencias_barbero ON barber_absences (barber_id, date_from, date_to)")
    op.execute("ALTER TABLE pqrs ADD COLUMN IF NOT EXISTS respuesta text")
    op.execute("ALTER TABLE pqrs ADD COLUMN IF NOT EXISTS respondida_at timestamptz")


def downgrade() -> None:
    op.execute("ALTER TABLE pqrs DROP COLUMN IF EXISTS respondida_at")
    op.execute("ALTER TABLE pqrs DROP COLUMN IF EXISTS respuesta")
    op.execute("DROP TABLE IF EXISTS barber_absences")
    op.execute("DROP TABLE IF EXISTS closed_days")
