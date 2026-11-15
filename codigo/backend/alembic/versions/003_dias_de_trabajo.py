"""Días de trabajo por barbero (users.work_days).

Idempotente: solo agrega la columna si falta. Los barberos existentes quedan de lunes a sábado.

Revision ID: 003
Revises: 002
Create Date: 2026-11-11
"""
import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columnas = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "work_days" not in columnas:
        op.add_column("users", sa.Column("work_days", sa.Text(), nullable=False, server_default="0,1,2,3,4,5"))


def downgrade() -> None:
    op.drop_column("users", "work_days")
