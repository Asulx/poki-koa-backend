"""
Serializadores de la aplicación 'operacion'.

Se mantiene el contrato en ``snake_case`` que ya usa la API de ``cunas``;
el frontend adapta los nombres a su propio modelo en ``camelCase``.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import AsignacionTurno, RegistroActividad, Turno

Usuario = get_user_model()


class TurnoSerializer(serializers.ModelSerializer):
    """CRUD del catálogo de turnos."""

    duracion_horas = serializers.FloatField(read_only=True)

    class Meta:
        model = Turno
        fields = [
            "id",
            "nombre",
            "hora_inicio",
            "hora_fin",
            "activo",
            "duracion_horas",
        ]

    def validate(self, attrs):
        """Valida el turno con las reglas de dominio del modelo."""
        instancia = Turno(**attrs)
        instancia.clean()
        return attrs


class AsignacionTurnoSerializer(serializers.ModelSerializer):
    """
    Serializa una asignación de turno.

    Campos derivados de solo lectura (``usuario_nombre``, ``turno_nombre``,
    ``cuna_identificador``) evitan que el frontend tenga que hacer
    peticiones adicionales para pintar la tabla.
    """

    usuario_nombre = serializers.SerializerMethodField()
    usuario_iniciales = serializers.SerializerMethodField()
    usuario_rol = serializers.SerializerMethodField()
    turno_nombre = serializers.CharField(source="turno.nombre", read_only=True)
    turno_hora_inicio = serializers.TimeField(source="turno.hora_inicio", read_only=True)
    turno_hora_fin = serializers.TimeField(source="turno.hora_fin", read_only=True)
    cuna_identificador = serializers.CharField(
        source="cuna.identificador", read_only=True, default=None
    )

    class Meta:
        model = AsignacionTurno
        fields = [
            "id",
            "usuario",
            "usuario_nombre",
            "usuario_iniciales",
            "usuario_rol",
            "turno",
            "turno_nombre",
            "turno_hora_inicio",
            "turno_hora_fin",
            "cuna",
            "cuna_identificador",
            "fecha",
            "creado_por",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["creado_por", "creado_en", "actualizado_en"]

    def get_usuario_nombre(self, obj):
        perfil = getattr(obj.usuario, "perfil", None)
        if perfil:
            return perfil.nombre_completo
        return obj.usuario.get_full_name().strip() or obj.usuario.username

    def get_usuario_iniciales(self, obj):
        perfil = getattr(obj.usuario, "perfil", None)
        if perfil:
            return perfil.iniciales
        nombre = obj.usuario.get_full_name().strip() or obj.usuario.username
        return nombre[:2].upper()

    def get_usuario_rol(self, obj):
        perfil = getattr(obj.usuario, "perfil", None)
        return perfil.rol if perfil else None

    def validate_fecha(self, value):
        """Impide registrar asignaciones con más de un año de antigüedad."""
        limite = timezone.localdate().replace(year=timezone.localdate().year - 1)
        if value < limite:
            raise serializers.ValidationError(
                "No se pueden registrar asignaciones con más de un año de antigüedad."
            )
        return value

    def validate(self, attrs):
        """
        Ejecuta las validaciones de dominio del modelo.

        Se construye una instancia sin guardar para reutilizar ``clean()``
        y mantener una única fuente de verdad de las reglas de negocio.
        Además se comprueba la unicidad de la asignación, porque el
        ``UniqueConstraint`` con ``cuna`` nullable no siempre se traduce en
        un validador automático de DRF.
        """
        instancia = AsignacionTurno(
            usuario=attrs.get("usuario", getattr(self.instance, "usuario", None)),
            turno=attrs.get("turno", getattr(self.instance, "turno", None)),
            cuna=attrs.get("cuna", getattr(self.instance, "cuna", None)),
            fecha=attrs.get("fecha", getattr(self.instance, "fecha", None)),
        )
        if self.instance is not None:
            instancia.pk = self.instance.pk
        instancia.clean()

        duplicadas = AsignacionTurno.objects.filter(
            usuario=instancia.usuario,
            turno=instancia.turno,
            cuna=instancia.cuna,
            fecha=instancia.fecha,
        )
        if self.instance is not None:
            duplicadas = duplicadas.exclude(pk=self.instance.pk)
        if duplicadas.exists():
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Ya existe una asignación idéntica para esa persona, "
                        "turno, cuna y fecha."
                    )
                }
            )

        return attrs


class RegistroActividadSerializer(serializers.ModelSerializer):
    """Vista de solo lectura de la bitácora de auditoría."""

    usuario_nombre = serializers.SerializerMethodField()
    accion_display = serializers.CharField(source="get_accion_display", read_only=True)

    class Meta:
        model = RegistroActividad
        fields = [
            "id",
            "usuario",
            "usuario_nombre",
            "accion",
            "accion_display",
            "entidad",
            "entidad_id",
            "descripcion",
            "metadata",
            "ip_address",
            "creado_en",
        ]
        read_only_fields = fields

    def get_usuario_nombre(self, obj):
        if obj.usuario is None:
            return "Sistema"
        perfil = getattr(obj.usuario, "perfil", None)
        if perfil:
            return perfil.nombre_completo
        return obj.usuario.get_full_name().strip() or obj.usuario.username


class MisCunasSerializer(serializers.Serializer):
    """
    Contrato de salida de ``GET /api/mis-cunas/``.

    Se declara explícitamente para documentar la forma de la respuesta en
    lugar de devolver diccionarios anónimos desde la vista.
    """

    cuna_id = serializers.IntegerField()
    cuna_identificador = serializers.CharField()
    turno = serializers.CharField()
    hora_inicio = serializers.TimeField()
    hora_fin = serializers.TimeField()
    paciente_id = serializers.IntegerField(allow_null=True)
    paciente_nombre = serializers.CharField(allow_null=True)
    paciente_identificador = serializers.CharField(allow_null=True)
    ritmo_cardiaco = serializers.IntegerField(allow_null=True)
    spo2 = serializers.IntegerField(allow_null=True)
    temperatura = serializers.FloatField(allow_null=True)
    alertas_activas = serializers.IntegerField()
