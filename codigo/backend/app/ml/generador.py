"""Generador de citas sintéticas para entrenar el modelo de inasistencias mientras no haya datos reales.

Es reproducible: con la misma semilla produce exactamente las mismas citas (lo verifica una prueba).
Cada regla de abajo está explicada, con su fuente, en ``supuestos.md``.

    python -m app.tareas generar-datos            # escribe datos/citas_sinteticas.csv
"""
import csv
import math
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from app.ml import caracteristicas as car

SEMILLA = 2026
NUM_CITAS = 5000
NUM_CLIENTES = 600
PROPORCION_INVITADOS = 0.22
INICIO = date(2026, 1, 5)  # lunes
DIAS = 300

# Catálogo igual al de la migración 002: (nombre, precio, minutos, probabilidad)
SERVICIOS = (
    ("Corte clásico", 25000, 30, 0.50),
    ("Barba perfilada", 18000, 20, 0.15),
    ("Combo corte + barba", 40000, 50, 0.25),
    ("Tratamiento capilar", 35000, 40, 0.10),
)
PROB_SEGUNDO_SERVICIO = 0.08

# Demanda por día (lunes … domingo) y por hora de inicio (8 a. m. … 7:30 p. m.).
PESO_DIA = (0.8, 0.9, 0.9, 1.0, 1.3, 1.6, 0.4)
HORAS = [h + m / 60 for h in range(8, 20) for m in (0, 30)]
PESO_HORA = [1.6 if 17 <= h < 19.5 else 1.2 if 10 <= h < 12 else 0.7 if h < 9 else 1.0 for h in HORAS]

# Anticipación en horas: (mínimo, máximo, probabilidad).
ANTICIPACION_REGISTRADOS = ((1, 10, 0.30), (14, 34, 0.25), (40, 80, 0.20), (90, 170, 0.15), (170, 500, 0.10))
ANTICIPACION_INVITADOS = ((0, 2, 0.70), (2, 72, 0.30))

# Efectos sobre la probabilidad de faltar (en escala logit: +0,4 ≈ +5 puntos porcentuales alrededor de 15 %).
INTERCEPTO = -0.45
EFECTO_ANTICIPACION = 0.55        # por cada unidad de log(1 + días): el predictor más fuerte en la literatura
EFECTO_FRANJA = (0.30, -0.10, 0.0, 0.20)
EFECTO_DIA = (0.15, 0.0, 0.0, 0.0, 0.05, -0.20, 0.25)
EFECTO_PRECIO_POR_MIL = -0.012    # citas más caras (combos) se cumplen un poco más
EFECTO_DOS_SERVICIOS = -0.15
TASA_INVITADOS = 0.20             # sin historial: propensión de la población, algo más alta
RUIDO = 0.25


def _logit(p: float) -> float:
    return math.log(p / (1 - p))


def _sigmoide(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _elegir(rng: np.random.Generator, opciones, pesos):
    pesos = np.asarray(pesos, dtype=float)
    return opciones[rng.choice(len(opciones), p=pesos / pesos.sum())]


def generar(semilla: int = SEMILLA, num_citas: int = NUM_CITAS) -> list[dict]:
    """Devuelve las citas ordenadas por fecha, cada una con sus características y si hubo inasistencia."""
    rng = np.random.default_rng(semilla)

    # Cada cliente tiene una «propensión a faltar» oculta (Beta con media ≈ 15 %) y una frecuencia de visitas.
    propension = rng.beta(1.3, 7.5, NUM_CLIENTES)
    frecuencia = rng.gamma(2.0, 1.0, NUM_CLIENTES)

    dias = [INICIO + timedelta(days=d) for d in range(DIAS)]
    citas = []
    for _ in range(num_citas):
        dia = _elegir(rng, dias, [PESO_DIA[d.weekday()] for d in dias])
        hora = _elegir(rng, HORAS, PESO_HORA)
        inicio = datetime.combine(dia, datetime.min.time()) + timedelta(hours=hora)
        invitado = rng.random() < PROPORCION_INVITADOS
        cliente = None if invitado else int(rng.choice(NUM_CLIENTES, p=frecuencia / frecuencia.sum()))
        rango = _elegir(rng, ANTICIPACION_INVITADOS if invitado else ANTICIPACION_REGISTRADOS,
                        [r[2] for r in (ANTICIPACION_INVITADOS if invitado else ANTICIPACION_REGISTRADOS)])
        anticipacion = float(rng.uniform(rango[0], rango[1]))
        principal = _elegir(rng, SERVICIOS, [s[3] for s in SERVICIOS])
        servicios = [principal]
        if principal[0] != "Combo corte + barba" and rng.random() < PROB_SEGUNDO_SERVICIO:
            servicios.append(_elegir(rng, [s for s in SERVICIOS if s is not principal], [1, 1, 1]))
        citas.append({"cliente": cliente, "inicio": inicio, "creada": inicio - timedelta(hours=anticipacion),
                      "servicios": servicios, "ruido": float(rng.normal(0, RUIDO)),
                      "azar": float(rng.random()), "ruido_invitado": float(rng.normal(0, 0.6))})

    citas.sort(key=lambda c: c["inicio"])
    historial: dict[int, list[tuple[datetime, int]]] = {}
    filas = []
    for c in citas:
        invitado = c["cliente"] is None
        previas = [] if invitado else [y for fin, y in historial.get(c["cliente"], []) if fin < c["creada"]]
        hora = c["inicio"].hour + c["inicio"].minute / 60
        anticipacion = (c["inicio"] - c["creada"]).total_seconds() / 3600
        precio = sum(s[1] for s in c["servicios"])
        x = car.construir(dia_semana=c["inicio"].weekday(), hora=hora, anticipacion_horas=anticipacion,
                          es_invitado=invitado, citas_previas=len(previas), faltas_previas=sum(previas),
                          precio_cop=precio,
                          num_servicios=len(c["servicios"]))

        base = (_logit(TASA_INVITADOS) + c["ruido_invitado"]) if invitado else _logit(propension[c["cliente"]])
        z = (base + INTERCEPTO
             + EFECTO_ANTICIPACION * math.log1p(anticipacion / 24)
             + EFECTO_FRANJA[x.franja] + EFECTO_DIA[x.dia_semana]
             + EFECTO_PRECIO_POR_MIL * (precio / 1000 - 30)
             + (EFECTO_DOS_SERVICIOS if len(c["servicios"]) > 1 else 0.0)
             + c["ruido"])
        probabilidad = _sigmoide(z)
        falto = int(c["azar"] < probabilidad)
        if not invitado:
            historial.setdefault(c["cliente"], []).append((c["inicio"], falto))
        filas.append({"fecha": c["inicio"].strftime("%Y-%m-%d %H:%M"), "cliente": "" if invitado else c["cliente"],
                      **asdict(x), "probabilidad_real": round(probabilidad, 4), "inasistencia": falto})
    return filas


def guardar_csv(filas: list[dict], ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


def leer_csv(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8") as f:
        return [{k: (v if k in ("fecha", "cliente") else float(v)) for k, v in fila.items()} for fila in csv.DictReader(f)]
