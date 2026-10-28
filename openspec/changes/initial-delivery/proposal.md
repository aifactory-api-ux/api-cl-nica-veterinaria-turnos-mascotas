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
