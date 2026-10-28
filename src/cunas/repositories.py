"""Adaptador de persistencia Django para la operación de administración de medicamentos."""

from .medicamentos import RegistroMedicamento
from .models import Medicamento


class DjangoMedicamentoRepository:
    """Implementación concreta de `MedicamentoRepository` sobre el ORM de Django."""

    def obtener(self, medicamento_id: int) -> RegistroMedicamento | None:
        """Obtiene una proyección inmutable (`RegistroMedicamento`) o None si no existe."""
        datos = (
            Medicamento.objects.filter(pk=medicamento_id)
            .values("id", "paciente_id", "estado")
            .first()
        )
        return RegistroMedicamento(**datos) if datos else None

    def confirmar_pendiente(
        self, medicamento: RegistroMedicamento
    ) -> RegistroMedicamento | None:
        """
        Ejecuta una actualización condicional atómica (compare-and-set) de
        'Pendiente' a 'Administrado', evitando doble administración concurrente.
        """
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
