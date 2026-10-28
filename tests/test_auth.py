"""Pruebas del registro, el inicio de sesión y la protección de las rutas.

Las pruebas de registro e inicio de sesión usan la aplicación real. Las
comprobaciones de 401 y 403 se hacen contra una aplicación mínima que monta
las mismas dependencias de autenticación y autorización, porque los routers
protegidos del dominio (mascotas, veterinarios y turnos) se añaden en los
bloques de trabajo posteriores.
"""

from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user, require_client, require_vet
from app.core.security import decode_access_token
from app.db.base import get_db
from app.db.models import ROLE_CLIENT, ROLE_VET, User

EMAIL_CLIENTE = "cliente@clinica.test"
EMAIL_VETERINARIO = "vet@clinica.test"
PASSWORD = "secreto123"


@pytest.fixture()
def cliente_protegido(db_engine: Engine) -> Iterator[TestClient]:
    """Cliente HTTP de una aplicación con rutas protegidas.

    Monta ``get_current_user``, ``require_client`` y ``require_vet`` sobre la
    misma base de datos de la prueba, para comprobar los códigos 401 y 403 de
    la autenticación y de la autorización.
    """
    aplicacion = FastAPI()

    @aplicacion.get("/protegido")
    def protegido(usuario: User = Depends(get_current_user)) -> dict[str, object]:
        return {"id": usuario.id, "email": usuario.email, "role": usuario.role}

    @aplicacion.post("/solo-clientes")
    def solo_clientes(usuario: User = Depends(require_client)) -> dict[str, object]:
        return {"id": usuario.id}

    @aplicacion.post("/solo-veterinarios")
    def solo_veterinarios(usuario: User = Depends(require_vet)) -> dict[str, object]:
        return {"id": usuario.id}

    def _get_db() -> Iterator[Session]:
        sesion = sessionmaker(
            bind=db_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )()
        try:
            yield sesion
        finally:
            sesion.close()

    aplicacion.dependency_overrides[get_db] = _get_db
    with TestClient(aplicacion) as cliente:
        yield cliente


def _registrar(client: TestClient, email: str, role: str) -> dict[str, object]:
    """Registra un usuario y devuelve el cuerpo de la respuesta."""
    respuesta = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "role": role},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def _iniciar_sesion(client: TestClient, email: str) -> str:
    """Inicia sesión y devuelve el token de acceso."""
    respuesta = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert respuesta.status_code == 200
    return str(respuesta.json()["access_token"])


