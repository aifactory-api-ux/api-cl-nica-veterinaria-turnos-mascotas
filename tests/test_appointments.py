"""Pruebas de la agenda de turnos.

El módulo reúne dos grupos de pruebas:

- Pruebas unitarias de ``app.services.scheduling``, que ejercitan cada regla
  de la franja horaria por separado (duración, minutos de inicio, días de
  atención, ventana de apertura y rechazo del pasado).
- Pruebas de la API sobre la aplicación real, que reservan, listan y cancelan
  turnos con el token de un cliente o de un veterinario.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Appointment, Pet, User
from app.services.scheduling import (
    SlotError,
    ensure_aware_utc,
    fin_de_turno,
    slot_overlaps,
    validate_slot,
)

PASSWORD = "secreto123"

# Instante de referencia de las pruebas unitarias: todo horario anterior se
# considera pasado.
AHORA = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)

# Fechas de apoyo en UTC. 2030-06-10 es lunes y 2030-06-15 es sábado.
LUNES_10 = datetime(2030, 6, 10, 10, 0, tzinfo=timezone.utc)
SABADO_17_30 = datetime(2030, 6, 15, 17, 30, tzinfo=timezone.utc)
DOMINGO_10 = datetime(2030, 6, 16, 10, 0, tzinfo=timezone.utc)


def _token_de(client: TestClient, email: str) -> str:
    """Inicia sesión y devuelve el token de acceso del usuario indicado."""
    respuesta = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert respuesta.status_code == 200
    return str(respuesta.json()["access_token"])


def _encabezados(token: str) -> dict[str, str]:
    """Construye el encabezado `Authorization` con el token indicado."""
    return {"Authorization": f"Bearer {token}"}


def _reserva(pet_id: int, vet_id: int, start_at: str) -> dict[str, object]:
    """Construye el cuerpo de una petición de reserva de turno."""
    return {"pet_id": pet_id, "vet_id": vet_id, "start_at": start_at}


# --------------------------------------------------------------------------
# Reglas de la franja horaria (pruebas unitarias)
# --------------------------------------------------------------------------


def test_validate_slot_acepta_un_inicio_valido() -> None:
    inicio = validate_slot(LUNES_10, now=AHORA)

    assert inicio == LUNES_10


def test_validate_slot_acepta_un_inicio_en_punto_y_media() -> None:
    inicio = validate_slot(
        datetime(2030, 6, 10, 10, 30, tzinfo=timezone.utc), now=AHORA
    )

    assert inicio.minute == 30


def test_validate_slot_acepta_el_ultimo_inicio_del_sabado() -> None:
    inicio = validate_slot(SABADO_17_30, now=AHORA)

    assert inicio == SABADO_17_30
    assert fin_de_turno(inicio) == datetime(2030, 6, 15, 18, 0, tzinfo=timezone.utc)


def test_validate_slot_rechaza_un_inicio_anterior_a_las_nueve() -> None:
    with pytest.raises(SlotError):
        validate_slot(datetime(2030, 6, 10, 8, 30, tzinfo=timezone.utc), now=AHORA)


def test_validate_slot_rechaza_un_inicio_posterior_a_las_once_treinta() -> None:
    with pytest.raises(SlotError):
        validate_slot(datetime(2030, 6, 10, 18, 0, tzinfo=timezone.utc), now=AHORA)


def test_validate_slot_rechaza_el_domingo() -> None:
    with pytest.raises(SlotError):
        validate_slot(DOMINGO_10, now=AHORA)


def test_validate_slot_rechaza_minutos_que_no_son_00_ni_30() -> None:
    with pytest.raises(SlotError):
        validate_slot(datetime(2030, 6, 10, 10, 15, tzinfo=timezone.utc), now=AHORA)


def test_validate_slot_rechaza_segundos_no_nulos() -> None:
    with pytest.raises(SlotError):
        validate_slot(datetime(2030, 6, 10, 10, 0, 30, tzinfo=timezone.utc), now=AHORA)


def test_validate_slot_rechaza_un_instante_ya_transcurrido() -> None:
    with pytest.raises(SlotError):
        validate_slot(datetime(2020, 1, 7, 10, 0, tzinfo=timezone.utc), now=AHORA)


def test_el_error_de_dominio_expone_el_motivo_del_rechazo() -> None:
    with pytest.raises(SlotError) as error:
        validate_slot(datetime(2030, 6, 10, 8, 30, tzinfo=timezone.utc), now=AHORA)

    assert error.value.motivo
    assert isinstance(error.value.motivo, str)


def test_validate_slot_normaliza_a_utc_el_inicio() -> None:
    inicio = validate_slot(
        datetime(2030, 6, 10, 12, 0, tzinfo=timezone(timedelta(hours=2))), now=AHORA
    )

    assert inicio == LUNES_10
    assert inicio.utcoffset() == timedelta(0)


def test_validate_slot_interpreta_como_utc_un_valor_naive() -> None:
    inicio = validate_slot(datetime(2030, 6, 10, 10, 0), now=AHORA)

    assert inicio == LUNES_10


def test_fin_de_turno_dura_treinta_minutos() -> None:
    assert fin_de_turno(LUNES_10) == LUNES_10 + timedelta(minutes=30)


def test_ensure_aware_utc_interpreta_como_utc_un_valor_naive() -> None:
    momento = datetime(2030, 6, 10, 10, 0)

    normalizado = ensure_aware_utc(momento)

    assert normalizado == LUNES_10
    assert normalizado.tzinfo is timezone.utc


def test_slot_overlaps_detecta_el_solapamiento() -> None:
    inicio = LUNES_10
    fin = fin_de_turno(inicio)

    assert slot_overlaps(inicio, fin, inicio, fin) is True
    assert slot_overlaps(inicio, fin, inicio + timedelta(minutes=15), fin) is True


def test_slot_overlaps_no_confunde_las_franjas_contiguas() -> None:
    inicio = LUNES_10
    fin = fin_de_turno(inicio)

    assert slot_overlaps(inicio, fin, fin, fin + timedelta(minutes=30)) is False
    assert slot_overlaps(inicio, fin, LUNES_10 + timedelta(hours=1), LUNES_10 + timedelta(hours=1, minutes=30)) is False


# --------------------------------------------------------------------------
# Reserva de turnos
# --------------------------------------------------------------------------


def test_el_cliente_reserva_un_turno(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
    db_session: Session,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["pet_id"] == pet.id
    assert cuerpo["vet_id"] == vet_user.id
    assert cuerpo["status"] == "scheduled"
    assert cuerpo["id"] > 0

    # El turno queda persistido con sus dos extremos y el estado inicial.
    db_session.expire_all()
    persistido = db_session.scalars(
        select(Appointment).where(Appointment.id == cuerpo["id"])
    ).one()
    assert persistido.status == "scheduled"
    assert persistido.pet_id == pet.id
    assert persistido.vet_id == vet_user.id


def test_el_end_at_es_exactamente_treinta_minutos_despues_del_start_at(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    inicio = datetime.fromisoformat(cuerpo["start_at"])
    fin = datetime.fromisoformat(cuerpo["end_at"])
    assert inicio == datetime(2030, 6, 10, 10, 0, tzinfo=timezone.utc)
    assert fin - inicio == timedelta(minutes=30)
    assert fin == datetime(2030, 6, 10, 10, 30, tzinfo=timezone.utc)


def test_un_veterinario_no_puede_agendar_un_turno(
    client: TestClient,
    vet_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, vet_user.email)

    respuesta = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )

    assert respuesta.status_code == 403


def test_no_se_puede_agendar_sobre_una_mascota_ajena(
    client: TestClient,
    client_user: User,
    vet_user: User,
    user_factory,
    pet_factory,
) -> None:
    otro_cliente = user_factory(email="otro@clinica.test")
    mascota_ajena = pet_factory(owner=otro_cliente, name="Rufino")
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(mascota_ajena.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )

    assert respuesta.status_code == 403


def test_una_mascota_inexistente_devuelve_404(
    client: TestClient,
    client_user: User,
    vet_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(999999, vet_user.id, "2030-06-10T10:00:00Z"),
    )

    assert respuesta.status_code == 404


def test_un_veterinario_inexistente_devuelve_404(
    client: TestClient,
    client_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, 999999, "2030-06-10T10:00:00Z"),
    )

    assert respuesta.status_code == 404


def test_un_usuario_que_no_es_veterinario_devuelve_404(
    client: TestClient,
    client_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, client_user.id, "2030-06-10T10:00:00Z"),
    )

    assert respuesta.status_code == 404


@pytest.mark.parametrize(
    ("start_at", "motivo"),
    [
        ("no-es-una-fecha", "formato no ISO 8601"),
        ("2030-06-10T10:15:00Z", "minutos que no son 00 ni 30"),
        ("2030-06-16T10:00:00Z", "domingo"),
        ("2030-06-10T08:30:00Z", "antes de las 09:00"),
        ("2030-06-10T18:00:00Z", "después de las 17:30"),
        ("2020-01-07T10:00:00Z", "fecha pasada"),
    ],
)
def test_un_horario_invalido_devuelve_422(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
    start_at: str,
    motivo: str,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, start_at),
    )

    assert respuesta.status_code == 422, motivo


def test_un_turno_duplicado_del_veterinario_devuelve_409(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, client_user.email)
    cuerpo = _reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z")

    primera = client.post("/appointments", headers=_encabezados(token), json=cuerpo)
    segunda = client.post("/appointments", headers=_encabezados(token), json=cuerpo)

    assert primera.status_code == 201
    assert segunda.status_code == 409


def test_otra_franja_del_mismo_veterinario_se_puede_reservar(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, client_user.email)

    primera = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )
    segunda = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T11:00:00Z"),
    )

    assert primera.status_code == 201
    assert segunda.status_code == 201


# --------------------------------------------------------------------------
# Listado de turnos
# --------------------------------------------------------------------------


def test_el_cliente_ve_solo_los_turnos_de_sus_mascotas(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
    user_factory,
    pet_factory,
) -> None:
    otro_cliente = user_factory(email="otro@clinica.test")
    mascota_ajena = pet_factory(owner=otro_cliente, name="Rufino")
    token = _token_de(client, client_user.email)
    token_otro = _token_de(client, otro_cliente.email)

    propia = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )
    ajena = client.post(
        "/appointments",
        headers=_encabezados(token_otro),
        json=_reserva(mascota_ajena.id, vet_user.id, "2030-06-10T11:00:00Z"),
    )
    assert propia.status_code == 201
    assert ajena.status_code == 201

    respuesta = client.get("/appointments", headers=_encabezados(token))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [turno["id"] for turno in cuerpo] == [propia.json()["id"]]


def test_el_veterinario_ve_solo_sus_propios_turnos(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
    vet_factory,
) -> None:
    otro_vet = vet_factory(email="otro-vet@clinica.test")
    token_cliente = _token_de(client, client_user.email)

    propio = client.post(
        "/appointments",
        headers=_encabezados(token_cliente),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )
    ajeno = client.post(
        "/appointments",
        headers=_encabezados(token_cliente),
        json=_reserva(pet.id, otro_vet.id, "2030-06-10T11:00:00Z"),
    )
    assert propio.status_code == 201
    assert ajeno.status_code == 201

    token_vet = _token_de(client, vet_user.email)
    respuesta = client.get("/appointments", headers=_encabezados(token_vet))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [turno["id"] for turno in cuerpo] == [propio.json()["id"]]


def test_el_listado_de_turnos_exige_token(
    client: TestClient,
) -> None:
    respuesta = client.get("/appointments")

    assert respuesta.status_code == 401


# --------------------------------------------------------------------------
# Cancelación de turnos
# --------------------------------------------------------------------------


def test_el_dueno_de_la_mascota_cancela_el_turno(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, client_user.email)
    reserva = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )
    turno_id = reserva.json()["id"]

    respuesta = client.post(
        f"/appointments/{turno_id}/cancel", headers=_encabezados(token)
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == turno_id
    assert cuerpo["status"] == "cancelled"


def test_el_veterinario_del_turno_lo_cancela(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
) -> None:
    token_cliente = _token_de(client, client_user.email)
    reserva = client.post(
        "/appointments",
        headers=_encabezados(token_cliente),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )
    turno_id = reserva.json()["id"]

    token_vet = _token_de(client, vet_user.email)
    respuesta = client.post(
        f"/appointments/{turno_id}/cancel", headers=_encabezados(token_vet)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "cancelled"


def test_un_usuario_ajeno_no_puede_cancelar_el_turno(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
    user_factory,
) -> None:
    token_cliente = _token_de(client, client_user.email)
    reserva = client.post(
        "/appointments",
        headers=_encabezados(token_cliente),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )
    turno_id = reserva.json()["id"]

    otro_cliente = user_factory(email="otro@clinica.test")
    token_otro = _token_de(client, otro_cliente.email)
    respuesta = client.post(
        f"/appointments/{turno_id}/cancel", headers=_encabezados(token_otro)
    )

    assert respuesta.status_code == 403


def test_cancelar_dos_veces_el_mismo_turno_devuelve_409(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, client_user.email)
    reserva = client.post(
        "/appointments",
        headers=_encabezados(token),
        json=_reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z"),
    )
    turno_id = reserva.json()["id"]

    primera = client.post(f"/appointments/{turno_id}/cancel", headers=_encabezados(token))
    segunda = client.post(f"/appointments/{turno_id}/cancel", headers=_encabezados(token))

    assert primera.status_code == 200
    assert segunda.status_code == 409


def test_cancelar_un_turno_inexistente_devuelve_404(
    client: TestClient,
    client_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post("/appointments/999999/cancel", headers=_encabezados(token))

    assert respuesta.status_code == 404


def test_un_horario_cancelado_se_puede_volver_a_agendar(
    client: TestClient,
    client_user: User,
    vet_user: User,
    pet: Pet,
) -> None:
    token = _token_de(client, client_user.email)
    cuerpo = _reserva(pet.id, vet_user.id, "2030-06-10T10:00:00Z")
    reserva = client.post("/appointments", headers=_encabezados(token), json=cuerpo)
    turno_id = reserva.json()["id"]

    cancelacion = client.post(
        f"/appointments/{turno_id}/cancel", headers=_encabezados(token)
    )
    nueva = client.post("/appointments", headers=_encabezados(token), json=cuerpo)

    assert cancelacion.status_code == 200
    assert nueva.status_code == 201
    assert nueva.json()["status"] == "scheduled"
    assert nueva.json()["id"] != turno_id
