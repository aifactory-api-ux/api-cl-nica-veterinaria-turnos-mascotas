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
