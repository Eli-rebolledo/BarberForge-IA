"""Tareas de una sola vez para Kubernetes (Job) o mantenimiento manual.

    python -m app.tareas migrar          # alembic upgrade head + datos iniciales (admin y agenda de la semana)
    python -m app.tareas indexar         # reconstruye el índice del asistente
    python -m app.tareas generar-datos   # feature 011: citas sintéticas → datos/citas_sinteticas.csv
    python -m app.tareas entrenar        # feature 011: entrena con datos sintéticos → app/ml/modelo_inasistencia.joblib
    python -m app.tareas reentrenar      # feature 011: entrena con las citas reales de la base (CronJob semanal)

En Kubernetes, el Job de migraciones corre antes de actualizar la API, así las réplicas nuevas nunca
arrancan con un esquema viejo."""
import json
import logging
import sys
import time
from pathlib import Path

from app.services import arranque

log = logging.getLogger("barberforge.tareas")


def migrar(reintentos: int = 30) -> None:
    for intento in range(1, reintentos + 1):
        try:
            arranque.migrar()
            arranque.preparar_datos()
            log.info("migraciones aplicadas y datos iniciales listos")
            return
        except Exception as e:  # noqa: BLE001 - la base puede estar arrancando: se reintenta
            log.warning("intento %s/%s: la base aún no responde (%s)", intento, reintentos, type(e).__name__)
            time.sleep(5)
    raise SystemExit("No se pudo conectar a la base de datos")


RUTA_DATOS = Path("datos/citas_sinteticas.csv")


def generar_datos(ruta: Path = RUTA_DATOS) -> None:
    from app.ml import generador
    filas = generador.generar()
    generador.guardar_csv(filas, ruta)
    tasa = sum(f["inasistencia"] for f in filas) / len(filas)
    log.info("%s citas sintéticas en %s (inasistencia: %.1f %%)", len(filas), ruta, tasa * 100)


def entrenar(ruta_datos: Path | None = None) -> None:
    """Entrena con datos sintéticos, guarda el modelo que va en la imagen y lo registra en MLflow."""
    from app.ml import entrenamiento, generador
    filas = generador.leer_csv(ruta_datos) if ruta_datos else generador.generar()
    paquete, resultados = entrenamiento.entrenar(filas, "sintetico")
    ruta = entrenamiento.guardar(paquete)
    for nombre, r in resultados.items():
        m = r["metricas"]
        log.info("%-20s AUC %.3f · recall %.2f · precisión %.2f · alertas %.0f %%", nombre, m["auc"], m["recall"],
                 m["precision"], m["alertas_pct"] * 100)
    log.info("ganador: %s → %s", paquete["algoritmo"], ruta)
    run = entrenamiento.registrar_en_mlflow(paquete, resultados, {"semilla": generador.SEMILLA, "citas": len(filas)})
    if run:
        log.info("registrado en MLflow (run %s). Para verlo: mlflow ui --backend-store-uri sqlite:///mlflow.db", run)


def reentrenar() -> None:
    from app import db as bd
    from app.services import prediccion
    with bd.SessionLocal() as db:
        resultado = prediccion.reentrenar(db)
    log.info("reentrenamiento: %s", json.dumps(resultado, ensure_ascii=False))


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    orden = argv[1] if len(argv) > 1 else ""
    if orden == "migrar":
        migrar()
    elif orden == "indexar":
        ok = arranque._reindexar()
        log.info("índice reconstruido (%s)", "con embeddings" if ok else "solo palabras clave")
    elif orden == "generar-datos":
        generar_datos()
    elif orden == "entrenar":
        entrenar(Path(argv[2]) if len(argv) > 2 else None)
    elif orden == "reentrenar":
        reentrenar()
    else:
        raise SystemExit("Uso: python -m app.tareas [migrar|indexar|generar-datos|entrenar|reentrenar]")


if __name__ == "__main__":
    main(sys.argv)
