"""
Vistas de la aplicación 'usuarios'.

Expone el ciclo de vida de la sesión y la consulta de personal:

- ``POST /api/auth/login/``   → inicia sesión y entrega el token.
- ``POST /api/auth/logout/``  → invalida el token del usuario actual.
- ``GET  /api/auth/me/``      → datos del usuario autenticado.
- ``GET  /api/personal/``     → listado de personal clínico (autenticado).

Decisiones de diseño
--------------------
Se utiliza ``rest_framework.authtoken`` en lugar de JWT para mantener la
dependencia mínima y porque el frontend ya envía ``Authorization: Bearer``
o ``Token``; el cliente se unifica con ``Token`` en un único interceptor.
"""

import logging

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PerfilUsuario
from .permissions import EsAdministrador
from .serializers import (
    CrearUsuarioSerializer,
    LoginSerializer,
    PerfilUsuarioSerializer,
    UsuarioSerializer,
)
from .throttles import LoginThrottle

logger = logging.getLogger("usuarios")

Usuario = get_user_model()


class LoginView(APIView):
    """
    Inicio de sesión por credenciales.

    Precondiciones
    --------------
    - Cuerpo JSON con ``username`` y ``password``.

    Postcondiciones
    ---------------
    - HTTP 200 con ``token``, ``usuario`` y ``perfil`` cuando las
      credenciales son válidas.
    - HTTP 400 con ``detail`` cuando son inválidas.

    Notas de seguridad
    ------------------
    El mensaje de error es idéntico para usuario inexistente y contraseña
    incorrecta, de modo que la respuesta no permita enumerar cuentas.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializador = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializador.is_valid(raise_exception=True)

        username = serializador.validated_data["username"]
        password = serializador.validated_data["password"]

        usuario = authenticate(request=request, username=username, password=password)

        if usuario is None:
            # Mensaje genérico a propósito: no revela si el usuario existe.
            return Response(
                {"detail": "Usuario o contraseña incorrectos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not usuario.is_active:
            return Response(
                {"detail": "La cuenta está deshabilitada. Contacta al administrador."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        perfil = getattr(usuario, "perfil", None)

        # ``get_or_create`` evita acumular tokens si el usuario inicia sesión
        # varias veces desde el mismo dispositivo.
        token, _ = Token.objects.get_or_create(user=usuario)

        logger.info("Inicio de sesión exitoso para '%s'", usuario.username)

        return Response(
            {
                "token": token.key,
                "usuario": UsuarioSerializer(usuario).data,
                "perfil": PerfilUsuarioSerializer(perfil).data if perfil else None,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    Cierre de sesión.

    Elimina el token del usuario. Si el token ya no existe, la operación es
    idempotente y devuelve HTTP 204 igualmente.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logger.info("Cierre de sesión para '%s'", request.user.username)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """
    Devuelve el usuario autenticado y su perfil clínico.

    El frontend usa esta vista al recargar la página para rehidratar la
    sesión sin confiar únicamente en ``localStorage``.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        perfil = getattr(request.user, "perfil", None)
        return Response(
            {
                "usuario": UsuarioSerializer(request.user).data,
                "perfil": PerfilUsuarioSerializer(perfil).data if perfil else None,
            }
        )


class PersonalViewSet(viewsets.ModelViewSet):
    """
    Administración del personal clínico.

    Lectura: cualquier usuario autenticado (lo necesita el módulo de turnos
    para poblar el selector de personal).
    Escritura: solo administradores.
    """

    queryset = Usuario.objects.select_related("perfil").order_by("first_name", "username")
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), EsAdministrador()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()

        rol = self.request.query_params.get("rol")
        if rol:
            queryset = queryset.filter(perfil__rol=rol)

        activo = self.request.query_params.get("activo")
        if activo is not None:
            queryset = queryset.filter(is_active=activo.lower() in {"1", "true", "si", "sí"})

        busqueda = self.request.query_params.get("search")
        if busqueda:
            queryset = queryset.filter(
                Q(first_name__icontains=busqueda)
                | Q(last_name__icontains=busqueda)
                | Q(username__icontains=busqueda)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Crea un usuario con contraseña y perfil en una sola operación.

        Se sobreescribe ``create`` porque ``UsuarioSerializer`` es de solo
        lectura: la escritura usa ``CrearUsuarioSerializer``.
        """
        serializador = CrearUsuarioSerializer(data=request.data)
        serializador.is_valid(raise_exception=True)
        usuario = serializador.save()
        return Response(
            UsuarioSerializer(usuario).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def desactivar(self, request, pk=None):
        """
        Desactiva un usuario sin borrarlo (preserva el historial de auditoría).

        Un administrador no puede desactivarse a sí mismo para evitar dejar
        el sistema sin acceso.
        """
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            return Response(
                {"detail": "No puedes desactivar tu propia cuenta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        return Response(UsuarioSerializer(usuario).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def activar(self, request, pk=None):
        """Reactiva un usuario previamente desactivado."""
        usuario = self.get_object()
        usuario.is_active = True
        usuario.save(update_fields=["is_active"])
        return Response(UsuarioSerializer(usuario).data)


class PerfilViewSet(viewsets.ModelViewSet):
    """
    CRUD de perfiles clínicos.

    Solo administradores pueden modificar roles o turnos; la lectura queda
    disponible para el personal autenticado.
    """

    queryset = PerfilUsuario.objects.select_related("usuario").all()
    serializer_class = PerfilUsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), EsAdministrador()]
        return [IsAuthenticated()]
