#!/usr/bin/env bash
#
# Arranque local de la API Clínica Veterinaria.
#
# El script prepara un entorno virtual con las dependencias del proyecto y
# levanta el servidor Uvicorn, de modo que el equipo no tenga que repetir los
# comandos de instalación a mano en cada máquina.
#
# Uso:
#   ./run.sh          Prepara el entorno y arranca la API.
#   ./run.sh setup    Prepara el entorno virtual e instala las dependencias.
#   ./run.sh test     Instala las dependencias de desarrollo y ejecuta pytest.
#   ./run.sh serve    Prepara el entorno y arranca la API con Uvicorn.
#
# Variables de entorno opcionales:
#   PYTHON     Intérprete usado para crear el entorno virtual (por defecto python3).
#   VENV_DIR   Ruta del entorno virtual (por defecto .venv en la raíz del repositorio).
#   HOST       Dirección de escucha del servidor (por defecto 127.0.0.1).
#   PORT       Puerto de escucha del servidor (por defecto 8000).
#
# La configuración de la API (DATABASE_URL, JWT_SECRET, JWT_ALGORITHM y
# JWT_EXPIRE_MINUTES) se lee del entorno y del archivo .env de la raíz del
# repositorio, tal y como describe el README. Este script no fija ningún
# secreto: la clave de firma la proporciona el entorno.

set -euo pipefail

RAIZ="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ"

PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-$RAIZ/.venv}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

COMANDO="${1:-serve}"
[ "$#" -gt 0 ] && shift || true

informar() {
  printf 'run.sh: %s\n' "$*" >&2
}

fallar() {
  printf 'run.sh: %s\n' "$*" >&2
  exit 1
}

comprobar_version() {
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

tiene_dependencias_de_ejecucion() {
  "$1" -c 'import fastapi, uvicorn, sqlalchemy, jwt, bcrypt, pydantic_settings, psycopg' \
    >/dev/null 2>&1
}

tiene_dependencias_de_desarrollo() {
  "$1" -c 'import pytest, httpx, yaml' >/dev/null 2>&1
}

crear_entorno_virtual() {
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    informar "Creando el entorno virtual en $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR" \
      || fallar "No se pudo crear el entorno virtual en $VENV_DIR."
  fi
  printf '%s' "$VENV_DIR/bin/python"
}

instalar_requisitos() {
  local interprete="$1"
  local archivo="$2"
  informar "Instalando las dependencias de $(basename "$archivo")"
  "$interprete" -m pip install --disable-pip-version-check --upgrade pip >/dev/null
  "$interprete" -m pip install --disable-pip-version-check -r "$archivo" \
    || fallar "No se pudieron instalar las dependencias de $archivo."
}

preparar_entorno() {
  local con_desarrollo="${1:-no}"

  if [ -x "$VENV_DIR/bin/python" ]; then
    INTERPRETE="$VENV_DIR/bin/python"
  else
    INTERPRETE="$(crear_entorno_virtual)"
  fi

  comprobar_version "$INTERPRETE" \
    || fallar "Se necesita Python 3.11 o superior para ejecutar la API."

  if ! tiene_dependencias_de_ejecucion "$INTERPRETE"; then
    instalar_requisitos "$INTERPRETE" "$RAIZ/requirements.txt"
  fi

  if [ "$con_desarrollo" = "si" ] && ! tiene_dependencias_de_desarrollo "$INTERPRETE"; then
    instalar_requisitos "$INTERPRETE" "$RAIZ/requirements-dev.txt"
  fi
}

avisar_de_la_configuracion() {
  if [ -z "${JWT_SECRET:-}" ] && [ ! -f "$RAIZ/.env" ]; then
    informar "Aviso: no hay JWT_SECRET en el entorno ni un archivo .env en la raíz."
    informar "La API usará el valor de desarrollo; define el tuyo antes de publicarla."
  fi
}

arrancar_servidor() {
  informar "Arrancando la API en http://$HOST:$PORT"
  exec "$INTERPRETE" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
}

case "$COMANDO" in
  setup)
    preparar_entorno "si"
    informar "Entorno preparado en $VENV_DIR"
    ;;
  test)
    preparar_entorno "si"
    cd "$RAIZ"
    exec "$INTERPRETE" -m pytest "$@"
    ;;
  serve)
    preparar_entorno "no"
    avisar_de_la_configuracion
    arrancar_servidor
    ;;
  help | -h | --help)
    sed -n '3,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    ;;
  *)
    fallar "Comando desconocido: $COMANDO. Usa setup, test o serve."
    ;;
esac
