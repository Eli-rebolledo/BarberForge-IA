"""BarberForge AI - API: autenticación, catálogo, agendamiento, asistente RAG y recordatorios."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app import db as bd
from app.config import get_settings
from app.core import telemetria
from app.routers import (
    admin,
    asistente,
    auth,
    barberias,
    barberos,
    chat,
    citas,
    cuenta,
    disponibilidad,
    health,
    servicios,
)
from app.services import arranque
from app.services.errores import ErrorDominio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("barberforge")


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    tareas = []
    s = get_settings()
    if s.tareas_fondo:
        tareas = [asyncio.create_task(arranque.iniciar_base_de_datos())]
        if s.indexar_al_arrancar:
            tareas.append(asyncio.create_task(arranque.indexar_asistente()))
        if s.ejecutar_recordatorios:
            tareas.append(asyncio.create_task(arranque.recordatorios()))
    yield
    for t in tareas:
        t.cancel()


VERSION = "1.1.0"
app = FastAPI(title="BarberForge AI", version=VERSION, lifespan=ciclo_de_vida)
telemetria.configurar(app, bd.engine, VERSION)

if get_settings().origenes_cors:
    app.add_middleware(CORSMiddleware, allow_origins=get_settings().origenes_cors,
                       allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ErrorDominio)
async def error_de_dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detalle()})


@app.exception_handler(OperationalError)
async def base_no_disponible(_: Request, exc: OperationalError) -> JSONResponse:
    log.error("error de base de datos: %s", str(exc.orig)[:200])
    return JSONResponse(status_code=503,
                        content={"detail": "La base de datos no está disponible. Intenta de nuevo en unos segundos."})


for modulo in (health, admin, auth, cuenta, barberias, servicios, barberos, disponibilidad, citas, chat,
               asistente):
    app.include_router(modulo.router)
