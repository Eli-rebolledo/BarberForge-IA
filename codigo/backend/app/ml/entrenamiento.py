"""Entrena y compara tres modelos de inasistencia: regresión logística, árbol de decisión y Random Forest.
(XGBoost se probó aparte, en app/ml/comparar_modelos.py, sin meterlo en la imagen de la API.)

- División POR FECHA: entrena con el 80 % más antiguo y evalúa con el 20 % más reciente. Así se simula lo que
  pasa en la vida real (el modelo predice citas futuras), y es más honesto que mezclar al azar.
- Métricas: AUC, precisión y recall con el umbral de decisión, matriz de confusión y Brier.
- Gana el de mayor AUC; si empatan, la regresión logística (es más fácil de explicar).
- Si MLflow está instalado (requirements-ml.txt), cada entrenamiento queda registrado como un «run».

    python -m app.tareas entrenar                 # datos sintéticos → app/ml/modelo_inasistencia.joblib
"""
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from app.ml import caracteristicas as car

log = logging.getLogger("barberforge.ml")

RUTA_MODELO = Path(__file__).with_name("modelo_inasistencia.joblib")
UMBRAL = 0.20  # ver supuestos.md: con 0,20 se detectan ~6 de cada 10 inasistencias
PROPORCION_PRUEBA = 0.20
EXPERIMENTO_MLFLOW = "barberforge-inasistencias"


def _preprocesamiento() -> ColumnTransformer:
    return ColumnTransformer([
        ("categoricas", OneHotEncoder(categories=[list(range(7)), list(range(4))], handle_unknown="ignore"),
         list(car.CATEGORICAS)),
        ("logaritmicas", make_pipeline(FunctionTransformer(np.log1p, feature_names_out="one-to-one"), StandardScaler()),
         list(car.LOGARITMICAS)),
        ("numericas", StandardScaler(), list(car.NUMERICAS)),
    ])


def candidatos(semilla: int = 2026) -> dict[str, Pipeline]:
    return {
        "regresion_logistica": Pipeline([("pre", _preprocesamiento()),
                                         ("modelo", LogisticRegression(max_iter=2000, C=1.0))]),
        "arbol_decision": Pipeline([("modelo", DecisionTreeClassifier(max_depth=5, min_samples_leaf=40,
                                                                      random_state=semilla))]),
        # Muchos árboles con datos y variables al azar: menos sobreajuste que un solo árbol.
        "random_forest": Pipeline([("modelo", RandomForestClassifier(n_estimators=200, max_depth=6,
                                                                     min_samples_leaf=20, n_jobs=1,
                                                                     random_state=semilla))]),
    }


def matriz(filas: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    x = np.array([[float(f[n]) for n in car.NOMBRES] for f in filas], dtype=float)
    y = np.array([int(f["inasistencia"]) for f in filas], dtype=int)
    return x, y


def dividir_por_fecha(filas: list[dict]) -> tuple[list[dict], list[dict]]:
    ordenadas = sorted(filas, key=lambda f: f["fecha"])
    corte = int(len(ordenadas) * (1 - PROPORCION_PRUEBA))
    return ordenadas[:corte], ordenadas[corte:]


def evaluar(modelo, x: np.ndarray, y: np.ndarray, umbral: float = UMBRAL) -> dict:
    p = modelo.predict_proba(x)[:, 1]
    pred = (p >= umbral).astype(int)
    vn, fp, fn, vp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "auc": round(float(roc_auc_score(y, p)), 3) if len(set(y)) > 1 else None,
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "brier": round(float(brier_score_loss(y, p)), 4),
        "tasa_inasistencia": round(float(y.mean()), 4),
        "alertas_pct": round(float(pred.mean()), 4),
        "matriz": {"verdaderos_negativos": int(vn), "falsos_positivos": int(fp),
                   "falsos_negativos": int(fn), "verdaderos_positivos": int(vp)},
        "n": int(len(y)),
    }


