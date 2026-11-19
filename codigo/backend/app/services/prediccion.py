"""Predicción de inasistencias (feature 011): calcula el riesgo de cada cita y reentrena con citas reales.

Regla de negocio:
    riesgo >= ML_UMBRAL_RIESGO (0,20)  → aviso extra 60 min antes + el recordatorio habitual de 40 min
    riesgo menor, o sin modelo         → solo el recordatorio de 40 min (como antes de esta feature)

El modelo se busca en este orden: el último modelo ACTIVO de la tabla ml_models (reentrenado con citas reales,
firmado) y, si no hay, el que viene en la imagen (app/ml/modelo_inasistencia.joblib, entrenado con datos
sintéticos). Si nada carga, la app sigue funcionando igual que antes: nunca se cae por el modelo.
"""
import hashlib
import hmac
import io
import json
import logging
import time
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import joblib
import numpy as np
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import metricas
from app.core.tiempo import ahora_local, zona
from app.ml import caracteristicas as car
from app.ml import entrenamiento
from app.models import Cita, ModeloML
from app.models.cita import ESTADOS_ACTIVOS

log = logging.getLogger("barberforge.prediccion")

ESTADOS_CERRADOS = ("completada", "inasistencia")
ANTICIPACION_DESCONOCIDA_H = 24.0  # citas creadas antes de la migración 007 (sin created_at)
REVISAR_CADA_S = 300               # cada cuánto se mira si hay un modelo nuevo en la base
MIN_POR_CLASE = 20                 # mínimo de inasistencias y de citas cumplidas para reentrenar

_cache: dict = {"paquete": None, "clave": None, "revisado": None}


def reiniciar_cache() -> None:
    _cache.update(paquete=None, clave=None, revisado=None)


# ---------- firma de modelos guardados en la base ----------

def _clave_firma() -> bytes:
    return hashlib.sha256(b"barberforge-ml|" + get_settings().jwt_secret.encode()).digest()


def firmar(contenido: bytes) -> str:
    return hmac.new(_clave_firma(), contenido, hashlib.sha256).hexdigest()


# ---------- cargar el modelo ----------

def _desde_archivo() -> dict | None:
    try:
        return entrenamiento.cargar()
    except Exception:  # noqa: BLE001 - sin modelo la app sigue igual que antes
        log.warning("no se pudo cargar el modelo empaquetado %s", entrenamiento.RUTA_MODELO, exc_info=True)
        return None


def _desde_base(db: Session, modelo_id: int) -> dict | None:
    fila = db.get(ModeloML, modelo_id)
    if fila is None or not hmac.compare_digest(firmar(fila.content), fila.signature):
        log.error("el modelo %s de ml_models tiene una firma inválida: se ignora", modelo_id)
        return None
    return joblib.load(io.BytesIO(fila.content))


def modelo_activo(db: Session) -> dict | None:
    """Devuelve el paquete del modelo (ver entrenamiento.entrenar) o None. Revisa la base cada 5 minutos."""
    if not get_settings().ml_activo:
        return None
    ahora = time.monotonic()
    if _cache["revisado"] is not None and ahora - _cache["revisado"] < REVISAR_CADA_S:
        return _cache["paquete"]
    _cache["revisado"] = ahora
    try:
        modelo_id = db.scalar(select(ModeloML.id).where(ModeloML.is_active).order_by(ModeloML.id.desc()).limit(1))
    except Exception:  # noqa: BLE001 - p. ej. la migración 007 aún no corre
        db.rollback()
        modelo_id = None
    clave = f"bd:{modelo_id}" if modelo_id else "archivo"
    if clave == _cache["clave"]:
        return _cache["paquete"]
    paquete = _desde_base(db, modelo_id) if modelo_id else None
    if paquete is None:
        paquete, clave = _desde_archivo(), "archivo"
    _cache.update(paquete=paquete, clave=clave if paquete else None)
    if paquete:
        log.info("modelo de inasistencias cargado: %s", paquete["version"])
    return paquete


# ---------- características de una cita (las mismas que en el entrenamiento) ----------

def _creada_local(cita: Cita, inicio: datetime) -> datetime:
    if cita.created_at is None:
        return inicio - timedelta(hours=ANTICIPACION_DESCONOCIDA_H)
    creada = cita.created_at if cita.created_at.tzinfo else cita.created_at.replace(tzinfo=UTC)  # SQLite no guarda zona
    return creada.astimezone(zona()).replace(tzinfo=None)


def caracteristicas_de(db: Session, cita: Cita) -> car.Caracteristicas:
    inicio = datetime.combine(cita.appointment_date, cita.start_time)
    creada = _creada_local(cita, inicio)
    citas_previas = faltas_previas = 0
    if cita.client_id is not None:
        # Solo cuenta lo que ya se sabía al agendar: citas del cliente que terminaron antes de ese momento.
        for estado, fecha, hora in db.execute(select(Cita.status, Cita.appointment_date, Cita.start_time).where(
                Cita.client_id == cita.client_id, Cita.id != cita.id, Cita.status.in_(ESTADOS_CERRADOS))):
            if datetime.combine(fecha, hora) < creada:
                citas_previas += 1
                faltas_previas += estado == "inasistencia"
    servicios = cita.servicios or [cita.servicio]
    return car.construir(
        dia_semana=cita.appointment_date.weekday(), hora=cita.start_time.hour + cita.start_time.minute / 60,
        anticipacion_horas=(inicio - creada).total_seconds() / 3600, es_invitado=cita.client_id is None,
        citas_previas=citas_previas, faltas_previas=faltas_previas,
        precio_cop=cita.price_cop or sum(s.price_cop for s in servicios), num_servicios=len(servicios))


