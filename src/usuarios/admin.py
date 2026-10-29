"""
Configuración del panel de administración para 'usuarios'.

Permite gestionar los perfiles clínicos junto al usuario de Django en una
sola pantalla. El rol y el turno se editan en un inline porque el perfil
siempre existe (lo crea una señal) y no tiene sentido administrarlo aparte.
"""

from django.contrib import admin

from .models import PerfilUsuario


class PerfilUsuarioInline(admin.StackedInline):
    """Inline que muestra el perfil clínico dentro del usuario."""

    model = PerfilUsuario
    can_delete = False
    extra = 0
    fields = ("rol", "turno")


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    """Administración directa de perfiles clínicos."""

    list_display = ("usuario", "rol", "turno", "actualizado_en")
    list_filter = ("rol", "turno")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name")
    readonly_fields = ("creado_en", "actualizado_en")
    ordering = ("usuario__username",)
