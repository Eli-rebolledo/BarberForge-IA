"""Predicción de inasistencias (feature 011).

- appointments.created_at: cuándo se agendó (para calcular la anticipación). Las citas que ya existían quedan
  en nulo a propósito: ponerles la fecha de hoy inventaría una anticipación falsa.
- appointments.no_show_risk: probabilidad de inasistencia calculada al agendar (0 a 1).
- appointments.early_reminder_sent_at: cuándo salió el aviso extra de 60 minutos (solo citas de riesgo alto).
- ml_models: modelos reentrenados con citas reales, firmados.

Idempotente. Revision ID: 007  Revises: 006
"""
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS created_at timestamptz")
    op.execute("ALTER TABLE appointments ALTER COLUMN created_at SET DEFAULT now()")
    op.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS no_show_risk double precision")
    op.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS early_reminder_sent_at timestamptz")
    op.execute("""
        CREATE TABLE IF NOT EXISTS ml_models (
            id serial PRIMARY KEY,
            name text NOT NULL DEFAULT 'inasistencia',
            version text NOT NULL,
            origin text NOT NULL,
            algorithm text NOT NULL,
            metrics_json text NOT NULL DEFAULT '{}',
            content bytea NOT NULL,
            signature text NOT NULL,
            is_active boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now()
        )""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ml_models")
    op.execute("ALTER TABLE appointments DROP COLUMN IF EXISTS early_reminder_sent_at")
    op.execute("ALTER TABLE appointments DROP COLUMN IF EXISTS no_show_risk")
    op.execute("ALTER TABLE appointments DROP COLUMN IF EXISTS created_at")
