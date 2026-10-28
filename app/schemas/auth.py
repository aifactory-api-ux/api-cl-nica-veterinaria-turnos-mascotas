"""Esquemas de entrada y de salida del módulo de autenticación.

Los esquemas concentran la validación de la entrada: una contraseña demasiado
corta o un rol no admitido producen 422 de forma nativa de FastAPI, sin
código adicional en los routers.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Roles admitidos por la plataforma.
RolUsuario = Literal["client", "vet"]

# Longitud mínima de la contraseña de acceso.
MIN_PASSWORD_LENGTH = 8


class SolicitudRegistro(BaseModel):
    """Datos necesarios para registrar un usuario de la clínica."""

    email: str = Field(
        ...,
        min_length=3,
        max_length=320,
        description="Correo único del usuario.",
        examples=["cliente@clinica.test"],
    )
    password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        description="Contraseña de acceso, de al menos 8 caracteres.",
        examples=["secreto123"],
    )
    role: RolUsuario = Field(
        ...,
        description="Rol del usuario: `client` o `vet`.",
        examples=["client"],
    )

    @field_validator("email")
    @classmethod
    def _recortar_email(cls, valor: str) -> str:
        """Elimina los espacios accidentales del correo."""
        return valor.strip()


class SolicitudLogin(BaseModel):
    """Credenciales para iniciar sesión."""

    email: str = Field(
        ...,
        max_length=320,
        description="Correo con el que se registró el usuario.",
        examples=["cliente@clinica.test"],
    )
    password: str = Field(
        ...,
        description="Contraseña del usuario.",
        examples=["secreto123"],
    )

    @field_validator("email")
    @classmethod
    def _recortar_email(cls, valor: str) -> str:
        """Elimina los espacios accidentales del correo."""
        return valor.strip()


class RespuestaRegistro(BaseModel):
    """Identidad pública del usuario recién registrado."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador del usuario creado.")
    email: str = Field(..., description="Correo del usuario creado.")
    role: RolUsuario = Field(..., description="Rol del usuario creado.")


class RespuestaToken(BaseModel):
    """Token de acceso emitido tras un inicio de sesión correcto."""

    access_token: str = Field(..., description="Token JWT de acceso.")
    token_type: Literal["bearer"] = Field(
        default="bearer", description="Tipo de token que se debe enviar."
    )
