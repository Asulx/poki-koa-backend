"""
Permisos personalizados de la aplicación 'usuarios'.

Centraliza las reglas de autorización basadas en el rol clínico del
``PerfilUsuario``. Se implementan como clases de DRF para poder
reutilizarlas en cualquier ViewSet mediante ``permission_classes``.
"""

from rest_framework.permissions import BasePermission

from .models import PerfilUsuario


def obtener_perfil(usuario):
    """
    Devuelve el ``PerfilUsuario`` de un usuario autenticado.

    Contrato:
    - Retorna ``None`` si el usuario no está autenticado o es anónimo.
    - Retorna ``None`` si el usuario todavía no tiene perfil asociado.
    - Nunca lanza excepciones de base de datos.

    Parameters
    ----------
    usuario : django.contrib.auth.models.User | django.contrib.auth.models.AnonymousUser
        Usuario resuelto por el mecanismo de autenticación de DRF.
    """
    if usuario is None or not usuario.is_authenticated:
        return None

    try:
        return usuario.perfil
    except PerfilUsuario.DoesNotExist:
        return None


def rol_de(usuario):
    """
    Obtiene el rol clínico de un usuario.

    Parameters
    ----------
    usuario :
        Usuario de Django.

    Returns
    -------
    str | None
        Cadena con el rol (``administrador``, ``medico`` o ``enfermeria``)
        o ``None`` cuando no hay perfil.
    """
    perfil = obtener_perfil(usuario)
    return perfil.rol if perfil else None


class EsAdministrador(BasePermission):
    """
    Permite el acceso únicamente a usuarios con rol ``administrador``.

    Se usa en operaciones de configuración del sistema: alta de personal,
    eliminación de turnos y consulta de auditoría global.
    """

    message = "Se requiere el rol de administrador para esta operación."

    def has_permission(self, request, view):
        return rol_de(request.user) == PerfilUsuario.ROL_ADMINISTRADOR


class EsPersonalClinico(BasePermission):
    """
    Permite el acceso a cualquier usuario con perfil clínico.

    Considera administradores, médicos y personal de enfermería. Se usa en
    endpoints de lectura que no deben quedar abiertos al público, pero que
    tampoco exigen privilegios de administrador.
    """

    message = "Se requiere una sesión con perfil clínico activo."

    def has_permission(self, request, view):
        return rol_de(request.user) in {
            PerfilUsuario.ROL_ADMINISTRADOR,
            PerfilUsuario.ROL_MEDICO,
            PerfilUsuario.ROL_ENFERMERIA,
        }
