"""Endpoints de registro y listado de mascotas.

``POST /pets`` permite a un cliente registrar una mascota a su nombre y
``GET /pets`` devuelve el catálogo de mascotas del cliente autenticado.

Las dos operaciones exigen un token Bearer válido. El registro está reservado
a los clientes (un veterinario recibe 403) y el listado no filtra por rol, sino
por propietario: un veterinarian no tiene mascotas, así que su listado es un
arreglo vacío.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_client
from app.db.base import get_db
from app.db.models import Pet, User
from app.schemas.pet import RespuestaMascota, SolicitudMascota

router = APIRouter(prefix="/pets", tags=["mascotas"])

Sesion = Annotated[Session, Depends(get_db)]
Cliente = Annotated[User, Depends(require_client)]
Usuario = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=RespuestaMascota,
    status_code=status.HTTP_201_CREATED,
    summary="Registro de una mascota",
)
def registrar_mascota(
    solicitud: SolicitudMascota,
    cliente: Cliente,
    sesion: Sesion,
) -> RespuestaMascota:
    """Registra una mascota a nombre del cliente autenticado.

    El ``owner_id`` de la mascota es siempre el identificador del cliente que
    envía la petición: el cuerpo de la petición no puede atribuir la mascota a
    otro propietario.

    Responde 403 si quien llama es un veterinario y 422 si la especie no está
    admitida o la fecha de nacimiento es posterior al día actual.
    """
    mascota = Pet(
        name=solicitud.name,
        species=solicitud.species,
        birth_date=solicitud.birth_date,
        owner_id=cliente.id,
    )
    sesion.add(mascota)
    sesion.commit()
    sesion.refresh(mascota)

    return RespuestaMascota(
        id=mascota.id,
        name=mascota.name,
        species=mascota.species,
        birth_date=mascota.birth_date,
        owner_id=mascota.owner_id,
    )


@router.get(
    "",
    response_model=list[RespuestaMascota],
    summary="Listado de las mascotas del cliente autenticado",
)
def listar_mascotas(usuario: Usuario, sesion: Sesion) -> list[RespuestaMascota]:
    """Devuelve las mascotas cuyo propietario es el usuario autenticado.

    El listado es un arreglo completo, sin paginación ni filtros, y se ordena
    por identificador para que sea estable entre llamadas. Un cliente sin
    mascotas y un veterinario reciben un arreglo vacío.
    """
    mascotas = sesion.scalars(
        select(Pet).where(Pet.owner_id == usuario.id).order_by(Pet.id)
    ).all()

    return [
        RespuestaMascota(
            id=mascota.id,
            name=mascota.name,
            species=mascota.species,
            birth_date=mascota.birth_date,
            owner_id=mascota.owner_id,
        )
        for mascota in mascotas
    ]
