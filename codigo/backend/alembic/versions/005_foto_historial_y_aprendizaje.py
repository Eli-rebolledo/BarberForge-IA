"""Foto de barberos, historial del chat y aprendizaje del asistente.

- users.photo / photo_mime / photo_updated_at: foto del barbero.
- chat_messages: conversación guardada de cada usuario registrado.
- knowledge_docs: lo que sabe el asistente (antes estaba fijo en el código); se carga el conocimiento inicial
  más procedimientos internos de limpieza de máquinas.
- unanswered_questions: preguntas que no supo responder, para que el administrador se las enseñe.
- knowledge_chunks.doc_id / kind: cada fragmento sabe de qué documento viene.

Idempotente. Revision ID: 005  Revises: 004
"""
import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

DOCUMENTOS = sa.table("knowledge_docs", sa.column("title", sa.Text), sa.column("content", sa.Text),
                      sa.column("access_level", sa.Text))


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS photo bytea")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_mime text")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_updated_at timestamptz")

    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_docs (
            id serial PRIMARY KEY,
            title text NOT NULL,
            content text NOT NULL,
            access_level text NOT NULL DEFAULT 'public',
            kind text NOT NULL DEFAULT 'documento',
            question text,
            is_active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""")
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS "
               "doc_id integer REFERENCES knowledge_docs(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'documento'")

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id serial PRIMARY KEY,
            user_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            sender text NOT NULL,
            content text NOT NULL,
            sources json,
            options json,
            question text,
            can_rate integer NOT NULL DEFAULT 0,
            feedback smallint,
            created_at timestamptz NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_usuario ON chat_messages (user_id, id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS unanswered_questions (
            id serial PRIMARY KEY,
            question text NOT NULL,
            normalized text NOT NULL,
            access_level text NOT NULL DEFAULT 'public',
            asked_by_role text NOT NULL DEFAULT 'visitante',
            user_id integer REFERENCES users(id) ON DELETE SET NULL,
            reason text NOT NULL DEFAULT 'sin_respuesta',
            bot_answer text,
            times_asked integer NOT NULL DEFAULT 1,
            status text NOT NULL DEFAULT 'pendiente',
            doc_id integer REFERENCES knowledge_docs(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unanswered_questions_normalized ON unanswered_questions (normalized)")

    # Conocimiento inicial (solo si la tabla está vacía). Al arrancar, la API reindexa el asistente.
    if not op.get_bind().execute(sa.text("SELECT count(*) FROM knowledge_docs")).scalar():
        from app.services.rag import DOCUMENTOS_INICIALES
        op.bulk_insert(DOCUMENTOS, [{"title": t, "access_level": n, "content": c} for t, n, c in DOCUMENTOS_INICIALES])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS unanswered_questions")
    op.execute("DROP TABLE IF EXISTS chat_messages")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS doc_id")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS kind")
    op.execute("DROP TABLE IF EXISTS knowledge_docs")
    for col in ("photo", "photo_mime", "photo_updated_at"):
        op.execute(f"ALTER TABLE users DROP COLUMN IF EXISTS {col}")
