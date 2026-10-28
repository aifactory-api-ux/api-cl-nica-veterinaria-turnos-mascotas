# Spec Delta

## Purpose

Permite que un usuario autenticado consulte el directorio de veterinarios de la clínica, obteniendo el identificador y el email de cada uno para poder elegir a quién agendar un turno.

## ADDED Requirements

### Requirement: Listado de veterinarios
El sistema SHALL exponer `GET /vets` que responde con código HTTP 200 y un arreglo JSON con un objeto `{"id": ..., "email": ...}` por cada usuario registrado con rol `vet`, sin exponer contraseñas ni otros datos del usuario.

#### Scenario: Listado con veterinarios registrados
- **WHEN** existen dos usuarios con rol `vet` y se envía `GET /vets` con un token Bearer válido
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta es un arreglo de dos objetos
- **AND** cada objeto contiene la clave `id` y la clave `email` del veterinario
- **AND** ningún objeto contiene la contraseña del veterinario

#### Scenario: Listado sin veterinarios registrados
- **WHEN** no existe ningún usuario con rol `vet` y se envía `GET /vets` con un token Bearer válido
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta es un arreglo vacío

#### Scenario: El listado de veterinarios exige autenticación
- **WHEN** se envía `GET /vets` sin encabezado `Authorization` o con un token inválido
- **THEN** la API responde con código HTTP 401
