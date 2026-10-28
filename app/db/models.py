"""Entidades del dominio: usuarios, mascotas y turnos.

Los modelos son declarativos y portables: las mismas clases funcionan sobre
PostgreSQL (producción) y sobre SQLite (pruebas). La única diferencia entre
motores es el índice único parcial de los turnos activos, que solo PostgreSQL
recibe (ver :func:`_omitir_indices_parciales_postgresql`).
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import CreateIndex
from sqlalchemy.sql.compiler import DDLCompiler

from app.db.base import Base

# Roles admitidos por la plataforma.
ROLE_CLIENT = "client"
ROLE_VET = "vet"

# Especies admitidas para una mascota.
SPECIES_DOG = "dog"
SPECIES_CAT = "cat"
SPECIES_OTHER = "other"

# Estados de un turno.
STATUS_SCHEDULED = "scheduled"
STATUS_CANCELLED = "cancelled"

# Nombre del índice único parcial que impide dos turnos activos del mismo
# veterinario en la misma franja.
INDEX_UNIQUE_ACTIVE_SLOT = "uq_appointments_vet_start_scheduled"


def _es_indice_parcial_de_postgresql(index: Index) -> bool:
    """Indica si el índice declara una condición parcial específica de PostgreSQL."""
    opciones = index.dialect_options.get("postgresql") or {}
    return "where" in opciones


@compiles(CreateIndex, "sqlite")
def _omitir_indices_parciales_postgresql(
    element: CreateIndex, compiler: DDLCompiler, **kwargs: Any
) -> str:
    """Omite en SQLite los índices con condición parcial exclusiva de PostgreSQL.

    El índice único parcial sobre ``(vet_id, start_at)`` usa la sintaxis
    ``WHERE`` de PostgreSQL. Como SQLite no admite índices filtrados por
    estado, se omite allí y la aplicación resuelve el solapamiento de
    horarios con una comprobación explícita antes de insertar el turno.
    """
    if _es_indice_parcial_de_postgresql(element.element):
        return ""
    return compiler.visit_create_index(element, **kwargs)


class User(Base):
    """Usuario de la plataforma: cliente de la clínica o veterinario."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pets: Mapped[list["Pet"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    vet_appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="vet",
        foreign_keys="Appointment.vet_id",
        cascade="all, delete-orphan",
    )


class Pet(Base):
    """Mascota registrada por un cliente."""

    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    species: Mapped[str] = mapped_column(String(16), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="pets")
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan"
    )


class Appointment(Base):
    """Turno de una mascota con un veterinario."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vet_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=STATUS_SCHEDULED, server_default=STATUS_SCHEDULED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pet: Mapped["Pet"] = relationship(back_populates="appointments")
    vet: Mapped["User"] = relationship(
        back_populates="vet_appointments", foreign_keys=[vet_id]
    )

    __table_args__ = (
        Index(
            INDEX_UNIQUE_ACTIVE_SLOT,
            "vet_id",
            "start_at",
            unique=True,
            postgresql_where=text(f"status = '{STATUS_SCHEDULED}'"),
        ),
    )
