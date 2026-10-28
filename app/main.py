"""Punto de entrada de la aplicación FastAPI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import appointments, auth, health, pets, vets
from app.db.base import Base, engine

logger = logging.getLogger(__name__)


def _preparar_esquema() -> None:
    """Crea las tablas del dominio si todavía no existen.

    La sonda de salud no depende de la base de datos, así que si el motor no
    está disponible se registra el aviso y la API sigue aceptando peticiones.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as error:
        logger.warning(
            "No se pudo preparar el esquema de la base de datos: %s", error
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Prepara el esquema antes de atender la primera petición."""
    _preparar_esquema()
    yield


app = FastAPI(
    title="API Clínica Veterinaria",
    description=(
        "API REST de la clínica veterinaria: registro de usuarios, "
        "mascotas y agenda de turnos con veterinarios."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(vets.router)
app.include_router(pets.router)
app.include_router(appointments.router)
