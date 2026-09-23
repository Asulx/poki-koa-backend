"""
Configuración de URLs principal del proyecto Poki Koa (Mamoru).

Define dos grupos de rutas:
- /admin/    → Panel de administración de Django
- /api/      → Todas las rutas de la API REST (delegadas a cunas/urls.py)
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Panel de administración de Django (interfaz web para gestionar la base de datos)
    path("admin/", admin.site.urls),
    # Documentación interactiva de la API REST (OpenAPI 3.0, Swagger UI y Redoc)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Rutas de la API REST: delega a cunas/urls.py todo lo que empiece con /api/
    path("api/", include("cunas.urls")),
]
