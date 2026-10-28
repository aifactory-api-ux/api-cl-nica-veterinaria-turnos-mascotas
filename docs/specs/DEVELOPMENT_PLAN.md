# Tasks

Todas las pruebas de esta lista las escribe el propio agente Developer dentro del grupo que implementa el comportamiento correspondiente: el equipo es solo Developer, sin QA ni DevSec.

Ninguna tarea exige `docker build` ni `docker compose up` (el entorno de entrega no tiene demonio Docker); los archivos de contenedor se verifican de forma estática.

## 1. Andamiaje del proyecto y dependencias

- [ ] 1.1 Crear la estructura de paquetes `app/`, `app/core/`, `app/db/`, `app/schemas/`, `app/api/`, `app/api/routes/` y `app/services/` con sus `__init__.py`, más el directorio `tests/`, `app/main.py` (aplicación FastAPI vacía) y `app/core/config.py` con los ajustes `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM` y `JWT_EXPIRE_MINUTES` leídos del entorno; verificar que `python -c "from app.main import app; print(app.title)"` imprime el título de la aplicación sin error.
- [ ] 1.2 Crear `requirements.txt` (fastapi, uvicorn[standard], sqlalchemy, psycopg[binary], pydantic-settings, pyjwt, bcrypt) y `requirements-dev.txt` (pytest, httpx, pyyaml) y verificar que `pip install -r requirements.txt -r requirements-dev.txt` termina sin error de resolución.
- [ ] 1.3 Crear `pytest.ini` con `testpaths = tests` y `addopts = -q` y verificar que `pytest --collect-only` no reporta errores de configuración (solo que todavía no hay pruebas).

## 2. Persistencia y sesión de base de datos

- [ ] 2.1 Implementar `app/db/base.py` (Base declarativa, motor, `SessionLocal`, dependencia `get_db`) y `app/db/models.py` con las entidades `User` (email único, hash de contraseña, rol), `Pet` (nombre, especie, fecha de nacimiento, `owner_id`) y `Appointment` (`pet_id`, `vet_id`, `start_at`, `end_at`, `status`), declarando el índice único parcial sobre `(vet_id, start_at)` filtrado por `status = 'scheduled'` solo para PostgreSQL, de modo que la misma clase de modelo sirva en SQLite; verificar que `python -c "from app.db.models import User, Pet, Appointment; print('modelos ok')"` no falla.
- [ ] 2.2 Crear `tests/conftest.py` con los fixtures de pruebas: motor SQLite en archivo temporal, creación del esquema, sesión aislada por prueba, cliente de `TestClient` y factories de usuario, veterinario y mascota; verificar que `pytest --collect-only` importa `tests/conftest.py` sin errores de fixtures.
- [ ] 2.3 Escribir `tests/test_persistence.py` con pruebas de comportamiento que comprueban que el esquema se crea en una base vacía, que un `User`, un `Pet` y un `Appointment` se guardan y se leen con sus relaciones, y que la restricción de unicidad del email rechaza un segundo `User` con el mismo correo; verificar que `pytest tests/test_persistence.py` pasa.

## 3. Endpoint de salud

- [ ] 3.1 Implementar `app/api/routes/health.py` con `GET /health` que responde `200` y el cuerpo `{"status": "ok"}` sin exigir credenciales, y registrar el router en `app/main.py`; verificar con una prueba que el endpoint devuelve ese cuerpo.
- [ ] 3.2 Escribir `tests/test_health.py` con pruebas de que `GET /health` responde `200` con `{"status": "ok"}` y de que no exige encabezado `Authorization` ni devuelve 401 cuando el token es inválido; verificar que `pytest tests/test_health.py` pasa.
- [ ] 3.3 Crear `README.md` con la sección de puesta en marcha (requisitos, instalación de dependencias, variables de entorno, arranque local con `uvicorn app.main:app --host 0.0.0.0 --port 8000` y ejemplo `curl` de `GET /health`); verificar que los comandos escritos en el README son los que ejecuta la aplicación y que el ejemplo `curl` coincide con la respuesta del endpoint.

## 4. Autenticación y autorización

