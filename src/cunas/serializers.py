"""
Serializadores de la API REST para la aplicación 'cunas'.


Los serializadores convierten las instancias de los modelos de Django
a formatos como JSON (y viceversa), permitiendo la comunicación con el
frontend (React/Vite) u otros clientes HTTP.


Cada serializador corresponde a un modelo:
- MedicoSerializer      → modelo Medico
- BebeSerializer        → modelo Bebe
- CunaSerializer        → modelo Cuna (anida BebeSerializer para respuestas detalladas)
- MedicamentoSerializer → modelo Medicamento (incluye datos derivados de Paciente y Cuna)
"""


from django.utils import timezone


from rest_framework import serializers


from .models import Medico, Bebe, Cuna, Medicamento




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


    Validaciones de campo:
    - `peso`: debe ser mayor a 0 (no se admiten valores nulos, negativos ni cero).
    - `fecha_nacimiento`: no puede ser una fecha posterior a hoy.
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


    def validate_peso(self, value):
        """
        Valida que el peso sea mayor a 0.


        Un peso de 0 o negativo no es fisiológicamente válido para un
        paciente registrado en el sistema.
        """
        if value <= 0:
            raise serializers.ValidationError(
                "El peso debe ser mayor a 0."
            )
        return value


    def validate_fecha_nacimiento(self, value):
        """
        Valida que la fecha de nacimiento no sea futura.


        Usa timezone.now().date() para respetar la zona horaria configurada
        en Django (settings.TIME_ZONE) en lugar de datetime.date.today().
        """
        if value > timezone.now().date():
            raise serializers.ValidationError(
                "La fecha de nacimiento no puede ser una fecha futura."
            )
        return value




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




class MedicamentoSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Medicamento.


    Agrega campos calculados (solo lectura) para facilitar que el frontend
    (React/Vite) construya la tabla de control de fármacos sin necesidad 
    de cruzar múltiples endpoints.
    """


    # Extrae el nombre del bebé directamente a través de la relación ForeignKey
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo',
        read_only=True
    )
    
    # Campo calculado dinámicamente mediante el método get_cuna
    cuna = serializers.SerializerMethodField()


    class Meta:
        model = Medicamento
        fields = '__all__'


    def get_cuna(self, obj):
        """
        Obtiene el identificador de la cuna asociada al paciente que recibe
        el medicamento. Retorna 'Sin cuna' si el bebé no está asignado a ninguna.
        """
        # Verificamos si el bebé tiene la relación inversa 'cuna_asignada'
        if hasattr(obj.paciente, 'cuna_asignada') and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return "Sin cuna"
