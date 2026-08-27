"""
Serializadores de la API REST para la aplicación 'cunas'.

Los serializadores convierten las instancias de los modelos de Django
a formatos como JSON (y viceversa), permitiendo la comunicación con el
frontend (React/Vite) u otros clientes HTTP.

Cada serializador corresponde a un modelo:
- MedicoSerializer      → modelo Medico
- BebeSerializer        → modelo Bebe (incluye cuna, signos vitales, medicamentos y alertas)
- CunaSerializer        → modelo Cuna (anida BebeSerializer para respuestas detalladas)
- MedicamentoSerializer → modelo Medicamento
- AlertaSerializer      → modelo Alerta (historial de eventos de signos vitales)
"""

from django.utils import timezone
from rest_framework import serializers

from .models import Medico, Bebe, Cuna, Medicamento, Alerta


class MedicoSerializer(serializers.ModelSerializer):
    """Serializa todos los campos del modelo Medico."""

    class Meta:
        model = Medico
        fields = '__all__'


class AlertaSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Alerta.
    Agrega `paciente_nombre` (solo lectura) para el frontend.
    """
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo',
        read_only=True
    )

    class Meta:
        model = Alerta
        fields = '__all__'


class MedicamentoSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Medicamento.
    Agrega campos derivados (solo lectura) para el frontend.
    """
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo',
        read_only=True
    )
    cuna = serializers.SerializerMethodField()

    class Meta:
        model = Medicamento
        fields = '__all__'

    def get_cuna(self, obj):
        if hasattr(obj.paciente, 'cuna_asignada') and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return "Sin cuna"


class BebeSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Bebe.

    Agrega campos calculados y relaciones de solo lectura para el frontend:
    - `medico_nombre`: Nombre del médico responsable
    - `cuna_identificador`: Identificador de la cuna asignada
    - `signos_vitales`: Diccionario con ritmo_cardiaco, spo2 y temperatura de la cuna
    - `medicamentos`: Lista de medicamentos prescritos
    - `alertas`: Historial de alertas registradas sobre signos vitales

    Validaciones de campo:
    - `peso`: debe ser mayor a 0 si está presente.
    - `fecha_nacimiento`: no puede ser una fecha posterior a hoy.
    """

    medico_nombre = serializers.CharField(
        source='medico_a_cargo.nombre_completo',
        read_only=True
    )
    cuna_identificador = serializers.SerializerMethodField()
    signos_vitales = serializers.SerializerMethodField()
    medicamentos = MedicamentoSerializer(many=True, read_only=True)
    alertas = AlertaSerializer(many=True, read_only=True)

    class Meta:
        model = Bebe
        fields = '__all__'

    def get_cuna_identificador(self, obj):
        if hasattr(obj, 'cuna_asignada') and obj.cuna_asignada:
            return obj.cuna_asignada.identificador
        return None

    def get_signos_vitales(self, obj):
        if hasattr(obj, 'cuna_asignada') and obj.cuna_asignada:
            return {
                'ritmo_cardiaco': obj.cuna_asignada.ritmo_cardiaco,
                'spo2': obj.cuna_asignada.spo2,
                'temperatura': obj.cuna_asignada.temperatura,
            }
        return None

    def validate_peso(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "El peso debe ser mayor a 0."
            )
        return value

    def validate_fecha_nacimiento(self, value):
        if value is not None and value > timezone.now().date():
            raise serializers.ValidationError(
                "La fecha de nacimiento no puede ser una fecha futura."
            )
        return value


class CunaSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Cuna.
    Incluye `paciente_detalle` que embebe la información del bebé.
    """
    paciente_detalle = BebeSerializer(source='paciente', read_only=True)

    class Meta:
        model = Cuna
        fields = '__all__'
