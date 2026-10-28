"""Directorio de veterinarios de la clínica.

``GET /vets`` devuelve el identificador y el correo de cada usuario con rol
``vet`` para que los clientes puedan elegir con quién agendar un turno.

La respuesta se modela con un esquema propio que expone únicamente esos dos
campos: el hash de contraseña nunca forma parte del cuerpo, aunque la consulta
lea la fila completa del usuario.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import ROLE_VET, User

router = APIRouter(prefix="/vets", tags=["veterinarios"])


class Veterinario(BaseModel):
    """Identidad pública de un veterinario del directorio."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador del veterinario.")
    email: str = Field(..., description="Correo del veterinario.")


@router.get(
    "",
    response_model=list[Veterinario],
    summary="Listado de veterinarios",
    dependencies=[Depends(get_current_user)],
)
def listar_veterinarios(sesion: Session = Depends(get_db)) -> list[Veterinario]:
    """Devuelve los veterinarios registrados en la clínica.

    Exige un token Bearer válido: sin encabezado ``Authorization`` o con un
    token inválido la API responde 401. El orden por identificador mantiene
    estable el listado entre llamadas.
    """
    veterinarios = sesion.scalars(
        select(User).where(User.role == ROLE_VET).order_by(User.id)
    ).all()

    return [
        Veterinario(id=veterinario.id, email=veterinario.email)
        for veterinario in veterinarios
    ]
