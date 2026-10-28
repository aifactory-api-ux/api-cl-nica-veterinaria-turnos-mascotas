# Proposal

## Why

La clínica veterinaria no tiene hoy ninguna vía digital para registrar clientes, veterinarios y mascotas, ni para agendar turnos: toda la gestión de agenda es manual y no deja trazabilidad. El equipo interno necesita una API REST única, lista para ejecutar, donde los clientes registren sus mascotas y agenden turnos con veterinarios aplicando las reglas de agenda del consultorio (franjas de 30 minutos, lunes a sábado, sin doble reserva).

## What Changes

- Se crea una API REST con FastAPI respaldada por PostgreSQL, que expone los endpoints de salud, autenticación, veterinarios, mascotas y turnos.
- `GET /health` responde `200 {"status": "ok"}` como sonda de disponibilidad del servicio.
- `POST /auth/register` y `POST /auth/login` emiten tokens JWT (`bearer`) y apply las reglas de email duplicado (409), contraseña corta (422), rol inválido (422) y credenciales incorrectas (401).
- Todos los endpoints salvo `GET /health`, `POST /auth/register` y `POST /auth/login` exigen `Authorization: Bearer` y responden 401 sin token o con token inválido.
- `GET /vets` expone el directorio de veterinarios registrados.
- `POST /pets` y `GET /pets` permiten a un cliente registrar y listar sus propias mascotas, validando especie (`dog`, `cat`, `other`) y fecha de nacimiento no futura; un veterinario recibe 403.
- `POST /appointments`, `GET /appointments` y `POST /appointments/{id}/cancel` gestionan la agenda: solo clientes agendan, solo sobre mascotas propias, en franjas de 30 minutos de lunes a sábado entre 09:00 y 18:00, sin double booking del veterinario y con cancelación que libera el horario.
- Se agrega un `Dockerfile` en la raíz del repositorio y un `docker-compose.yml` en la raíz que construyen y ejecutan la API junto con PostgreSQL.
- Se entrega una suite de pruebas con pytest y un README con las instrucciones de levantar el proyecto y ejemplos `curl` de cada endpoint.

## Capabilities

### New Capabilities
- `health`: Sonda de disponibilidad del servicio (`GET /health`).
- `auth`: Registro de usuarios con rol `client`/`vet`, inicio de sesión con JWT y aplicación del token Bearer en los endpoints protegidos.
- `vets`: Directorio de veterinarios registrados consultable por los usuarios autenticados.
- `pets`: Registro y consulta de las mascotas de un cliente, con validación de especie y fecha de nacimiento.
- `appointments`: Agenda de turnos: creación bajo reglas de franja horaria y disponibilidad, consulta por propietario o veterinario, y cancelación que libera el horario.
- `containerization`: Construcción y ejecución del proyecto en contenedores mediante `Dockerfile` y `docker-compose.yml` en la raíz del repositorio.

### Modified Capabilities

Ninguna. El repositorio no tiene especificaciones previas; todas las capacidades de esta entrega son nuevas.

## Impact

- **Código nuevo**: API FastAPI organized en módulos de salud, autenticación, veterinarios, mascotas y turnos, con capa de acceso a datos sobre PostgreSQL.
- **Contrato HTTP**: seis rutas de lectura (`GET /health`, `GET /vets`, `GET /pets`, `GET /appointments`) y cinco de escritura (`POST /auth/register`, `POST /auth/login`, `POST /pets`, `POST /appointments`, `POST /appointments/{id}/cancel`), con `Authorization: Bearer` en las marcadas como protegidas.
- **Dependencias**: servidor FastAPI con soporte OpenAPI, ORM/session contra PostgreSQL, librería de codificación y validación de contraseñas, librería de JWT y cliente PostgreSQL para los contenedores.
- **Persistencia**: nuevas tablas de usuarios, mascotas y turnos en PostgreSQL, con `start_at` en UTC.
- **Operación**: `Dockerfile` y `docker-compose.yml` en la raíz del repositorio para levantar la API y la base de datos.


<!-- specs/appointments/spec.md -->
# Spec Delta

## Purpose

