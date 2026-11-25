"""Experimento: compara los candidatos del proyecto con XGBoost, con los mismos datos y la misma división por fecha.

XGBoost NO va en la imagen de la API (pesa y no ganó); se instala solo para este experimento:
    pip install -r requirements-ml.txt
    python -m app.ml.comparar_modelos            → docs/evaluacion-ml/comparacion_modelos.csv (+ MLflow si está)
"""
import csv
import logging
import sys
from pathlib import Path

from sklearn.pipeline import Pipeline

from app.ml import entrenamiento, generador

log = logging.getLogger("barberforge.ml")
SALIDA = Path(__file__).resolve().parents[4] / "docs" / "evaluacion-ml" / "comparacion_modelos.csv"


def modelos(semilla: int = generador.SEMILLA) -> dict[str, Pipeline]:
    todos = entrenamiento.candidatos(semilla)
    try:
        from xgboost import XGBClassifier
    except ImportError:
        log.warning("xgboost no está instalado (pip install -r requirements-ml.txt): se compara sin él")
        return todos
    todos["xgboost"] = Pipeline([("modelo", XGBClassifier(n_estimators=300, max_depth=2, learning_rate=0.02,
                                                          subsample=0.8, colsample_bytree=0.8,
                                                          eval_metric="logloss", random_state=semilla))])
    return todos


def comparar(filas: list[dict] | None = None, salida: Path = SALIDA) -> list[dict]:
    filas = filas or generador.generar()
    entrena, prueba = entrenamiento.dividir_por_fecha(filas)
    x_ent, y_ent = entrenamiento.matriz(entrena)
    x_pru, y_pru = entrenamiento.matriz(prueba)
    tabla = []
    for nombre, modelo in modelos().items():
        modelo.fit(x_ent, y_ent)
        m = entrenamiento.evaluar(modelo, x_pru, y_pru)
        tabla.append({"modelo": nombre, "auc": m["auc"], "recall": m["recall"], "precision": m["precision"],
                      "brier": m["brier"], "alertas_pct": m["alertas_pct"], "en_el_proyecto": nombre != "xgboost"})
    tabla.sort(key=lambda f: -(f["auc"] or 0))
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tabla[0]))
        w.writeheader()
        w.writerows(tabla)
    _a_mlflow(tabla)
    return tabla


def _a_mlflow(tabla: list[dict]) -> None:
    try:
        import mlflow
    except ImportError:
        return
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment(entrenamiento.EXPERIMENTO_MLFLOW + "-comparacion")
    for f in tabla:
        with mlflow.start_run(run_name=f"comparacion-{f['modelo']}"):
            mlflow.set_tag("algoritmo", f["modelo"])
            mlflow.log_metrics({k: float(v) for k, v in f.items() if isinstance(v, int | float) and k != "en_el_proyecto"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for f in comparar():
        log.info("%-20s AUC %.3f · recall %.2f · precisión %.2f", f["modelo"], f["auc"], f["recall"], f["precision"])
    log.info("guardado en %s", SALIDA)
    sys.exit(0)
