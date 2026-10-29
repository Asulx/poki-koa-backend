"""
Configuración del panel de administración para 'operacion'.

La bitácora se expone en modo **solo lectura**: por definición de auditoría,
un registro no debe poder editarse ni eliminarse desde la interfaz.
"""

from django.contrib import admin

from .models import AsignacionTurno, RegistroActividad, Turno


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    """Administración del catálogo de turnos."""

    list_display = ("nombre", "hora_inicio", "hora_fin", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(AsignacionTurno)
class AsignacionTurnoAdmin(admin.ModelAdmin):
    """Administración de asignaciones de personal."""

    list_display = ("usuario", "turno", "fecha", "cuna", "creado_por")
    list_filter = ("turno", "fecha")
    search_fields = ("usuario__username", "usuario__first_name", "cuna__identificador")
    date_hierarchy = "fecha"
    autocomplete_fields = ("usuario", "creado_por")


@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    """Bitácora de auditoría en modo solo lectura."""

    list_display = ("creado_en", "usuario", "accion", "entidad", "entidad_id", "descripcion")
    list_filter = ("accion", "entidad")
    search_fields = ("descripcion", "usuario__username")
    date_hierarchy = "creado_en"
    ordering = ("-creado_en",)

    def has_add_permission(self, request):
        """La bitácora solo se escribe desde el sistema, no a mano."""
        return False

    def has_change_permission(self, request, obj=None):
        """Los registros son inmutables."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Los registros no se eliminan desde el panel."""
        return False
