# Spec Delta

## Purpose

Permite que cada cliente registre las mascotas que atiende en la clínica y consulte su propio catálogo, para poder agendarle turnos con los veterinarios.

## ADDED Requirements

### Requirement: Registro de una mascota por su cliente
El sistema SHALL exponer `POST /pets` que recibe `name`, `species` y `birth_date`, y responde con código HTTP 201 y el cuerpo JSON `{"id": ..., "name": ..., "species": ..., "birth_date": ..., "owner_id": ...}`, donde `owner_id` es el identificador del cliente autenticado.

#### Scenario: Registro de una mascota por el cliente
- **WHEN** se envía `POST /pets` con `name` `Firulais`, `species` `dog` y `birth_date` `2020-05-10`, usando el token de un cliente
- **THEN** la API responde con código HTTP 201
- **AND** el cuerpo de la respuesta contiene `name` `Firulais`, `species` `dog` y `birth_date` `2020-05-10`
- **AND** el cuerpo de la respuesta contiene un `id` de mascota y un `owner_id` igual al `id` del cliente autenticado

### Requirement: Solo los clientes registran mascotas
El sistema SHALL responder con código HTTP 403 cuando un usuario con rol `vet` intenta registrar una mascota.

#### Scenario: Un veterinario intenta registrar una mascota
- **WHEN** se envía `POST /pets` con `name` `Firulais`, `species` `dog` y `birth_date` `2020-05-10`, usando el token de un veterinario
- **THEN** la API responde con código HTTP 403

### Requirement: Especie dentro de dog, cat u other
El sistema SHALL rechazar con código HTTP 422 el registro de una mascota cuya `species` no sea `dog`, `cat` ni `other`.

#### Scenario: Registro con especie no admitida
- **WHEN** se envía `POST /pets` con `name` `Firulais`, `species` `bird` y `birth_date` `2020-05-10`, usando el token de un cliente
- **THEN** la API responde con código HTTP 422

### Requirement: Fecha de nacimiento no futura
El sistema SHALL rechazar con código HTTP 422 el registro de una mascota cuya `birth_date` sea posterior al día actual.

#### Scenario: Registro con fecha de nacimiento futura
- **WHEN** se envía `POST /pets` con `name` `Firulais`, `species` `dog` y `birth_date` `2999-01-01`, usando el token de un cliente
- **THEN** la API responde con código HTTP 422

### Requirement: Listado de las mascotas del cliente autenticado
El sistema SHALL exponer `GET /pets` que responde con código HTTP 200 y un arreglo JSON con las mascotas cuyo `owner_id` es el identificador del cliente autenticado, sin incluir mascotas de otros clientes.

#### Scenario: Listado con mascotas propias y ajenas
- **WHEN** el cliente autenticado tiene dos mascotas y otro cliente tiene una, y se envía `GET /pets` con el token del primer cliente
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta es un arreglo con las dos mascotas del cliente autenticado
- **AND** el cuerpo de la respuesta no contiene la mascota del otro cliente

#### Scenario: Listado sin mascotas propias
- **WHEN** el cliente autenticado no tiene mascotas y se envía `GET /pets` con su token
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta es un arreglo vacío

#### Scenario: Listado de mascotas de un veterinario
- **WHEN** se envía `GET /pets` con el token de un veterinario
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta es un arreglo vacío
