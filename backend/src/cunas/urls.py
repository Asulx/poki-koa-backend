from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicoViewSet, BebeViewSet, CunaViewSet

# El router crea automáticamente las URLs para nuestra API
router = DefaultRouter()
router.register(r'medicos', MedicoViewSet)
router.register(r'bebes', BebeViewSet)
router.register(r'cunas', CunaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]