def test_el_registro_de_un_cliente_devuelve_201_con_sus_campos(
    client: TestClient,
) -> None:
    respuesta = client.post(
        "/auth/register",
        json={"email": EMAIL_CLIENTE, "password": PASSWORD, "role": ROLE_CLIENT},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["email"] == EMAIL_CLIENTE
    assert cuerpo["role"] == ROLE_CLIENT
    assert isinstance(cuerpo["id"], int)


def test_el_registro_de_un_veterinario_devuelve_201_con_sus_campos(
    client: TestClient,
) -> None:
    respuesta = client.post(
        "/auth/register",
        json={"email": EMAIL_VETERINARIO, "password": PASSWORD, "role": ROLE_VET},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["email"] == EMAIL_VETERINARIO
    assert cuerpo["role"] == ROLE_VET
    assert isinstance(cuerpo["id"], int)


def test_el_registro_no_devuelve_la_contrasena(client: TestClient) -> None:
    respuesta = client.post(
        "/auth/register",
        json={"email": EMAIL_CLIENTE, "password": PASSWORD, "role": ROLE_CLIENT},
    )

    cuerpo = respuesta.json()
    assert "password" not in cuerpo
    assert "password_hash" not in cuerpo
    assert PASSWORD not in respuesta.text


def test_el_registro_con_un_email_duplicado_devuelve_409(client: TestClient) -> None:
    _registrar(client, EMAIL_CLIENTE, ROLE_CLIENT)

    respuesta = client.post(
        "/auth/register",
        json={"email": EMAIL_CLIENTE, "password": PASSWORD, "role": ROLE_CLIENT},
    )

    assert respuesta.status_code == 409


def test_el_registro_con_una_contrasena_corta_devuelve_422(client: TestClient) -> None:
    respuesta = client.post(
        "/auth/register",
        json={"email": "corto@clinica.test", "password": "corta", "role": ROLE_CLIENT},
    )

    assert respuesta.status_code == 422


def test_el_registro_con_un_rol_invalido_devuelve_422(client: TestClient) -> None:
    respuesta = client.post(
        "/auth/register",
        json={"email": "otro@clinica.test", "password": PASSWORD, "role": "admin"},
    )

    assert respuesta.status_code == 422


def test_el_login_devuelve_un_token_bearer(client: TestClient) -> None:
    _registrar(client, EMAIL_CLIENTE, ROLE_CLIENT)

    respuesta = client.post(
        "/auth/login",
        json={"email": EMAIL_CLIENTE, "password": PASSWORD},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["access_token"]


def test_el_token_identifica_al_usuario_y_su_rol(client: TestClient) -> None:
    registrado = _registrar(client, EMAIL_CLIENTE, ROLE_CLIENT)

    token = _iniciar_sesion(client, EMAIL_CLIENTE)

    payload = decode_access_token(token)
    assert payload["sub"] == str(registrado["id"])
    assert payload["role"] == ROLE_CLIENT
    assert payload["email"] == EMAIL_CLIENTE
    assert "exp" in payload


def test_el_login_con_una_contrasena_incorrecta_devuelve_401(client: TestClient) -> None:
    _registrar(client, EMAIL_CLIENTE, ROLE_CLIENT)

    respuesta = client.post(
        "/auth/login",
        json={"email": EMAIL_CLIENTE, "password": "otra-clave"},
    )

    assert respuesta.status_code == 401


def test_el_login_de_un_usuario_inexistente_devuelve_401(client: TestClient) -> None:
    respuesta = client.post(
        "/auth/login",
        json={"email": "nadie@clinica.test", "password": PASSWORD},
    )

    assert respuesta.status_code == 401


def test_una_ruta_protegida_sin_token_devuelve_401(cliente_protegido: TestClient) -> None:
    respuesta = cliente_protegido.get("/protegido")

    assert respuesta.status_code == 401


def test_una_ruta_protegida_con_un_token_invalido_devuelve_401(
    cliente_protegido: TestClient,
) -> None:
    respuesta = cliente_protegido.get(
        "/protegido", headers={"Authorization": "Bearer token-invalido"}
    )

    assert respuesta.status_code == 401


def test_el_token_del_login_sirve_en_una_ruta_protegida(
    client: TestClient, cliente_protegido: TestClient
) -> None:
    registrado = _registrar(client, EMAIL_CLIENTE, ROLE_CLIENT)
    token = _iniciar_sesion(client, EMAIL_CLIENTE)

    respuesta = cliente_protegido.get(
        "/protegido", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == registrado["id"]
    assert cuerpo["email"] == EMAIL_CLIENTE
    assert cuerpo["role"] == ROLE_CLIENT


def test_una_operacion_de_clientes_responde_403_a_un_veterinario(
    client: TestClient, cliente_protegido: TestClient
) -> None:
    _registrar(client, EMAIL_VETERINARIO, ROLE_VET)
    token = _iniciar_sesion(client, EMAIL_VETERINARIO)

    respuesta = cliente_protegido.post(
        "/solo-clientes", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 403


def test_una_operacion_de_veterinarios_responde_403_a_un_cliente(
    client: TestClient, cliente_protegido: TestClient
) -> None:
    _registrar(client, EMAIL_CLIENTE, ROLE_CLIENT)
    token = _iniciar_sesion(client, EMAIL_CLIENTE)

    respuesta = cliente_protegido.post(
        "/solo-veterinarios", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 403


def test_una_operacion_de_clientes_acepta_a_un_cliente(
    client: TestClient, cliente_protegido: TestClient
) -> None:
    registrado = _registrar(client, EMAIL_CLIENTE, ROLE_CLIENT)
    token = _iniciar_sesion(client, EMAIL_CLIENTE)

    respuesta = cliente_protegido.post(
        "/solo-clientes", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == registrado["id"]


def test_el_registro_y_el_login_no_exigen_credenciales(client: TestClient) -> None:
    esquema = client.get("/openapi.json").json()

    assert esquema["paths"]["/auth/register"]["post"].get("security", []) == []
    assert esquema["paths"]["/auth/login"]["post"].get("security", []) == []
