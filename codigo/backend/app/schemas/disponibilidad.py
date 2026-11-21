from datetime import date, time

from pydantic import BaseModel


class GenerarDisponibilidadIn(BaseModel):
    barber_id: int
    date_from: date
    date_to: date
    start: time = time(9)
    end: time = time(17)
    minutes: int = 30
    days: list[int] | None = None  # sin indicar, usa los días de trabajo del barbero
    dates: list[date] | None = None  # fechas concretas (tiene prioridad sobre el rango y los días)


class FranjaOut(BaseModel):
    date: str  # AAAA-MM-DD
    time: str  # HH:MM


class CerrarDiasIn(BaseModel):
    barber_id: int
    dates: list[date]


class DiaCalendarioOut(BaseModel):
    date: str
    total: int  # franjas del día
    ocupadas: int  # citas activas ese día
    bloqueo: str | None = None  # «Festivo: …» o «Ausencia: …» si ese día no se atiende
