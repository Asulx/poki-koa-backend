"""
Configuración de URLs de la aplicación 'cunas'.

Usa el DefaultRouter de Django REST Framework para registrar los ViewSets
y generar automáticamente todas las rutas CRUD.

Rutas generadas bajo el prefijo /api/ (definido en poki_koa/urls.py):

    /api/medicos/           GET (lista), POST (crear)
    /api/medicos/{id}/      GET (detalle), PUT (actualizar), DELETE (borrar)
    /api/bebes/             GET (lista), POST (crear)
    /api/bebes/{id}/        GET (detalle), PUT (actualizar), DELETE (borrar)
    /api/cunas/             GET (lista), POST (crear)
    /api/cunas/{id}/        GET (detalle), PUT (actualizar), DELETE (borrar)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicoViewSet, BebeViewSet, CunaViewSet

# El router genera automáticamente todas las URLs a partir de los ViewSets registrados
router = DefaultRouter()
router.register(r'medicos', MedicoViewSet)
router.register(r'bebes', BebeViewSet)
router.register(r'cunas', CunaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]