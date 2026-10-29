"""Configuración de la aplicación 'cunas' en Poki Koa."""

from django.apps import AppConfig


class CunasConfig(AppConfig):
    """Configuración de la aplicación de monitoreo neonatal 'cunas'.

    Define las propiedades principales del módulo de cunas y conecta
    las señales del motor de alertas al inicializar el contexto de Django.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "cunas"
    verbose_name = "Monitoreo de Cunas Neonatales"

    """Conecta las señales del motor de alertas al inicializar la aplicación.

    @returns None
    """

    def ready(self) -> None:
        # Importar señales al inicializar la app
        import cunas.signals  # noqa: F401

