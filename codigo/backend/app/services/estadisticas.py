"""Indicadores del panel del administrador: ingresos, citas, servicios y barberos."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.tiempo import hoy
from app.models import Cita, Usuario
from app.models.cita import ESTADOS_ACTIVOS
from app.schemas.admin import (
    AjustesOut,
    BarberoRendimientoOut,
    EstadisticasOut,
    MesOut,
    ServicioTopOut,
)
from app.services import barberia, citas

MESES = ["ene.", "feb.", "mar.", "abr.", "may.", "jun.", "jul.", "ago.", "sept.", "oct.", "nov.", "dic."]


def _mes_atras(d: date, n: int) -> date:
    i = d.year * 12 + d.month - 1 - n
    return date(i // 12, i % 12 + 1, 1)


def _precio(c: Cita) -> int:
    return c.price_cop or c.servicio.price_cop


def resumen(db: Session) -> EstadisticasOut:
    h = hoy()
    inicio, anterior = h.replace(day=1), _mes_atras(h, 1)
    todas = list(db.scalars(select(Cita).where(Cita.appointment_date >= _mes_atras(h, 5))).unique())
    ingreso = lambda c: _precio(c) if c.status == "completada" else 0  # noqa: E731 - solo cuenta lo realizado
    mes = [c for c in todas if c.appointment_date >= inicio]
    previo = [c for c in todas if anterior <= c.appointment_date < inicio]
    meses = []
    for n in range(5, -1, -1):
        d0 = _mes_atras(h, n)
        d1 = _mes_atras(h, n - 1) if n else h + timedelta(days=1)
        grupo = [c for c in todas if d0 <= c.appointment_date < d1] if n else mes
        meses.append(MesOut(mes=f"{d0:%Y-%m}", etiqueta=MESES[d0.month - 1], total=sum(map(ingreso, grupo)),
                            citas=sum(c.status == "completada" for c in grupo)))
    estados: dict[str, int] = {}
    for c in mes:
        estados[c.status] = estados.get(c.status, 0) + 1
    cuenta = [c for c in mes if c.status in (*ESTADOS_ACTIVOS, "completada")]
    top: dict[str, list[int]] = {}
    for c in cuenta:
        for s in (c.servicios or [c.servicio]):
            fila = top.setdefault(s.name, [0, 0])
            fila[0] += 1
            fila[1] += s.price_cop if c.status == "completada" else 0
    por_barbero: dict[str, list[int]] = {}
    for c in cuenta:
        fila = por_barbero.setdefault(c.barbero.full_name, [0, 0, 0])
        fila[0] += 1
        fila[1] += c.status == "completada"
        fila[2] += ingreso(c)
    hechas = [c for c in mes if c.status == "completada"]
    perdidas = sum(c.status.startswith("cancelada") or c.status == "inasistencia" for c in mes)
    activas = [c for c in todas if c.status in ESTADOS_ACTIVOS and c.appointment_date >= h]
    proximas = sorted(activas, key=lambda c: (c.appointment_date, c.start_time))[:6]
    return EstadisticasOut(
        ingresos_mes=sum(map(ingreso, mes)), ingresos_mes_anterior=sum(map(ingreso, previo)),
        ingresos_hoy=sum(ingreso(c) for c in mes if c.appointment_date == h),
        por_cobrar=sum(_precio(c) for c in activas), citas_mes=len(mes),
        citas_hoy=sum(c.appointment_date == h and c.status in (*ESTADOS_ACTIVOS, "completada") for c in mes),
        pendientes=sum(c.status == "pendiente" for c in activas),
        ticket_promedio=sum(map(ingreso, hechas)) // len(hechas) if hechas else 0,
        tasa_cancelacion=round(100 * perdidas / len(mes)) if mes else 0,
        ingresos_6_meses=meses, estados=estados,
        top_servicios=[ServicioTopOut(nombre=k, cantidad=v[0], ingresos=v[1])
                       for k, v in sorted(top.items(), key=lambda x: -x[1][0])[:5]],
        barberos=[BarberoRendimientoOut(nombre=k, citas=v[0], completadas=v[1], ingresos=v[2])
                  for k, v in sorted(por_barbero.items(), key=lambda x: -x[1][2])],
        proximas=[citas._salida(c) for c in proximas])


def ajustes(db: Session) -> AjustesOut:
    s, f = get_settings(), barberia.ficha(db)
    return AjustesOut(barberia=f.nombre, direccion=f.direccion, horario=f.horario, buzon_url=s.mailhog_url,
                      recordatorio_minutos=citas.MINUTOS_RECORDATORIO, confirmar_minutos=citas.MINUTOS_PARA_CONFIRMAR)


def clientes(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).where(Usuario.role == "cliente", Usuario.is_active)
                           .order_by(Usuario.full_name)))
