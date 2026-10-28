"""Configuración de la aplicación leída de variables de entorno."""

from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores por defecto pensados solo para desarrollo local; en producción
# se fijan por entorno (ver README y docker-compose.yml).
DEFAULT_DATABASE_URL = "postgresql+psycopg://clinica:clinica@localhost:5432/clinica"
DEFAULT_JWT_SECRET = "desarrollo-cambiar-en-produccion"
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_JWT_EXPIRE_MINUTES = 480


class Settings(BaseSettings):
    """Ajustes de la aplicación tomados del entorno.

    Los nombres de las variables de entorno son los nombres de los campos en
    mayúsculas: ``DATABASE_URL``, ``JWT_SECRET``, ``JWT_ALGORITHM`` y
    ``JWT_EXPIRE_MINUTES``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = DEFAULT_DATABASE_URL
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = DEFAULT_JWT_ALGORITHM
    jwt_expire_minutes: int = DEFAULT_JWT_EXPIRE_MINUTES


settings = Settings()