Permite gestionar la agenda de turnos de la clínica veterinaria: agendar, consultar y cancelar citas entre las mascotas de un cliente y un veterinario, respetando la franja horaria del consultorio y evitando reservas duplicadas.

## ADDED Requirements

### Requirement: Creación de un turno por un cliente
El sistema SHALL exponer `POST /appointments` que recibe `pet_id`, `vet_id` y `start_at`, y responde con código HTTP 201 y el cuerpo JSON `{"id": ..., "pet_id": ..., "vet_id": ..., "start_at": ..., "end_at": ..., "status": "scheduled"}`.

#### Scenario: Reserva de un horario disponible
- **WHEN** un cliente con una mascota propia envía `POST /appointments` con su `pet_id`, el `vet_id` de un veterinario y un `start_at` válido y libre
- **THEN** la API responde con código HTTP 201
- **AND** el cuerpo de la respuesta contiene el `pet_id` y el `vet_id` enviados
- **AND** el cuerpo de la respuesta contiene `status` con el valor `scheduled`
- **AND** el `end_at` de la respuesta es exactamente 30 minutos después del `start_at` enviado

### Requirement: Solo los clientes agendan turnos
El sistema SHALL responder con código HTTP 403 cuando un usuario con rol `vet` intenta agendar un turno.

#### Scenario: Un veterinario intenta agendar un turno
- **WHEN** se envía `POST /appointments` con `pet_id`, `vet_id` y `start_at` usando el token de un veterinario
- **THEN** la API responde con código HTTP 403

### Requirement: Solo se agendan turnos sobre mascotas propias
El sistema SHALL responder con código HTTP 403 cuando un cliente intenta agendar un turno para una mascota que no le pertenece.

#### Scenario: Un cliente intenta agendar sobre la mascota de otro cliente
- **WHEN** el cliente B envía `POST /appointments` con el `pet_id` de una mascota del cliente A, un `vet_id` válido y un `start_at` válido
- **THEN** la API responde con código HTTP 403

### Requirement: Mascota inexistente en la reserva
El sistema SHALL responder con código HTTP 404 cuando la reserva referencia un `pet_id` que no corresponde a ninguna mascota.

#### Scenario: Reserva con pet_id inexistente
- **WHEN** se envía `POST /appointments` con un `pet_id` inexistente, un `vet_id` válido y un `start_at` válido
- **THEN** la API responde con código HTTP 404

### Requirement: Veterinario inexistente en la reserva
El sistema SHALL responder con código HTTP 404 cuando la reserva referencia un `vet_id` que no corresponde a ningún veterinario.

