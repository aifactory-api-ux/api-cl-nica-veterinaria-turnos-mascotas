"""Base declarativa, motor y sesión de base de datos.

La conexión real usa PostgreSQL (``DATABASE_URL``). Las mismas clases de
modelo funcionan sobre SQLite, que es el motor que emplean las pruebas.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base declarativa común a las tablas del dominio."""


engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Entrega una sesión por petición y la cierra al terminar.

    Se usa como dependencia de FastAPI: cada petición recibe su propia
    sesión y esta se libera aunque la operación falle.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
