from datetime import timedelta

from app.core.tiempo import hoy
from tests.conftest import token


def _franja(client, c, minutos=30):
    return client.get("/api/availability", params={"barber_id": c["barbero"].id, "minutes": minutos}).json()[0]


def test_cita_en_local_sin_cuenta_queda_confirmada(client, catalogo):
    f = _franja(client, catalogo)
    h = token(client, "carlos@demo.co")
    r = client.post("/api/appointments", headers=h, json={
        "service_ids": [catalogo["corte"].id], "date": f["date"], "time": f["time"], "guest_name": "Pedro Sin Cuenta"})
    assert r.status_code == 200, r.text
    cita = client.get("/api/appointments", headers=h).json()[0]
    assert cita["status"] == "confirmada" and cita["walk_in"] and cita["client"] == "Pedro Sin Cuenta"
    sin_cliente = client.post("/api/appointments", headers=h, json={
        "service_ids": [catalogo["corte"].id], "date": f["date"], "time": f["time"]})
    assert sin_cliente.status_code == 400


def test_varios_servicios_suman_y_bloquean_franjas(client, catalogo):
    ids = [catalogo["corte"].id, catalogo["barba"].id]  # 30 + 20 = 50 min -> 2 franjas de 30
    f = _franja(client, catalogo, 50)
    h = token(client, "ana@correo.co")
    assert client.post("/api/appointments", headers=h, json={
        "service_ids": ids, "barber_id": catalogo["barbero"].id, "date": f["date"], "time": f["time"]}).status_code == 200
    cita = client.get("/api/appointments", headers=h).json()[0]
    assert cita["price"] == 43000 and cita["duration"] == 50 and len(cita["services"]) == 2
    libres = client.get("/api/availability", params={"barber_id": catalogo["barbero"].id}).json()
    assert {"date": f["date"], "time": f["time"]} not in libres
    segunda = {"date": f["date"], "time": "09:30"} if f["time"] == "09:00" else None
    if segunda:
        assert segunda not in libres  # el segundo bloque quedó ocupado por la duración


def test_admin_calendario_fechas_y_estadisticas(client, catalogo):
    a = token(client, "admin@correo.co")
    d = str(hoy() + timedelta(days=20))
    r = client.post("/api/availability", headers=a, json={
        "barber_id": catalogo["barbero"].id, "date_from": d, "date_to": d, "dates": [d], "start": "09:00", "end": "10:00"})
    assert r.status_code == 200
    mes = d[:7]
    dias = client.get("/api/availability/calendar", headers=a, params={"barber_id": catalogo["barbero"].id, "month": mes}).json()
    assert any(x["date"] == d and x["total"] == 2 for x in dias)
    assert client.post("/api/availability/close", headers=a, json={"barber_id": catalogo["barbero"].id, "dates": [d]}).status_code == 200
    s = client.get("/api/admin/stats", headers=a).json()
    assert s["ingresos_mes"] == 0 and len(s["ingresos_6_meses"]) == 6


def test_recuperar_contrasena(client, catalogo, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.services.correo.enviar", lambda *a: enviados.append(a) or True)
    assert client.post("/api/password/forgot", json={"email": "nadie@x.co"}).status_code == 200
    assert not enviados
    client.post("/api/password/forgot", json={"email": "admin@correo.co"})
    token_ = enviados[0][2].split("token=")[1].split("\n")[0]
    assert client.post("/api/password/reset", json={"token": token_, "password": "NuevaClave99"}).status_code == 200
    assert client.post("/api/login", json={"email": "admin@correo.co", "password": "NuevaClave99"}).status_code == 200
    assert client.post("/api/password/reset", json={"token": token_, "password": "OtraClave99"}).status_code == 400
