"""
Registro de modelos en el panel de administración de Django.


Al registrar los modelos aquí, quedan disponibles en la interfaz web
de administración de Django (http://127.0.0.1:8000/admin/) para que
el equipo pueda ver, crear, editar y eliminar registros fácilmente
sin necesidad de conectarse directamente a la base de datos.
"""


from django.contrib import admin
from .models import Medico, Bebe, Cuna, Medicamento


# Registros básicos
admin.site.register(Medico)
admin.site.register(Bebe)
admin.site.register(Cuna)


# Registro personalizado para Medicamento
@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    # Definimos las columnas que queremos ver en la tabla del panel
    list_display = ('obtener_cuna', 'paciente', 'nombre', 'dosis', 'via', 'hora', 'estado')
    
    # Agregamos filtros laterales (muy útiles para filtrar por "Pendiente" o "Administrado")
    list_filter = ('estado', 'via', 'hora')
    
    # Agregamos una barra de búsqueda para buscar por nombre de fármaco o paciente
    search_fields = ('nombre', 'paciente__nombre_completo')


    # Método personalizado para obtener la cuna (C01, C02, etc.) a través del paciente
    def obtener_cuna(self, obj):
        # Verificamos si el paciente tiene una cuna asignada
        if hasattr(obj.paciente, 'cuna_asignada') and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return "Sin cuna"
    
    # Le ponemos título a la columna del método personalizado
    obtener_cuna.short_description = 'Cuna'
