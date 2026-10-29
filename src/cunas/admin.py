"""Registro de modelos en el panel de administración de Django.

Al registrar los modelos aquí, quedan disponibles en la interfaz web
de administración de Django (http://127.0.0.1:8000/admin/) para que
el equipo pueda ver, crear, editar y eliminar registros fácilmente
sin necesidad de conectarse directamente a la base de datos.
"""

from django.contrib import admin

from .models import Alerta, Bebe, Cuna, Medicamento, Medico, PlanCuidado

# Registros básicos
admin.site.register(Medico)
admin.site.register(Bebe)
admin.site.register(Cuna)
admin.site.register(PlanCuidado)


# Registro personalizado para Medicamento
@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    """Administración personalizada para el modelo Medicamento.

    Configura la visualización en lista, filtros y campos de búsqueda para
    el control de fármacos, dosis y vías de administración en la unidad neonatal.
    """

    list_display = (
        "obtener_cuna",
        "paciente",
        "nombre",
        "dosis",
        "via",
        "hora",
        "estado",
    )
    list_filter = ("estado", "via", "hora")
    search_fields = ("nombre", "paciente__nombre_completo")

    """Obtiene el identificador de la cuna asignada al paciente del medicamento.

    @param obj - Instancia del modelo Medicamento que está siendo evaluada.
    @returns str - Identificador único de la cuna o 'Sin cuna' si no está asignada.
    """

    def obtener_cuna(self, obj):
        if hasattr(obj.paciente, "cuna_asignada") and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return "Sin cuna"

    obtener_cuna.short_description = "Cuna"


# Registro personalizado para Alerta
@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    """Administración personalizada para el modelo Alerta.

    Define la interfaz de gestión para las alertas del sistema de monitoreo,
    permitiendo filtrar por estado activo, nivel de severidad y tipo de signo vital.
    """

    list_display = (
        "id",
        "nivel",
        "tipo",
        "mensaje",
        "paciente",
        "cuna",
        "valor_leido",
        "activa",
        "fecha_hora",
    )
    list_filter = ("activa", "nivel", "tipo", "fecha_hora")
    search_fields = ("mensaje", "paciente__nombre_completo", "cuna__identificador")
