"""Pruebas de la sonda de disponibilidad del servicio.

Las pruebas ejercitan el endpoint público ``GET /health``: debe responder
``200`` con el cuerpo ``{"status": "ok"}`` y no debe exigir credenciales ni
consultar la base de datos.
"""

from fastapi.testclient import TestClient


def test_la_sonda_de_salud_responde_ok_sin_credenciales(client: TestClient) -> None:
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_la_sonda_de_salud_ignora_un_token_invalido(client: TestClient) -> None:
    respuesta = client.get("/health", headers={"Authorization": "Bearer token-invalido"})

    assert respuesta.status_code != 401
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_la_ruta_de_salud_es_publica_en_el_openapi(client: TestClient) -> None:
    esquema = client.get("/openapi.json").json()

    assert "/health" in esquema["paths"]
    assert "get" in esquema["paths"]["/health"]
    assert esquema["paths"]["/health"]["get"].get("security", []) == []