#### Scenario: Reserva con vet_id inexistente
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` inexistente y un `start_at` válido
- **THEN** la API responde con código HTTP 404

### Requirement: start_at como fecha-hora ISO 8601 en UTC
El sistema SHALL exigir que `start_at` sea una fecha-hora ISO 8601 válida e interpretarla en UTC, y SHALL responder con código HTTP 422 cuando el valor no sea una fecha-hora ISO 8601 válida.

#### Scenario: Reserva con start_at no ISO 8601
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y `start_at` con el valor `no-es-una-fecha`
- **THEN** la API responde con código HTTP 422

#### Scenario: Reserva con start_at en UTC
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y `start_at` con el valor `2030-06-10T10:00:00Z`
- **THEN** la API responde con código HTTP 201
- **AND** el `start_at` devuelto en la respuesta representa ese instante en UTC

### Requirement: Turnos que empiezan en punto o y media
El sistema SHALL aceptar únicamente horarios de inicio con minutos `00` o `30`, y SHALL responder con código HTTP 422 cuando `start_at` tenga otros minutos.

#### Scenario: Reserva con minutos no múltiplos de 30
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y `start_at` con el valor `2030-06-10T10:15:00Z`
- **THEN** la API responde con código HTTP 422

#### Scenario: Reserva con inicio en punto y media
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y `start_at` con el valor `2030-06-10T10:30:00Z`
- **THEN** la API responde con código HTTP 201

### Requirement: Ventana de atención de lunes a sábado
El sistema SHALL aceptar como horario de inicio las franjas de 30 minutos desde las 09:00 hasta las 17:30 inclusive, de lunes a sábado, y SHALL responder con código HTTP 422 para cualquier otro horario de inicio.

#### Scenario: Reserva en domingo
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y un `start_at` de domingo dentro de la franja horaria
- **THEN** la API responde con código HTTP 422

#### Scenario: Reserva antes de las 09:00
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y un `start_at` de un día de lunes a sábado a las 08:30
- **THEN** la API responde con código HTTP 422

#### Scenario: Reserva después de las 17:30
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y un `start_at` de un día de lunes a sábado a las 18:00
- **THEN** la API responde con código HTTP 422

#### Scenario: Reserva el último inicio permitido
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y un `start_at` de sábado a las 17:30
- **THEN** la API responde con código HTTP 201
- **AND** el `end_at` de la respuesta es ese mismo sábado a las 18:00

### Requirement: No se agendan turnos en el pasado
El sistema SHALL responder con código HTTP 422 cuando `start_at` sea un instante ya transcurrido.

#### Scenario: Reserva en una fecha pasada
- **WHEN** se envía `POST /appointments` con un `pet_id` propio, un `vet_id` válido y un `start_at` del año 2020, un martes a las 10:00
- **THEN** la API responde con código HTTP 422

### Requirement: Sin doble reserva activa del veterinario
El sistema SHALL responder con código HTTP 409 cuando el veterinario indicado ya tenga un turno activo en el mismo horario.

#### Scenario: Veterinario con turno activo en la misma franja
- **WHEN** un veterinario ya tiene un turno con `status` `scheduled` que empieza a las 10:00 y un cliente intenta agendar otra reserva con el mismo veterinario a las 10:00
- **THEN** la API responde con código HTTP 409

#### Scenario: Reserva en otra franja del mismo veterinario
- **WHEN** un veterinario ya tiene un turno con `status` `scheduled` que empieza a las 10:00 y un cliente intenta agendar una reserva con el mismo veterinario a las 11:00
- **THEN** la API responde con código HTTP 201

### Requirement: Listado de turnos del cliente
El sistema SHALL exponer `GET /appointments` que, para un cliente autenticado, responde con código HTTP 200 y un arreglo JSON con los turnos de las mascotas que le pertenecen.

#### Scenario: Listado de turnos de un cliente
- **WHEN** el cliente tiene un turno agendado para su mascota y otro cliente tiene un turno agendado para la suya, y se envía `GET /appointments` con el token del primer cliente
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta contiene el turno de la mascota del cliente autenticado
- **AND** el cuerpo de la respuesta no contiene el turno de la mascota del otro cliente

### Requirement: Listado de turnos del veterinario
El sistema SHALL exponer `GET /appointments` que, para un veterinario autenticado, responde con código HTTP 200 y un arreglo JSON con los turnos en los que participa como veterinario.

#### Scenario: Listado de turnos de un veterinario
- **WHEN** un veterinario tiene un turno agendado y otro veterinario tiene otro, y se envía `GET /appointments` con el token del primer veterinario
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta contiene el turno en el que participa el veterinario autenticado
- **AND** el cuerpo de la respuesta no contiene el turno del otro veterinario

### Requirement: Cancelación por el dueño de la mascota o el veterinario del turno
El sistema SHALL exponer `POST /appointments/{id}/cancel` y SHALL permitir la cancelación al cliente dueño de la mascota del turno y al veterinario asignado, devolviendo el turno actualizado con `status` `cancelled` y código HTTP 200.

#### Scenario: Cancelación por el cliente dueño de la mascota
- **WHEN** el cliente dueño de la mascota envía `POST /appointments/{id}/cancel` sobre un turno con `status` `scheduled`
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta es el turno cancelado con `status` `cancelled`

#### Scenario: Cancelación por el veterinario del turno
- **WHEN** el veterinario asignado al turno envía `POST /appointments/{id}/cancel` sobre un turno con `status` `scheduled`
- **THEN** la API responde con código HTTP 200
- **AND** el cuerpo de la respuesta es el turno cancelado con `status` `cancelled`

### Requirement: Cancelación restringida a los participantes del turno
El sistema SHALL responder con código HTTP 403 cuando un usuario que no es el dueño de la mascota ni el veterinario del turno intenta cancelarlo.

#### Scenario: Cancelación por un usuario no participante
- **WHEN** un cliente que no es dueño de la mascota del turno envía `POST /appointments/{id}/cancel`
- **THEN** la API responde con código HTTP 403

### Requirement: Cancelación de un turno ya cancelado
El sistema SHALL responder con código HTTP 409 cuando se intenta cancelar un turno que ya está en estado `cancelled`.

#### Scenario: Doble cancelación del mismo turno
- **WHEN** el cliente dueño de la mascota cancela un turno y luego vuelve a enviar `POST /appointments/{id}/cancel` sobre ese mismo turno
- **THEN** la API responde con código HTTP 409

### Requirement: Cancelación de un turno inexistente
El sistema SHALL responder con código HTTP 404 cuando se intenta cancelar un identificador de turno que no existe.

#### Scenario: Cancelación con identificador inexistente
- **WHEN** se envía `POST /appointments/999999/cancel` con un token Bearer válido
- **THEN** la API responde con código HTTP 404

### Requirement: El horario cancelado queda libre
El sistema SHALL permitir agendar un nuevo turno en un horario que fue cancelado previamente, y SHALL responder con código HTTP 201 a esa nueva reserva.

#### Scenario: Reagendamiento en un horario cancelado
- **WHEN** un turno con `status` `scheduled` que empieza a las 10:00 es cancelado y el cliente agenda de nuevo una reserva con el mismo veterinario a las 10:00
- **THEN** la API responde con código HTTP 201
- **AND** el cuerpo de la respuesta contiene el nuevo turno con `status` `scheduled`


<!-- specs/auth/spec.md -->
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


<!-- specs/containerization/spec.md -->
# Spec Delta

## Purpose

Permite que el equipo interno ejecute la API y su base de datos PostgreSQL de forma reproducible en cualquier entorno, a partir de los archivos de contenedor versionados en la raíz del repositorio, sin instalar dependencias a mano.

## ADDED Requirements

### Requirement: Imagen y composición de contenedores
El proyecto SHALL incluir un `Dockerfile` en la raíz del repositorio que construya la imagen de la aplicación, y un `docker-compose.yml` en la raíz del repositorio que construya esa imagen, aprovisione un servicio PostgreSQL y ejecute el servicio de la API conectado a él.

#### Scenario: La composición declara la API y la base de datos
- **WHEN** se carga el `docker-compose.yml` de la raíz del repositorio
- **THEN** define un servicio que construye la imagen de la API a partir del `Dockerfile` de la raíz del repositorio
- **AND** define un servicio de PostgreSQL
- **AND** el servicio de la API recibe la URL de conexión de ese servicio de PostgreSQL
- **AND** el servicio de la API declara su dependencia del servicio de PostgreSQL

#### Scenario: La imagen de la aplicación expone la API
- **WHEN** se inspecciona el `Dockerfile` de la raíz del repositorio
- **THEN** define una imagen que instala las dependencias de la aplicación y ejecuta el servidor de la API

#### Scenario: La imagen incluye los archivos que la aplicación necesita
- **WHEN** se inspecciona el `Dockerfile` de la raíz del repositorio
- **THEN** todas las rutas que copia a la imagen son archivos existentes del proyecto en el repositorio


<!-- specs/health/spec.md -->
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


<!-- specs/pets/spec.md -->
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


<!-- specs/vets/spec.md -->
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


# Design

## Context

El repositorio está vacío: no hay código, dependencias ni infraestructura previa, y no existe ninguna especificación archivada (ver `openspec list --specs`). Todo lo que sigue se crea desde cero en esta entrega.

Restricciones que condicionan el diseño:

- La API se ejecuta sobre PostgreSQL, pero el entorno de entrega no tiene demonio Docker: el servicio de base de datos solo puede existir dentro de los contenedores de `docker-compose.yml`. Por eso la capa de persistencia se mantiene portable entre PostgreSQL y SQLite, y la suite de pruebas corre contra SQLite sin depender de ningún servidor externo.
- El producto lo usa únicamente el equipo interno de la clínica; no hay frontend, ni multi-tenant, ni integraciones externas.
- El equipo de entrega es un único agente Developer: escribe el código y también las pruebas de cada bloque de trabajo (no hay agentes QA ni DevSec que revisen en paralelo).
- Los archivos de contenedor se verifican de forma estática (el YAML se parsea y toda ruta `COPY` existe en el repositorio); en el entorno de entrega no se ejecuta `docker build` ni `docker compose up`.

Los requisitos observables están en `specs/`; este documento solo cubre cómo se implementan.

## Goals / Non-Goals

**Goals:**

- Un servidor FastAPI con los routers de salud, autenticación, veterinarios, mascotas y turnos, servible con `uvicorn` y con Docker.
- Un único modelo ORM con las tres entidades del dominio (usuarios, mascotas, turnos) y reglas de negocio de la agenda aisladas en un módulo de dominio testeable de forma aislada.
- Autenticación por token JWT con los códigos de error acordados (401 sin token o con token inválido, 409 duplicados y solapamientos, 403 roles y participación).
- Pruebas con pytest que ejerciten el comportamiento de la API (endpoints HTTP y reglas de agenda) sin exigir un servidor de base de datos.
- `Dockerfile` y `docker-compose.yml` en la raíz que construyen la imagen y levantan la API junto con PostgreSQL.

**Non-Goals:**

- Interfaz web, panel de administración, correo electrónico o cualquier canal de notificación.
- Migraciones versionadas de esquema (Alembic): la entrega inicial crea el esquema al arrancar.
- Paginación, filtros o ordenamiento en los listados: el volumen de la clínica es pequeño y los contratos de `GET /pets`, `GET /vets` y `GET /appointments` son arreglos completos.
- Multi-tenant, roles adicionales, recuperación de contraseña, rotación o revocación de tokens.
- Política CORS: la API se consume desde el mismo origen de red o desde `curl`; no se expone middleware CORS.
- Cualquier requisito sobre pruebas o documentación en las especificaciones: viven en `tasks.md`.

## Decisions

### D1. Estructura del proyecto y separación por routers

La aplicación se divide por dominio técnico, con la lógica de negocio fuera de los handlers HTTP.

- **Alternativa considerada**: un único `main.py` con todo el código. Se descartó porque mezcla validación de entrada, acceso a datos y reglas de agenda, y hace imposible probar las reglas de la franja horaria sin levantar la API.

### D2. Persistencia: SQLAlchemy 2.0 síncrono sobre PostgreSQL

- El ORM es SQLAlchemy 2.0 en modo síncrono, con el driver `psycopg` (v3) y URL `postgresql+psycopg://...`.
- Se evita SQLAlchemy asíncrono porque FastAPI con `def` (síncrono) y `TestClient` cubren el caso de uso sin la complejidad del event loop, y la clínica no necesita concurrencia alta por request.
- La URL de conexión se lee de la variable de entorno `DATABASE_URL` (`app/core/config.py` con `pydantic-settings`), con un valor por defecto local para desarrollo.

