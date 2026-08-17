"""
Serializadores de la API REST para la aplicación 'cunas'.

Los serializadores convierten las instancias de los modelos de Django
a formatos como JSON (y viceversa), permitiendo la comunicación con el
frontend (React/Vite) u otros clientes HTTP.

Cada serializador corresponde a un modelo:
- MedicoSerializer  → modelo Medico
- BebeSerializer    → modelo Bebe
- CunaSerializer    → modelo Cuna (anida BebeSerializer para respuestas detalladas)
"""

from rest_framework import serializers
from .models import Medico, Bebe, Cuna


class MedicoSerializer(serializers.ModelSerializer):
    """Serializa todos los campos del modelo Medico."""

    class Meta:
        model = Medico
        fields = '__all__'


class BebeSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Bebe.

    Agrega el campo `medico_nombre` (solo lectura) para que el frontend
    reciba directamente el nombre del médico en lugar de solo su ID numérico.
    """

    # Campo extra derivado de la relación ForeignKey con Medico.
    # read_only=True: solo aparece en respuestas GET, no se usa en POST/PUT.
    medico_nombre = serializers.CharField(
        source='medico_a_cargo.nombre_completo',
        read_only=True
    )

    class Meta:
        model = Bebe
        fields = '__all__'


class CunaSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Cuna.

    Incluye el campo anidado `paciente_detalle` que embebe la información
    completa del bebé (y su médico) dentro de la respuesta de la cuna.
    Esto simplifica las consultas del frontend al evitar llamadas adicionales.
    """

    # Campo anidado: cuando el frontend solicite datos de una cuna,
    # recibirá el objeto completo del bebé en lugar de solo su ID.
    # read_only=True: se usa solo para lectura, las escrituras siguen
    # usando el campo `paciente` (ID) del modelo.
    paciente_detalle = BebeSerializer(source='paciente', read_only=True)

    class Meta:
        model = Cuna
        fields = '__all__'