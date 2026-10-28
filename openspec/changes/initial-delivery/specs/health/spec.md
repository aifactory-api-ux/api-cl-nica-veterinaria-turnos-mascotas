# Spec Delta

## Purpose

Permite comprobar que la API de la clínica veterinaria está levantada y respondiendo peticiones, sin exigir credenciales ni depender del estado de la base de datos, para que la operación y el monitoreo puedan usarla como sonda de disponibilidad.

## ADDED Requirements

### Requirement: Sonda de disponibilidad del servicio
El sistema SHALL exponer `GET /health` como endpoint público que responde con código HTTP 200 y el cuerpo JSON `{"status": "ok"}`.

#### Scenario: Consulta de salud de una API disponible
- **WHEN** se envía una petición `GET /health` sin encabezado `Authorization`
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta es `{"status": "ok"}`

#### Scenario: La sonda de salud ignora credenciales ausentes o inválidas
- **WHEN** se envía una petición `GET /health` con un encabezado `Authorization` ausente o con un token inválido
- **THEN** la API responde con código HTTP 200 y el cuerpo `{"status": "ok"}`
- **AND** no responde con código HTTP 401
