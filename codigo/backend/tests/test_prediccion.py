"""Feature 011 · predicción de inasistencias: generador, entrenamiento, modelo empaquetado, riesgo al agendar,
aviso de 60 minutos, reentrenamiento con citas reales y que la app no se caiga sin modelo."""
import io
import random
from datetime import datetime, time, timedelta

import joblib
import numpy as np
import pytest

from app.config import get_settings
from app.core.tiempo import ahora_local, ahora_utc, hoy
from app.ml import caracteristicas as car
from app.ml import entrenamiento, generador
from app.models import Cita, ModeloML, Rol
from app.services import citas as citas_srv
from app.services import prediccion
from tests.conftest import crear_usuario, token


@pytest.fixture(autouse=True)
def cache_limpio():
    prediccion.reiniciar_cache()
    yield
    prediccion.reiniciar_cache()


@pytest.fixture
def correos(monkeypatch):
    enviados = []
    monkeypatch.setattr("app.services.correo.enviar", lambda *a: enviados.append(a) or True)
    return enviados


def _cita(db, catalogo, inicio: datetime, estado="pendiente", cliente=None, riesgo=None, creada=None) -> Cita:
    corte = catalogo["corte"]
    cita = Cita(barber_id=catalogo["barbero"].id, service_id=corte.id, servicios=[corte],
                client_id=(cliente or catalogo["cliente"]).id, appointment_date=inicio.date(),
                start_time=inicio.time().replace(second=0, microsecond=0), status=estado,
                price_cop=corte.price_cop, duration_minutes=30, no_show_risk=riesgo,
                created_at=creada or ahora_utc())
    db.add(cita)
    db.commit()
    return cita


# ---------- generador y entrenamiento ----------

def test_generador_es_reproducible_y_tiene_una_tasa_realista():
    a, b = generador.generar(semilla=7, num_citas=400), generador.generar(semilla=7, num_citas=400)
    assert a == b
    assert a != generador.generar(semilla=8, num_citas=400)
    tasa = sum(f["inasistencia"] for f in generador.generar()) / generador.NUM_CITAS
    assert 0.12 <= tasa <= 0.25


def test_caracteristicas_invitado_sin_historial_y_tasa_suavizada():
    x = car.construir(dia_semana=5, hora=8.5, anticipacion_horas=-3, es_invitado=True, citas_previas=9,
                      faltas_previas=4, precio_cop=25000, num_servicios=1)
    assert (x.citas_previas, x.faltas_previas, x.es_invitado, x.franja, x.anticipacion_horas) == (0, 0, 1, 0, 0)
    assert x.tasa_faltas == car.TASA_PREVIA
    assert len(x.vector()) == len(car.NOMBRES)
    # un cliente que faltó 1 de 1 citas no queda con 100 % de tasa
    assert car.tasa_suavizada(1, 1) < 0.5


def test_entrenamiento_elige_un_modelo_util_y_se_puede_guardar(tmp_path):
    paquete, resultados = entrenamiento.entrenar(generador.generar(), "sintetico")
    assert set(resultados) == {"regresion_logistica", "arbol_decision"}
    assert paquete["metricas"]["auc"] > 0.65
    assert paquete["caracteristicas"] == list(car.NOMBRES)
    ruta = entrenamiento.guardar(paquete, tmp_path / "m.joblib")
    assert entrenamiento.cargar(ruta)["version"] == paquete["version"]


def test_el_modelo_empaquetado_usa_las_variables_actuales():
    """Si alguien cambia caracteristicas.py sin volver a entrenar, esta prueba lo avisa."""
    paquete = entrenamiento.cargar()
    assert paquete["caracteristicas"] == list(car.NOMBRES), "Corre: python -m app.tareas entrenar"
    assert paquete["origen"] == "sintetico"
    x = car.construir(dia_semana=5, hora=14.5, anticipacion_horas=48, es_invitado=False, citas_previas=3,
                      faltas_previas=1, precio_cop=25000, num_servicios=1)
    p = paquete["modelo"].predict_proba(np.asarray([x.vector()]))[0][1]
    assert 0 < p < 1


def test_el_modelo_empaquetado_es_reproducible():
    """Con la misma semilla, volver a entrenar da las mismas métricas que el modelo que va en la imagen."""
    paquete, _ = entrenamiento.entrenar(generador.generar(), "sintetico")
    guardado = entrenamiento.cargar()["metricas"]
    assert paquete["metricas"]["auc"] == pytest.approx(guardado["auc"], abs=0.01)
    assert paquete["metricas"]["recall"] == pytest.approx(guardado["recall"], abs=0.03)