### D3. Autenticación: JWT HS256 emitido por la propia API

- `POST /auth/login` emite un JWT HS256 con `sub` = id del usuario, `role`, `email`, `exp`; la vida por defecto es de 480 minutos (8 horas) y se configura con `JWT_EXPIRE_MINUTES`.
- La clave se lee de `JWT_SECRET` (valor por defecto solo para desarrollo local).
- La verificación se implementa en `app/core/security.py` con `PyJWT`; `app/api/deps.py` expone `get_current_user`, `require_client` y `require_vet`.
- La cabecera se lee con `HTTPBearer(auto_error=False)` para poder responder **401** (y no 403) cuando faltan credenciales, tal como fija `specs/auth/spec.md`. FastAPI devuelve 403 por defecto cuando `auto_error=True`, que es el código incorrecto para este contrato.
- **Alternativa considerada**: OAuth2 con `OAuth2PasswordBearer` y `WWW-Authenticate`. Se descartó porque introduce el formulario de token de FastAPI, que no es parte del contrato solicitado y complica los ejemplos `curl` del README.

### D4. Hash de contraseñas con `bcrypt` directo

- `app/core/security.py` usa el paquete `bcrypt` (`hashpw`/`checkpw`) sin `passlib`, porque `passlib` no es compatible con `bcrypt >= 4.1` y eso rompería el arranque.
- El hash se almacena en `users.password_hash`; el campo `password` nunca se serializa en ninguna respuesta.
- La longitud mínima de 8 caracteres se valida en el esquema Pydantic (`min_length=8`), lo que produce 422 de forma nativa de FastAPI.

