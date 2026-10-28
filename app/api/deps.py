"""Dependencias de autenticación y autorización de la API.

``get_current_user`` resuelve el usuario a partir del encabezado
``Authorization: Bearer <access_token>``. La cabecera se lee con
``HTTPBearer(auto_error=False)`` porque FastAPI responde 403 cuando faltan
credenciales y el contrato de la plataforma exige 401 tanto si el encabezado
falta como si el token no es válido.

``require_client`` y ``require_vet`` añaden la comprobación de rol sobre el
usuario ya autenticado y responden 403 cuando el rol no permite la operación.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.base import get_db
from app.db.models import ROLE_CLIENT, ROLE_VET, User

esquema_bearer = HTTPBearer(
    auto_error=False,
    description="Token JWT devuelto por `POST /auth/login`.",
)

CredencialesBearer = Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)]
Sesion = Annotated[Session, Depends(get_db)]


def _credenciales_rechazadas() -> HTTPException:
    """Construye el error 401 que comparten los fallos de autenticación."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de autenticación ausentes o inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(credenciales: CredencialesBearer, sesion: Sesion) -> User:
    """Devuelve el usuario autenticado indicado por el token Bearer.

    Responde 401 si falta el encabezado, si el token no se puede decodificar,
    si ha expirado o si el usuario al que apunta ya no existe.
    """
    if credenciales is None or not credenciales.credentials:
        raise _credenciales_rechazadas()

    try:
        payload = decode_access_token(credenciales.credentials)
    except jwt.PyJWTError:
        raise _credenciales_rechazadas() from None

    identificador = payload.get("sub")
    if identificador is None:
        raise _credenciales_rechazadas()

    try:
        user_id = int(identificador)
    except (TypeError, ValueError):
        raise _credenciales_rechazadas() from None

    usuario = sesion.get(User, user_id)
    if usuario is None:
        raise _credenciales_rechazadas()

    return usuario


def require_client(usuario: Annotated[User, Depends(get_current_user)]) -> User:
    """Exige el rol `client`; responde 403 si el usuario tiene otro rol."""
    if usuario.role != ROLE_CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación solo está disponible para los clientes.",
        )
    return usuario


def require_vet(usuario: Annotated[User, Depends(get_current_user)]) -> User:
    """Exige el rol `vet`; responde 403 si el usuario tiene otro rol."""
    if usuario.role != ROLE_VET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación solo está disponible para los veterinarios.",
        )
    return usuario
