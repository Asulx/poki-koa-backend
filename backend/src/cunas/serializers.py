from rest_framework import serializers
from .models import Medico, Bebe, Cuna

class MedicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medico
        fields = '__all__'

class BebeSerializer(serializers.ModelSerializer):
    # Agregamos este campo extra para que React reciba el nombre del médico directamente,
    # y no solo un número de ID incomprensible.
    medico_nombre = serializers.CharField(source='medico_a_cargo.nombre_completo', read_only=True)

    class Meta:
        model = Bebe
        fields = '__all__'

class CunaSerializer(serializers.ModelSerializer):
    # Esto "anida" la información. Cuando pidas una cuna, te traerá toda la información
    # del bebé que está adentro, y a su vez, la del médico a cargo. ¡Perfecto para tu diseño!
    paciente_detalle = BebeSerializer(source='paciente', read_only=True)

    class Meta:
        model = Cuna
        fields = '__all__'