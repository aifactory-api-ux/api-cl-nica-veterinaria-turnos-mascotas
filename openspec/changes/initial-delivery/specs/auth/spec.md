# Spec Delta

## Purpose

Permite que clientes y veterinarios se registren en la plataforma, inicien sesión para recibir un token JWT y que la API use ese token para distinguir al usuario autenticado y su rol en el resto de las operaciones.

## ADDED Requirements

### Requirement: Registro de un usuario con rol
El sistema SHALL exponer `POST /auth/register` que recibe `email`, `password` y `role`, y responde con código HTTP 201 y el cuerpo JSON `{"id": ..., "email": ..., "role": ...}` con el identificador del usuario creado, su email y su rol.

#### Scenario: Registro de un cliente
- **WHEN** se envía `POST /auth/register` con `email` `cliente@clinica.test`, `password` `secreto123` y `role` `client`
- **THEN** la API responde con código HTTP 201
- **AND** el cuerpo de la respuesta contiene `email` `cliente@clinica.test` y `role` `client`
- **AND** el cuerpo de la respuesta contiene el `id` del usuario creado
- **AND** el cuerpo de la respuesta no contiene la contraseña

#### Scenario: Registro de un veterinario
- **WHEN** se envía `POST /auth/register` con `email` `vet@clinica.test`, `password` `secreto123` y `role` `vet`
- **THEN** la API responde con código HTTP 201
- **AND** el cuerpo de la respuesta contiene `email` `vet@clinica.test` y `role` `vet`

### Requirement: Email único en el registro
El sistema SHALL rechazar con código HTTP 409 el registro de un `email` que ya está registrado, sin crear un segundo usuario con ese email.

#### Scenario: Registro con email duplicado
- **WHEN** ya existe un usuario con `email` `cliente@clinica.test` y se envía `POST /auth/register` con ese mismo `email`, `password` `secreto123` y `role` `client`
- **THEN** la API responde con código HTTP 409

### Requirement: Contraseña de al menos 8 caracteres
El sistema SHALL rechazar con código HTTP 422 el registro con una `password` de menos de 8 caracteres.

#### Scenario: Registro con contraseña demasiado corta
- **WHEN** se envía `POST /auth/register` con `email` `corto@clinica.test`, `password` `corta` (5 caracteres) y `role` `client`
- **THEN** la API responde con código HTTP 422

### Requirement: Rol limitado a client o vet
El sistema SHALL rechazar con código HTTP 422 el registro con un `role` distinto de `client` y `vet`.

#### Scenario: Registro con rol inválido
- **WHEN** se envía `POST /auth/register` con `email` `otro@clinica.test`, `password` `secreto123` y `role` `admin`
- **THEN** la API responde con código HTTP 422

### Requirement: Inicio de sesión con token JWT
El sistema SHALL exponer `POST /auth/login` que recibe `email` y `password`, y responde con código HTTP 200 y el cuerpo JSON `{"access_token": ..., "token_type": "bearer"}` donde `access_token` es un JWT que identifica al usuario y su rol.

#### Scenario: Inicio de sesión válido
- **WHEN** se envía `POST /auth/login` con el `email` y la `password` de un usuario registrado
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta contiene `token_type` con el valor `bearer`
- **AND** el cuerpo de la respuesta contiene un `access_token` no vacío

#### Scenario: El token entregado identifica al usuario y su rol
- **WHEN** se decodifica el `access_token` devuelto al iniciar sesión
- **THEN** el token es un JWT que contiene el `id` del usuario autenticado
- **AND** el token contiene el rol `client` o `vet` de ese usuario

#### Scenario: Credenciales incorrectas
- **WHEN** se envía `POST /auth/login` con un `email` registrado y una `password` incorrecta
- **THEN** la API responde con código HTTP 401

#### Scenario: Usuario inexistente
- **WHEN** se envía `POST /auth/login` con un `email` que no está registrado
- **THEN** la API responde con código HTTP 401

### Requirement: Endpoints protegidos con token Bearer
El sistema SHALL exigir el encabezado `Authorization: Bearer <access_token>` en todas las operaciones distintas de `GET /health`, `POST /auth/register` y `POST /auth/login`, y SHALL responder con código HTTP 401 cuando el encabezado falta o el token no es válido.

#### Scenario: Operación protegida sin encabezado Authorization
- **WHEN** se envía `GET /pets` sin encabezado `Authorization`
- **THEN** la API responde con código HTTP 401

#### Scenario: Operación protegida con token inválido
- **WHEN** se envía `GET /pets` con el encabezado `Authorization: Bearer token-invalido`
- **THEN** la API responde con código HTTP 401

#### Scenario: Operación protegida con token válido
- **WHEN** se envía `GET /pets` con el encabezado `Authorization: Bearer <access_token>` de un usuario registrado
- **THEN** la API responde con un código HTTP distinto de 401
- **AND** la respuesta corresponde al usuario del token

### Requirement: Identidad y rol derivados del token
El sistema SHALL usar el token Bearer presentado para determinar el `id` y el rol del usuario que realiza la operación, sin exigir datos de identidad adicionales en el cuerpo de la petición.

#### Scenario: El rol del token gobierna el resultado de la operación
- **WHEN** un cliente y un veterinario presentan tokens válidos en una misma operación
- **THEN** la API usa el rol del token para decidir si la operación se permite
- **AND** no toma el rol de ningún otro cuerpo de petición
