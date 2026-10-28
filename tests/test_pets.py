"""Pruebas del registro y del listado de mascotas.

Las pruebas usan la aplicación real: inician sesión con el token de un
usuario y llaman a ``POST /pets`` y ``GET /pets``, de modo que se ejercita el
mismo camino que un cliente de la clínica.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Pet, User

PASSWORD = "secreto123"


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


def test_el_cliente_registra_una_mascota(
    client: TestClient,
    client_user: User,
    db_session: Session,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/pets",
        headers=_encabezados(token),
        json={"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["name"] == "Firulais"
    assert cuerpo["species"] == "dog"
    assert cuerpo["birth_date"] == "2020-05-10"
    assert cuerpo["owner_id"] == client_user.id
    assert cuerpo["id"] > 0

    # La mascota queda persistida con el cliente autenticado como propietario.
    db_session.expire_all()
    persistida = db_session.scalars(
        select(Pet).where(Pet.id == cuerpo["id"])
    ).one()
    assert persistida.name == "Firulais"
    assert persistida.owner_id == client_user.id


def test_un_veterinario_no_puede_registrar_mascotas(
    client: TestClient,
    vet_user: User,
) -> None:
    token = _token_de(client, vet_user.email)

    respuesta = client.post(
        "/pets",
        headers=_encabezados(token),
        json={"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"},
    )

    assert respuesta.status_code == 403


@pytest.mark.parametrize("especie", ["dog", "cat", "other"])
def test_se_aceptan_las_especies_admitidas(
    client: TestClient,
    client_user: User,
    especie: str,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/pets",
        headers=_encabezados(token),
        json={
            "name": "Firulais",
            "species": especie,
            "birth_date": "2020-05-10",
        },
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["species"] == especie


def test_una_especie_no_admitida_se_rechaza(
    client: TestClient,
    client_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/pets",
        headers=_encabezados(token),
        json={"name": "Firulais", "species": "bird", "birth_date": "2020-05-10"},
    )

    assert respuesta.status_code == 422


def test_una_fecha_de_nacimiento_futura_se_rechaza(
    client: TestClient,
    client_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/pets",
        headers=_encabezados(token),
        json={"name": "Firulais", "species": "dog", "birth_date": "2999-01-01"},
    )

    assert respuesta.status_code == 422


def test_una_fecha_de_nacimiento_invalida_se_rechaza(
    client: TestClient,
    client_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.post(
        "/pets",
        headers=_encabezados(token),
        json={
            "name": "Firulais",
            "species": "dog",
            "birth_date": "no-es-una-fecha",
        },
    )

    assert respuesta.status_code == 422


def test_el_listado_devuelve_solo_las_mascotas_del_cliente(
    client: TestClient,
    client_user: User,
    pet_factory: Callable[..., Pet],
    user_factory: Callable[..., User],
) -> None:
    primera = pet_factory(owner=client_user, name="Firulais")
    segunda = pet_factory(owner=client_user, name="Michi", species="cat")
    otro_cliente = user_factory(email="otro@clinica.test")
    ajena = pet_factory(owner=otro_cliente, name="Rayo")

    token = _token_de(client, client_user.email)
    respuesta = client.get("/pets", headers=_encabezados(token))

    assert respuesta.status_code == 200
    listado = respuesta.json()
    assert [mascota["id"] for mascota in listado] == [primera.id, segunda.id]
    assert [mascota["name"] for mascota in listado] == ["Firulais", "Michi"]
    assert all(mascota["owner_id"] == client_user.id for mascota in listado)
    assert ajena.id not in [mascota["id"] for mascota in listado]
    assert "Rayo" not in respuesta.text


def test_el_listado_sin_mascotas_devuelve_un_arreglo_vacio(
    client: TestClient,
    client_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.get("/pets", headers=_encabezados(token))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_listado_de_un_veterinario_devuelve_un_arreglo_vacio(
    client: TestClient,
    vet_user: User,
) -> None:
    token = _token_de(client, vet_user.email)

    respuesta = client.get("/pets", headers=_encabezados(token))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_registro_sin_token_devuelve_401(client: TestClient) -> None:
    respuesta = client.post(
        "/pets",
        json={"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"},
    )

    assert respuesta.status_code == 401


def test_el_registro_con_un_token_invalido_devuelve_401(client: TestClient) -> None:
    respuesta = client.post(
        "/pets",
        headers={"Authorization": "Bearer token-invalido"},
        json={"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"},
    )

    assert respuesta.status_code == 401


def test_el_listado_sin_token_devuelve_401(client: TestClient) -> None:
    respuesta = client.get("/pets")

    assert respuesta.status_code == 401


def test_el_listado_con_un_token_invalido_devuelve_401(client: TestClient) -> None:
    respuesta = client.get(
        "/pets", headers={"Authorization": "Bearer token-invalido"}
    )

    assert respuesta.status_code == 401


def test_la_mascota_registrada_aparece_en_el_listado(
    client: TestClient,
    client_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    registro = client.post(
        "/pets",
        headers=_encabezados(token),
        json={"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"},
    )
    listado = client.get("/pets", headers=_encabezados(token))

    assert registro.status_code == 201
    assert listado.status_code == 200
    assert listado.json() == [registro.json()]
