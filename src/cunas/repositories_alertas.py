
"""Repositorio Django para la resolución de alertas."""

from dataclasses import replace

from .alertas_service import RegistroAlerta
from .models import Alerta


class DjangoAlertaRepository:
    CAMPOS = (
        "id",
        "paciente_id",
        "cuna_id",
        "tipo",
        "mensaje",
        "nivel",
        "fecha_hora",
        "activa",
        "valor_leido",
    )

    def obtener(self, alerta_id: int) -> RegistroAlerta | None:
        """Busca una alerta por su identificador."""

        datos = (
            Alerta.objects.filter(pk=alerta_id)
            .values(*self.CAMPOS)
            .first()
        )

        return RegistroAlerta(**datos) if datos else None

    def confirmar_activa(
        self, alerta: RegistroAlerta
    ) -> RegistroAlerta | None:
        """Resuelve la alerta únicamente si continúa activa."""

        # Actualización condicional (compare-and-set).
        # Evita que dos solicitudes resuelvan la misma alerta.
        filas = Alerta.objects.filter(
            pk=alerta.id,
            activa=True,
        ).update(activa=False)

        # Si no se actualizó ninguna fila, la alerta ya no
        # estaba activa o fue eliminada.
        if filas == 0:
            return None

        # POST: devuelve la alerta resuelta.
        # INV: conserva todos los demás campos originales.
        return replace(alerta, activa=False)
