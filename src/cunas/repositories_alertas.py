"""Repositorio Django para la resolución de alertas en Poki Koa."""

from dataclasses import replace

from .alertas_service import RegistroAlerta
from .models import Alerta


class DjangoAlertaRepository:
    """Implementación de persistencia basada en ORM de Django para el servicio de alertas.

    Proporciona métodos de consulta y actualización condicional (compare-and-set)
    para sincronizar el dominio con la base de datos de forma concurrente y segura.
    """

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

    """Busca una alerta por su identificador único en la base de datos y la mapea a un registro inmutable.

    @param alerta_id - Identificador entero de la alerta a consultar.
    @returns RegistroAlerta | None - Instancia de proyección inmutable o None si no se encuentra.
    """

    def obtener(self, alerta_id: int) -> RegistroAlerta | None:
        datos = Alerta.objects.filter(pk=alerta_id).values(*self.CAMPOS).first()

        return RegistroAlerta(**datos) if datos else None

    """Resuelve la alerta únicamente si continúa activa mediante una actualización atómica condicional.

    @param alerta - Registro inmutable actual de la alerta a confirmar como inactiva.
    @returns RegistroAlerta | None - Alerta actualizada con activa=False o None en caso de conflicto por concurrencia.
    """

    def confirmar_activa(self, alerta: RegistroAlerta) -> RegistroAlerta | None:
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
