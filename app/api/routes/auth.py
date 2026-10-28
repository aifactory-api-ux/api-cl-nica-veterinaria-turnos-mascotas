"""Endpoints de registro e inicio de sesión.

``POST /auth/register`` crea un cliente o un veterinario y devuelve su
identidad pública. ``POST /auth/login`` comprueba las credenciales y emite un
token JWT que el cliente debe enviar en las operaciones protegidas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import get_db
from app.db.models import User
from app.schemas.auth import (
    RespuestaRegistro,
    RespuestaToken,
    SolicitudLogin,
    SolicitudRegistro,
)

router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post(
    "/register",
    response_model=RespuestaRegistro,
    status_code=status.HTTP_201_CREATED,
    summary="Registro de un cliente o un veterinario",
)
def registrar(
    solicitud: SolicitudRegistro,
    sesion: Session = Depends(get_db),
) -> RespuestaRegistro:
    """Crea un usuario con el rol indicado.

    Responde 409 si el correo ya está registrado y 422 si la contraseña es
    demasiado corta o el rol no es admitido.
    """
    existente = sesion.scalar(select(User).where(User.email == solicitud.email))
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario registrado con ese correo.",
        )

    usuario = User(
        email=solicitud.email,
        password_hash=hash_password(solicitud.password),
        role=solicitud.role,
    )
    sesion.add(usuario)
    try:
        sesion.commit()
    except IntegrityError:
        # La restricción de unicidad del correo también cubre dos registros
        # simultáneos con el mismo email.
        sesion.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario registrado con ese correo.",
        ) from None
    sesion.refresh(usuario)

    return RespuestaRegistro(id=usuario.id, email=usuario.email, role=usuario.role)


@router.post(
    "/login",
    response_model=RespuestaToken,
    summary="Inicio de sesión de un usuario",
)
def iniciar_sesion(
    solicitud: SolicitudLogin,
    sesion: Session = Depends(get_db),
) -> RespuestaToken:
    """Comprueba las credenciales y emite un token de acceso.

    Responde 401 si el correo no existe o la contraseña no coincide. El
    mensaje es el mismo en ambos casos para no revelar qué correos están
    registrados.
    """
    usuario = sesion.scalar(select(User).where(User.email == solicitud.email))
    if usuario is None or not verify_password(solicitud.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=usuario.id, role=usuario.role, email=usuario.email)
    return RespuestaToken(access_token=token, token_type="bearer")
