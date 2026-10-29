"""
Configuración de la aplicación 'usuarios'.

La aplicación extiende el modelo ``auth.User`` de Django con un perfil
de dominio (``PerfilUsuario``) que agrega el rol clínico y el turno de
trabajo. No se reemplaza ``AUTH_USER_MODEL`` para no romper las
migraciones ni los datos ya existentes del proyecto.
"""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Configuración de la aplicación 'usuarios'."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
    verbose_name = "Usuarios y Roles"

    def ready(self):
        """Conecta las señales que crean el perfil al registrar un usuario."""
        import usuarios.signals  # noqa: F401
