from datetime import datetime, timezone
from cunas.models import Cuna


class CunaService:
    """
    Servicio de dominio encargado de la gestión y telemetría de cunas neonatales.
    Aplica diseño por contrato y programación defensiva.
    """

    def __init__(self, cuna_model=Cuna):
        """
        Dependencia explícita: se recibe el modelo/repositorio de cunas.
        Esto permite sustituirlo por un objeto simulado (Mock/Fake)
        durante las pruebas unitarias sin acoplarse a la base de datos real.
        """
        self.model = cuna_model

    def actualizar_telemetria(
        self,
        cuna_id: str,
        ritmo_cardiaco: int,
        spo2: int,
        temperatura: float,
    ):
        """
        Actualiza los signos vitales medidos por los sensores de una cuna.

        Precondiciones:
        - cuna_id debe ser un string no vacío.
        - 30 <= ritmo_cardiaco <= 250 (bpm).
        - 50 <= spo2 <= 100 (porcentaje de saturación).
        - 30.0 <= temperatura <= 45.0 (°C).

        Postcondiciones:
        - La cuna persiste las métricas actualizadas y la fecha/hora actual.
        - Se retorna la instancia actualizada.

        Invariante:
        - SpO2 nunca puede superar el 100% ni ser negativo en el sistema.
        - La cuna persistida debe conservar su identificador e ID único.
        """

        # -------------------------------------------------------------
        # 1. VALIDACIÓN DEFENSIVA EN LA FRONTERA (Datos externos)
        # -------------------------------------------------------------
        if not cuna_id or not str(cuna_id).strip():
            raise ValueError("cuna_id es obligatorio y no puede estar vacío.")

        if not isinstance(ritmo_cardiaco, int) or not (30 <= ritmo_cardiaco <= 250):
            raise ValueError(
                f"Ritmo cardíaco inválido: {ritmo_cardiaco}. Debe estar entre 30 y 250 bpm."
            )

        if not isinstance(spo2, int) or not (50 <= spo2 <= 100):
            raise ValueError(
                f"SpO2 inválido: {spo2}. Debe ser un porcentaje entre 50% y 100%."
            )

        if not isinstance(temperatura, (int, float)) or not (30.0 <= float(temperatura) <= 45.0):
            raise ValueError(
                f"Temperatura inválida: {temperatura}. Debe estar entre 30.0 y 45.0 °C."
            )

        # -------------------------------------------------------------
        # 2. OPERACIÓN CON LA DEPENDENCIA INYECTADA
        # -------------------------------------------------------------
        try:
            cuna = self.model.objects.get(identificador=cuna_id)
        except self.model.DoesNotExist:
            raise LookupError(f"No existe la cuna con identificador: {cuna_id}")

        cuna.ritmo_cardiaco = ritmo_cardiaco
        cuna.spo2 = spo2
        cuna.temperatura = float(temperatura)
        cuna.ultima_actualizacion = datetime.now(timezone.utc)
        cuna.save()

        # -------------------------------------------------------------
        # 3. ASERCIONES INTERNAS E INVARIANTES (Supuestos del sistema)
        # -------------------------------------------------------------
        assert cuna.id is not None, "Invariante violada: la cuna no tiene ID asignado."
        assert 0 <= cuna.spo2 <= 100, f"Invariante violada: SpO2 inconsistente ({cuna.spo2})."

        return cuna