def importancia(nombre: str, modelo: Pipeline) -> dict[str, float]:
    """Coeficientes (logística) o importancia (árbol y Random Forest), para explicar el modelo en la sustentación."""
    final = modelo.named_steps["modelo"]
    if nombre == "regresion_logistica":
        nombres = ([f"dia_semana={d}" for d in range(7)] + [f"franja={f}" for f in range(4)]
                   + [car.NOMBRES[i] for i in car.LOGARITMICAS] + [car.NOMBRES[i] for i in car.NUMERICAS])
        valores = final.coef_[0]
    else:
        nombres, valores = list(car.NOMBRES), final.feature_importances_
    pares = sorted(zip(nombres, (round(float(v), 4) for v in valores), strict=True), key=lambda p: -abs(p[1]))
    return dict(pares)


def entrenar(filas: list[dict], origen: str, umbral: float = UMBRAL, semilla: int = 2026) -> tuple[dict, dict]:
    """Entrena los candidatos, elige el mejor y lo vuelve a entrenar con TODOS los datos.
    Devuelve (paquete, resultados). El paquete es lo que se guarda y lo que la app carga."""
    entrenamiento, prueba = dividir_por_fecha(filas)
    x_ent, y_ent = matriz(entrenamiento)
    x_pru, y_pru = matriz(prueba)
    if len(set(y_ent)) < 2:
        raise ValueError("Los datos de entrenamiento no tienen citas cumplidas e inasistencias a la vez")

    resultados = {}
    for nombre, modelo in candidatos(semilla).items():
        modelo.fit(x_ent, y_ent)
        resultados[nombre] = {"metricas": evaluar(modelo, x_pru, y_pru, umbral), "importancia": importancia(nombre, modelo)}

    ganador = max(resultados, key=lambda n: (resultados[n]["metricas"]["auc"] or 0, n == "regresion_logistica"))
    final = candidatos(semilla)[ganador]
    x_todo, y_todo = matriz(filas)
    final.fit(x_todo, y_todo)

    ahora = datetime.now(UTC)
    paquete = {
        "modelo": final,
        "version": f"{origen}-{ganador}-{ahora:%Y%m%d%H%M}",
        "origen": origen,  # «sintetico» o «real»
        "algoritmo": ganador,
        "caracteristicas": list(car.NOMBRES),
        "umbral": umbral,
        "metricas": resultados[ganador]["metricas"],
        "comparacion": {n: r["metricas"] for n, r in resultados.items()},
        "importancia": resultados[ganador]["importancia"],
        "filas_entrenamiento": len(entrenamiento),
        "filas_prueba": len(prueba),
        "entrenado": ahora.isoformat(timespec="seconds"),
        "sklearn": sklearn.__version__,
    }
    return paquete, resultados


def guardar(paquete: dict, ruta: Path = RUTA_MODELO) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(paquete, ruta, compress=3)
    return ruta


def cargar(ruta: Path = RUTA_MODELO) -> dict:
    return joblib.load(ruta)


def registrar_en_mlflow(paquete: dict, resultados: dict, parametros: dict) -> str | None:
    """Registra un run por candidato y marca el ganador. Si MLflow no está instalado, no hace nada.

    Por defecto guarda en codigo/backend/mlflow.db; se ve con:
        mlflow ui --backend-store-uri sqlite:///mlflow.db
    """
    try:
        import mlflow
    except ImportError:
        log.info("MLflow no está instalado (pip install -r requirements-ml.txt): no se registra el experimento")
        return None
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment(EXPERIMENTO_MLFLOW)
    id_ganador = None
    for nombre, r in resultados.items():
        with mlflow.start_run(run_name=f"{paquete['origen']}-{nombre}") as run:
            mlflow.set_tags({"origen": paquete["origen"], "algoritmo": nombre,
                             "ganador": str(nombre == paquete["algoritmo"]).lower()})
            mlflow.log_params({**parametros, "algoritmo": nombre, "umbral": paquete["umbral"],
                               "filas_entrenamiento": paquete["filas_entrenamiento"],
                               "filas_prueba": paquete["filas_prueba"]})
            m = r["metricas"]
            mlflow.log_metrics({k: v for k, v in m.items() if isinstance(v, int | float)})
            mlflow.log_metrics({k: float(v) for k, v in m["matriz"].items()})
            mlflow.log_dict(r["importancia"], "importancia.json")
            if nombre == paquete["algoritmo"]:
                mlflow.log_dict({k: v for k, v in paquete.items() if k != "modelo"}, "paquete.json")
                mlflow.sklearn.log_model(paquete["modelo"], name="modelo")
                id_ganador = run.info.run_id
    return id_ganador
