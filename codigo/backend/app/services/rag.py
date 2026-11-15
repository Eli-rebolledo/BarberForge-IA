"""Base de conocimiento del asistente: documentos en la base de datos, indexado con embeddings y búsqueda
con filtro por rol. Lo que el administrador le enseña (preguntas que no sabía) también vive aquí."""
import logging
import re
import unicodedata

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.db import es_postgres
from app.models import DocumentoConocimiento, FragmentoConocimiento, Rol, Servicio, Usuario
from app.models.conocimiento import NIVEL_INTERNO, NIVEL_PUBLICO, TIPO_APRENDIDO, TIPO_DOCUMENTO
from app.services import ia

log = logging.getLogger(__name__)

TIPO_SERVICIO = "servicio"
TIPO_PREGUNTA = "pregunta"  # solo la pregunta aprendida: sirve para reconocerla rápido, no para el contexto
TAMANO_FRAGMENTO = 700
# Distancia coseno máxima para considerar que dos preguntas son «la misma» (nomic-embed-text).
DISTANCIA_MISMA_PREGUNTA = 0.08
PARECIDO_MINIMO = 0.6  # proporción de palabras en común (sin acentos ni palabras vacías)

# Conocimiento inicial: se carga una sola vez (migración 005). Después el administrador lo edita en el panel.
DOCUMENTOS_INICIALES = [
    ("Preguntas frecuentes", NIVEL_PUBLICO,
     "Horario: lunes a sábado de 9:00 a 17:00, domingos cerrado. Dirección: Popayán, Cauca. "
     "Se agenda desde la plataforma o por este chat."),
    ("Políticas de la barbería", NIVEL_PUBLICO,
     "Puedes cancelar desde Mis citas o pidiéndoselo a este asistente (escribe «cancelar cita»). "
     "Si no confirmas el recordatorio enviado 40 minutos antes, la cita se cancela a los 15 minutos y la "
     "franja queda libre."),
    ("Cómo agendar", NIVEL_PUBLICO,
     "Puedes agendar en la plataforma eligiendo uno o varios servicios, tu barbero y una hora del calendario. "
     "Si llegas al local y está ocupado, el barbero o el administrador pueden crear la cita por ti sin que "
     "tengas que registrarte. Los recordatorios por correo son automáticos."),
    ("Pagos y datos", NIVEL_PUBLICO,
     "No pedimos cédula para agendar: solo nombre y correo. Tus datos se tratan según la Ley 1581 de 2012."),
    ("Guía de estilos", NIVEL_PUBLICO,
     "Fade bajo para rostro ovalado; barba perfilada con navaja para rostro redondo. "
     "Usa producto mate y repite el corte cada dos semanas."),
    ("Manual de procedimientos", NIVEL_INTERNO,
     "Higiene: desinfectar máquinas y peines con barbicida entre clientes y cambiar la capa. "
     "Caja: registrar cada servicio completado antes de llamar al siguiente cliente."),
    ("Limpieza y desinfección de máquinas", NIVEL_INTERNO,
     "Entre cada cliente: 1) Desconecta o apaga la máquina. 2) Retira el pelo de las cuchillas con el cepillo "
     "de cerdas duras. 3) Rocía desinfectante en aerosol para cuchillas (tipo Clippercide) por ambos lados y "
     "deja actuar el tiempo que indica la etiqueta. 4) Seca con una toalla de papel limpia. "
     "Al final del día: desmonta la cuchilla, sumérgela en barbicida (sin el motor) el tiempo indicado por el "
     "fabricante, sécala bien, ponle 2 o 3 gotas de aceite lubricante sobre los dientes, enciende la máquina "
     "unos segundos para que el aceite se reparta y limpia el exceso. Los peines y cepillos van al barbicida; "
     "cambia el líquido cada día o cuando se vea turbio."),
    ("Mantenimiento de cuchillas y navajas", NIVEL_INTERNO,
     "Lubrica las cuchillas de las máquinas a diario; si tiran del pelo o se calientan, revisa la alineación "
     "y el aceite. Las hojas de navaja son de un solo uso: cámbialas con cada cliente y deséchalas en el "
     "guardián de cortopunzantes, nunca en la basura común. Las tijeras se limpian con alcohol y se secan."),
    ("Cierre del puesto de trabajo", NIVEL_INTERNO,
     "Al cerrar: barre el pelo del puesto, desinfecta silla, apoyacabezas y mesón, lava capas y toallas, "
     "deja las máquinas limpias y lubricadas y marca en el sistema las citas completadas o no asistidas."),
]

