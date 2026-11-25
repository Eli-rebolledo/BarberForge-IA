"""El servicio completo con Whisper y la API simulados."""
import httpx
from fastapi.testclient import TestClient

from app import enrutador, transcripcion
from app.main import app

cliente = TestClient(app)


class Respuesta:
    def __init__(self, datos, status=200):
        self.datos, self.status_code = datos, status

    def json(self):
        return self.datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


def test_nota_de_voz_que_agenda(monkeypatch):
    llamadas = []
    monkeypatch.setattr(transcripcion, "transcribir", lambda audio: ("Quiero agendar una barba con Carlos", 3.2))

    def post(url, json=None, headers=None, timeout=None):
        llamadas.append((url, json, headers))
        return Respuesta({"reply": "¿Con qué barbero?", "sources": [], "options": [{"label": "Carlos Mena"}]})

    monkeypatch.setattr(enrutador.httpx, "post", post)
    r = cliente.post("/voz/", files={"audio": ("nota.webm", b"\x1a\x45", "audio/webm")},
                     data={"responder_con_voz": "false"}, headers={"Authorization": "Bearer abc"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["intencion"]["intencion"] == "agendar" and d["metodo_intencion"] == "reglas"
    assert llamadas[0][0] == "http://api.prueba/api/chat"
    assert llamadas[0][2] == {"Authorization": "Bearer abc"}
    assert d["respuesta"]["options"][0]["label"] == "Carlos Mena" and d["audio"] is None


def test_pqrs_por_voz_pasa_por_el_chat(monkeypatch):
    """La PQRS hablada va al chat con canal «voz»: si no trae el detalle, el asistente lo pide antes de radicar."""
    def post(url, json=None, headers=None, timeout=None):
        assert url.endswith("/api/chat") and json == {"message": "tengo una queja", "channel": "voz"}
        return Respuesta({"reply": "Para registrar tu queja, cuéntame en un solo mensaje qué pasó.", "sources": []})

    monkeypatch.setattr(enrutador.httpx, "post", post)
    r = cliente.post("/voz/texto", json={"texto": "tengo una queja"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["intencion"]["intencion"] == "pqrs" and d["respuesta"]["reply"].startswith("Para registrar tu queja")


def test_audio_vacio_o_api_caida(monkeypatch):
    def caida(*a, **k):
        raise httpx.ConnectError("sin API")

    assert cliente.post("/voz/", files={"audio": ("n.webm", b"", "audio/webm")}).status_code == 400
    monkeypatch.setattr(enrutador.httpx, "post", caida)
    assert cliente.post("/voz/texto", json={"texto": "¿Cuál es el horario?"}).status_code == 502


def test_health():
    assert cliente.get("/voz/health").json()["status"] == "ok"