### D5. Validación de entrada con Pydantic v2 y errores HTTP explícitos

- Los cuerpos de entrada se modelan con Pydantic v2 (`app/schemas/`), de modo que los errores de esquema (contraseña corta, rol inválido, especie no admitida, `start_at` no ISO 8601) devuelven 422 sin código adicional.
- Las reglas que dependen de estado (email duplicado, conflicto de horario, turno ya cancelado) se resuelven en el servicio y se traducen a 409 con `HTTPException`.
- Las reglas que dependen del rol o de la pertenencia del recurso (veterinario que registra mascota, cliente que agenda sobre mascota ajena, tercero que cancela) devuelven 403 con `HTTPException`.
- Los recursos inexistentes (mascota, veterinario, turno) devuelven 404.
- El cuerpo de error es el `{"detail": ...}` por defecto de FastAPI, que es consistente en todos los códigos.

### D6. Reglas de agenda como funciones puras

- `app/services/scheduling.py` concentra las reglas de `specs/appointments/spec.md`: `SLOT_MINUTES = 30`, apertura 09:00, último inicio 17:30 (cierre 18:00), días de lunes a sábado y minutos `00`/`30`.
- Las funciones (`validate_slot`, `slot_overlaps`) reciben y devuelven `datetime` con zona horaria y lanzan un error de dominio con un motivo (`SlotError`) que el router traduce a 422.
- **Alternativa considerada**: validar el horario dentro del router con condicionales en línea. Se descartó porque mezcla validación con el acceso a datos y preclude probar cada regla de forma aislada.

