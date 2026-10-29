"""
Rutas de la aplicación 'usuarios'.

Se registran bajo el prefijo ``/api/`` definido en ``poki_koa/urls.py``:

    /api/auth/login/     POST  → inicio de sesión
    /api/auth/logout/    POST  → cierre de sesión
    /api/auth/me/        GET   → usuario autenticado
    /api/personal/       CRUD  → personal clínico
    /api/perfiles/       CRUD  → perfiles y roles
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LoginView, LogoutView, MeView, PerfilViewSet, PersonalViewSet

router = DefaultRouter()
router.register(r"personal", PersonalViewSet, basename="personal")
router.register(r"perfiles", PerfilViewSet, basename="perfil")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("", include(router.urls)),
]
