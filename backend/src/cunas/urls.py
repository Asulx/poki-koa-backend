from django.urls import path
from .views import obtener_resumen_cunas

urlpatterns = [
    path('resumen/', obtener_resumen_cunas, name='resumen_cunas'),
]