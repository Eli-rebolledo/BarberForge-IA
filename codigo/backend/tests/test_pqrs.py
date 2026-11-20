"""Feature 012: PQRS que llegan por el asistente de voz."""
from tests.conftest import token


def test_visitante_radica_una_queja_y_el_admin_la_ve(client, catalogo, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.services.correo.enviar", lambda destino, asunto, cuerpo: enviados.append((destino, asunto)) or True)
    r = client.post("/api/pqrs", json={"tipo": "queja", "descripcion": "Me atendieron tarde y de mal modo",
                                       "resumen": "Atención tarde"})
    assert r.status_code == 200, r.text
    assert r.json()["radicado"].startswith("PQRS-")
    assert "15 días hábiles" in r.json()["mensaje"]
    assert enviados and enviados[0][0] == "admin@correo.co"
    lista = client.get("/api/admin/pqrs", headers=token(client, "admin@correo.co")).json()
    assert lista[0]["tipo"] == "queja" and lista[0]["quien"] == "Visitante" and lista[0]["canal"] == "voz"


def test_cliente_radica_y_queda_su_nombre(client, catalogo):
    cab = token(client, "ana@correo.co")
    assert client.post("/api/pqrs", json={"tipo": "sugerencia", "descripcion": "Pongan música más suave"},
                       headers=cab).status_code == 200
    lista = client.get("/api/admin/pqrs", headers=token(client, "admin@correo.co")).json()
    assert lista[0]["quien"] == "Ana Ruiz"


def test_solo_el_admin_lista_y_se_validan_los_datos(client, catalogo):
    assert client.get("/api/admin/pqrs", headers=token(client, "ana@correo.co")).status_code == 403
    assert client.post("/api/pqrs", json={"tipo": "otra", "descripcion": "texto suficiente"}).status_code == 422
    assert client.post("/api/pqrs", json={"tipo": "queja", "descripcion": "ok"}).status_code == 422


def test_admin_responde_y_cierra_la_pqrs(client, catalogo, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.services.correo.enviar", lambda destino, asunto, cuerpo: enviados.append((destino, asunto, cuerpo)) or True)
    pid = client.post("/api/pqrs", json={"tipo": "reclamo", "descripcion": "Me cobraron dos veces el corte"},
                      headers=token(client, "ana@correo.co")).json()["id"]
    admin = token(client, "admin@correo.co")
    r = client.patch(f"/api/admin/pqrs/{pid}", json={"estado": "cerrada", "respuesta": "Ya te devolvimos los $25.000."},
                     headers=admin)
    assert r.status_code == 200, r.text
    destino, asunto, cuerpo = enviados[-1]
    assert destino == "ana@correo.co" and asunto.startswith("Respuesta a tu reclamo PQRS-") and "quedó cerrada" in cuerpo
    fila = client.get("/api/admin/pqrs", headers=admin).json()[0]
    assert fila["estado"] == "cerrada" and fila["respuesta"].startswith("Ya te devolvimos") and fila["respondida_at"]
    total = len(enviados)
    client.patch(f"/api/admin/pqrs/{pid}", json={"estado": "en_tramite"}, headers=admin)  # sin texto nuevo: no reenvía
    assert len(enviados) == total
    assert client.patch(f"/api/admin/pqrs/{pid}", json={"estado": "otro"}, headers=admin).status_code == 422
    assert client.patch(f"/api/admin/pqrs/{pid}", json={"estado": "cerrada"},
                        headers=token(client, "ana@correo.co")).status_code == 403
    assert client.patch("/api/admin/pqrs/999", json={"estado": "cerrada"}, headers=admin).status_code == 404


def test_pqrs_por_el_chat_escrito(client, catalogo, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.services.correo.enviar", lambda d, a, c: enviados.append(a) or True)
    cab = token(client, "ana@correo.co")
    # Con el detalle en el mismo mensaje: se radica de una vez y se avisa al administrador.
    r = client.post("/api/chat", json={"message": "Quiero poner una queja, el sábado esperé 40 minutos y nadie me avisó"},
                    headers=cab).json()
    assert "PQRS-" in r["reply"] and "15 días hábiles" in r["reply"]
    assert any("Nueva queja" in a for a in enviados)
    # Solo la intención: pide el detalle y el siguiente mensaje es el reclamo.
    r = client.post("/api/chat", json={"message": "quiero hacer un reclamo"}, headers=cab).json()
    assert r["reply"].startswith("Para registrar tu reclamo")
    r = client.post("/api/chat", json={"message": "Me cobraron dos veces el corte del martes"}, headers=cab).json()
    assert "Registré tu reclamo" in r["reply"]
    lista = client.get("/api/admin/pqrs", headers=token(client, "admin@correo.co")).json()
    assert {p["canal"] for p in lista} == {"chat"} and sorted(p["tipo"] for p in lista) == ["queja", "reclamo"]
    # Una pregunta sobre las PQRS no crea ninguna: la responde el asistente.
    client.post("/api/chat", json={"message": "¿Cuál es el plazo para responder una queja?"}, headers=cab)
    assert len(client.get("/api/admin/pqrs", headers=token(client, "admin@correo.co")).json()) == 2
    # Un visitante sin detalle recibe un ejemplo de cómo escribirla.
    r = client.post("/api/chat", json={"message": "tengo una sugerencia"}).json()
    assert "Escríbela completa en un solo mensaje" in r["reply"]


def test_pqrs_sin_detalle_pide_la_descripcion_antes_de_radicar(client, catalogo, monkeypatch):
    monkeypatch.setattr("app.services.correo.enviar", lambda *a: True)
    cab = token(client, "ana@correo.co")
    admin = token(client, "admin@correo.co")
    # «tengo una queja» o «quiero poner una queja por el mal servicio» no cuentan qué pasó: se pregunta primero.
    for frase in ("tengo una queja", "Quiero poner una queja por el mal servicio"):
        r = client.post("/api/chat", json={"message": frase}, headers=cab).json()
        assert r["reply"].startswith("Para registrar tu queja"), r["reply"]
    assert client.get("/api/admin/pqrs", headers=admin).json() == []
    # Si se arrepiente, no se registra nada.
    r = client.post("/api/chat", json={"message": "no"}, headers=cab).json()
    assert "no registré" in r["reply"]
    assert client.get("/api/admin/pqrs", headers=admin).json() == []
    # Por voz: también pregunta, y la descripción queda radicada con canal «voz».
    r = client.post("/api/chat", json={"message": "tengo una queja", "channel": "voz"}, headers=cab).json()
    assert r["reply"].startswith("Para registrar tu queja")
    r = client.post("/api/chat", json={"message": "El barbero llegó media hora tarde y no me avisaron",
                                       "channel": "voz"}, headers=cab).json()
    assert "PQRS-" in r["reply"]
    lista = client.get("/api/admin/pqrs", headers=admin).json()
    assert len(lista) == 1 and lista[0]["canal"] == "voz" and "media hora tarde" in lista[0]["descripcion"]


def test_detalle_de_pqrs():
    from app.services.chat import tiene_detalle
    assert not tiene_detalle("tengo una queja")
    assert not tiene_detalle("buenas, quiero hacer un reclamo sobre la atención")
    assert tiene_detalle("me cobraron dos veces el corte del martes")
    assert tiene_detalle("Quiero hacer un reclamo porque me cobraron de más")  # frases del Golden Dataset de voz
    assert tiene_detalle("Quiero poner una queja, el sábado esperé 40 minutos y nadie me avisó")


def test_otras_palabras_tambien_son_pqrs():
    from app.services.chat import PQRS, _tipo_pqrs
    casos = {"Quisiera pedir que me envíen la factura de mi último corte": "peticion",
             "Les quiero dar una felicitación a Carlos por el corte": "sugerencia",
             "Quiero hacer una solicitud": "peticion", "Quiero reclamar por un cobro": "reclamo",
             "Sugerencia: deberían abrir más temprano": "sugerencia", "Me trataron mal ayer": "queja"}
    for frase, tipo in casos.items():
        assert PQRS.search(frase.lower()) and _tipo_pqrs(frase.lower()) == tipo, frase
