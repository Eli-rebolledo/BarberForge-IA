from datetime import date, time

from pydantic import BaseModel


class CitaIn(BaseModel):
    barber_id: int | None = None  # un barbero que agenda siempre lo hace en su propia agenda
    service_ids: list[int] = []
    service_id: int | None = None  # compatibilidad: un solo servicio
    date: date
    time: time
    # Solo para barberos y administradores (cita creada en el local):
    client_id: int | None = None
    guest_name: str | None = None
    guest_phone: str | None = None
    guest_email: str | None = None


class CitaCreadaOut(BaseModel):
    id: int


class CitaOut(BaseModel):
    id: int
    date: date
    time: str  # HH:MM
    status: str
    service: str  # nombres unidos con " + "
    services: list[str]
    barber: str
    barber_id: int
    client: str
    client_phone: str | None = None
    walk_in: bool = False
    price: int
    duration: int
    # Feature 011: solo lo ven el barbero y el administrador (al cliente no se le muestra su «riesgo»).
    riesgo: float | None = None
    riesgo_alto: bool = False


class EstadoCitaIn(BaseModel):
    status: str
