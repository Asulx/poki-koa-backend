"""Contrato de negocio para resolver alertas clínicas neonatales, independiente de Django.

Aplica Diseño por Contrato (Precondiciones, Postcondiciones e Invariantes)
y desacopla el almacenamiento mediante `AlertaRepository` (`Protocol`).
"""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol


class AlertaOperacionError(Exception):
    """Excepción base para entradas inválidas en operaciones de alerta (HTTP 400)."""

    status_code = 400


class AlertaNoEncontrada(AlertaOperacionError):
    """Se lanza cuando la alerta solicitada no existe en el repositorio (HTTP 404)."""

    status_code = 404


class AlertaEstadoNoPermitido(AlertaOperacionError):
    """Se lanza cuando se intenta resolver una alerta ya inactiva o modificada concurrentemente (HTTP 409)."""

    status_code = 409


@dataclass(frozen=True)
class RegistroAlerta:
    """Proyección inmutable de una alerta clínica neonatal."""

    id: int
    paciente_id: int | None
    cuna_id: int | None
    tipo: str
    mensaje: str
    nivel: str
    fecha_hora: datetime
    activa: bool
    valor_leido: float | None


class AlertaRepository(Protocol):
    """Contrato de persistencia requerido por `AlertaService`."""

    """Obtiene una alerta o None si no existe.

    @param alerta_id - Identificador único de la alerta a buscar.
    @returns RegistroAlerta | None - Instancia de la alerta encontrada o None si no existe.
    """

    def obtener(self, alerta_id: int) -> RegistroAlerta | None: ...

    """Cambia el estado solo si la alerta continúa activa.

    Retorna None si ya no puede realizarse la actualización.

    @param alerta - Registro actual de la alerta a confirmar como inactiva.
    @returns RegistroAlerta | None - Alerta actualizada o None en caso de conflicto.
    """

    def confirmar_activa(self, alerta: RegistroAlerta) -> RegistroAlerta | None: ...


class AlertaService:
    """Servicio de dominio encargado de la resolución controlada de alertas activas."""

    """Inyecta explícitamente el repositorio para permitir el uso de Fakes en pruebas.

    @param repositorio - Implementación del protocolo AlertaRepository para la persistencia.
    @returns None
    """

    def __init__(self, repositorio: AlertaRepository) -> None:
        self._repositorio = repositorio

    """Resuelve una alerta activa conservando sus demás datos.

    @param alerta_id - Identificador de la alerta, admitiendo formato entero o cadena numérica.
    @returns RegistroAlerta - El registro de la alerta con su estado actualizado a inactiva.
    """

    def resolver_alerta(self, alerta_id: int | str) -> RegistroAlerta:
        # PRE 1: ID entero positivo, hasta 2**63 - 1.
        # Las entradas externas se validan con excepciones, no assert.
        if isinstance(alerta_id, str):
            if (
                not alerta_id.isascii()
                or not alerta_id.isdecimal()
                or alerta_id.startswith("0")
                or len(alerta_id) > 19
            ):
                raise AlertaOperacionError("alerta_id debe ser un entero positivo.")
            alerta_id = int(alerta_id)

        if type(alerta_id) is not int or not 0 < alerta_id <= 2**63 - 1:
            raise AlertaOperacionError("alerta_id debe ser un entero positivo.")

        # PRE 2: la alerta debe existir.
        actual = self._repositorio.obtener(alerta_id)
        if actual is None:
            raise AlertaNoEncontrada("La alerta no existe.")

        # PRE 3: solo se resuelven alertas activas.
        if not actual.activa:
            raise AlertaEstadoNoPermitido("Solo se puede resolver una alerta activa.")

        # INV: el repositorio devuelve la alerta solicitada.
        assert actual.id == alerta_id, "Invariante: identidad de la alerta."

        # La dependencia realiza la actualización.
        resultado = self._repositorio.confirmar_activa(actual)

        if resultado is None:
            raise AlertaEstadoNoPermitido(
                "La alerta cambió; recargue antes de resolver."
            )

        # POST: activa=False.
        # INV: todos los demás campos conservan su valor.
        assert resultado == replace(actual, activa=False), (
            "Invariante: solo cambia el estado de la alerta."
        )

        return resultado
