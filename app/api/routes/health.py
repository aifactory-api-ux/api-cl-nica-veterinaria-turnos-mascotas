"""Sonda de disponibilidad del servicio.

``GET /health`` es un endpoint público: no exige encabezado ``Authorization``
ni consulta la base de datos, de modo que el monitoreo pueda comprobar que la
API está levantada sin depender del estado del resto de componentes.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["salud"])


class EstadoSalud(BaseModel):
    """Cuerpo de la respuesta de la sonda de salud."""

    status: Literal["ok"] = "ok"


@router.get(
    "/health",
    response_model=EstadoSalud,
    summary="Sonda de disponibilidad del servicio",
)
def consultar_salud() -> EstadoSalud:
    """Indica que la API está disponible.

    Un encabezado ``Authorization`` ausente o con un token inválido no altera
    la respuesta: el endpoint no valida credenciales.
    """
    return EstadoSalud(status="ok")
