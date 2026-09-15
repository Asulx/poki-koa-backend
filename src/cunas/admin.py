"""
Registro de modelos en el panel de administración de Django.


Al registrar los modelos aquí, quedan disponibles en la interfaz web
de administración de Django (http://127.0.0.1:8000/admin/) para que
el equipo pueda ver, crear, editar y eliminar registros fácilmente
sin necesidad de conectarse directamente a la base de datos.
"""

from django.contrib import admin

from .models import (
    Alerta,
    Apoderado,
    AsignacionTurno,
    Bebe,
    Cuna,
    Medicamento,
    Medico,
    PlanCuidado,
    Turno,
)

# Registros básicos y personalizados
admin.site.register(Medico)
admin.site.register(Cuna)
admin.site.register(Alerta)
admin.site.register(PlanCuidado)


@admin.register(Bebe)
class BebeAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "edad_meses", "sexo", "medico_a_cargo", "matriculado", "fecha_ingreso")
    list_filter = ("matriculado", "sexo", "medico_a_cargo")
    search_fields = ("nombre_completo", "diagnostico")


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "hora_inicio", "hora_fin", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(AsignacionTurno)
class AsignacionTurnoAdmin(admin.ModelAdmin):
    list_display = ("medico", "turno", "fecha", "activo", "obtener_cantidad_cunas")
    list_filter = ("turno", "activo", "fecha")
    filter_horizontal = ("cunas",)
    search_fields = ("medico__nombre_completo", "turno__nombre")

    def obtener_cantidad_cunas(self, obj):
        return obj.cunas.count()

    obtener_cantidad_cunas.short_description = "N° Cunas"


@admin.register(Apoderado)
class ApoderadoAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "rut", "bebe", "obtener_matricula", "telefono", "email")
    list_filter = ("bebe__matriculado",)
    search_fields = ("nombre_completo", "rut", "bebe__nombre_completo")

    def obtener_matricula(self, obj):
        return obj.bebe.matriculado

    obtener_matricula.boolean = True
    obtener_matricula.short_description = "Matrícula Activa"


# Registro personalizado para Medicamento
@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    # Definimos las columnas que queremos ver en la tabla del panel
    list_display = (
        "obtener_cuna",
        "paciente",
        "nombre",
        "dosis",
        "via",
        "hora",
        "estado",
    )

    # Agregamos filtros laterales (muy útiles para filtrar por "Pendiente" o "Administrado")
    list_filter = ("estado", "via", "hora")

    # Agregamos una barra de búsqueda para buscar por nombre de fármaco o paciente
    search_fields = ("nombre", "paciente__nombre_completo")

    # Método personalizado para obtener la cuna (C01, C02, etc.) a través del paciente
    def obtener_cuna(self, obj):
        # Verificamos si el paciente tiene una cuna asignada
        if hasattr(obj.paciente, "cuna_asignada") and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return "Sin cuna"

    # Le ponemos título a la columna del método personalizado
    obtener_cuna.short_description = "Cuna"