- [ ] 4.1 Implementar `app/core/security.py` (hash y verificación de contraseñas con `bcrypt`, emisión y decodificación de tokens JWT HS256 con `sub`, `role`, `email` y `exp`) y `app/api/deps.py` (`get_current_user` con `HTTPBearer(auto_error=False)` que devuelve 401 ante credenciales ausentes o token inválido, y `require_client` / `require_vet` que devuelven 403 ante un rol no permitido); verificar con una prueba que un token ausente o inválido produce 401 en una ruta protegida.
- [ ] 4.2 Implementar `app/schemas/auth.py` (registro con `email`, `password` de mínimo 8 caracteres y `role` limitado a `client` o `vet`; login con `email` y `password`) y `app/api/routes/auth.py` con `POST /auth/register` (201 con `{id, email, role}` y 409 ante email duplicado) y `POST /auth/login` (200 con `{access_token, token_type: "bearer"}` y 401 ante credenciales incorrectas); verificar con una prueba que el token devuelto por el login se acepta después en una ruta protegida.
- [ ] 4.3 Escribir `tests/test_auth.py` con pruebas de que el registro de cliente y de veterinario devuelve 201 con los campos correctos, de que el email duplicado devuelve 409, de que una contraseña de menos de 8 caracteres y un rol inválido devuelven 422, de que el login devuelve un JWT con `token_type` `bearer` identificable, de que unas credenciales incorrectas devuelven 401 y de que una ruta protegida devuelve 401 sin token y con token inválido; verificar que `pytest tests/test_auth.py` pasa.
- [ ] 4.4 Añadir al `README.md` los ejemplos `curl` de `POST /auth/register` y `POST /auth/login` y el uso del encabezado `Authorization: Bearer <access_token>`; verificar que los ejemplos del README devuelven los mismos códigos y cuerpos que fija `specs/auth/spec.md`.

## 5. Directorio de veterinarios

- [ ] 5.1 Implementar `app/api/routes/vets.py` con `GET /vets` que exige token Bearer y responde 200 con el arreglo de `{id, email}` de los usuarios con rol `vet`, sin exponer contraseñas; verificar con una prueba que el listado incluye solo veterinarios.
- [ ] 5.2 Escribir `tests/test_vets.py` con pruebas de que el listado devuelve un objeto con `id` y `email` por veterinario, de que devuelve un arreglo vacío sin veterinarios registrados, de que un cliente no puede ver contraseñas ajenas y de que sin token devuelve 401; verificar que `pytest tests/test_vets.py` pasa.
- [ ] 5.3 Añadir al `README.md` el ejemplo `curl` de `GET /vets`; verificar que el ejemplo coincide con la respuesta real del endpoint.

## 6. Mascotas

- [ ] 6.1 Implementar `app/schemas/pet.py` (especie limitada a `dog`, `cat` u `other`; `birth_date` no posterior a hoy) y `app/api/routes/pets.py` con `POST /pets` (201 con `{id, name, species, birth_date, owner_id}`, 403 para el rol `vet`, 422 por especie o fecha inválidas) y `GET /pets` que devuelve solo las mascotas del cliente autenticado; verificar con una prueba que `owner_id` es el cliente autenticado.
- [ ] 6.2 Escribir `tests/test_pets.py` con pruebas de registro exitoso, de 403 al registrar un veterinario, de 422 por especie `bird` y por fecha de nacimiento futura, y de que el listado devuelve solo las mascotas del cliente autenticado (arreglo vacío si no tiene o si es veterinario); verificar que `pytest tests/test_pets.py` pasa.
- [ ] 6.3 Añadir al `README.md` los ejemplos `curl` de `POST /pets` y `GET /pets`; verificar que los ejemplos coinciden con la respuesta real del endpoint.

## 7. Reglas de agenda y turnos

