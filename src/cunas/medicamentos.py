"""
Contratos de negocio para la administración de medicación neonatal.

Este módulo es independiente de Django y del motor de base de datos,
aplicando Diseño por Contrato (Precondiciones, Postcondiciones e Invariantes)
e inyección de dependencias mediante `Protocol`.
"""

from dataclasses import dataclass, replace
from typing import Protocol


class OperacionError(Exception):
    """Excepción base para errores de contrato o entradas mal formadas (HTTP 400)."""

    status_code = 400


class MedicamentoNoEncontrado(OperacionError):
    """Se lanza cuando el identificador solicitado no existe en el repositorio (HTTP 404)."""

    status_code = 404


class EstadoNoPermitido(OperacionError):
    """Se lanza cuando el medicamento ya fue administrado o cambió concurrentemente (HTTP 409)."""

    status_code = 409


@dataclass(frozen=True)
class RegistroMedicamento:
    """Representación inmutable del estado de administración de un medicamento."""

    id: int
    paciente_id: int
    estado: str


class MedicamentoRepository(Protocol):
    """Contrato de persistencia requerido por `MedicamentoService`."""

    def obtener(self, medicamento_id: int) -> RegistroMedicamento | None:
        """Recupera un medicamento por su ID primario o retorna None si no existe."""
        ...

    def confirmar_pendiente(
        self, medicamento: RegistroMedicamento
    ) -> RegistroMedicamento | None:
        """Actualiza solo si sigue pendiente y conserva paciente e ID.

        Retorna None si otro proceso cambió o eliminó el registro.
        """
        ...


class MedicamentoService:
    """Servicio de dominio que gobierna la transición de medicación `Pendiente` -> `Administrado`."""

    def __init__(self, repositorio: MedicamentoRepository):
        """Recibe explícitamente el repositorio para permitir pruebas aisladas con Fakes."""
        self._repositorio = repositorio

    def administrar(self, medicamento_id: int | str) -> RegistroMedicamento:
        """
        Confirma la administración de un medicamento pendiente.

        Precondiciones:
        - `medicamento_id` debe ser un entero positivo (1..2**63 - 1) o cadena decimal canónica.
        - El medicamento debe existir y encontrarse en estado 'Pendiente'.

        Postcondición:
        - El estado persiste como 'Administrado' y se retorna el `RegistroMedicamento` actualizado.

        Invariantes:
        - Se conserva el `id` del medicamento y su `paciente_id` entero positivo.
        """
        # PRE: ID entero positivo (o cadena decimal canónica), hasta 2**63 - 1.
        # Validación externa: no usar assert; bool tampoco es un ID válido.
        if isinstance(medicamento_id, str):
            if (
                not medicamento_id.isascii()
                or not medicamento_id.isdecimal()
                or medicamento_id.startswith("0")
                or len(medicamento_id) > 19
            ):
                raise OperacionError("medicamento_id debe ser un entero positivo.")
            medicamento_id = int(medicamento_id)
        if type(medicamento_id) is not int or not 0 < medicamento_id <= 2**63 - 1:
            raise OperacionError("medicamento_id debe ser un entero positivo.")

        # PRE: el medicamento existe y su estado es Pendiente.
        actual = self._repositorio.obtener(medicamento_id)
        if actual is None:
            raise MedicamentoNoEncontrado("El medicamento no existe.")
        if actual.estado != "Pendiente":
            raise EstadoNoPermitido(
                "Solo se puede administrar un medicamento Pendiente."
            )

        # INV: el repositorio entrega la identidad solicitada y un paciente válido.
        assert actual.id == medicamento_id, "Invariante: identidad del medicamento."
        assert type(actual.paciente_id) is int and actual.paciente_id > 0, (
            "Invariante: el medicamento pertenece a un paciente válido."
        )
        resultado = self._repositorio.confirmar_pendiente(actual)
        if resultado is None:
            raise EstadoNoPermitido(
                "El medicamento cambió; recargue antes de administrar."
            )

        # POST: estado Administrado; INV: se conservan ID y paciente.
        assert resultado == replace(actual, estado="Administrado"), (
            "Invariante: solo cambia Pendiente a Administrado, conservando ID y paciente."
        )
        return resultado
