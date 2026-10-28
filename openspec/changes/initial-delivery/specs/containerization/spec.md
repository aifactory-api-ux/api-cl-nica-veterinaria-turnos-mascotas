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
