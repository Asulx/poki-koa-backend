"""
Señales de la aplicación 'usuarios'.

Garantiza que todo usuario de Django posea un ``PerfilUsuario``. Esto es
necesario porque el sistema consulta el rol en cada inicio de sesión y no
debe fallar cuando un usuario se crea desde el panel de administración,
desde una migración de datos o desde un comando de gestión.
"""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario

Usuario = get_user_model()


@receiver(post_save, sender=Usuario)
def crear_perfil_al_registrar_usuario(sender, instance, created, **kwargs):
    """
    Crea el perfil del usuario de forma idempotente.

    Reglas:
    - Un superusuario se crea con rol ``administrador``.
    - El resto de usuarios se crea con rol ``enfermeria`` por defecto; el
      administrador puede cambiarlo luego desde ``/admin/`` o vía API.

    Se usa ``get_or_create`` para que guardar dos veces al mismo usuario no
    duplique perfiles ni sobrescriba un rol ya asignado.
    """
    if kwargs.get("raw", False):
        return

    if not created:
        return

    rol_por_defecto = (
        PerfilUsuario.ROL_ADMINISTRADOR if instance.is_superuser else PerfilUsuario.ROL_ENFERMERIA
    )
    PerfilUsuario.objects.get_or_create(
        usuario=instance,
        defaults={"rol": rol_por_defecto},
    )
