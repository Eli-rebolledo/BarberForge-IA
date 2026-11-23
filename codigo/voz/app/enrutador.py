"""Lleva la intención a la API existente de BarberForge: todo pasa por el chat (RAG, agendar, cancelar, mis citas y
PQRS). Una PQRS hablada también va al chat: si solo dice «tengo una queja», el asistente pregunta qué pasó antes de
radicarla, igual que en el chat escrito, y queda registrada con canal «voz».

No duplica nada: el agendamiento por voz pasa por el mismo servicio de citas, que calcula el riesgo de
inasistencia con el modelo de machine learning (feature 011)."""
import re
import unicodedata

import httpx

from app.config import config


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


# Lo que el chat de la API ya entiende (app/services/chat.py). Si la frase no lo trae, se le agrega.
CHAT_AGENDAR = re.compile(r"agendar|reservar|quiero una cita|sacar (una )?cita|pedir (una )?cita")
CHAT_CANCELAR = re.compile(r"(cancelar|anular|cancela|anula|cancelo)\b.*\b(cita|turno|reserva)s?")
# Copia de PQRS de app/services/chat.py: si la frase no lo trae, se le antepone el tipo («Petición: …»).
CHAT_PQRS = re.compile(r"\b(quejas?|quejarme|reclam\w*|petici[oó]n|peticiones|solicitud(es)?|sugerencias?|sugiero|"
                       r"sugerir|felicit\w*|pqrs?|quisiera pedir que|solicito que|me atendieron mal|mal servicio|"
                       r"mala atenci[oó]n|me trataron mal|inconformidad)\b")
NOMBRE_PQRS = {"peticion": "Petición", "queja": "Queja", "reclamo": "Reclamo", "sugerencia": "Sugerencia"}
CHAT_MIS_CITAS = re.compile(r"mis citas|mi agenda|mis turnos|mis pr[oó]ximas citas|pr[oó]ximas citas|mis reservas")


def mensaje_para_chat(texto: str, intencion: dict) -> str:
    """Frase que se le envía al chat de la API según la intención detectada."""
    t = texto.strip()
    bajo = t.lower()
    i = intencion["intencion"]
    if i == "agendar":
        extra = " ".join(x for x in (intencion.get("servicio"), f"con {intencion['barbero']}" if intencion.get("barbero")
                                     else None) if x)
        base = t if CHAT_AGENDAR.search(bajo) else f"agendar {t}"
        return f"{base} {extra}".strip() if extra and _sin_tildes(extra) not in _sin_tildes(base) else base
    if i == "cancelar":
        return t if CHAT_CANCELAR.search(bajo) else "cancelar cita"
    if i == "mis_citas":
        return t if CHAT_MIS_CITAS.search(bajo) else "mis citas"
    if i == "pqrs":  # el chat pide el detalle si falta y la radica con canal «voz»
        nombre = NOMBRE_PQRS.get(intencion.get("tipo_pqrs") or "queja", "Queja")
        return t if CHAT_PQRS.search(bajo) else f"{nombre}: {t}"
    if i == "saludo":
        return t or "hola"
    return t


def _cabeceras(autorizacion: str | None) -> dict:
    return {"Authorization": autorizacion} if autorizacion else {}


def chat(mensaje: str, autorizacion: str | None) -> dict:
    r = httpx.post(f"{config().api_url}/api/chat", json={"message": mensaje, "channel": "voz"},
                   headers=_cabeceras(autorizacion), timeout=240)
    r.raise_for_status()
    return r.json()


def responder(texto: str, intencion: dict, autorizacion: str | None) -> tuple[dict, str | None]:
    """Devuelve la respuesta (con la forma de la del chat) y el mensaje que se envió al chat."""
    mensaje = mensaje_para_chat(texto, intencion)
    return chat(mensaje, autorizacion), mensaje
