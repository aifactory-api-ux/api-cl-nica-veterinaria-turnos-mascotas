"""Reglas de agenda del consultorio veterinario.

Este módulo concentra, en funciones puras, las reglas que gobiernan los
horarios de la clínica:

- Cada turno dura 30 minutos.
- El inicio solo puede caer en punto (minuto ``00``) o en media (minuto ``30``).
- La clínica atiende de lunes a sábado.
- El primer inicio permitido es a las 09:00 y el último a las 17:30, de modo
  que el último turno termina a las 18:00.
- No se agenda en instantes ya transcurridos.

Las funciones reciben y devuelven ``datetime`` con zona horaria y no acceden
a la base de datos, de modo que cada regla se pueda probar de forma aislada.
El router de turnos traduce el error de dominio :class:`SlotError` a una
respuesta 422 con el motivo del rechazo.

El módulo normaliza además los ``datetime`` a UTC, porque SQLite no conserva
la zona horaria al leer una columna ``DateTime(timezone=True)``: un valor
naive devuelto por el driver se interpreta como UTC.
"""

from datetime import datetime, time, timedelta, timezone

# Duración de cada turno de la clínica, en minutos.
SLOT_MINUTES = 30

# Apertura del consultorio: primer horario de inicio admitido.
OPENING_TIME = time(9, 0)

# Último horario de inicio admitido; el turno termina a las 18:00.
LAST_START_TIME = time(17, 30)

# Cierre del consultorio.
CLOSING_TIME = time(18, 0)

# Días de atención, con la numeración de ``datetime.weekday``: de lunes (0) a
# sábado (5). El domingo (6) queda fuera.
DIAS_DE_ATENCION = (0, 1, 2, 3, 4, 5)

# Minutos admitidos en el inicio de un turno.
MINUTOS_ADMITIDOS = (0, 30)


class SlotError(Exception):
    """Error de dominio con el motivo por el que se rechaza un horario.

    El atributo ``motivo`` describe la regla incumplida y es el texto que el
    router devuelve en el campo ``detail`` de la respuesta 422.
    """

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


def utcnow() -> datetime:
    """Devuelve el instante actual en UTC, con zona horaria."""
    return datetime.now(timezone.utc)


def ensure_aware_utc(momento: datetime) -> datetime:
    """Normaliza a UTC un ``datetime``, interpretando como UTC los naive.

    Los valores naive aparecen al leer de SQLite, que no conserva la zona
    horaria de las columnas ``DateTime(timezone=True)``. Como la API solo
    almacena instantes en UTC, esa es la lectura correcta.
    """
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def fin_de_turno(inicio: datetime) -> datetime:
    """Devuelve el instante en que termina un turno que empieza en ``inicio``."""
    return inicio + timedelta(minutes=SLOT_MINUTES)


def validate_slot(start_at: datetime, *, now: datetime | None = None) -> datetime:
    """Comprueba que un horario de inicio cumple las reglas de la clínica.

    Devuelve el instante de inicio normalizado a UTC cuando el horario es
    válido y lanza :class:`SlotError` con el motivo del rechazo en caso
    contrario.

    El instante de referencia para descartar el pasado es ``now`` si se
    indica y, en su defecto, el momento actual.
    """
    inicio = ensure_aware_utc(start_at)
    referencia = ensure_aware_utc(now) if now is not None else utcnow()

    if inicio <= referencia:
        raise SlotError("La fecha y hora del turno ya han pasado.")

    if inicio.minute not in MINUTOS_ADMITIDOS or inicio.second or inicio.microsecond:
        raise SlotError("Los turnos deben empezar en punto o en media.")

    if inicio.weekday() not in DIAS_DE_ATENCION:
        raise SlotError("La clínica atiende de lunes a sábado.")

    if inicio.time() < OPENING_TIME:
        raise SlotError("La clínica abre a las 09:00.")

    if inicio.time() > LAST_START_TIME:
        raise SlotError("El último turno puede empezar a las 17:30.")

    return inicio


def slot_overlaps(
    inicio_candidato: datetime,
    fin_candidato: datetime,
    inicio_existente: datetime,
    fin_existente: datetime,
) -> bool:
    """Indica si dos franjas horarias se solapan.

    Dos intervalos se solapan cuando ninguno termina antes de que el otro
    empiece; los extremos compartidos (un turno que empieza al terminar el
    anterior) no se consideran solapamiento.
    """
    return inicio_candidato < fin_existente and inicio_existente < fin_candidato
