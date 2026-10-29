"""Serializadores de la API REST para la aplicación 'cunas'.

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
    """Serializa todos los campos del modelo Alerta.

    Agrega `paciente_nombre` y `cuna_identificador` (solo lectura) para el frontend.
    """

    paciente_nombre = serializers.SerializerMethodField()
    cuna_identificador = serializers.SerializerMethodField()

    class Meta:
        model = Alerta
        fields = "__all__"

    """Obtiene el nombre completo del paciente asociado directamente a la alerta o mediante la cuna.

    @param obj - Instancia del modelo Alerta evaluada.
    @returns str | None - Nombre del paciente o None si no está vinculado.
    """

    def get_paciente_nombre(self, obj):
        if obj.paciente:
            return obj.paciente.nombre_completo
        if obj.cuna and obj.cuna.paciente:
            return obj.cuna.paciente.nombre_completo
        return None

    """Obtiene el identificador de la cuna asociada a la alerta o al paciente asignado.

    @param obj - Instancia del modelo Alerta evaluada.
    @returns str | None - Identificador de la cuna o None si no existe relación.
    """

    def get_cuna_identificador(self, obj):
        if obj.cuna:
            return obj.cuna.identificador
        if (
            obj.paciente
            and hasattr(obj.paciente, "cuna_asignada")
            and obj.paciente.cuna_asignada
        ):
            return obj.paciente.cuna_asignada.identificador
        return None


class MedicamentoSerializer(serializers.ModelSerializer):
    """Serializa todos los campos del modelo Medicamento.

    Agrega campos derivados (solo lectura) para el frontend.
    """

    paciente_nombre = serializers.CharField(
        source="paciente.nombre_completo", read_only=True
    )
    cuna = serializers.SerializerMethodField()

    class Meta:
        model = Medicamento
        fields = "__all__"

    """Obtiene el identificador de la cuna asignada al paciente del medicamento.

    @param obj - Instancia del modelo Medicamento evaluada.
    @returns str - Identificador de la cuna o 'Sin cuna'.
    """

    def get_cuna(self, obj):
        if hasattr(obj.paciente, "cuna_asignada") and obj.paciente.cuna_asignada:
            return obj.paciente.cuna_asignada.identificador
        return "Sin cuna"


class BebeSerializer(serializers.ModelSerializer):
    """Serializa todos los campos del modelo Bebe.

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

    """Permite aceptar 'nombre' como alias de 'nombre_completo' en peticiones POST/PUT.

    @param data - Datos de entrada enviados en la solicitud HTTP.
    @returns dict - Diccionario procesado con el campo normalizado.
    """

    def to_internal_value(self, data):
        if (
            isinstance(data, dict)
            and "nombre" in data
            and "nombre_completo" not in data
        ):
            data = data.copy()
            data["nombre_completo"] = data["nombre"]
        return super().to_internal_value(data)

    """Obtiene el identificador de la cuna asignada al bebé.

    @param obj - Instancia del modelo Bebe.
    @returns str | None - Identificador de la cuna o None.
    """

    def get_cuna_identificador(self, obj):
        cuna = self._cuna_asignada(obj)
        return cuna.identificador if cuna else None

    """Método delegado para obtener el identificador de la cuna.

    @param obj - Instancia del modelo Bebe.
    @returns str | None - Identificador de la cuna.
    """

    def get_cuna(self, obj):
        return self.get_cuna_identificador(obj)

    """Método delegado para obtener el número de cuna.

    @param obj - Instancia del modelo Bebe.
    @returns str | None - Identificador de la cuna.
    """

    def get_numero_cuna(self, obj):
        return self.get_cuna_identificador(obj)

    """Obtiene la clave primaria de la cuna asignada al paciente.

    @param obj - Instancia del modelo Bebe.
    @returns int | None - ID de la cuna o None.
    """

    def get_cuna_id(self, obj):
        cuna = self._cuna_asignada(obj)
        return cuna.id if cuna else None

    """Obtiene el estado booleano del funcionamiento de la cánula de oxígeno.

    @param obj - Instancia del modelo Bebe.
    @returns bool | None - Estado de la cánula o None.
    """

    def get_estado_canula(self, obj):
        cuna = self._cuna_asignada(obj)
        return cuna.canula_ok if cuna else None

    """Método delegado para verificar el estado OK de la cánula.

    @param obj - Instancia del modelo Bebe.
    @returns bool | None - Estado de la cánula o None.
    """

    def get_canula_ok(self, obj):
        return self.get_estado_canula(obj)

    """Obtiene el estado de actividad de la vía intravenosa.

    @param obj - Instancia del modelo Bebe.
    @returns bool | None - Estado de la vía IV o None.
    """

    def get_via_intravenosa(self, obj):
        cuna = self._cuna_asignada(obj)
        return cuna.via_iv_activa if cuna else None

    """Método delegado para verificar la vía IV activa.

    @param obj - Instancia del modelo Bebe.
    @returns bool | None - Estado de la vía IV o None.
    """

    def get_via_iv_activa(self, obj):
        return self.get_via_intravenosa(obj)

    """Obtiene un diccionario resumen con los signos vitales actuales medidos en la cuna.

    @param obj - Instancia del modelo Bebe.
    @returns dict[str, Any] | None - Diccionario con ritmo cardíaco, SpO2 y temperatura, o None.
    """

    def get_signos_vitales(self, obj):
        cuna = self._cuna_asignada(obj)
        if not cuna:
            return None
        return {
            "ritmo_cardiaco": cuna.ritmo_cardiaco,
            "spo2": cuna.spo2,
            "temperatura": cuna.temperatura,
        }

    """Obtiene la cuna relacionada sin propagar la excepción DoesNotExist.

    @param obj - Instancia del modelo Bebe.
    @returns Cuna | None - Instancia de Cuna asociada o None.
    """

    @staticmethod
    def _cuna_asignada(obj):
        try:
            return obj.cuna_asignada
        except Cuna.DoesNotExist:
            return None

    """Valida que el peso del paciente sea un valor estrictamente positivo.

    @param value - Valor numérico del peso.
    @returns float | None - Valor validado del peso.
    """

    def validate_peso(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("El peso debe ser mayor a 0.")
        return value

    """Valida que la fecha de nacimiento no corresponda a una fecha futura.

    @param value - Fecha de nacimiento propuesta.
    @returns date | None - Fecha validada.
    """

    def validate_fecha_nacimiento(self, value):
        if value is not None and value > timezone.now().date():
            raise serializers.ValidationError(
                "La fecha de nacimiento no puede ser una fecha futura."
            )
        return value


class CunaSerializer(serializers.ModelSerializer):
    """Serializa todos los campos del modelo Cuna.

    Incluye `paciente_detalle` que embebe la información del bebé.
    """

    paciente_detalle = BebeSerializer(source="paciente", read_only=True)

    class Meta:
        model = Cuna
        fields = "__all__"


class PlanCuidadoSerializer(serializers.ModelSerializer):
    """Serializa todos los campos del modelo PlanCuidado.

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

    """Obtiene el identificador de la cuna asociada al paciente.

    Retorna 'Sin cuna' si el bebé no está asignado a ninguna.

    @param obj - Instancia del modelo PlanCuidado.
    @returns str - Identificador de la cuna o 'Sin cuna'.
    """

    def get_cuna(self, obj):
        if hasattr(obj.bebe, "cuna_asignada") and obj.bebe.cuna_asignada:
            return obj.bebe.cuna_asignada.identificador
        return "Sin cuna"


class MedicamentoCatalogoSerializer(serializers.ModelSerializer):
    """Serializa los productos del catálogo de medicamentos validando stock y dosis."""

    class Meta:
        model = MedicamentoCatalogo
        fields = ["id", "nombre", "principio_activo", "dosis_mg", "stock"]
        read_only_fields = ["id"]
