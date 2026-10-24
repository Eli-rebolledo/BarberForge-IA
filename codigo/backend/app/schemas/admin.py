from pydantic import BaseModel

from app.schemas.cita import CitaOut


class MesOut(BaseModel):
    mes: str
    etiqueta: str
    total: int
    citas: int


class ServicioTopOut(BaseModel):
    nombre: str
    cantidad: int
    ingresos: int


class BarberoRendimientoOut(BaseModel):
    nombre: str
    citas: int
    completadas: int
    ingresos: int


class EstadisticasOut(BaseModel):
    ingresos_mes: int
    ingresos_mes_anterior: int
    ingresos_hoy: int
    por_cobrar: int
    citas_mes: int
    citas_hoy: int
    pendientes: int
    ticket_promedio: int
    tasa_cancelacion: int
    ingresos_6_meses: list[MesOut]
    estados: dict[str, int]
    top_servicios: list[ServicioTopOut]
    barberos: list[BarberoRendimientoOut]
    proximas: list[CitaOut]


class AjustesOut(BaseModel):
    barberia: str
    direccion: str
    horario: str
    recordatorio_minutos: int
    confirmar_minutos: int
    buzon_url: str
