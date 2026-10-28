"""Primitivas criptográficas de la API: contraseñas y tokens de acceso.

El módulo concentra las dos operaciones sensibles de la plataforma:

- ``bcrypt`` para calcular y verificar el hash de una contraseña.
- ``PyJWT`` para emitir y decodificar tokens HS256 que llevan el ``sub``
  (identificador del usuario), el ``role``, el ``email`` y el ``exp``.

La clave de firma, el algoritmo y la vigencia del token se leen de la
configuración (``JWT_SECRET``, ``JWT_ALGORITHM`` y ``JWT_EXPIRE_MINUTES``), de
modo que ningún secreto queda escrito en el código.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# Número máximo de bytes que bcrypt procesa. El resto se descarta de forma
# explícita para no depender del truncamiento interno de la biblioteca, que
# lanza un error con las versiones actuales.
MAX_BYTES_DE_PASSWORD = 72


def _password_a_bytes(password: str) -> bytes:
    """Codifica la contraseña y la limita al máximo admitido por bcrypt."""
    return password.encode("utf-8")[:MAX_BYTES_DE_PASSWORD]


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de la contraseña, listo para persistir."""
    return bcrypt.hashpw(_password_a_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Indica si la contraseña corresponde al hash almacenado.

    Un hash vacío o con un formato que bcrypt no reconoce no valida ninguna
    contraseña, en lugar de propagar el error.
    """
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_password_a_bytes(password), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_access_token(*, user_id: int, role: str, email: str) -> str:
    """Emite un token de acceso JWT para el usuario indicado."""
    emitido = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "email": email,
        "iat": int(emitido.timestamp()),
        "exp": emitido + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica el token y comprueba su firma y su vigencia.

    Lanza ``jwt.PyJWTError`` si el token está mal formado, ha expirado o no
    fue firmado con la clave configurada.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
