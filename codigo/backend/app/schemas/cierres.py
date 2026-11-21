from datetime import date

from pydantic import BaseModel, Field


class FestivoIn(BaseModel):
    date: date
    date_to: date | None = None  # opcional: cierra varios días seguidos (p. ej. vacaciones colectivas)
    motivo: str = Field(default="Festivo", max_length=80)


class FestivosColombiaIn(BaseModel):
    year: int


class FestivoOut(BaseModel):
    id: int
    date: date
    motivo: str


class FestivoCreadoOut(BaseModel):
    id: int
    dias: int        # días cerrados (1 si no se indicó date_to)
    canceladas: int  # citas activas de esos días que se cancelaron (con aviso por correo)


class FestivosCargadosOut(BaseModel):
    creados: int
    canceladas: int


class CitaAfectadaOut(BaseModel):
    id: int
    date: date
    time: str
    client: str
    barber: str
    service: str


class AusenciaIn(BaseModel):
    date_from: date
    date_to: date
    motivo: str = Field(default="Ausencia", max_length=80)


class AusenciaOut(BaseModel):
    id: int
    barber_id: int
    barber: str
    date_from: date
    date_to: date
    motivo: str


class AusenciaCreadaOut(BaseModel):
    id: int
    reasignadas: int
    canceladas: int
