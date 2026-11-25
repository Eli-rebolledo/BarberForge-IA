from tests.conftest import token

NUEVO = {"email": "luis@demo.co", "full_name": "Luis Ortiz", "password": "Clave12345",
         "specialties": "Tratamientos"}


def test_listar_y_filtrar_por_servicio(client, catalogo):
    barberos = client.get("/api/barbers").json()
    assert barberos[0]["full_name"] == "Carlos Mena"
    assert sorted(barberos[0]["service_ids"]) == sorted([catalogo["corte"].id, catalogo["barba"].id])
    assert client.get("/api/barbers", params={"service_id": 999}).json() == []


def test_crear_barbero_con_servicios_elegidos(client, catalogo):
    admin = token(client, "admin@correo.co")
    r = client.post("/api/barbers", json={**NUEVO, "service_ids": [catalogo["barba"].id]}, headers=admin)
    assert r.status_code == 200
    luis = next(b for b in client.get("/api/barbers").json() if b["full_name"] == "Luis Ortiz")
    assert luis["service_ids"] == [catalogo["barba"].id]


def test_crear_barbero_sin_servicios_ofrece_todos(client, catalogo):
    client.post("/api/barbers", json=NUEVO, headers=token(client, "admin@correo.co"))
    luis = next(b for b in client.get("/api/barbers").json() if b["full_name"] == "Luis Ortiz")
    assert len(luis["service_ids"]) == 2


def test_barbero_duplicado_y_permisos(client, catalogo):
    admin = token(client, "admin@correo.co")
    assert client.post("/api/barbers", json=NUEVO, headers=token(client, "ana@correo.co")).status_code == 403
    client.post("/api/barbers", json=NUEVO, headers=admin)
    assert client.post("/api/barbers", json=NUEVO, headers=admin).status_code == 409


def test_desactivar_barbero_lo_oculta_al_publico(client, catalogo):
    admin = token(client, "admin@correo.co")
    client.post(f"/api/barbers/{catalogo['barbero'].id}/toggle", headers=admin)
    assert client.get("/api/barbers").json() == []
    assert client.get("/api/barbers", headers=admin).json()[0]["is_active"] is False


def test_actualizar_dias_de_trabajo(client, catalogo):
    admin = token(client, "admin@correo.co")
    ruta = f"/api/barbers/{catalogo['barbero'].id}/days"
    assert client.put(ruta, json={"work_days": [0, 1]}, headers=admin).status_code == 200
    assert client.get("/api/barbers").json()[0]["work_days"] == [0, 1]
    assert client.put(ruta, json={"work_days": []}, headers=admin).status_code == 400
    assert client.put(ruta, json={"work_days": [7]}, headers=admin).status_code == 400
    assert client.put(ruta, json={"work_days": [0]}, headers=token(client, "ana@correo.co")).status_code == 403


def test_detalle_y_editar_barbero(client, catalogo):
    admin = token(client, "admin@correo.co")
    bid = catalogo["barbero"].id
    assert client.get(f"/api/barbers/{bid}", headers=token(client, "ana@correo.co")).status_code == 403
    d = client.get(f"/api/barbers/{bid}", headers=admin).json()
    assert d["email"] == catalogo["barbero"].email
    r = client.put(f"/api/barbers/{bid}", headers=admin, json={
        "email": "NUEVO@demo.co", "full_name": "Carlos M.", "specialties": "Fade", "service_ids": [catalogo["barba"].id]})
    assert r.status_code == 200
    d = client.get(f"/api/barbers/{bid}", headers=admin).json()
    assert (d["email"], d["full_name"], d["service_ids"]) == ("nuevo@demo.co", "Carlos M.", [catalogo["barba"].id])


def test_editar_barbero_con_correo_repetido(client, catalogo):
    admin = token(client, "admin@correo.co")
    client.post("/api/barbers", json=NUEVO, headers=admin)
    bid = catalogo["barbero"].id
    r = client.put(f"/api/barbers/{bid}", headers=admin, json={"email": NUEVO["email"], "full_name": "Carlos"})
    assert r.status_code == 409