- [ ] 7.1 Implementar `app/services/scheduling.py` con las reglas de franja horaria en funciones puras: duración de 30 minutos, inicio en punto o y media, días de lunes a sábado, ventana de inicio de 09:00 a 17:30 y rechazo de instantes ya transcurridos, exponiendo el error de dominio con el motivo; verificar con pruebas unitarias de `validate_slot` en `tests/test_appointments.py` para cada regla por separado, incluidos los casos límite de 08:30, 17:30, 18:00 y el domingo.
- [ ] 7.2 Implementar `app/schemas/appointment.py` (petición con `pet_id`, `vet_id` y `start_at` ISO 8601) y `app/api/routes/appointments.py` con `POST /appointments` (201 con `{id, pet_id, vet_id, start_at, end_at, status: "scheduled"}` y `end_at` 30 minutos después; 403 si quien agenda es veterinario o la mascota es ajena; 404 si la mascota o el veterinario no existen; 422 por fecha-hora inválida, minutos no `00`/`30`, día u hora fuera de la ventana o fecha pasada; 409 si el veterinario ya tiene un turno activo en esa franja), `GET /appointments` (turnos del cliente o del veterinario según el token) y `POST /appointments/{id}/cancel` (cancelación por el dueño o el veterinario, 403 para terceros, 404 si el turno no existe, 409 si ya estaba cancelado); verificar con una prueba que el `end_at` devuelto es exactamente 30 minutos después del `start_at`.
- [ ] 7.3 Escribir `tests/test_appointments.py` con pruebas de reserva válida, de los 403 (veterinario que agenda y mascota ajena), de los 404 (mascota y veterinario inexistentes), de los 422 (formato no ISO 8601, minutos `10:15`, domingo, 08:30, 18:00 y fecha pasada), del 409 por turno activo duplicado, del listado por cliente y por veterinario, de la cancelación por dueño y por veterinario, del 403 al cancelar un turno ajeno, del 409 al cancelar dos veces y de que un horario cancelado se puede volver a agendar; verificar que `pytest tests/test_appointments.py` pasa.
- [ ] 7.4 Añadir al `README.md` los ejemplos `curl` de `POST /appointments`, `GET /appointments` y `POST /appointments/{id}/cancel` con los casos de error relevantes; verificar que los ejemplos coinciden con la respuesta real de cada endpoint.

## 8. Contenedores

- [ ] 8.1 Crear `Dockerfile` en la raíz del repositorio sobre `python:3.11-slim`, que instale `requirements.txt`, copie `app/` y arranque `uvicorn app.main:app --host 0.0.0.0 --port 8000`; verificar de forma estática que toda ruta de origen de las instrucciones `COPY` existe en el repositorio ejecutando `python -c "import pathlib; d=pathlib.Path('Dockerfile').read_text(); srcs=[p for l in d.splitlines() if l.strip().upper().startswith('COPY') for p in l.split()[1:-1]]; missing=[s for s in srcs if not pathlib.Path(s).exists()]; print('missing:', missing); raise SystemExit(1 if missing else 0)"` y que el comando termina con código 0.
- [ ] 8.2 Crear `docker-compose.yml` en la raíz del repositorio con el servicio `db` (`postgres:16-alpine`, volumen persistente y healthcheck con `pg_isready`) y el servicio `api` (`build: .`, `depends_on` el servicio `db` con `condition: service_healthy`, `DATABASE_URL` apuntando a `db` y puerto `8000:8000`); verificar de forma estática que `python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"` parsea el archivo sin error y que los nombres de servicio, la imagen de PostgreSQL, la variable `DATABASE_URL` y la dependencia entre servicios son los previstos.
- [ ] 8.3 Crear `.env.example` con `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM` y `JWT_EXPIRE_MINUTES` y su valor de ejemplo, y añadir al `README.md` la sección de ejecución con `docker compose up --build` y las variables que sobreescribir; verificar que los nombres de las variables del `.env.example` coinciden con los que lee `app/core/config.py` y con los que declara `docker-compose.yml`.

## 9. Verificación integral

- [ ] 9.1 Ejecutar `pytest` completo y verificar que todas las pruebas pasan sin errores ni fallos.
- [ ] 9.2 Verificar que el documento OpenAPI de la aplicación expone las rutas `GET /health`, `POST /auth/register`, `POST /auth/login`, `GET /vets`, `POST /pets`, `GET /pets`, `POST /appointments`, `GET /appointments` y `POST /appointments/{id}/cancel` con los códigos de éxito acordados.
- [ ] 9.3 Comprobar en local que el servidor responde en `http://127.0.0.1:8000/health` arrancándolo en segundo plano con `uvicorn app.main:app --host 127.0.0.1 --port 8000 & echo $! > /tmp/opencode/uvicorn.pid`, anotando el PID, y detener únicamente ese PID registrado al terminar la comprobación; verificar que la respuesta es `{"status":"ok"}` y que no queda ningún proceso servidor en ejecución.
