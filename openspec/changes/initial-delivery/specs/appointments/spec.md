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