# ---------- predecir ----------

def umbral() -> float:
    return get_settings().ml_umbral_riesgo


def es_alto(riesgo: float | None) -> bool:
    return riesgo is not None and riesgo >= umbral()


def calcular(db: Session, cita: Cita) -> float | None:
    try:
        paquete = modelo_activo(db)
        if paquete is None:
            return None
        x = np.asarray([caracteristicas_de(db, cita).vector()], dtype=float)
        return round(float(paquete["modelo"].predict_proba(x)[0][1]), 4)
    except Exception:  # noqa: BLE001 - una falla del modelo nunca debe impedir agendar
        log.exception("no se pudo calcular el riesgo de la cita %s", cita.id)
        return None


def actualizar_riesgo(db: Session, cita: Cita) -> float | None:
    """Calcula el riesgo, lo guarda en la cita y lo cuenta en la métrica barberforge.ml.predicciones."""
    riesgo = calcular(db, cita)
    if riesgo is None:
        return None
    cita.no_show_risk = riesgo
    db.commit()
    metricas.predicciones.add(1, {"nivel": "alto" if es_alto(riesgo) else "bajo"})
    return riesgo


# ---------- panel del administrador ----------

def info(db: Session) -> dict:
    paquete = modelo_activo(db)
    hoy = ahora_local().date()
    proximas = db.scalars(select(Cita.no_show_risk).where(
        Cita.status.in_(ESTADOS_ACTIVOS), Cita.appointment_date >= hoy)).all()
    datos = {"activo": paquete is not None, "umbral": umbral(),
             "citas_proximas": len(proximas), "citas_riesgo_alto": sum(es_alto(r) for r in proximas)}
    if paquete:
        datos.update({k: paquete[k] for k in ("version", "origen", "algoritmo", "entrenado", "metricas")})
        datos["importancia"] = dict(list(paquete.get("importancia", {}).items())[:5])
    return datos


# ---------- reentrenar con citas reales ----------

def filas_reales(db: Session) -> list[dict]:
    citas = db.scalars(select(Cita).where(Cita.status.in_(ESTADOS_CERRADOS))
                       .order_by(Cita.appointment_date, Cita.start_time)).unique()
    return [{"fecha": f"{c.appointment_date} {c.start_time:%H:%M}", **asdict(caracteristicas_de(db, c)),
             "inasistencia": int(c.status == "inasistencia")} for c in citas]


def reentrenar(db: Session, minimo: int | None = None, registrar_mlflow: bool = True) -> dict:
    """Entrena con las citas reales cerradas. El modelo nuevo solo se activa si, en las citas reales más
    recientes, su AUC es igual o mejor que el del modelo que está en uso."""
    minimo = get_settings().ml_minimo_reentrenamiento if minimo is None else minimo
    filas = filas_reales(db)
    faltas = sum(f["inasistencia"] for f in filas)
    if len(filas) < minimo or faltas < MIN_POR_CLASE or len(filas) - faltas < MIN_POR_CLASE:
        return {"entrenado": False, "citas": len(filas), "inasistencias": faltas,
                "motivo": f"Faltan datos: se necesitan al menos {minimo} citas cerradas, con {MIN_POR_CLASE} o más "
                          f"inasistencias y {MIN_POR_CLASE} o más cumplidas. Se sigue usando el modelo actual."}

    paquete, resultados = entrenamiento.entrenar(filas, "real", umbral())
    _, prueba = entrenamiento.dividir_por_fecha(filas)
    x_prueba, y_prueba = entrenamiento.matriz(prueba)
    actual = modelo_activo(db)
    auc_actual = None
    if actual:
        try:
            auc_actual = entrenamiento.evaluar(actual["modelo"], x_prueba, y_prueba, umbral())["auc"]
        except Exception:  # noqa: BLE001 - un modelo viejo incompatible se reemplaza
            auc_actual = None
    auc_nuevo = paquete["metricas"]["auc"]
    activar = auc_actual is None or (auc_nuevo is not None and auc_nuevo >= auc_actual)

    buffer = io.BytesIO()
    joblib.dump(paquete, buffer, compress=3)
    contenido = buffer.getvalue()
    if activar:
        db.execute(update(ModeloML).values(is_active=False))
    fila = ModeloML(version=paquete["version"], origin="real", algorithm=paquete["algoritmo"],
                    metrics_json=json.dumps({**paquete["metricas"], "auc_modelo_anterior": auc_actual}),
                    content=contenido, signature=firmar(contenido), is_active=activar)
    db.add(fila)
    db.commit()
    reiniciar_cache()
    if registrar_mlflow:
        entrenamiento.registrar_en_mlflow(paquete, resultados, {"origen": "real", "citas": len(filas)})
    return {"entrenado": True, "activado": activar, "version": paquete["version"], "citas": len(filas),
            "inasistencias": faltas, "auc_nuevo": auc_nuevo, "auc_anterior": auc_actual,
            "algoritmo": paquete["algoritmo"]}
