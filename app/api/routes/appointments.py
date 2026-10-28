"""Endpoints de la agenda de turnos.

El módulo expone las tres operaciones de la agenda:

- ``POST /appointments`` reserva un turno para una mascota propia.
- ``GET /appointments`` lista los turnos del cliente o del veterinario según
  el token presentado.
- ``POST /appointments/{id}/cancel`` cancela un turno ya reservado.

Las reglas de franja horaria viven en ``app.services.scheduling``; aquí se
resuelven las que dependen del estado (existencia de la mascota, del
veterinario, disponibilidad del horario y estado del turno) y se traducen a
los códigos HTTP del contrato.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_client
from app.db.base import get_db
from app.db.models import (
    ROLE_VET,
    STATUS_CANCELLED,
    STATUS_SCHEDULED,
    Appointment,
    Pet,
    User,
)
from app.schemas.appointment import RespuestaTurno, SolicitudTurno
from app.services.scheduling import (
    SlotError,
    ensure_aware_utc,
    fin_de_turno,
    slot_overlaps,
    validate_slot,
)

router = APIRouter(prefix="/appointments", tags=["turnos"])

Sesion = Annotated[Session, Depends(get_db)]
Cliente = Annotated[User, Depends(require_client)]
Usuario = Annotated[User, Depends(get_current_user)]

# Starlette obsoletizó el alias ``HTTP_422_UNPROCESSABLE_ENTITY`` y el nombre
# sustituto no está disponible en todas las versiones compatibles con FastAPI,
# por lo que se usa el valor numérico del código de estado.
CODIGO_NO_PROCESABLE = 422


def _a_respuesta(turno: Appointment) -> RespuestaTurno:
    """Construye la respuesta pública de un turno.

    Los instantes se normalizan a UTC porque SQLite no conserva la zona
    horaria de las columnas ``DateTime(timezone=True)``.
    """
    return RespuestaTurno(
        id=turno.id,
        pet_id=turno.pet_id,
        vet_id=turno.vet_id,
        start_at=ensure_aware_utc(turno.start_at),
        end_at=ensure_aware_utc(turno.end_at),
        status=turno.status,
    )


def _buscar_mascota(sesion: Session, pet_id: int) -> Pet | None:
    """Devuelve la mascota con el identificador indicado, si existe."""
    return sesion.get(Pet, pet_id)


def _buscar_veterinario(sesion: Session, vet_id: int) -> User | None:
    """Devuelve el veterinario con el identificador indicado, si existe."""
    veterinario = sesion.get(User, vet_id)
    if veterinario is None or veterinario.role != ROLE_VET:
        return None
    return veterinario


def _hay_turno_activo(sesion: Session, vet_id: int, inicio, fin) -> bool:
    """Indica si el veterinario tiene un turno activo que se solape con la franja.

    Solo se consideran los turnos en estado ``scheduled``: un turno cancelado
    libera su horario y permite volver a agendarlo.
    """
    turnos = sesion.scalars(
        select(Appointment).where(
            Appointment.vet_id == vet_id,
            Appointment.status == STATUS_SCHEDULED,
        )
    ).all()

    return any(
        slot_overlaps(
            inicio,
            fin,
            ensure_aware_utc(turno.start_at),
            ensure_aware_utc(turno.end_at),
        )
        for turno in turnos
    )


@router.post(
    "",
    response_model=RespuestaTurno,
    status_code=status.HTTP_201_CREATED,
    summary="Reserva de un turno",
)
def agendar_turno(
    solicitud: SolicitudTurno,
    cliente: Cliente,
    sesion: Sesion,
) -> RespuestaTurno:
    """Reserva un turno para una mascota del cliente autenticado.

    Solo los clientes agendan: un veterinario recibe 403. La mascota debe
    pertenecer al cliente (403 en caso contrario) y el veterinario debe
    existir (404 en caso contrario). El horario debe cumplir las reglas de la
    franja del consultorio (422 en caso contrario) y no puede solaparse con
    otro turno activo del mismo veterinario (409 en caso contrario).
    """
    mascota = _buscar_mascota(sesion, solicitud.pet_id)
    if mascota is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La mascota indicada no existe.",
        )

    if mascota.owner_id != cliente.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes agendar turnos para tus propias mascotas.",
        )

    veterinario = _buscar_veterinario(sesion, solicitud.vet_id)
    if veterinario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El veterinario indicado no existe.",
        )

    try:
        inicio = validate_slot(solicitud.start_at)
    except SlotError as error:
        raise HTTPException(
            status_code=CODIGO_NO_PROCESABLE,
            detail=error.motivo,
        ) from None

    fin = fin_de_turno(inicio)
    if _hay_turno_activo(sesion, veterinario.id, inicio, fin):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El veterinario ya tiene un turno activo en esa franja horaria.",
        )

    turno = Appointment(
        pet_id=mascota.id,
        vet_id=veterinario.id,
        start_at=inicio,
        end_at=fin,
        status=STATUS_SCHEDULED,
    )
    sesion.add(turno)
    sesion.commit()
    sesion.refresh(turno)

    return _a_respuesta(turno)


@router.get(
    "",
    response_model=list[RespuestaTurno],
    summary="Listado de los turnos del usuario autenticado",
)
def listar_turnos(usuario: Usuario, sesion: Sesion) -> list[RespuestaTurno]:
    """Devuelve los turnos del cliente o del veterinario según el token.

    Un cliente ve los turnos de sus propias mascotas y un veterinario los
    turnos en los que atiende. El listado es un arreglo completo, sin
    paginación ni filtros, ordenado por hora de inicio.
    """
    consulta = select(Appointment).order_by(Appointment.start_at, Appointment.id)

    if usuario.role == ROLE_VET:
        consulta = consulta.where(Appointment.vet_id == usuario.id)
    else:
        consulta = consulta.join(Pet, Appointment.pet_id == Pet.id).where(
            Pet.owner_id == usuario.id
        )

    return [_a_respuesta(turno) for turno in sesion.scalars(consulta).all()]


@router.post(
    "/{id}/cancel",
    response_model=RespuestaTurno,
    summary="Cancelación de un turno",
)
def cancelar_turno(
    id: Annotated[
        int, Path(..., ge=1, description="Identificador del turno a cancelar.")
    ],
    usuario: Usuario,
    sesion: Sesion,
) -> RespuestaTurno:
    """Cancela un turno reservado.

    Solo el cliente dueño de la mascota o el veterinario asignado pueden
    cancelar el turno; cualquier otro usuario recibe 403. Un turno ya
    cancelado devuelve 409 y un identificador inexistente, 404. La
    cancelación libera la franja, de modo que puede volver a agendarse.
    """
    turno = sesion.get(Appointment, id)
    if turno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El turno indicado no existe.",
        )

    mascota = _buscar_mascota(sesion, turno.pet_id)
    es_dueno = mascota is not None and mascota.owner_id == usuario.id
    es_veterinario = turno.vet_id == usuario.id

    if not (es_dueno or es_veterinario):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Solo el dueño de la mascota o el veterinario del turno "
                "puede cancelarlo."
            ),
        )

    if turno.status == STATUS_CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El turno ya está cancelado.",
        )

    turno.status = STATUS_CANCELLED
    sesion.commit()
    sesion.refresh(turno)

    return _a_respuesta(turno)