# ---------- riesgo al agendar ----------

def test_al_agendar_se_guarda_el_riesgo_y_solo_lo_ve_el_personal(client, catalogo, db):
    manana = hoy() + timedelta(days=1)
    r = client.post("/api/appointments", headers=token(client, "ana@correo.co"),
                    json={"barber_id": catalogo["barbero"].id, "service_ids": [catalogo["corte"].id],
                          "date": str(manana), "time": "09:00"})
    assert r.status_code == 200, r.text
    cita = db.get(Cita, r.json()["id"])
    db.refresh(cita)
    assert cita.created_at is not None and 0 < cita.no_show_risk < 1

    propia = client.get("/api/appointments", headers=token(client, "ana@correo.co")).json()[0]
    assert propia["riesgo"] is None and propia["riesgo_alto"] is False  # el cliente no ve su «riesgo»
    admin = client.get("/api/appointments", headers=token(client, "admin@correo.co")).json()[0]
    assert admin["riesgo"] == pytest.approx(cita.no_show_risk)
    assert admin["riesgo_alto"] == (cita.no_show_risk >= get_settings().ml_umbral_riesgo)


def test_el_historial_solo_cuenta_lo_que_se_sabia_al_agendar(db, catalogo):
    ahora = ahora_local()
    for dias, estado in ((30, "inasistencia"), (20, "inasistencia"), (10, "completada"), (5, "cancelada_cliente")):
        _cita(db, catalogo, ahora - timedelta(days=dias), estado=estado)
    nueva = _cita(db, catalogo, ahora + timedelta(days=3))
    x = prediccion.caracteristicas_de(db, nueva)
    assert (x.citas_previas, x.faltas_previas) == (3, 2)
    assert 70 < x.anticipacion_horas < 74
    # una cita vieja (creada antes de esas citas) no «ve» el futuro
    vieja = _cita(db, catalogo, ahora - timedelta(days=40), estado="completada",
                  creada=ahora_utc() - timedelta(days=41))
    assert prediccion.caracteristicas_de(db, vieja).citas_previas == 0


def test_sin_modelo_o_con_modelo_roto_se_puede_agendar_igual(client, catalogo, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "ml_activo", False)
    cab = token(client, "ana@correo.co")
    manana = str(hoy() + timedelta(days=1))
    r = client.post("/api/appointments", headers=cab, json={"barber_id": catalogo["barbero"].id,
                    "service_ids": [catalogo["corte"].id], "date": manana, "time": "09:00"})
    assert r.status_code == 200 and db.get(Cita, r.json()["id"]).no_show_risk is None

    monkeypatch.setattr(get_settings(), "ml_activo", True)

    class Roto:
        def predict_proba(self, _x):
            raise RuntimeError("modelo dañado")

    monkeypatch.setattr(prediccion, "modelo_activo", lambda _db: {"modelo": Roto(), "version": "roto"})
    r = client.post("/api/appointments", headers=cab, json={"barber_id": catalogo["barbero"].id,
                    "service_ids": [catalogo["corte"].id], "date": manana, "time": "10:00"})
    assert r.status_code == 200 and db.get(Cita, r.json()["id"]).no_show_risk is None


# ---------- recordatorios: 60 + 40 minutos con riesgo alto, solo 40 con riesgo bajo ----------

def test_riesgo_alto_recibe_aviso_de_60_minutos_y_riesgo_bajo_no(db, catalogo, correos):
    otro = crear_usuario(db, "otro@correo.co", Rol.CLIENTE, "Otro Cliente")
    en_50 = ahora_local() + timedelta(minutes=50)
    alta = _cita(db, catalogo, en_50, riesgo=0.85)
    baja = _cita(db, catalogo, en_50 + timedelta(minutes=2), cliente=otro, riesgo=0.05)
    citas_srv.procesar_recordatorios(db)
    asuntos = [(destino, asunto) for destino, asunto, _ in correos]
    assert ("ana@correo.co", f"Tu cita en {get_settings().barberia_nombre} es en una hora") in asuntos
    assert all(destino != "otro@correo.co" for destino, _ in asuntos)
    db.refresh(alta), db.refresh(baja)
    assert alta.early_reminder_sent_at is not None and baja.early_reminder_sent_at is None
    assert alta.reminder_sent_at is None  # a los 50 min todavía no sale el de 40

    citas_srv.procesar_recordatorios(db)  # el aviso de 60 no se repite
    assert len([a for a in correos if "es en una hora" in a[1]]) == 1


