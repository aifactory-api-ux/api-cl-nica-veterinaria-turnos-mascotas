"""Fixtures compartidas de la suite de pruebas.

Las pruebas no dependen de un servidor de base de datos: cada una trabaja
contra un archivo SQLite temporal con el esquema creado, de modo que los
datos de una prueba no affecten a las siguientes.
"""

from collections.abc import Callable, Generator
from datetime import date
from pathlib import Path

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, get_db
from app.db.models import (
    ROLE_CLIENT,
    ROLE_VET,
    SPECIES_DOG,
    Pet,
    User,
)
from app.main import app

PASSWORD_DE_PRUEBA = "secreto123"


def _hash_de_contrasena(password: str) -> str:
    """Genera el hash de una contraseña con bcrypt, el algoritmo de la API."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@pytest.fixture()
def db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    """Motor SQLite sobre un archivo temporal con el esquema ya creado."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'clinica.sqlite3'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Sesión aislada de la prueba en curso."""
    session = sessionmaker(
        bind=db_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine: Engine) -> Generator[TestClient, None, None]:
    """Cliente HTTP que opera contra la base temporal de la prueba."""
    factory_sesiones = sessionmaker(
        bind=db_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    def _get_db() -> Generator[Session, None, None]:
        sesion = factory_sesiones()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as cliente_http:
            yield cliente_http
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def user_factory(db_session: Session) -> Callable[..., User]:
    """Crea un usuario persistido y devuelve el modelo."""

    def _factory(
        email: str = "cliente@clinica.test",
        role: str = ROLE_CLIENT,
        password: str = PASSWORD_DE_PRUEBA,
    ) -> User:
        usuario = User(
            email=email,
            password_hash=_hash_de_contrasena(password),
            role=role,
        )
        db_session.add(usuario)
        db_session.commit()
        db_session.refresh(usuario)
        return usuario

    return _factory


@pytest.fixture()
def vet_factory(user_factory: Callable[..., User]) -> Callable[..., User]:
    """Crea un veterinario persistido y devuelve el modelo."""

    def _factory(
        email: str = "vet@clinica.test",
        password: str = PASSWORD_DE_PRUEBA,
    ) -> User:
        return user_factory(email=email, role=ROLE_VET, password=password)

    return _factory


@pytest.fixture()
def pet_factory(db_session: Session) -> Callable[..., Pet]:
    """Crea una mascota persistida a nombre de un cliente y devuelve el modelo."""

    def _factory(
        owner: User,
        name: str = "Firulais",
        species: str = SPECIES_DOG,
        birth_date: date = date(2020, 5, 10),
    ) -> Pet:
        mascota = Pet(
            name=name,
            species=species,
            birth_date=birth_date,
            owner_id=owner.id,
        )
        db_session.add(mascota)
        db_session.commit()
        db_session.refresh(mascota)
        return mascota

    return _factory


@pytest.fixture()
def client_user(user_factory: Callable[..., User]) -> User:
    """Cliente de la clínica registrado en la base de la prueba."""
    return user_factory(email="cliente@clinica.test", role=ROLE_CLIENT)


@pytest.fixture()
def vet_user(vet_factory: Callable[..., User]) -> User:
    """Veterinario registrado en la base de la prueba."""
    return vet_factory(email="vet@clinica.test")


@pytest.fixture()
def pet(client_user: User, pet_factory: Callable[..., Pet]) -> Pet:
    """Mascota del cliente de la prueba."""
    return pet_factory(owner=client_user)