def test_editar_contrasena_del_barbero(client, catalogo):
    admin = token(client, "admin@correo.co")
    bid = catalogo["barbero"].id
    correo = catalogo["barbero"].email
    r = client.put(f"/api/barbers/{bid}", headers=admin, json={"email": correo, "full_name": "Carlos", "password": "corta"})
    assert r.status_code == 400
    client.put(f"/api/barbers/{bid}", headers=admin, json={"email": correo, "full_name": "Carlos", "password": "OtraClave99"})
    assert client.post("/api/login", json={"email": correo, "password": "OtraClave99"}).status_code == 200


def test_eliminar_barbero_sin_citas(client, catalogo):
    admin = token(client, "admin@correo.co")
    client.post("/api/barbers", json=NUEVO, headers=admin)
    luis = next(b for b in client.get("/api/barbers", headers=admin).json() if b["full_name"] == "Luis Ortiz")
    assert client.delete(f"/api/barbers/{luis['id']}", headers=token(client, "ana@correo.co")).status_code == 403
    assert client.delete(f"/api/barbers/{luis['id']}", headers=admin).status_code == 200
    assert all(b["full_name"] != "Luis Ortiz" for b in client.get("/api/barbers", headers=admin).json())
    assert client.delete(f"/api/barbers/{luis['id']}", headers=admin).status_code == 404


# ---------- reasignación al desactivar y eliminación con citas ----------

def _segundo_barbero(db, catalogo):
    from datetime import time, timedelta

    from app.core.tiempo import hoy
    from app.models import Rol
    from app.services.disponibilidad import generar_franjas
    from tests.conftest import crear_usuario
    luis = crear_usuario(db, "luis@demo.co", Rol.BARBERO, "Luis Ortiz", servicios=[catalogo["corte"], catalogo["barba"]])
    manana = hoy() + timedelta(days=1)
    generar_franjas(db, luis.id, manana, manana + timedelta(days=2), time(9), time(11), 30, set(range(7)))
    return luis


def _cita(client, catalogo, barbero_id, franja):
    return client.post("/api/appointments", headers=token(client, "ana@correo.co"), json={
        "barber_id": barbero_id, "service_id": catalogo["corte"].id, "date": franja["date"], "time": franja["time"]})


def test_desactivar_pasa_las_citas_a_otro_barbero_libre(client, catalogo, db):
    luis = _segundo_barbero(db, catalogo)
    admin = token(client, "admin@correo.co")
    franja = client.get("/api/availability", params={"barber_id": catalogo["barbero"].id}).json()[0]
    assert _cita(client, catalogo, catalogo["barbero"].id, franja).status_code == 200
    r = client.post(f"/api/barbers/{catalogo['barbero'].id}/toggle", headers=admin)
    assert r.status_code == 200 and r.json()["reasignadas"] == 1 and r.json()["canceladas"] == 0
    cita = client.get("/api/appointments", headers=token(client, "ana@correo.co")).json()[0]
    assert cita["barber"] == "Luis Ortiz" and cita["barber_id"] == luis.id and cita["status"] == "pendiente"
    assert (cita["date"], cita["time"]) == (franja["date"], franja["time"])


def test_desactivar_cancela_la_cita_si_nadie_esta_libre(client, catalogo, db):
    luis = _segundo_barbero(db, catalogo)
    admin = token(client, "admin@correo.co")
    franja = client.get("/api/availability", params={"barber_id": catalogo["barbero"].id}).json()[0]
    assert _cita(client, catalogo, catalogo["barbero"].id, franja).status_code == 200
    assert _cita(client, catalogo, luis.id, franja).status_code == 200  # Luis ya tiene esa hora ocupada
    r = client.post(f"/api/barbers/{catalogo['barbero'].id}/toggle", headers=admin)
    assert r.json()["reasignadas"] == 0 and r.json()["canceladas"] == 1
    estados = sorted(c["status"] for c in client.get("/api/appointments", headers=token(client, "ana@correo.co")).json())
    assert estados == ["cancelada_admin", "pendiente"]


