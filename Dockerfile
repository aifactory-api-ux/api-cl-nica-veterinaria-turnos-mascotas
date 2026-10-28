# Imagen de la API Clínica Veterinaria.
#
# La imagen instala las dependencias de la aplicación, copia el paquete `app/`
# y arranca el servidor Uvicorn escuchando en el puerto 8000.

FROM python:3.11-slim

# Ajustes del intérprete y de pip: salida sin búfer, sin archivos .pyc y sin
# caché de descargas en la imagen. PYTHONPATH apunta al directorio de trabajo
# para que el paquete `app` sea importable desde cualquier cwd.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/srv

WORKDIR /srv

# El servidor se ejecuta con un usuario sin privilegios.
RUN useradd --create-home --uid 10001 clinica

# Dependencias de la aplicación. Se copian antes que el código para que la capa
# de instalación se reutilice mientras el código de la API no cambie.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código de la API: el paquete `app` queda en /srv/app.
COPY app/ ./app/

# Puerto en el que escucha la API.
EXPOSE 8000

USER clinica

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
