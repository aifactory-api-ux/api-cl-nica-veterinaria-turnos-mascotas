# API Clínica Veterinaria

API REST de la clínica veterinaria: los clientes registran sus mascotas y agendan
turnos con veterinarios, aplicando las reglas de agenda del consultorio (franjas de
30 minutos, de lunes a sábado, sin doble reserva del veterinario).

La API está construida con FastAPI y persiste los datos en PostgreSQL.

## Requisitos

- Python 3.11 o superior.
- PostgreSQL 14 o superior para los datos de la clínica. La sonda `GET /health` no
  consulta la base de datos, pero el resto de la API sí lo hace.

## Instalación de dependencias

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

El segundo comando instala las dependencias de desarrollo (pytest y httpx), necesarias
solo para ejecutar las pruebas.

## Variables de entorno

La aplicación lee las variables del entorno y, si existe, de un archivo `.env` en la raíz
del repositorio.

| Variable | Valor por defecto | Descripción |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://clinica:clinica@localhost:5432/clinica` | Cadena de conexión a PostgreSQL. |
| `JWT_SECRET` | `desarrollo-cambiar-en-produccion` | Clave de firma de los tokens JWT. Debe tener un valor propio fuera del desarrollo local. |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma de los tokens. |
| `JWT_EXPIRE_MINUTES` | `480` | Vigencia del token de acceso, en minutos. |

La raíz del repositorio incluye el archivo `.env.example`, que es la plantilla de
estas cuatro variables. Para usarla, copia el archivo y ajusta los valores:

```bash
cp .env.example .env
```

Contenido de la plantilla:

```
DATABASE_URL=postgresql+psycopg://clinica:clinica@localhost:5432/clinica
JWT_SECRET=cambia-esta-clave-en-produccion
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
```

## Base de datos

Crea la base de datos en PostgreSQL antes de arrancar el servidor:

```bash
createdb clinica
```

Las tablas (`users`, `pets` y `appointments`) se crean automáticamente al arrancar la
aplicación a partir de los modelos ORM, siempre que la base de datos exista y el usuario
de conexión tenga permisos sobre ella.

## Puesta en marcha

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

La API queda disponible en `http://127.0.0.1:8000` y su documentación interactiva en
`http://127.0.0.1:8000/docs`.

### Script de arranque

La raíz del repositorio incluye el script `run.sh`, que prepara un entorno virtual
propio con las dependencias del proyecto y levanta el servidor:

```bash
./run.sh
```

El script entiende tres comandos:

| Comando | Descripción |
| --- | --- |
| `./run.sh setup` | Crea el entorno virtual `.venv` e instala las dependencias del proyecto y de desarrollo. |
| `./run.sh test` | Prepara el entorno y ejecuta la suite completa de pruebas con pytest. |
| `./run.sh serve` | Prepara el entorno y arranca el servidor Uvicorn (comportamiento por defecto). |

La dirección y el puerto de escucha se ajustan con las variables `HOST` y `PORT`
(por defecto `127.0.0.1:8000`):

```bash
HOST=0.0.0.0 PORT=8000 ./run.sh serve
```

El script no fija ningún secreto: la configuración de la API se sigue leyendo del
entorno y del archivo `.env` de la raíz del repositorio.

### Comprobación de disponibilidad

```bash
curl -i http://127.0.0.1:8000/health
```

Respuesta:

```
HTTP/1.1 200 OK
content-type: application/json

{"status":"ok"}
```

El endpoint es público: no exige el encabezado `Authorization` y un token ausente o
inválido no altera la respuesta.

## Ejecución con contenedores

La forma recomendada para el equipo es levantar la API y PostgreSQL a la vez con
Docker Compose. Los dos servicios están declarados en `docker-compose.yml` de la
raíz del repositorio:

- `db`: PostgreSQL 16 sobre Alpine, con un volumen persistente para los datos de
  la clínica y una comprobación de salud con `pg_isready`.
- `api`: la imagen de la aplicación, construida a partir del `Dockerfile` de la raíz.

```bash
docker compose up --build
```

El servicio `api` espera a que la comprobación de salud de PostgreSQL sea
satisfactoria y entonces crea las tablas que falten, de modo que no hace falta
ningún paso manual de migración. La API queda disponible en
`http://127.0.0.1:8000` y su documentación interactiva en
`http://127.0.0.1:8000/docs`.

Para detener los contenedores conservando los datos:

```bash
docker compose down
```

