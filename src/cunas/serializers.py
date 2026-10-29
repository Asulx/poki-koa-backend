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

from .models import (
    Alerta,
    Bebe,
    Cuna,
    Medicamento,
    MedicamentoCatalogo,
    Medico,
    PlanCuidado,
)


class MedicoSerializer(serializers.ModelSerializer):
    """Serializa todos los campos del modelo Medico."""

    class Meta:
        model = Medico
        fields = "__all__"


class AlertaSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Alerta.
    Agrega `paciente_nombre` y `cuna_identificador` (solo lectura) para el frontend.
    """

    paciente_nombre = serializers.SerializerMethodField()
    cuna_identificador = serializers.SerializerMethodField()
    nivel_display = serializers.CharField(source="get_nivel_display", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Alerta
        fields = "__all__"

    def get_paciente_nombre(self, obj):
        if obj.paciente:
            return obj.paciente.nombre_completo
        if obj.cuna and obj.cuna.paciente:
            return obj.cuna.paciente.nombre_completo
        return None

    def get_cuna_identificador(self, obj):
        if obj.cuna:
            return obj.cuna.identificador
        if obj.paciente and hasattr(obj.paciente, "cuna_asignada") and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return None


class MedicamentoSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Medicamento.
    Agrega campos derivados (solo lectura) para el frontend.
    """

    paciente_nombre = serializers.CharField(
        source="paciente.nombre_completo", read_only=True
    )
    cuna = serializers.SerializerMethodField()

    class Meta:
        model = Medicamento
        fields = "__all__"

    def get_cuna(self, obj):
        if hasattr(obj.paciente, "cuna_asignada") and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return "Sin cuna"


class BebeSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo Bebe.

    Agrega campos calculados y relaciones de solo lectura para el frontend:
    - `nombre`: Alias de `nombre_completo` para el frontend
    - `medico_nombre`: Nombre del médico responsable
    - `medico_responsable`: Alias de `medico_nombre` para el frontend
    - `cuna`: Identificador de la cuna asignada
    - `numero_cuna`: Alias de identificador de cuna
    - `cuna_identificador`: Identificador de la cuna asignada
    - `cuna_id`: Clave primaria de la cuna asignada
    - `estado_canula`: Estado funcional de la cánula de oxígeno (True/False/None)
    - `canula_ok`: Alias booleano de `estado_canula`
    - `via_intravenosa`: Estado de la vía intravenosa (True/False/None)
    - `via_iv_activa`: Alias booleano de `via_intravenosa`
    - `signos_vitales`: Diccionario con ritmo_cardiaco, spo2 y temperatura de la cuna
    - `medicamentos`: Lista de medicamentos prescritos
    - `alertas`: Historial de alertas registradas sobre signos vitales

    Validaciones de campo:
    - `peso`: debe ser mayor a 0 si está presente.
    - `fecha_nacimiento`: no puede ser una fecha posterior a hoy.
    """

    nombre = serializers.CharField(source="nombre_completo", read_only=True)
    medico_nombre = serializers.CharField(
        source="medico_a_cargo.nombre_completo", read_only=True, default=None
    )
    medico_responsable = serializers.CharField(
        source="medico_a_cargo.nombre_completo", read_only=True, default=None
    )
    cuna = serializers.SerializerMethodField()
    numero_cuna = serializers.SerializerMethodField()
    cuna_identificador = serializers.SerializerMethodField()
    cuna_id = serializers.SerializerMethodField()
    estado_canula = serializers.SerializerMethodField()
    canula_ok = serializers.SerializerMethodField()
    via_intravenosa = serializers.SerializerMethodField()
    via_iv_activa = serializers.SerializerMethodField()
    signos_vitales = serializers.SerializerMethodField()
    medicamentos = MedicamentoSerializer(many=True, read_only=True)
    alertas = AlertaSerializer(many=True, read_only=True)

    class Meta:
        model = Bebe
        fields = "__all__"

    def to_internal_value(self, data):
        # Permite aceptar 'nombre' como alias de 'nombre_completo' en peticiones POST/PUT
        if isinstance(data, dict) and "nombre" in data and "nombre_completo" not in data:
            data = data.copy()
            data["nombre_completo"] = data["nombre"]
        return super().to_internal_value(data)

    def get_cuna_identificador(self, obj):
        cuna = self._cuna_asignada(obj)
        return cuna.identificador if cuna else None

    def get_cuna(self, obj):
        return self.get_cuna_identificador(obj)

    def get_numero_cuna(self, obj):
        return self.get_cuna_identificador(obj)

    def get_cuna_id(self, obj):
        cuna = self._cuna_asignada(obj)
        return cuna.id if cuna else None

    def get_estado_canula(self, obj):
        cuna = self._cuna_asignada(obj)
        return cuna.canula_ok if cuna else None

    def get_canula_ok(self, obj):
        return self.get_estado_canula(obj)

    def get_via_intravenosa(self, obj):
        cuna = self._cuna_asignada(obj)
        return cuna.via_iv_activa if cuna else None

    def get_via_iv_activa(self, obj):
        return self.get_via_intravenosa(obj)

    def get_signos_vitales(self, obj):
        cuna = self._cuna_asignada(obj)
        if not cuna:
            return None
        return {
            "ritmo_cardiaco": cuna.ritmo_cardiaco,
            "spo2": cuna.spo2,
            "temperatura": cuna.temperatura,
        }

    @staticmethod
    def _cuna_asignada(obj):
        """Obtiene la cuna relacionada sin propagar DoesNotExist."""
        try:
            return obj.cuna_asignada
        except Cuna.DoesNotExist:
            return None

    def validate_peso(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("El peso debe ser mayor a 0.")
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

    Campos derivados de solo lectura:

    - ``estado``: ``ocupada`` si hay paciente, ``mantenimiento`` si está
      fuera de servicio, ``disponible`` en caso contrario. Se deriva en
      lugar de almacenarse para que nunca contradiga la asignación real.
    - ``tiene_alerta_critica``: ``True`` si la cuna tiene al menos una
      alerta crítica activa (lo usa el mapa de cunas para pintar el pulso
      rojo).
    - ``paciente_nombre`` / ``paciente_identificador``: atajos para evitar
      que el frontend navegue dentro de ``paciente_detalle`` en las tablas.
    """

    paciente_detalle = BebeSerializer(source="paciente", read_only=True)
    estado = serializers.SerializerMethodField()
    tiene_alerta_critica = serializers.SerializerMethodField()
    paciente_nombre = serializers.SerializerMethodField()
    paciente_identificador = serializers.SerializerMethodField()

    class Meta:
        model = Cuna
        fields = "__all__"

    def get_estado(self, obj):
        """Estado operativo derivado de la asignación y el mantenimiento."""
        if getattr(obj, "paciente_id", None):
            return "ocupada"
        if obj.en_mantenimiento:
            return "mantenimiento"
        return "disponible"

    def get_tiene_alerta_critica(self, obj):
        """
        Indica si hay alertas críticas activas.

        Si el ViewSet anotó el valor con ``Exists`` se usa esa anotación
        (evita N+1 consultas); si no, se consulta de forma directa.
        """
        anotado = getattr(obj, "alerta_critica_anotada", None)
        if anotado is not None:
            return bool(anotado)
        if not obj.pk:
            return False
        return obj.alertas.filter(activa=True, nivel="Critica").exists()

    def get_paciente_nombre(self, obj):
        return obj.paciente.nombre_completo if obj.paciente else None

    def get_paciente_identificador(self, obj):
        return obj.paciente.identificador if obj.paciente else None


class PlanCuidadoSerializer(serializers.ModelSerializer):
    """
    Serializa todos los campos del modelo PlanCuidado.

    Agrega campos calculados (solo lectura) para que el frontend pueda
    mostrar el nombre del paciente y la cuna asignada directamente en
    la tabla de protocolos de atención.
    """

    # Extrae el nombre del bebé a través de la relación ForeignKey (campo 'bebe')
    paciente_nombre = serializers.CharField(
        source="bebe.nombre_completo",
        read_only=True,
    )

    # Campo calculado dinámicamente para obtener la cuna
    cuna = serializers.SerializerMethodField()

    class Meta:
        model = PlanCuidado
        fields = "__all__"

    def get_cuna(self, obj):
        """
        Obtiene el identificador de la cuna asociada al paciente.
        Retorna 'Sin cuna' si el bebé no está asignado a ninguna.
        """
        if hasattr(obj.bebe, "cuna_asignada") and obj.bebe.cuna_asignada:
            return obj.bebe.cuna_asignada.identificador
        return "Sin cuna"


class MedicamentoCatalogoSerializer(serializers.ModelSerializer):
    """Serializa los productos del catálogo de medicamentos validando stock y dosis."""

    class Meta:
        model = MedicamentoCatalogo
        fields = ["id", "nombre", "principio_activo", "dosis_mg", "stock"]
        read_only_fields = ["id"]
