"""
Configuración de URLs principal del proyecto Poki Koa (Mamoru).

Define dos grupos de rutas:
- /admin/    → Panel de administración de Django
- /api/      → Todas las rutas de la API REST (delegadas a cunas/urls.py)
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Panel de administración de Django (interfaz web para gestionar la base de datos)
    path("admin/", admin.site.urls),
    # Autenticación, personal y perfiles: /api/auth/..., /api/personal/, /api/perfiles/
    path("api/", include("usuarios.urls")),
    # Turnos, asignaciones, reportes y auditoría: /api/turnos/, /api/reportes/...
    path("api/", include("operacion.urls")),
    # Rutas clínicas de la API REST: delega a cunas/urls.py todo lo que empiece con /api/
    path("api/", include("cunas.urls")),
]
