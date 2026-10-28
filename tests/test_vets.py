"""Pruebas del directorio de veterinarios.

Las pruebas usan la aplicación real: registran usuarios, inician sesión y
consultan ``GET /vets`` con el token obtenido, de modo que se ejercita el
mismo camino que un cliente de la clínica.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.db.models import ROLE_CLIENT, User

PASSWORD = "secreto123"


def _token_de(client: TestClient, email: str) -> str:
    """Inicia sesión y devuelve el token de acceso del usuario indicado."""
    respuesta = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert respuesta.status_code == 200
    return str(respuesta.json()["access_token"])


def test_el_listado_devuelve_el_id_y_el_email_de_cada_veterinario(
    client: TestClient,
    client_user: User,
    vet_factory: Callable[..., User],
) -> None:
    primero = vet_factory(email="vet1@clinica.test")
    segundo = vet_factory(email="vet2@clinica.test")
    token = _token_de(client, client_user.email)

    respuesta = client.get("/vets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    listado = respuesta.json()
    assert len(listado) == 2
    assert listado == [
        {"id": primero.id, "email": "vet1@clinica.test"},
        {"id": segundo.id, "email": "vet2@clinica.test"},
    ]


def test_el_listado_incluye_solo_veterinarios(
    client: TestClient,
    client_user: User,
    vet_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.get("/vets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    listado = respuesta.json()
    assert [veterinario["email"] for veterinario in listado] == [vet_user.email]
    assert client_user.email not in [veterinario["email"] for veterinario in listado]


def test_el_listado_sin_veterinarios_devuelve_un_arreglo_vacio(
    client: TestClient,
    client_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.get("/vets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_listado_no_expone_las_contrasenas(
    client: TestClient,
    client_user: User,
    vet_user: User,
) -> None:
    token = _token_de(client, client_user.email)

    respuesta = client.get("/vets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    for veterinario in respuesta.json():
        assert set(veterinario.keys()) == {"id", "email"}
    assert PASSWORD not in respuesta.text
    assert vet_user.password_hash not in respuesta.text


def test_el_listado_sin_token_devuelve_401(client: TestClient) -> None:
    respuesta = client.get("/vets")

    assert respuesta.status_code == 401


def test_el_listado_con_un_token_invalido_devuelve_401(client: TestClient) -> None:
    respuesta = client.get(
        "/vets", headers={"Authorization": "Bearer token-invalido"}
    )

    assert respuesta.status_code == 401


def test_un_veterinario_tambien_puede_consultar_el_directorio(
    client: TestClient,
    vet_user: User,
) -> None:
    token = _token_de(client, vet_user.email)

    respuesta = client.get("/vets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert [veterinario["email"] for veterinario in respuesta.json()] == [
        vet_user.email
    ]


@pytest.mark.parametrize("rol", [ROLE_CLIENT, "vet"])
def test_el_listado_solo_exige_un_usuario_autenticado(
    client: TestClient,
    user_factory: Callable[..., User],
    rol: str,
) -> None:
    usuario = user_factory(email=f"usuario-{rol}@clinica.test", role=rol)
    token = _token_de(client, usuario.email)

    respuesta = client.get("/vets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
