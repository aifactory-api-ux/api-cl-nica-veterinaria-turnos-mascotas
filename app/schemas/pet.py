"""Esquemas de entrada y de salida del módulo de mascotas.

El esquema de registro concentra las dos reglas que la clínica impone a una
mascota: la especie debe pertenecer al catálogo admitido (``dog``, ``cat`` u
``other``) y la fecha de nacimiento no puede ser posterior al día actual. Ambas
se validan con Pydantic, de modo que la API responde 422 sin código adicional
en el router.
"""

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Especies admitidas para una mascota. Coinciden con las constantes
# SPECIES_DOG, SPECIES_CAT y SPECIES_OTHER de ``app.db.models``.
EspecieMascota = Literal["dog", "cat", "other"]

# Longitud máxima del nombre de una mascota, igual al tamaño de su columna.
MAX_NOMBRE_MASCOTA = 120


def _hoy_en_utc() -> date:
    """Devuelve el día actual en UTC, la zona con la que se interpretan las fechas."""
    return datetime.now(timezone.utc).date()


class SolicitudMascota(BaseModel):
    """Datos necesarios para registrar una mascota."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_NOMBRE_MASCOTA,
        description="Nombre de la mascota.",
        examples=["Firulais"],
    )
    species: EspecieMascota = Field(
        ...,
        description="Especie de la mascota: `dog`, `cat` u `other`.",
        examples=["dog"],
    )
    birth_date: date = Field(
        ...,
        description="Fecha de nacimiento de la mascota, que no puede ser futura.",
        examples=["2020-05-10"],
    )

    @field_validator("name")
    @classmethod
    def _recortar_nombre(cls, valor: str) -> str:
        """Elimina los espacios accidentales y descarta los nombres vacíos."""
        nombre = valor.strip()
        if not nombre:
            raise ValueError("El nombre de la mascota no puede estar vacío.")
        return nombre

    @field_validator("birth_date")
    @classmethod
    def _rechazar_fecha_futura(cls, valor: date) -> date:
        """Rechaza las fechas de nacimiento posteriores al día actual."""
        if valor > _hoy_en_utc():
            raise ValueError(
                "La fecha de nacimiento no puede ser posterior al día actual."
            )
        return valor


class RespuestaMascota(BaseModel):
    """Datos públicos de una mascota registrada en la clínica."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador de la mascota.")
    name: str = Field(..., description="Nombre de la mascota.")
    species: EspecieMascota = Field(..., description="Especie de la mascota.")
    birth_date: date = Field(..., description="Fecha de nacimiento de la mascota.")
    owner_id: int = Field(
        ..., description="Identificador del cliente dueño de la mascota."
    )
