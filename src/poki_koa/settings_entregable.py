"""Configuración exclusivamente local para la demostración del Entregable 2."""

from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_entregable.sqlite3",
    }
}
