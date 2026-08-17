"""
Registro de modelos en el panel de administración de Django.

Al registrar los modelos aquí, quedan disponibles en la interfaz web
de administración de Django (http://127.0.0.1:8000/admin/) para que
el equipo pueda ver, crear, editar y eliminar registros fácilmente
sin necesidad de conectarse directamente a la base de datos.
"""

from django.contrib import admin
from .models import Medico, Bebe, Cuna

# Registra los tres modelos principales del sistema de monitoreo
admin.site.register(Medico)
admin.site.register(Bebe)
admin.site.register(Cuna)