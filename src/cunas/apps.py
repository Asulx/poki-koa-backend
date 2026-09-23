"""
Configuración de la aplicación 'cunas'.
"""

from django.apps import AppConfig


class CunasConfig(AppConfig):
    """
    Configuración de la aplicación 'cunas'.
    Conecta las señales para el motor de alertas en el método ready().
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "cunas"
    verbose_name = "Monitoreo de Cunas Neonatales"

    def ready(self):
        # Importar señales al inicializar la app
        import cunas.signals  # noqa: F401

