"""Aprendizaje del asistente: preguntas que no supo responder, respuestas que no sirvieron y lo que el
administrador le enseña. El modelo de IA no se reentrena: aprende porque lo enseñado entra en su base de
conocimiento (RAG) y, si alguien repite la pregunta, se responde directo desde la base de datos."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentoConocimiento, MensajeChat, PreguntaPendiente, Rol, Usuario
from app.models.conocimiento import NIVEL_INTERNO, NIVEL_PUBLICO, NIVELES, TIPO_APRENDIDO, TIPO_DOCUMENTO
from app.schemas.asistente import DocumentoIn, EnsenarIn
from app.services import rag
from app.services.errores import DatosInvalidos, NoEncontrado

LONGITUD_MINIMA = 4


def registrar_pendiente(db: Session, pregunta: str, usuario: Usuario | None, motivo: str = "sin_respuesta",
                        respuesta_bot: str | None = None) -> PreguntaPendiente | None:
    """Guarda la pregunta para que el administrador la enseñe. Si ya estaba pendiente, suma una vez más."""
    clave = rag.normalizar(pregunta)
    if len(clave) < LONGITUD_MINIMA:
        return None
    rol = usuario.role if usuario else "visitante"
    nivel = NIVEL_INTERNO if rol in (Rol.BARBERO, Rol.ADMIN) else NIVEL_PUBLICO
    existente = db.scalar(select(PreguntaPendiente).where(
        PreguntaPendiente.normalized == clave, PreguntaPendiente.status == "pendiente"))
    if existente:
        existente.times_asked += 1
        if motivo == "no_util":
            existente.reason, existente.bot_answer = motivo, respuesta_bot or existente.bot_answer
        if nivel == NIVEL_PUBLICO:  # si también la pregunta un cliente, la respuesta debe ser pública
            existente.access_level = NIVEL_PUBLICO
        db.commit()
        return existente
    nueva = PreguntaPendiente(question=pregunta.strip()[:500], normalized=clave, access_level=nivel,
                              asked_by_role=rol, user_id=usuario.id if usuario else None, reason=motivo,
                              bot_answer=(respuesta_bot or None) and respuesta_bot[:2000])
    db.add(nueva)
    db.commit()
    return nueva


def listar_pendientes(db: Session, estado: str = "pendiente") -> list[PreguntaPendiente]:
    return list(db.scalars(select(PreguntaPendiente).where(PreguntaPendiente.status == estado)
                           .order_by(PreguntaPendiente.times_asked.desc(), PreguntaPendiente.updated_at.desc())
                           .limit(200)))


def _pendiente(db: Session, pregunta_id: int) -> PreguntaPendiente:
    p = db.get(PreguntaPendiente, pregunta_id)
    if not p:
        raise NoEncontrado("Pregunta no encontrada")
    return p


def _nivel(nivel: str) -> str:
    if nivel not in NIVELES:
        raise DatosInvalidos("Visibilidad inválida")
    return nivel


def ensenar(db: Session, pregunta_id: int, datos: EnsenarIn) -> DocumentoConocimiento:
    """El administrador escribe la respuesta: queda como conocimiento aprendido y se avisa a quien preguntó."""
    p = _pendiente(db, pregunta_id)
    respuesta = datos.answer.strip()
    if len(respuesta) < 2:
        raise DatosInvalidos("Escribe la respuesta")
    pregunta = (datos.question or p.question).strip()[:500]
    doc = DocumentoConocimiento(title=(datos.title or "").strip()[:120] or pregunta[:120], content=respuesta,
                                access_level=_nivel(datos.access_level or p.access_level),
                                kind=TIPO_APRENDIDO, question=pregunta)
    db.add(doc)
    db.flush()
    # Otras preguntas pendientes iguales también quedan resueltas.
    for otra in db.scalars(select(PreguntaPendiente).where(PreguntaPendiente.normalized == p.normalized,
                                                          PreguntaPendiente.status == "pendiente")):
        otra.status, otra.doc_id = "respondida", doc.id
    p.status, p.doc_id = "respondida", doc.id
    if p.user_id:  # la persona lo verá en su chat la próxima vez que lo abra
        db.add(MensajeChat(user_id=p.user_id, sender="bot", question=p.question, can_rate=1,
                           sources=["Respuestas aprendidas"],
                           content=f"Ya aprendí la respuesta a lo que me preguntaste («{p.question}»):\n{respuesta}"))
    db.commit()
    rag.indexar_documento(db, doc)
    return doc


def descartar(db: Session, pregunta_id: int) -> None:
    p = _pendiente(db, pregunta_id)
    p.status = "descartada"
    db.commit()


# ---------- documentos de la base de conocimiento ----------

def listar_documentos(db: Session) -> list[DocumentoConocimiento]:
    return list(db.scalars(select(DocumentoConocimiento).order_by(
        DocumentoConocimiento.kind, DocumentoConocimiento.title)))


def _documento(db: Session, doc_id: int) -> DocumentoConocimiento:
    doc = db.get(DocumentoConocimiento, doc_id)
    if not doc:
        raise NoEncontrado("Documento no encontrado")
    return doc


def _validar(datos: DocumentoIn) -> tuple[str, str]:
    titulo, contenido = datos.title.strip(), datos.content.strip()
    if not titulo or len(contenido) < 2:
        raise DatosInvalidos("Escribe el título y el contenido")
    if len(contenido) > 20000:
        raise DatosInvalidos("El contenido es muy largo (máximo 20.000 caracteres)")
    return titulo[:120], contenido


def crear_documento(db: Session, datos: DocumentoIn) -> DocumentoConocimiento:
    titulo, contenido = _validar(datos)
    kind = TIPO_APRENDIDO if (datos.question or "").strip() else TIPO_DOCUMENTO
    doc = DocumentoConocimiento(title=titulo, content=contenido, access_level=_nivel(datos.access_level), kind=kind,
                                question=(datos.question or "").strip()[:500] or None)
    db.add(doc)
    db.commit()
    rag.indexar_documento(db, doc)
    return doc


def editar_documento(db: Session, doc_id: int, datos: DocumentoIn) -> DocumentoConocimiento:
    doc = _documento(db, doc_id)
    doc.title, doc.content = _validar(datos)
    doc.access_level = _nivel(datos.access_level)
    doc.is_active = datos.is_active
    if doc.kind == TIPO_APRENDIDO:
        doc.question = (datos.question or doc.question or "").strip()[:500] or doc.question
    db.commit()
    rag.indexar_documento(db, doc)
    return doc


def eliminar_documento(db: Session, doc_id: int) -> None:
    doc = _documento(db, doc_id)
    rag.quitar_documento(db, doc.id)
    for p in db.scalars(select(PreguntaPendiente).where(PreguntaPendiente.doc_id == doc.id)):
        p.doc_id = None
    db.delete(doc)
    db.commit()
