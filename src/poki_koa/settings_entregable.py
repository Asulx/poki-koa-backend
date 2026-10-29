"""Configuración exclusivamente local para la demostración del Entregable 2 en Poki Koa.

Extiende la configuración base (`settings.py`) sobreescribiendo los parámetros
de persistencia para utilizar una base de datos SQLite local aislada (`db_entregable.sqlite3`).
"""

from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_entregable.sqlite3",
    }
}