_PALABRAS_VACIAS = set(
    "a al algo como con cual cuales cuando de del el ella en es esta este hay la las lo los me mi mis no o "
    "para pero por que quien se si su sus te tengo tiene tienen tu tus un una uno unos y ya yo usted ustedes "
    "puedo puede pueden quiero hola favor gracias donde cuanto cuanta cuantos cuantas cual cuales cuando "
    "hacer hace hago debo debe deben deberia sirve son estan algun alguna algunos esto eso".split())


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni signos: «¿Cuál es el HORARIO?» -> «cual es el horario»."""
    sin_acentos = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"[a-z0-9ñ]+", sin_acentos))


def _palabras(texto: str) -> set[str]:
    return {p for p in normalizar(texto).split() if len(p) > 2 and p not in _PALABRAS_VACIAS}


def _raiz(palabra: str) -> str:
    """Raíz aproximada: sin plural y sin las últimas letras («pagos» -> «pago», «limpieza» -> «limpie»)."""
    if len(palabra) > 4 and palabra.endswith("s"):
        palabra = palabra[:-1]
    return palabra[:max(5, len(palabra) - 2)]


def parecido(a: str, b: str) -> float:
    pa, pb = {_raiz(p) for p in _palabras(a)}, {_raiz(p) for p in _palabras(b)}
    return len(pa & pb) / len(pa | pb) if pa and pb else 0.0


def _texto_servicio(s: Servicio) -> str:
    precio = f"{s.price_cop:,}".replace(",", ".")
    return (f"{s.name} ({s.service_type}): {s.description} Precio ${precio} COP. "
            f"Duración {s.duration_minutes} minutos.")


def trocear(texto: str, tamano: int = TAMANO_FRAGMENTO) -> list[str]:
    """Divide un documento largo por párrafos en fragmentos de hasta `tamano` caracteres."""
    partes, actual = [], ""
    for parrafo in [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]:
        while len(parrafo) > tamano:  # párrafo enorme: se corta por frases
            corte = parrafo.rfind(". ", 0, tamano)
            corte = corte + 1 if corte > tamano // 3 else tamano
            partes.append(parrafo[:corte].strip())
            parrafo = parrafo[corte:].strip()
        if actual and len(actual) + len(parrafo) + 2 > tamano:
            partes.append(actual)
            actual = parrafo
        else:
            actual = f"{actual}\n\n{parrafo}" if actual else parrafo
    if actual:
        partes.append(actual)
    return partes or [texto.strip()]


def sembrar_documentos(db: Session) -> None:
    """Carga el conocimiento inicial si la tabla está vacía (pruebas y bases nuevas)."""
    if db.scalar(select(func.count(DocumentoConocimiento.id))):
        return
    db.add_all(DocumentoConocimiento(title=t, access_level=n, content=c) for t, n, c in DOCUMENTOS_INICIALES)
    db.commit()


class _Embeddings:
    """Calcula embeddings y deja de intentarlo en cuanto Ollama falla (no insiste en cada fragmento)."""

    def __init__(self) -> None:
        self.ok = True

    def __call__(self, texto: str) -> list[float] | None:
        vector = ia.embedding(texto) if self.ok else None
        self.ok = self.ok and vector is not None
        return vector


def _fragmentos_de(doc: DocumentoConocimiento, emb: _Embeddings) -> list[FragmentoConocimiento]:
    if not doc.is_active:
        return []
    if doc.kind == TIPO_APRENDIDO and doc.question:
        contenido = f"Pregunta: {doc.question}\nRespuesta: {doc.content}"
        return [FragmentoConocimiento(doc_id=doc.id, kind=TIPO_APRENDIDO, source=doc.title, content=contenido,
                                      access_level=doc.access_level, embedding=emb(contenido)),
                FragmentoConocimiento(doc_id=doc.id, kind=TIPO_PREGUNTA, source=doc.title, content=doc.question,
                                      access_level=doc.access_level, embedding=emb(doc.question))]
    return [FragmentoConocimiento(doc_id=doc.id, kind=TIPO_DOCUMENTO, source=doc.title, content=parte,
                                  access_level=doc.access_level, embedding=emb(f"{doc.title}. {parte}"))
            for parte in trocear(doc.content)]


def reindexar(db: Session) -> bool:
    """Reconstruye todo el índice. Devuelve False si algún embedding no se pudo calcular (se reintenta luego);
    sin embeddings la búsqueda por palabras clave sigue funcionando."""
    emb = _Embeddings()
    from app.services import barberia  # import local: barberia depende de servicios y barberos
    m = barberia.marca(db)
    datos = f"{m.nombre}. Dirección: {m.direccion}. Horario: {m.horario}. {m.descripcion}"
    fragmentos = [FragmentoConocimiento(kind=TIPO_SERVICIO, source="Datos de la barbería", content=datos,
                                        access_level=NIVEL_PUBLICO, embedding=emb(datos))]
    fragmentos += [FragmentoConocimiento(kind=TIPO_SERVICIO, source="Catálogo de servicios", content=_texto_servicio(s),
                                         access_level=NIVEL_PUBLICO, embedding=emb(_texto_servicio(s)))
                   for s in db.scalars(select(Servicio).where(Servicio.is_active).order_by(Servicio.id))]
    for doc in db.scalars(select(DocumentoConocimiento).order_by(DocumentoConocimiento.id)):
        fragmentos += _fragmentos_de(doc, emb)
    db.execute(delete(FragmentoConocimiento))
    db.add_all(fragmentos)
    db.commit()
    return emb.ok


def indexar_documento(db: Session, doc: DocumentoConocimiento) -> bool:
    """Actualiza solo los fragmentos de un documento (al crearlo, editarlo o enseñar una respuesta)."""
    emb = _Embeddings()
    db.execute(delete(FragmentoConocimiento).where(FragmentoConocimiento.doc_id == doc.id))
    db.add_all(_fragmentos_de(doc, emb))
    db.commit()
    return emb.ok


def quitar_documento(db: Session, doc_id: int) -> None:
    db.execute(delete(FragmentoConocimiento).where(FragmentoConocimiento.doc_id == doc_id))


def reindexar_en_segundo_plano() -> None:
    """Para BackgroundTasks: abre su propia sesión y nunca propaga errores."""
    from app import db as bd
    try:
        with bd.SessionLocal() as db:
            reindexar(db)
    except Exception:  # noqa: BLE001 - una falla del indexado no debe afectar la petición
        log.exception("No se pudo reindexar el asistente")


def niveles_para(usuario: Usuario | None) -> list[str]:
    """Filtro por rol: solo barberos y administradores ven los documentos internos."""
    if usuario and usuario.role in (Rol.BARBERO, Rol.ADMIN):
        return [NIVEL_PUBLICO, NIVEL_INTERNO]
    return [NIVEL_PUBLICO]


def buscar(db: Session, pregunta: str, niveles: list[str], limite: int = 3) -> list[FragmentoConocimiento]:
    """Búsqueda semántica con pgvector; si no hay embeddings, búsqueda por palabras clave."""
    base = select(FragmentoConocimiento).where(FragmentoConocimiento.access_level.in_(niveles),
                                               FragmentoConocimiento.kind != TIPO_PREGUNTA)
    resultados: list[FragmentoConocimiento] = []
    if es_postgres(db):
        vector = ia.embedding(pregunta)
        if vector:
            resultados = list(db.scalars(
                base.where(FragmentoConocimiento.embedding.is_not(None))
                .order_by(FragmentoConocimiento.embedding.cosine_distance(vector)).limit(limite)))
    # Raíces de las palabras («limpio» -> «limpi» encuentra «limpieza»), sin acentos y tal como se escribieron.
    raices = {_raiz(p) for p in sorted(_palabras(pregunta), key=len, reverse=True)[:6]}
    originales = {_raiz(w) for w in re.findall(r"\w{3,}", pregunta.lower()) if _raiz(normalizar(w)) in raices}
    if not resultados and raices:
        candidatos = list(db.scalars(base.where(
            or_(*[func.lower(FragmentoConocimiento.content + " " + FragmentoConocimiento.source).like(f"%{r}%")
                  for r in raices | originales]))))

        def puntaje(c: FragmentoConocimiento) -> int:
            titulo, contenido = normalizar(c.source), normalizar(c.content)
            return sum(3 * (r in titulo) + min(contenido.count(r), 3) for r in raices)

        candidatos.sort(key=puntaje, reverse=True)
        resultados = candidatos[:limite]
    return resultados


def cobertura(pregunta: str, fragmento: FragmentoConocimiento) -> float:
    """Qué parte de las palabras de la pregunta aparece en el fragmento (0 a 1)."""
    raices = {_raiz(p) for p in _palabras(pregunta)}
    texto = normalizar(fragmento.source + " " + fragmento.content)
    return sum(r in texto for r in raices) / len(raices) if raices else 0.0


def texto_para_mostrar(fragmento: FragmentoConocimiento) -> str:
    """Contenido legible del fragmento (de lo aprendido se muestra solo la respuesta)."""
    if fragmento.kind == TIPO_APRENDIDO and "\nRespuesta: " in fragmento.content:
        return fragmento.content.split("\nRespuesta: ", 1)[1]
    return fragmento.content


def respuesta_aprendida(db: Session, pregunta: str, niveles: list[str]) -> DocumentoConocimiento | None:
    """Reconoce una pregunta que el administrador ya enseñó. La respuesta guardada se le da a llama3 como
    respuesta oficial para que la redacte; si la IA no responde, se usa tal cual."""
    aprendidos = list(db.scalars(select(DocumentoConocimiento).where(
        DocumentoConocimiento.kind == TIPO_APRENDIDO, DocumentoConocimiento.is_active,
        DocumentoConocimiento.access_level.in_(niveles))))
    if not aprendidos:
        return None
    clave = normalizar(pregunta)
    mejor = max(aprendidos, key=lambda d: (normalizar(d.question or "") == clave, parecido(pregunta, d.question or "")))
    if normalizar(mejor.question or "") == clave or parecido(pregunta, mejor.question or "") >= PARECIDO_MINIMO:
        return mejor
    if es_postgres(db):
        vector = ia.embedding(pregunta)
        if vector:
            distancia = FragmentoConocimiento.embedding.cosine_distance(vector)
            fila = db.execute(select(FragmentoConocimiento.doc_id, distancia).where(
                FragmentoConocimiento.kind == TIPO_PREGUNTA, FragmentoConocimiento.access_level.in_(niveles),
                FragmentoConocimiento.embedding.is_not(None)).order_by(distancia).limit(1)).first()
            if fila and fila[1] is not None and fila[1] <= DISTANCIA_MISMA_PREGUNTA:
                return db.get(DocumentoConocimiento, fila[0])
    return None