Para detenerlos y borrar también el volumen con los datos de la clínica:

```bash
docker compose down -v
```

### Variables que hay que sobreescribir

| Variable | Valor de ejemplo | ¿Sobreescribir? |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://clinica:clinica@localhost:5432/clinica` | Solo para la ejecución local. `docker-compose.yml` la fija apuntando al servicio `db`. |
| `JWT_SECRET` | `cambia-esta-clave-en-produccion` | Sí. Es la clave de firma de los tokens: usa un valor propio. |
| `JWT_ALGORITHM` | `HS256` | Solo si se cambia el algoritmo de firma. |
| `JWT_EXPIRE_MINUTES` | `480` | Solo si se cambia la vigencia del token. |

Docker Compose lee el archivo `.env` de la raíz del repositorio al arrancar, así
que basta con copiar la plantilla como se indica más arriba y editar
`JWT_SECRET` para que el contenedor `api` reciba ese valor sin tocar
`docker-compose.yml`.

El `DATABASE_URL` del archivo `.env` se aplica cuando la aplicación se ejecuta
fuera de los contenedores, contra un PostgreSQL local. Dentro de la composición
la conexión va al servicio `db`, que es alcanzable solo desde la red interna de
Docker Compose.

El archivo `.env` guarda secretos locales: no lo subas al repositorio ni lo
compartas fuera del equipo.

## Autenticación

Los usuarios se registran con un rol (`client` o `vet`) e inician sesión para
obtener un token JWT. Solo `GET /health`, `POST /auth/register` y
`POST /auth/login` son públicos; el resto de las operaciones de la clínica
(`/pets`, `/vets`, `/appointments`) exige el encabezado
`Authorization: Bearer <access_token>`.

### Registro de un usuario

```bash
curl -i -X POST http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "cliente@clinica.test", "password": "secreto123", "role": "client"}'
```

Respuesta (`201 Created`):

```
{"id":1,"email":"cliente@clinica.test","role":"client"}
```

La respuesta nunca incluye la contraseña. El correo es único: si ya está
registrado, la API responde `409 Conflict` con
`{"detail":"Ya existe un usuario registrado con ese correo."}`. Una contraseña de
menos de 8 caracteres o un rol distinto de `client` y `vet` se rechazan con
`422 Unprocessable Entity`.

### Inicio de sesión

```bash
curl -i -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "cliente@clinica.test", "password": "secreto123"}'
```

Respuesta (`200 OK`):

```
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer"}
```

El `access_token` es un JWT que lleva el identificador, el rol, el correo y la
vigencia del usuario (aquí está abreviado). Un correo inexistente o una
contraseña incorrecta devuelven `401 Unauthorized` con
`{"detail":"Credenciales incorrectas."}`.

### Operaciones protegidas

El token de acceso se envía en el encabezado `Authorization`:

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -i http://127.0.0.1:8000/pets \
  -H "Authorization: Bearer $TOKEN"
```

Sin ese encabezado la API responde `401 Unauthorized`, y con un token caducado o
manipulado, también. El token determina el usuario y su rol, de modo que
ninguna operación necesita enviar el rol en el cuerpo de la petición.

## Directorio de veterinarios

`GET /vets` devuelve los veterinarios registrados, con su identificador y su
correo, para poder elegir a quién agendar un turno. Exige un token Bearer
válido, sea de un cliente o de un veterinario.

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -i http://127.0.0.1:8000/vets \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta (`200 OK`):

```
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"email":"vet@clinica.test"}]
```

El cuerpo es un arreglo completo: no hay paginación ni filtros. Solo aparecen
los usuarios con rol `vet` y cada objeto contiene únicamente `id` y `email`,
sin contraseñas ni otros datos del usuario. Si la clínica todavía no tiene
veterinarios registrados, la respuesta es un arreglo vacío (`[]`). Sin
encabezado `Authorization` o con un token inválido, la API responde
`401 Unauthorized`.

## Mascotas

Los clientes registran las mascotas que llevan a la clínica y consultan su
propio catálogo. Solo el rol `client` puede registrar mascotas: un
veterinario recibe `403 Forbidden`. Ambas operaciones exigen un token Bearer
válido.

### Registro de una mascota

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -i -X POST http://127.0.0.1:8000/pets \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"}'
```

Respuesta (`201 Created`):

```
HTTP/1.1 201 Created
content-type: application/json

{"id":1,"name":"Firulais","species":"dog","birth_date":"2020-05-10","owner_id":1}
```

