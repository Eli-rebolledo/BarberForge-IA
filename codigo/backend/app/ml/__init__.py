"""Predicción de inasistencias (feature 011).

    caracteristicas.py   variables del modelo: las MISMAS en el generador, el entrenamiento y la app
    generador.py         citas sintéticas reproducibles (no hay datos reales todavía; ver supuestos.md)
    entrenamiento.py     regresión logística vs. árbol de decisión, división por fecha, métricas y MLflow
    modelo_inasistencia.joblib   modelo empaquetado en la imagen (se regenera con «python -m app.tareas entrenar»)
"""
