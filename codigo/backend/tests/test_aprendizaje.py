from app.models import MensajeChat, PreguntaPendiente
from app.services import rag
from tests.conftest import token


def _chat(client, mensaje, cab=None):
    r = client.post("/api/chat", json={"message": mensaje}, headers=cab or {})
    assert r.status_code == 200, r.text
    return r.json()


def test_el_asistente_aprende_lo_que_no_sabe(client, catalogo, db, monkeypatch):
    rag.reindexar(db)
    # El modelo encuentra «Pagos y datos» pero ahí no dice nada de Nequi: responde que no tiene la información.
    monkeypatch.setattr("app.services.ia.generar", lambda _p: "No tengo esa información.")
    cliente, admin = token(client, "ana@correo.co"), token(client, "admin@correo.co")
    pregunta = "¿Aceptan pagos con Nequi?"
    assert "Todavía no sé" in _chat(client, pregunta, cliente)["reply"]
    _chat(client, "aceptan pagos con nequi")  # un visitante pregunta lo mismo: se suma, no se duplica
    pendientes = client.get("/api/assistant/questions", headers=admin).json()
    assert len(pendientes) == 1 and pendientes[0]["times_asked"] == 2 and pendientes[0]["access_level"] == "public"

    r = client.post(f"/api/assistant/questions/{pendientes[0]['id']}/answer", headers=admin,
                    json={"answer": "Sí, recibimos Nequi, Daviplata y efectivo."})
    assert r.status_code == 200 and r.json()["kind"] == "aprendido"
    assert client.get("/api/assistant/questions", headers=admin).json() == []

    # Quien preguntó encuentra la respuesta en su chat.
    ultimo = client.get("/api/chat/history", headers=cliente).json()["messages"][-1]
    assert "Nequi, Daviplata" in ultimo["text"]
    # Y la próxima vez responde al instante desde la base de datos.
    r = _chat(client, "¿aceptan pago por Nequi?")
    assert "Daviplata" in r["reply"] and r["sources"] == ["Respuestas aprendidas"]


def test_respuesta_que_no_sirvio_queda_por_aprender(client, catalogo, db):
    rag.reindexar(db)
    cab = token(client, "ana@correo.co")
    r = _chat(client, "¿Cuál es el horario?", cab)
    o = client.post("/api/chat/feedback", headers=cab, json={"message_id": r["id"], "useful": False}).json()
    assert "mejor respuesta" in o["message"]
    p = db.query(PreguntaPendiente).one()
    assert p.reason == "no_util" and "lunes a sábado" in p.bot_answer.lower()
    assert db.get(MensajeChat, r["id"]).feedback == -1
    # Un visitante también puede calificar.
    assert client.post("/api/chat/feedback", json={"useful": True, "question": "x", "answer": "y"}).status_code == 200
    # Nadie puede calificar mensajes ajenos.
    otro = token(client, "carlos@demo.co")
    assert client.post("/api/chat/feedback", headers=otro, json={"message_id": r["id"], "useful": False}).status_code == 404


def test_pregunta_interna_del_barbero_se_ensena_solo_al_personal(client, catalogo, db):
    barbero, admin = token(client, "carlos@demo.co"), token(client, "admin@correo.co")
    _chat(client, "¿Cada cuánto se cambia el aceite del compresor?", barbero)
    p = client.get("/api/assistant/questions", headers=admin).json()[0]
    assert p["access_level"] == "internal" and p["asked_by_role"] == "barbero"
    client.post(f"/api/assistant/questions/{p['id']}/answer", headers=admin, json={"answer": "Cada 3 meses."})
    assert "Cada 3 meses" in _chat(client, "cada cuanto se cambia el aceite del compresor", barbero)["reply"]
    assert "Cada 3 meses" not in _chat(client, "cada cuanto se cambia el aceite del compresor")["reply"]


def test_documentos_de_conocimiento(client, catalogo, db):
    admin = token(client, "admin@correo.co")
    assert client.get("/api/assistant/knowledge", headers=token(client, "carlos@demo.co")).status_code == 403
    r = client.post("/api/assistant/knowledge", headers=admin, json={
        "title": "Esterilización de toallas", "access_level": "internal",
        "content": "Las toallas se lavan a 60 grados con hipoclorito y se secan al sol."})
    doc = r.json()
    assert r.status_code == 200 and doc["kind"] == "documento"
    barbero = token(client, "carlos@demo.co")
    assert "Esterilización de toallas" in _chat(client, "¿cómo lavo las toallas con hipoclorito?", barbero)["sources"]
    doc["content"] = "Las toallas se lavan con detergente enzimático."
    assert client.put(f"/api/assistant/knowledge/{doc['id']}", headers=admin, json=doc).status_code == 200
    assert "enzimático" in _chat(client, "¿cómo lavo las toallas con detergente?", barbero)["reply"]
    assert client.delete(f"/api/assistant/knowledge/{doc['id']}", headers=admin).status_code == 200
    assert "Esterilización de toallas" not in _chat(client, "toallas detergente enzimatico", barbero).get("sources", [])


def test_trocear_documentos_largos():
    texto = "\n\n".join(f"Párrafo {i}. " + "palabra " * 60 for i in range(6))
    partes = rag.trocear(texto, 700)
    assert len(partes) > 1 and all(len(p) <= 700 for p in partes)
