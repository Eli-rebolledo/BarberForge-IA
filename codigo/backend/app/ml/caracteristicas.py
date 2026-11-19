"""Variables del modelo de inasistencias.

Un solo lugar define qué ve el modelo, para que el generador sintético, el entrenamiento y la API calculen
exactamente lo mismo (si cada uno lo calculara a su manera, el modelo aprendería una cosa y en producción
recibiría otra).

Solo se usan datos que la app conoce EN EL MOMENTO DE AGENDAR. Por eso no está «confirmó el recordatorio»:
el aviso de 60 minutos se decide antes de que exista esa confirmación. Tampoco hay género, edad ni barrio:
la app no los pide y no hacen falta para decidir si mandar un correo más. La duración del servicio tampoco:
va casi pegada al precio y, con las dos, los coeficientes de la regresión se vuelven difíciles de explicar.
"""
from dataclasses import astuple, dataclass

# Probabilidad previa de faltar (15 %) para suavizar la tasa de clientes con poco historial:
# un cliente que faltó 1 de 1 citas no tiene «100 % de riesgo».
TASA_PREVIA = 0.15
PESO_PREVIO = 2.0
ANTICIPACION_MAXIMA_H = 24 * 30  # más de 30 días se trata igual que 30 días

NOMBRES = (
    "dia_semana",          # 0 = lunes … 6 = domingo
    "franja",              # 0 = antes de 10 a. m., 1 = 10 a 12, 2 = 12 a 5 p. m., 3 = desde las 5 p. m.
    "hora",                # 14.5 = 2:30 p. m.
    "anticipacion_horas",  # horas entre el momento de agendar y la cita
    "es_invitado",         # 1 = cita en el local sin cuenta (no hay historial)
    "citas_previas",       # citas anteriores del cliente ya cerradas (completadas o inasistencias)
    "faltas_previas",      # de esas, cuántas fueron inasistencias
    "tasa_faltas",         # faltas / citas, suavizada con TASA_PREVIA
    "precio_miles",        # precio total en miles de pesos
    "num_servicios",
)
# Índices por tipo, para el preprocesamiento del modelo.
CATEGORICAS = (0, 1)
LOGARITMICAS = (3, 5, 6)  # se transforman con log(1 + x): la diferencia entre 1 y 2 días importa más que entre 20 y 21
NUMERICAS = (2, 4, 7, 8, 9)


@dataclass(frozen=True)
class Caracteristicas:
    dia_semana: int
    franja: int
    hora: float
    anticipacion_horas: float
    es_invitado: int
    citas_previas: int
    faltas_previas: int
    tasa_faltas: float
    precio_miles: float
    num_servicios: int

    def vector(self) -> list[float]:
        return [float(x) for x in astuple(self)]


def franja_de(hora: float) -> int:
    if hora < 10:
        return 0
    if hora < 12:
        return 1
    if hora < 17:
        return 2
    return 3


def tasa_suavizada(citas: int, faltas: int) -> float:
    return (faltas + TASA_PREVIA * PESO_PREVIO) / (citas + PESO_PREVIO)


def construir(*, dia_semana: int, hora: float, anticipacion_horas: float, es_invitado: bool,
              citas_previas: int, faltas_previas: int, precio_cop: int,
              num_servicios: int) -> Caracteristicas:
    citas = 0 if es_invitado else max(0, citas_previas)
    faltas = 0 if es_invitado else min(max(0, faltas_previas), citas)
    return Caracteristicas(
        dia_semana=dia_semana,
        franja=franja_de(hora),
        hora=round(hora, 2),
        anticipacion_horas=round(min(max(0.0, anticipacion_horas), ANTICIPACION_MAXIMA_H), 2),
        es_invitado=int(es_invitado),
        citas_previas=citas,
        faltas_previas=faltas,
        tasa_faltas=round(tasa_suavizada(citas, faltas), 4),
        precio_miles=round(precio_cop / 1000, 1),
        num_servicios=max(1, num_servicios),
    )
