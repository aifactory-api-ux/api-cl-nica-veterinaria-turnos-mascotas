"""Esquemas de entrada y de salida de la agenda de turnos.

``SolicitudTurno`` modela la reserva de un turno: la mascota, el veterinario
y el instante de inicio en formato ISO 8601. El formato de la fecha-hora lo
valida Pydantic, de modo que un valor que no sea ISO 8601 produce 422 sin
código adicional en el router.

``RespuestaTurno`` describe el turno tal y como se expone en la API, con su
estado (`scheduled` o `cancelled`) y los dos extremos de la franja reservada.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Estados posibles de un turno.
EstadoTurno = Literal["scheduled", "cancelled"]


class SolicitudTurno(BaseModel):
    """Datos necesarios para reservar un turno."""

    pet_id: int = Field(
        ...,
        description="Identificador de la mascota que asiste a la cita.",
        examples=[1],
    )
    vet_id: int = Field(
        ...,
        description="Identificador del veterinario que atiende la cita.",
        examples=[2],
    )
    start_at: datetime = Field(
        ...,
        description=(
            "Fecha y hora de inicio del turno en UTC, con formato ISO 8601 "
            "(por ejemplo `2030-06-10T10:00:00Z`)."
        ),
        examples=["2030-06-10T10:00:00Z"],
    )


class RespuestaTurno(BaseModel):
    """Turno de la agenda tal y como se devuelve en la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador del turno.")
    pet_id: int = Field(..., description="Identificador de la mascota.")
    vet_id: int = Field(..., description="Identificador del veterinario.")
    start_at: datetime = Field(
        ..., description="Instante de inicio del turno, en UTC."
    )
    end_at: datetime = Field(
        ..., description="Instante de finalización del turno, en UTC."
    )
    status: EstadoTurno = Field(
        ..., description="Estado del turno: `scheduled` o `cancelled`."
    )