El `owner_id` es siempre el identificador del cliente que envía la petición:
el cuerpo de la petición no permite atribuir la mascota a otro propietario. La
especie admite `dog`, `cat` u `other`, y cualquier otro valor se rechaza con
`422 Unprocessable Entity`. La fecha de nacimiento no puede ser posterior al
día actual, así que una fecha como `2999-01-01` también produce 422.

### Listado de las mascotas del cliente

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -i http://127.0.0.1:8000/pets \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta (`200 OK`):

```
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"name":"Firulais","species":"dog","birth_date":"2020-05-10","owner_id":1}]
```

El listado es un arreglo completo con las mascotas del cliente autenticado, sin
las de otros clientes ni paginación. Un cliente sin mascotas recibe `[]`, y un
veterinario también, porque no es el propietario de ninguna. Sin encabezado
`Authorization` o con un token inválido, la API responde `401 Unauthorized`.

## Turnos

La agenda de la clínica reserva, consulta y cancela las citas de los clientes
con los veterinarios. Todas las operaciones exigen un token Bearer válido y
las horas se expresan en UTC con formato ISO 8601. Solo el rol `client`
reserva: un veterinario recibe `403 Forbidden`.

### Reserva de un turno

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -i -X POST http://127.0.0.1:8000/appointments \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"pet_id": 1, "vet_id": 2, "start_at": "2030-06-10T10:00:00Z"}'
```

Respuesta (`201 Created`):

```
HTTP/1.1 201 Created
content-type: application/json

{"id":1,"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:00:00Z","end_at":"2030-06-10T10:30:00Z","status":"scheduled"}
```

Cada turno dura 30 minutos y el `end_at` se calcula a partir del `start_at`. La
mascota debe pertenecer al cliente: si es de otro cliente, la API responde
`403 Forbidden` con
`{"detail":"Solo puedes agendar turnos para tus propias mascotas."}`. El
veterinario debe existir y tener el rol `vet`, así que un identificador
inexistente o el de un cliente producen `404 Not Found` con
`{"detail":"El veterinario indicado no existe."}`. Una `pet_id` inexistente
devuelve `{"detail":"La mascota indicada no existe."}`.

El horario debe cumplir las reglas de la clínica: turnos de 30 minutos que
empiezan en punto o en media, de lunes a sábado, con inicio entre las 09:00 y
las 17:30. Un horario fuera de esas reglas, o ya pasado, produce
`422 Unprocessable Entity` con el motivo del rechazo:

```
{"detail":"Los turnos deben empezar en punto o en media."}
```

Si el veterinario ya tiene un turno activo que se solape con la franja
solicitada, la API responde `409 Conflict`:

```
{"detail":"El veterinario ya tiene un turno activo en esa franja horaria."}
```

### Listado de los turnos

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -i http://127.0.0.1:8000/appointments \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta (`200 OK`):

```
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:00:00Z","end_at":"2030-06-10T10:30:00Z","status":"scheduled"}]
```

El listado es un arreglo completo, sin paginación ni filtros, ordenado por
hora de inicio. Un cliente ve los turnos de sus propias mascotas y un
veterinario los turnos en los que atiende. Los turnos cancelados se siguen
mostrando, con `status` igual a `cancelled`.

### Cancelación de un turno

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -i -X POST http://127.0.0.1:8000/appointments/1/cancel \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta (`200 OK`):

```
HTTP/1.1 200 OK
content-type: application/json

{"id":1,"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:00:00Z","end_at":"2030-06-10T10:30:00Z","status":"cancelled"}
```

Solo el dueño de la mascota o el veterinario del turno pueden cancelarlo; un
tercero recibe `403 Forbidden` con
`{"detail":"Solo el dueño de la mascota o el veterinario del turno puede cancelarlo."}`.
Un identificador de turno inexistente devuelve `404 Not Found` y cancelar un
turno que ya estaba cancelado devuelve `409 Conflict` con
`{"detail":"El turno ya está cancelado."}`. La cancelación libera la franja, de
modo que ese horario puede volver a agendarse.

Sin encabezado `Authorization` o con un token inválido, cualquiera de las tres
operaciones responde `401 Unauthorized`.

## Pruebas

```bash
pytest
```

La suite se ejecuta sobre SQLite en un archivo temporal, de modo que no necesita un
servidor de PostgreSQL en marcha. Con el script auxiliar, la misma suite se puede
ejecutar sobre el entorno virtual del proyecto con `./run.sh test`.
