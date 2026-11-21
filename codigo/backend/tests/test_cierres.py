"""Festivos (RF09) y ausencias de barberos (RF17)."""
from datetime import date, time, timedelta

from app.core.tiempo import hoy
from app.models import Rol
from app.services.cierres import festivos_colombia
from app.services.disponibilidad import generar_franjas
from tests.conftest import crear_usuario, token


def _libres(client, barbero_id):
    return client.get("/api/availability", params={"barber_id": barbero_id}).json()


def _primer_dia(client, catalogo) -> date:
    """Primer día con horario del barbero de prueba (el catálogo no genera domingos)."""
    return date.fromisoformat(_libres(client, catalogo["barbero"].id)[0]["date"])


def _agendar(client, catalogo, cab, dia: date, hora="09:00"):
    return client.post("/api/appointments", json={"barber_id": catalogo["barbero"].id,
                                                  "service_id": catalogo["corte"].id,
                                                  "date": str(dia), "time": hora}, headers=cab)


def test_festivos_de_colombia_2026():
    dias = dict(festivos_colombia(2026))
    assert len(dias) == 18
    assert dias[date(2026, 1, 12)] == "Reyes Magos"          # 6 de enero trasladado al lunes
    assert dias[date(2026, 4, 3)] == "Viernes Santo"
    assert dias[date(2026, 5, 18)] == "Ascensión del Señor"
    assert dias[date(2026, 6, 8)] == "Corpus Christi"
    assert dias[date(2026, 6, 15)] == "Sagrado Corazón"
    assert dias[date(2026, 12, 8)] == "Inmaculada Concepción"
    trasladados = [d for d, m in dias.items() if m in ("Reyes Magos", "San José", "Día de la Raza", "Todos los Santos")]
    assert all(d.weekday() == 0 for d in trasladados)


