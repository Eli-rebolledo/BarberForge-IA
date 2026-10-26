"""Tareas de una sola vez para Kubernetes (Job) o mantenimiento manual.

    python -m app.tareas migrar     # alembic upgrade head + datos iniciales (admin y agenda de la semana)
    python -m app.tareas indexar    # reconstruye el índice del asistente

En Kubernetes, el Job de migraciones corre antes de actualizar la API, así las réplicas nuevas nunca
arrancan con un esquema viejo."""
import logging
import sys
import time

from app.services import arranque

log = logging.getLogger("barberforge.tareas")


def migrar(reintentos: int = 30) -> None:
    for intento in range(1, reintentos + 1):
        try:
            arranque.migrar()
            arranque.preparar_datos()
            log.info("migraciones aplicadas y datos iniciales listos")
            return
        except Exception as e:  # noqa: BLE001 - la base puede estar arrancando: se reintenta
            log.warning("intento %s/%s: la base aún no responde (%s)", intento, reintentos, type(e).__name__)
            time.sleep(5)
    raise SystemExit("No se pudo conectar a la base de datos")


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    orden = argv[1] if len(argv) > 1 else ""
    if orden == "migrar":
        migrar()
    elif orden == "indexar":
        ok = arranque._reindexar()
        log.info("índice reconstruido (%s)", "con embeddings" if ok else "solo palabras clave")
    else:
        raise SystemExit("Uso: python -m app.tareas [migrar|indexar]")


if __name__ == "__main__":
    main(sys.argv)
