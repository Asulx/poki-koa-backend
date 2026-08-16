from django.contrib import admin
from .models import Medico, Bebe, Cuna

# Esto registra tus tres tablas en el panel de administrador
admin.site.register(Medico)
admin.site.register(Bebe)
admin.site.register(Cuna)