"""Adaptador de persistencia para la operación de administración."""

from .models import Medicamento
from .services import RegistroMedicamento


class DjangoMedicamentoRepository:
    def obtener(self, medicamento_id):
        datos = Medicamento.objects.filter(pk=medicamento_id).values(
            "id", "paciente_id", "estado"
        ).first()
        return RegistroMedicamento(**datos) if datos else None

    def confirmar_pendiente(self, medicamento):
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
