"""
Señales de Django para la aplicación 'cunas'.

Conecta eventos del ciclo de vida de los modelos con la lógica de negocio,
garantizando que cualquier cambio en los signos vitales de una cuna
(vía ORM, API REST o comando) active automáticamente el motor de alertas.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .alertas import procesar_alertas_cuna
from .models import Cuna, HistorialSignosVitales


@receiver(post_save, sender=Cuna)
def cuna_post_save_alertas_handler(sender, instance, created, **kwargs):
    """
    Evalúa los signos vitales de la cuna automáticamente cada vez que se crea
    o actualiza un registro de Cuna, y almacena una lectura en el historial
    para series temporales y gráficos clínicos.
    """
    # Si viene con raw=True (fixtures) o actualización específica de campos sin signos,
    # no procesamos.
    if kwargs.get("raw", False):
        return

    # Registrar en historial si hay al menos un signo vital reportado
    if (
        instance.ritmo_cardiaco is not None
        or instance.spo2 is not None
        or instance.temperatura is not None
    ):
        HistorialSignosVitales.objects.create(
            cuna=instance,
            ritmo_cardiaco=instance.ritmo_cardiaco,
            spo2=instance.spo2,
            temperatura=instance.temperatura,
        )

    procesar_alertas_cuna(instance)