### D7. Modelo de datos

Tres tablas, con claves foráneas y borrado en cascada para las filas dependientes:

- `users`: `id` (entero, clave primaria autoincremental), `email` (cadena, único), `password_hash` (cadena), `role` (cadena, `client` o `vet`), `created_at`.
- `pets`: `id`, `name` (cadena), `species` (cadena, `dog`, `cat` u `other`), `birth_date` (fecha), `owner_id` (clave foránea a `users.id`), `created_at`.
- `appointments`: `id`, `pet_id` (clave foránea a `pets.id`), `vet_id` (clave foránea a `users.id`), `start_at`, `end_at`, `status` (cadena, `scheduled` o `cancelled`), `created_at`.

Las columnas `start_at` y `end_at` son `DateTime(timezone=True)`; `birth_date` es `Date`. Los identificadores son enteros porque el contrato de respuesta expone `id` y el volumen de la clínica no justifica UUID.

- **Alternativa considerada**: tabla `appointments` sin `status` y con borrado físico al cancelar. Se descartó porque la cancelación debe ser visible en la respuesta (`status: "cancelled"`) y auditable.

### D8. Sin doble reserva: verificación en aplicación y respaldo en PostgreSQL

- La comprobación de solapamiento se hace dentro de la misma transacción que inserta el turno, filtrando por `vet_id` y `status = 'scheduled'`, y se traduce a 409.
- En PostgreSQL se añade además un índice único parcial `UNIQUE (vet_id, start_at) WHERE status = 'scheduled'` como red de seguridad ante reservas concurrentes; en SQLite se omite por no ser portable.
- La cancelación conserva `start_at` y cambia solo `status`, por lo que el índice parcial libera el horario y permite volver a agendarlo.

### D9. Fechas en UTC

- `start_at` y `end_at` se guardan como `DateTime(timezone=True)` (en PostgreSQL, `TIMESTAMP WITH TIME ZONE`) y se interpretan siempre en UTC.
- Un `start_at` sin zona horaria se interpreta como UTC; uno con offset se convierte a UTC antes de validarse.
- `app/core/time.py` centraliza `utcnow()` y `ensure_aware()` para normalizar los `datetime` que devuelve el driver, ya que SQLite no conserva la zona horaria.

