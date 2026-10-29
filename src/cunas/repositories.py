"""Adaptador de persistencia Django para la operación de administración de medicamentos en Poki Koa."""

from .medicamentos import RegistroMedicamento
from .models import Medicamento


class DjangoMedicamentoRepository:
    """Implementación concreta del protocolo `MedicamentoRepository` sobre el ORM de Django.

    Permite consultar el estado actual de los fármacos y ejecutar actualizaciones
    atómicas seguras (compare-and-set) para prevenir condiciones de carrera.
    """

    """Obtiene una proyección inmutable (`RegistroMedicamento`) o None si no existe en la base de datos.

    @param medicamento_id - Identificador único del medicamento a buscar.
    @returns RegistroMedicamento | None - Instancia de proyección inmutable o None si no se encuentra.
    """

    def obtener(self, medicamento_id: int) -> RegistroMedicamento | None:
        datos = (
            Medicamento.objects.filter(pk=medicamento_id)
            .values("id", "paciente_id", "estado")
            .first()
        )
        return RegistroMedicamento(**datos) if datos else None

    """Ejecuta una actualización condicional atómica (compare-and-set) de 'Pendiente' a 'Administrado'.

    Evita la doble administración concurrente asegurando el estado previo y la consistencia del paciente.

    @param medicamento - Instancia actual del registro de medicamento a confirmar.
    @returns RegistroMedicamento | None - Registro actualizado con estado 'Administrado' o None en caso de conflicto.
    """

    def confirmar_pendiente(
        self, medicamento: RegistroMedicamento
    ) -> RegistroMedicamento | None:
        # Compare-and-set: dos solicitudes concurrentes no confirman dos veces.
        filas = Medicamento.objects.filter(
            pk=medicamento.id,
            paciente_id=medicamento.paciente_id,
            estado="Pendiente",
        ).update(estado="Administrado")
        if filas == 0:
            return None
        return RegistroMedicamento(
            medicamento.id, medicamento.paciente_id, "Administrado"
        )
