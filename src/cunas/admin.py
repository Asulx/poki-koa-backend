"""
Registro de modelos en el panel de administración de Django.


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

    def obtener_cuna(self, obj):
        if hasattr(obj.paciente, "cuna_asignada") and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return "Sin cuna"

    obtener_cuna.short_description = "Cuna"


# Registro personalizado para Alerta
@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
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
