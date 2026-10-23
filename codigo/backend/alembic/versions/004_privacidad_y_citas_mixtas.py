"""Menos datos personales, citas sin cuenta, varios servicios por cita y recuperación de contraseña.

- Quita users.id_type / users.id_number (no son necesarios para agendar: minimización de datos).
- appointments: client_id opcional + guest_*, precio y duración de la cita, created_by_id.
- Tabla appointment_services (varios servicios por cita).
- users.reset_token_hash / reset_expires_at para recuperar la contraseña.

Idempotente. Revision ID: 004  Revises: 003
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS id_number")  # también elimina el UNIQUE que la usaba
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS id_type")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_hash text")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_expires_at timestamptz")

    op.execute("ALTER TABLE appointments ALTER COLUMN client_id DROP NOT NULL")
    for col in ("guest_name text", "guest_phone text", "guest_email text", "created_by_id integer REFERENCES users(id)",
                "price_cop integer NOT NULL DEFAULT 0", "duration_minutes integer NOT NULL DEFAULT 30"):
        op.execute(f"ALTER TABLE appointments ADD COLUMN IF NOT EXISTS {col}")
    op.execute("UPDATE appointments a SET price_cop = s.price_cop, duration_minutes = s.duration_minutes "
               "FROM services s WHERE s.id = a.service_id AND a.price_cop = 0")

    op.execute("CREATE TABLE IF NOT EXISTS appointment_services ("
               "appointment_id integer NOT NULL REFERENCES appointments(id), "
               "service_id integer NOT NULL REFERENCES services(id), "
               "PRIMARY KEY (appointment_id, service_id))")
    op.execute("INSERT INTO appointment_services(appointment_id, service_id) "
               "SELECT id, service_id FROM appointments ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS appointment_services")