def test_eliminar_barbero_con_citas_canceladas_si_pero_con_activas_no(client, catalogo):
    admin = token(client, "admin@correo.co")
    bid = catalogo["barbero"].id
    franja = client.get("/api/availability", params={"barber_id": bid}).json()[0]
    cita_id = _cita(client, catalogo, bid, franja).json()["id"]
    r = client.delete(f"/api/barbers/{bid}", headers=admin)
    assert r.status_code == 409  # cita pendiente
    client.post(f"/api/appointments/{cita_id}/cancel", headers=token(client, "ana@correo.co"))
    assert client.delete(f"/api/barbers/{bid}", headers=admin).status_code == 200
    assert client.get("/api/barbers", headers=admin).json() == []


def test_no_se_elimina_un_barbero_con_historial_atendido(client, catalogo, db):
    from app.models import Cita
    admin = token(client, "admin@correo.co")
    bid = catalogo["barbero"].id
    franja = client.get("/api/availability", params={"barber_id": bid}).json()[0]
    cita_id = _cita(client, catalogo, bid, franja).json()["id"]
    db.get(Cita, cita_id).status = "completada"
    db.commit()
    r = client.delete(f"/api/barbers/{bid}", headers=admin)
    assert r.status_code == 409 and "historial" in r.json()["detail"]


def test_el_tiempo_sobrante_de_un_servicio_corto_queda_libre(client, catalogo):
    """Una barba de 20 min deja libre desde el minuto 20 hasta la siguiente franja."""
    bid = catalogo["barbero"].id
    f = client.get("/api/availability", params={"barber_id": bid, "minutes": 20}).json()[0]
    assert f["time"] == "09:00"
    r = client.post("/api/appointments", headers=token(client, "ana@correo.co"), json={
        "barber_id": bid, "service_id": catalogo["barba"].id, "date": f["date"], "time": "09:00"})
    assert r.status_code == 200
    libres = client.get("/api/availability", params={"barber_id": bid, "minutes": 10}).json()
    assert {"date": f["date"], "time": "09:20"} in libres
    assert {"date": f["date"], "time": "09:00"} not in libres
    de_30 = client.get("/api/availability", params={"barber_id": bid, "minutes": 30}).json()
    assert {"date": f["date"], "time": "09:20"} in de_30  # 09:20-09:50 cabe antes de las 10:00


def test_foto_del_barbero(client, catalogo):
    import base64
    bid = catalogo["barbero"].id
    png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()
    admin, barbero, cliente = (token(client, c) for c in ("admin@correo.co", "carlos@demo.co", "ana@correo.co"))
    assert client.get(f"/api/barbers/{bid}/photo").status_code == 404
    assert client.put(f"/api/barbers/{bid}/photo", headers=cliente, json={"image": f"data:image/png;base64,{png}"}).status_code == 403
    assert client.put(f"/api/barbers/{bid}/photo", headers=admin, json={"image": "data:text/html;base64,PGI+"}).status_code == 400
    falso = base64.b64encode(b"<svg></svg>").decode()
    assert client.put(f"/api/barbers/{bid}/photo", headers=admin, json={"image": f"data:image/png;base64,{falso}"}).status_code == 400
    r = client.put(f"/api/barbers/{bid}/photo", headers=admin, json={"image": f"data:image/png;base64,{png}"})
    assert r.status_code == 200 and r.json()["photo_url"].startswith(f"/api/barbers/{bid}/photo?v=")
    foto = client.get(f"/api/barbers/{bid}/photo")
    assert foto.status_code == 200 and foto.headers["content-type"] == "image/png"
    assert client.get("/api/barbers").json()[0]["photo_url"]
    # El mismo barbero puede cambiar o quitar su foto.
    assert client.delete(f"/api/barbers/{bid}/photo", headers=barbero).status_code == 200
    assert client.get("/api/barbers").json()[0]["photo_url"] is None
