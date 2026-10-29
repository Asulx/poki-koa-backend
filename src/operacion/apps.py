"""
Configuración de la aplicación 'operacion'.

Agrupa todo lo que ocurre *alrededor* del paciente y no es dato clínico
directo: turnos del personal, asignación de cunas, bitácora de auditoría
y cálculo de métricas para el dashboard.

En ``ready`` se conectan las señales de auditoría. Se importan aquí (y no
en ``models.py``) para que el registro ocurra una sola vez y después de
que el registro de aplicaciones de Django esté listo.
"""

from django.apps import AppConfig


class OperacionConfig(AppConfig):
    """Configuración de la aplicación 'operacion'."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "operacion"
    verbose_name = "Operación y Auditoría"

    def ready(self):
        """Conecta las señales de auditoría del sistema."""
        import operacion.auditoria  # noqa: F401
