"""
Serializadores de la aplicación 'usuarios'.

Se separan tres responsabilidades:

- ``LoginSerializer``: valida credenciales y devuelve el usuario junto a su
  token de autenticación.
- ``UsuarioSerializer``: representa al usuario autenticado y su perfil para
  el frontend (``GET /api/auth/me/``).
- ``PerfilUsuarioSerializer``: CRUD administrativo del perfil clínico.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import PerfilUsuario

Usuario = get_user_model()


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    """Serializa el perfil clínico de un usuario."""

    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    nombre_completo = serializers.CharField(read_only=True)
    iniciales = serializers.CharField(read_only=True)

    class Meta:
        model = PerfilUsuario
        fields = [
            "id",
            "usuario",
            "rol",
            "rol_display",
            "turno",
            "nombre_completo",
            "iniciales",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["creado_en", "actualizado_en"]


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Representa al usuario autenticado con los datos que consume el frontend.

    El contrato de salida es estable y en ``snake_case``. El frontend es
    responsable de mapearlo a su propio modelo en ``camelCase``.
    """

    rol = serializers.SerializerMethodField()
    rol_display = serializers.SerializerMethodField()
    turno = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    iniciales = serializers.SerializerMethodField()
    es_administrador = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "nombre_completo",
            "iniciales",
            "rol",
            "rol_display",
            "turno",
            "es_administrador",
            "is_superuser",
            "is_staff",
        ]
        read_only_fields = fields

    def _perfil(self, obj):
        """Obtiene el perfil del usuario sin propagar ``DoesNotExist``."""
        try:
            return obj.perfil
        except PerfilUsuario.DoesNotExist:
            return None

    def get_rol(self, obj):
        perfil = self._perfil(obj)
        return perfil.rol if perfil else None

    def get_rol_display(self, obj):
        perfil = self._perfil(obj)
        return perfil.get_rol_display() if perfil else None

    def get_turno(self, obj):
        perfil = self._perfil(obj)
        return perfil.turno if perfil else None

    def get_nombre_completo(self, obj):
        perfil = self._perfil(obj)
        if perfil:
            return perfil.nombre_completo
        return obj.get_full_name().strip() or obj.username

    def get_iniciales(self, obj):
        perfil = self._perfil(obj)
        if perfil:
            return perfil.iniciales
        nombre = obj.get_full_name().strip() or obj.username
        partes = [parte for parte in nombre.split() if parte]
        if not partes:
            return "?"
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()

    def get_es_administrador(self, obj):
        perfil = self._perfil(obj)
        return bool(perfil and perfil.es_administrador)


class LoginSerializer(serializers.Serializer):
    """
    Valida credenciales de inicio de sesión.

    Reglas (precondiciones):
    - ``username`` y ``password`` son obligatorios y no vacíos.
    - Las credenciales deben ser válidas y el usuario debe estar activo.

    Postcondición: en caso de éxito, ``validate`` retorna un diccionario con
    las claves ``usuario`` y ``perfil``.
    """

    username = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(
        max_length=128,
        trim_whitespace=False,
        style={"input_type": "password"},
        write_only=True,
    )

    def validate(self, attrs):
        username = attrs.get("username", "").strip()
        password = attrs.get("password", "")

        if not username or not password:
            raise serializers.ValidationError(
                {
                    "detail": "Debes ingresar usuario y contraseña."
                }
            )

        attrs["username"] = username

        return attrs


class CrearUsuarioSerializer(serializers.Serializer):
    """
    Alta de personal desde la API (solo administradores).

    Se valida la contraseña con los validadores de Django para no relajar
    las reglas de seguridad configuradas en ``AUTH_PASSWORD_VALIDATORS``.
    """

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, max_length=128)
    rol = serializers.ChoiceField(
        choices=PerfilUsuario.ROL_CHOICES,
        default=PerfilUsuario.ROL_ENFERMERIA,
    )
    turno = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_username(self, value):
        username = value.strip()
        if Usuario.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        rol = validated_data.pop("rol", PerfilUsuario.ROL_ENFERMERIA)
        turno = validated_data.pop("turno", "") or None
        password = validated_data.pop("password")
        usuario = Usuario.objects.create_user(password=password, **validated_data)
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
        perfil.rol = rol
        perfil.turno = turno
        perfil.save(update_fields=["rol", "turno", "actualizado_en"])
        return usuario
