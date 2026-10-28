"""Pruebas de comportamiento de la capa de persistencia."""

from datetime import date, datetime, timedelta, timezone

import bcrypt
import pytest
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex

from app.db.models import (
    INDEX_UNIQUE_ACTIVE_SLOT,
    ROLE_CLIENT,
    ROLE_VET,
    STATUS_SCHEDULED,
    Appointment,
    Pet,
    User,
)

INICIO_DE_TURNO = datetime(2030, 6, 10, 10, 0, tzinfo=timezone.utc)


def test_el_esquema_se_crea_en_una_base_vacia(db_engine: Engine) -> None:
    inspector = inspect(db_engine)

    assert set(inspector.get_table_names()) == {"users", "pets", "appointments"}
    assert {"id", "email", "password_hash", "role", "created_at"} <= {
        columna["name"] for columna in inspector.get_columns("users")
    }
    assert {"id", "name", "species", "birth_date", "owner_id"} <= {
        columna["name"] for columna in inspector.get_columns("pets")
    }
    assert {"id", "pet_id", "vet_id", "start_at", "end_at", "status"} <= {
        columna["name"] for columna in inspector.get_columns("appointments")
    }


def test_el_email_esta_declarado_como_unico() -> None:
    columna_email = User.__table__.columns["email"]

    assert columna_email.unique is True


def test_un_usuario_se_guarda_y_se_lee(db_session: Session, user_factory) -> None:
    usuario = user_factory(email="cliente@clinica.test", role=ROLE_CLIENT)

    guardado = db_session.get(User, usuario.id)

    assert guardado is not None
    assert guardado.email == "cliente@clinica.test"
    assert guardado.role == ROLE_CLIENT
    assert guardado.password_hash != "secreto123"
    assert bcrypt.checkpw(b"secreto123", guardado.password_hash.encode("utf-8"))


def test_una_mascota_se_guarda_y_se_lee_con_su_dueno(
    db_session: Session, client_user: User, pet_factory
) -> None:
    mascota = pet_factory(
        owner=client_user,
        name="Firulais",
        species="dog",
        birth_date=date(2020, 5, 10),
    )

    guardada = db_session.get(Pet, mascota.id)

    assert guardada.owner_id == client_user.id
    assert guardada.name == "Firulais"
    assert guardada.species == "dog"
    assert guardada.birth_date == date(2020, 5, 10)
    assert guardada.owner.email == client_user.email
    assert [mascota_registrada.id for mascota_registrada in client_user.pets] == [guardada.id]


def test_un_turno_se_guarda_y_se_lee_con_su_mascota_y_veterinario(
    db_session: Session, client_user: User, vet_user: User, pet_factory
) -> None:
    mascota = pet_factory(owner=client_user)
    fin = INICIO_DE_TURNO + timedelta(minutes=30)
    turno = Appointment(
        pet_id=mascota.id,
        vet_id=vet_user.id,
        start_at=INICIO_DE_TURNO,
        end_at=fin,
        status=STATUS_SCHEDULED,
    )
    db_session.add(turno)
    db_session.commit()
    db_session.refresh(turno)

    guardado = db_session.get(Appointment, turno.id)

    assert guardado.pet_id == mascota.id
    assert guardado.vet_id == vet_user.id
    assert guardado.status == STATUS_SCHEDULED
    assert guardado.start_at.replace(tzinfo=timezone.utc) == INICIO_DE_TURNO
    assert guardado.end_at.replace(tzinfo=timezone.utc) == fin
    assert guardado.pet.name == mascota.name
    assert guardado.vet.email == vet_user.email
    assert guardado.vet.role == ROLE_VET
    assert [turno_registrado.id for turno_registrado in vet_user.vet_appointments] == [
        guardado.id
    ]


def test_el_email_duplicado_es_rechazado(db_session: Session, user_factory) -> None:
    user_factory(email="cliente@clinica.test", role=ROLE_CLIENT)

    db_session.add(
        User(email="cliente@clinica.test", password_hash="otro-hash", role=ROLE_CLIENT)
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    assert db_session.scalar(select(func.count()).select_from(User)) == 1


def test_el_indice_parcial_unico_se_declara_para_postgresql() -> None:
    indice = next(
        indice
        for indice in Appointment.__table__.indexes
        if indice.name == INDEX_UNIQUE_ACTIVE_SLOT
    )

    ddl = str(CreateIndex(indice).compile(dialect=postgresql.dialect()))

    assert "CREATE UNIQUE INDEX" in ddl
    assert "(vet_id, start_at)" in ddl
    assert "WHERE status = 'scheduled'" in ddl


def test_sqlite_no_crea_el_indice_parcial_de_postgresql(db_engine: Engine) -> None:
    indices = {indice["name"] for indice in inspect(db_engine).get_indexes("appointments")}

    assert INDEX_UNIQUE_ACTIVE_SLOT not in indices