### D10. Contenedores

- `Dockerfile` en la raíz: imagen `python:3.11-slim`, copia `requirements.txt`, instala dependencias, copia `app/` y arranca `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- `docker-compose.yml` en la raíz: servicio `db` (`postgres:16-alpine`, volumen persistente, `pg_isready` como healthcheck) y servicio `api` (`build: .`, `depends_on: db` con `condition: service_healthy`, `DATABASE_URL` apuntando a `db`, puerto `8000:8000`).
- La API crea el esquema al arrancar si las tablas no existen, de modo que `docker compose up` deja la base lista sin pasos manuales.
- Los archivos de contenedor nunca se construyen en el entorno de entrega (sin demonio Docker): se comprueban de forma estática (el YAML parsea y cada origen de `COPY` existe en el repositorio).

### D11. Pruebas sobre SQLite con los mismos modelos

- `tests/conftest.py` reemplaza la dependencia de sesión por una base SQLite en archivo temporal, crea el esquema con `Base.metadata.create_all` y expone un `client` de `TestClient` más los datos de apoyo (cliente, veterinario, mascota).
- La aplicación no usa tipos exclusivos de PostgreSQL, por lo que los mismos modelos funcionan en ambos motores.

### D12. Archivos a crear

Rutas exactas respecto de la raíz del repositorio:

```
Dockerfile
docker-compose.yml
requirements.txt
requirements-dev.txt
.env.example
pytest.ini
README.md
app/__init__.py
app/main.py
app/core/__init__.py
app/core/config.py
app/core/security.py
app/core/time.py
app/db/__init__.py
app/db/base.py
app/db/models.py
app/schemas/__init__.py
app/schemas/auth.py
app/schemas/pet.py
app/schemas/appointment.py
app/api/__init__.py
app/api/deps.py
app/api/routes/__init__.py
app/api/routes/health.py
app/api/routes/auth.py
app/api/routes/vets.py
app/api/routes/pets.py
app/api/routes/appointments.py
app/services/__init__.py
app/services/scheduling.py
tests/conftest.py
tests/test_persistence.py
tests/test_health.py
tests/test_auth.py
tests/test_vets.py
tests/test_pets.py
tests/test_appointments.py
```

## Risks / Trade-offs

- [El esquema se crea al arrancar y no hay migraciones versionadas] → Aceptable para la entrega inicial; cuando el esquema cambie sobre datos reales, la primera evolución se hará con Alembic antes de tocar producción.
- [SQLite en las pruebas y PostgreSQL en producción pueden divergir en semántica (zonas horarias, índice parcial)] → Se usa solo SQL estándar y los tipos `DateTime(timezone=True)`/`Date`; el índice parcial es opcional y la lógica de solapamiento, que es la crítica, se ejecuta en la aplicación y se prueba en ambos motores.
- [La verificación de solapamiento bajo concurrencia real depende del índice único parcial de PostgreSQL] → La transacción y el filtro por `vet_id` cubren el caso común, y el índice convierte la carrera en un error de integridad que la capa de servicio traduce a 409.
- [`JWT_SECRET` con valor por defecto solo para desarrollo] → El README documenta que en el contenedor hay que fijar `JWT_SECRET`; la variable de entorno es la única vía de configuración en el `docker-compose.yml`.
- [El token dura 8 horas sin revocación] → El equipo interno de la clínica lo acepta; si hiciera falta revocación, se añade una lista de tokens revocados o expiración más corta sin cambiar los contratos de `specs/auth/spec.md`.

## Migration Plan

No hay migración de datos: es la primera versión y no existe un sistema previo.

Puesta en marcha:

1. Construir la imagen y levantar la composición: `docker compose up --build`.
2. La API espera a que PostgreSQL esté disponible, crea el esquema y expone `GET /health` en el puerto `8000`.
3. Registrar el primer usuario y usar su token en los ejemplos `curl` del README.

Reversión: eliminar los contenedores y el volumen de datos (`docker compose down -v`) y volver a levantar la versión anterior; no hay estado que migrar entre versiones porque el esquema se recrea desde cero.
