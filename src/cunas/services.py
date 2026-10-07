"""Contratos de negocio independientes de Django y del almacenamiento."""

from dataclasses import dataclass, replace
from typing import Protocol


class OperacionError(Exception):
    status_code = 400


class MedicamentoNoEncontrado(OperacionError):
    status_code = 404


class EstadoNoPermitido(OperacionError):
    status_code = 409


@dataclass(frozen=True)
class RegistroMedicamento:
    id: int
    paciente_id: int
    estado: str


class MedicamentoRepository(Protocol):
    def obtener(self, medicamento_id: int) -> RegistroMedicamento | None: ...

    def confirmar_pendiente(
        self, medicamento: RegistroMedicamento
    ) -> RegistroMedicamento | None:
        """Actualiza solo si sigue pendiente y conserva paciente e ID.

        Retorna None si otro proceso cambió o eliminó el registro.
        """
        ...


class MedicamentoService:
    def __init__(self, repositorio: MedicamentoRepository):
        self._repositorio = repositorio

    def administrar(self, medicamento_id: int | str) -> RegistroMedicamento:
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
            raise EstadoNoPermitido("Solo se puede administrar un medicamento Pendiente.")

        # INV: el repositorio entrega la identidad solicitada y un paciente válido.
        assert actual.id == medicamento_id, "Invariante: identidad del medicamento."
        assert type(actual.paciente_id) is int and actual.paciente_id > 0, (
            "Invariante: el medicamento pertenece a un paciente válido."
        )
        resultado = self._repositorio.confirmar_pendiente(actual)
        if resultado is None:
            raise EstadoNoPermitido("El medicamento cambió; recargue antes de administrar.")

        # POST: estado Administrado; INV: se conservan ID y paciente.
        assert resultado == replace(actual, estado="Administrado"), (
            "Invariante: solo cambia Pendiente a Administrado, conservando ID y paciente."
        )
        return resultado