def test_el_aviso_de_60_no_sale_si_ya_faltan_menos_de_40_minutos(db, catalogo, correos):
    cita = _cita(db, catalogo, ahora_local() + timedelta(minutes=30), riesgo=0.9)
    citas_srv.procesar_recordatorios(db)
    db.refresh(cita)
    assert cita.early_reminder_sent_at is None and cita.reminder_sent_at is not None  # solo el de 40
    assert not [a for a in correos if "es en una hora" in a[1]]


def test_una_cita_sin_riesgo_calculado_se_evalua_en_el_ciclo(db, catalogo, correos):
    cita = _cita(db, catalogo, ahora_local() + timedelta(minutes=55), riesgo=None)
    citas_srv.procesar_recordatorios(db)
    db.refresh(cita)
    assert cita.no_show_risk is not None
    assert (cita.early_reminder_sent_at is not None) == prediccion.es_alto(cita.no_show_risk)


# ---------- reentrenamiento con citas reales ----------

def test_reentrenar_con_pocos_datos_no_cambia_el_modelo(db, catalogo):
    _cita(db, catalogo, ahora_local() - timedelta(days=2), estado="completada")
    resultado = prediccion.reentrenar(db, registrar_mlflow=False)
    assert resultado["entrenado"] is False and "Faltan datos" in resultado["motivo"]
    assert db.query(ModeloML).count() == 0


def _historial_real(db, catalogo, n=240):
    """Citas cerradas con un patrón claro: algunos clientes casi siempre faltan."""
    azar = random.Random(11)
    clientes = [crear_usuario(db, f"c{i}@correo.co", Rol.CLIENTE, f"Cliente {i}") for i in range(24)]
    inicio = ahora_local().replace(hour=9, minute=0, second=0, microsecond=0) - timedelta(days=n)
    for i in range(n):
        cliente = clientes[i % len(clientes)]
        cuando = inicio + timedelta(days=i, hours=azar.choice([0, 2, 4, 8]))
        falta = azar.random() < (0.7 if cliente.id % 4 == 0 else 0.08)
        _cita(db, catalogo, cuando, estado="inasistencia" if falta else "completada", cliente=cliente,
              creada=(cuando - timedelta(hours=azar.choice([2, 30, 200]))).replace(tzinfo=None) - timedelta(hours=5))


def test_reentrenar_con_citas_reales_guarda_un_modelo_firmado(db, catalogo):
    _historial_real(db, catalogo)
    resultado = prediccion.reentrenar(db, minimo=100, registrar_mlflow=False)
    assert resultado["entrenado"] is True, resultado
    fila = db.query(ModeloML).one()
    assert fila.origin == "real" and fila.signature == prediccion.firmar(fila.content)
    assert fila.is_active == resultado["activado"]
    if fila.is_active:
        assert prediccion.modelo_activo(db)["origen"] == "real"


def test_un_modelo_con_firma_alterada_no_se_carga(db):
    buffer = io.BytesIO()
    joblib.dump({"modelo": None, "version": "trampa", "origen": "real"}, buffer)
    db.add(ModeloML(version="trampa", origin="real", algorithm="x", content=buffer.getvalue(),
                    signature="0" * 64, is_active=True))
    db.commit()
    paquete = prediccion.modelo_activo(db)
    assert paquete is not None and paquete["origen"] == "sintetico"  # se ignora y se usa el empaquetado


# ---------- panel del administrador ----------

def test_panel_muestra_el_modelo_y_las_citas_de_riesgo(client, catalogo, db):
    _cita(db, catalogo, datetime.combine(hoy() + timedelta(days=1), time(9)), riesgo=0.9)
    _cita(db, catalogo, datetime.combine(hoy() + timedelta(days=1), time(10)), riesgo=0.05)
    r = client.get("/api/admin/ml", headers=token(client, "admin@correo.co"))
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["activo"] and datos["origen"] == "sintetico" and datos["metricas"]["auc"] > 0.6
    assert (datos["citas_proximas"], datos["citas_riesgo_alto"]) == (2, 1)
    assert client.get("/api/admin/ml", headers=token(client, "ana@correo.co")).status_code == 403