def test_festivo_cierra_el_dia_y_cancela_citas(client, catalogo):
    manana = _primer_dia(client, catalogo)
    cliente, admin = token(client, "ana@correo.co"), token(client, "admin@correo.co")
    assert _agendar(client, catalogo, cliente, manana).status_code == 200
    r = client.post("/api/closed-days", json={"date": str(manana), "motivo": "Día de la ciudad"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["canceladas"] == 1
    assert all(f["date"] != str(manana) for f in _libres(client, catalogo["barbero"].id))
    citas = client.get("/api/appointments", headers=cliente).json()
    assert citas[0]["status"] == "cancelada_admin"
    assert _agendar(client, catalogo, cliente, manana, "09:30").status_code == 409
    assert client.get("/api/closed-days").json()[0]["motivo"] == "Día de la ciudad"  # público
    # repetido → 409; pasado → 400; sin ser admin → 403
    assert client.post("/api/closed-days", json={"date": str(manana)}, headers=admin).status_code == 409
    assert client.post("/api/closed-days", json={"date": str(hoy() - timedelta(days=1))}, headers=admin).status_code == 400
    assert client.post("/api/closed-days", json={"date": str(manana)}, headers=cliente).status_code == 403


def test_cierre_de_varios_dias(client, catalogo):
    admin = token(client, "admin@correo.co")
    inicio = hoy() + timedelta(days=20)
    r = client.post("/api/closed-days", json={"date": str(inicio), "date_to": str(inicio + timedelta(days=4)),
                                              "motivo": "Vacaciones colectivas"}, headers=admin)
    assert r.status_code == 200 and r.json()["dias"] == 5
    assert len(client.get("/api/closed-days").json()) == 5
    # repetir el rango no duplica; un rango al revés o demasiado largo se rechaza
    assert client.post("/api/closed-days", json={"date": str(inicio), "date_to": str(inicio + timedelta(days=5))},
                       headers=admin).json()["dias"] == 1
    assert client.post("/api/closed-days", json={"date": str(inicio), "date_to": str(inicio - timedelta(days=1))},
                       headers=admin).status_code == 400
    assert client.post("/api/closed-days", json={"date": str(inicio), "date_to": str(inicio + timedelta(days=40))},
                       headers=admin).status_code == 400


def test_la_agenda_no_genera_franjas_en_festivos_y_borrar_reabre(client, catalogo, db):
    admin = token(client, "admin@correo.co")
    dia = hoy() + timedelta(days=4)
    while dia.weekday() == 6:
        dia += timedelta(days=1)
    festivo = client.post("/api/closed-days", json={"date": str(dia)}, headers=admin).json()
    assert generar_franjas(db, catalogo["barbero"].id, dia, dia, time(9), time(10), 30) == 0
    mes = client.get("/api/availability/calendar", params={"barber_id": catalogo["barbero"].id, "month": str(dia)[:7]},
                     headers=admin).json()
    assert any(d["date"] == str(dia) and d["bloqueo"].startswith("Festivo") for d in mes)
    assert client.delete(f"/api/closed-days/{festivo['id']}", headers=admin).status_code == 200
    assert any(f["date"] == str(dia) for f in _libres(client, catalogo["barbero"].id))  # se volvió a abrir


def test_cargar_festivos_de_colombia_no_duplica(client, catalogo):
    admin = token(client, "admin@correo.co")
    anio = hoy().year + 1
    primera = client.post("/api/closed-days/colombia", json={"year": anio}, headers=admin).json()
    assert primera["creados"] == 18
    assert client.post("/api/closed-days/colombia", json={"year": anio}, headers=admin).json()["creados"] == 0


def test_ausencia_pasa_las_citas_a_otro_barbero(client, catalogo, db):
    # Los dos trabajan todos los días y tienen agenda en los tres próximos: la prueba no depende de la fecha.
    catalogo["barbero"].dias_csv = "0,1,2,3,4,5,6"
    db.commit()
    otro = crear_usuario(db, "luis@demo.co", Rol.BARBERO, "Luis Peña", servicios=[catalogo["corte"], catalogo["barba"]])
    manana = hoy() + timedelta(days=1)
    for b in (catalogo["barbero"].id, otro.id):
        generar_franjas(db, b, manana, manana + timedelta(days=2), time(9), time(11), 30, set(range(7)))
    cliente, admin = token(client, "ana@correo.co"), token(client, "admin@correo.co")
    assert _agendar(client, catalogo, cliente, manana).status_code == 200
    r = client.post(f"/api/barbers/{catalogo['barbero'].id}/absences",
                    json={"date_from": str(manana), "date_to": str(manana + timedelta(days=1)), "motivo": "Vacaciones"},
                    headers=admin)
    assert r.status_code == 200, r.text
    assert r.json() | {"id": 0} == {"id": 0, "reasignadas": 1, "canceladas": 0}
    assert client.get("/api/appointments", headers=cliente).json()[0]["barber"] == "Luis Peña"
    libres = {f["date"] for f in _libres(client, catalogo["barbero"].id)}
    assert str(manana) not in libres and str(manana + timedelta(days=1)) not in libres
    assert str(manana + timedelta(days=2)) in libres  # el día siguiente a la ausencia sigue abierto
    lista = client.get("/api/absences", headers=admin).json()
    assert lista[0]["barber"] == "Carlos Mena" and lista[0]["motivo"] == "Vacaciones"
    assert client.delete(f"/api/absences/{lista[0]['id']}", headers=admin).status_code == 200
    assert str(manana + timedelta(days=1)) in {f["date"] for f in _libres(client, catalogo["barbero"].id)}


def test_ausencia_sin_reemplazo_cancela_y_valida_fechas(client, catalogo):
    manana = _primer_dia(client, catalogo)
    cliente, admin = token(client, "ana@correo.co"), token(client, "admin@correo.co")
    assert _agendar(client, catalogo, cliente, manana).status_code == 200
    url = f"/api/barbers/{catalogo['barbero'].id}/absences"
    r = client.post(url, json={"date_from": str(manana), "date_to": str(manana)}, headers=admin)
    assert r.json()["canceladas"] == 1
    assert client.post(url, json={"date_from": str(manana), "date_to": str(manana - timedelta(days=1))},
                       headers=admin).status_code == 400
    assert client.post(url, json={"date_from": str(hoy()), "date_to": str(hoy() + timedelta(days=400))},
                       headers=admin).status_code == 400
    assert client.post("/api/barbers/999/absences", json={"date_from": str(manana), "date_to": str(manana)},
                       headers=admin).status_code == 404


def test_el_chat_no_ofrece_horas_en_un_festivo(client, catalogo):
    admin = token(client, "admin@correo.co")
    manana = _primer_dia(client, catalogo)
    client.post("/api/closed-days", json={"date": str(manana)}, headers=admin)
    franjas = _libres(client, catalogo["barbero"].id)
    assert franjas and franjas[0]["date"] > str(manana)


def test_vista_previa_muestra_las_citas_afectadas(client, catalogo):
    cliente, admin = token(client, "ana@correo.co"), token(client, "admin@correo.co")
    dia = _primer_dia(client, catalogo)
    _agendar(client, catalogo, cliente, dia)
    previa = client.get("/api/closed-days/preview", params={"date": str(dia)}, headers=admin).json()
    assert len(previa) == 1 and previa[0]["client"] == "Ana Ruiz" and previa[0]["barber"] == "Carlos Mena"
    url = f"/api/barbers/{catalogo['barbero'].id}/absences/preview"
    assert len(client.get(url, params={"date_from": str(dia), "date_to": str(dia)}, headers=admin).json()) == 1
    assert client.get("/api/closed-days/preview", params={"date": str(dia)}, headers=cliente).status_code == 403


def test_el_asistente_informa_los_dias_sin_atencion(client, catalogo):
    admin = token(client, "admin@correo.co")
    dia = hoy() + timedelta(days=15)
    client.post("/api/closed-days", json={"date": str(dia), "motivo": "Inventario anual"}, headers=admin)
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
             "noviembre", "diciembre"]
    r = client.post("/api/chat", json={"message": f"¿Abren el {dia.day} de {meses[dia.month - 1]}?"}).json()
    assert "Inventario anual" in r["reply"] and "no atiende" in r["reply"]
