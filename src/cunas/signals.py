"""Señales de Django para la aplicación 'cunas' en Poki Koa.

Conecta eventos del ciclo de vida de los modelos con la lógica de negocio,
garantizando que cualquier cambio en los signos vitales de una cuna
(vía ORM, API REST o comando) active automáticamente el motor de alertas.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .alertas import procesar_alertas_cuna
from .models import Cuna

"""Evalúa los signos vitales de la cuna automáticamente cada vez que se crea o actualiza un registro de Cuna.

@param sender - Modelo que emite la señal (Cuna).
@param instance - Instancia específica del modelo Cuna que fue guardada.
@param created - Booleano que indica si el registro acaba de ser creado (True) o actualizado (False).
@param kwargs - Argumentos adicionales opcionales de la señal de Django.
@returns None
"""


@receiver(post_save, sender=Cuna)
def cuna_post_save_alertas_handler(sender, instance, created, **kwargs):
    # Si viene con raw=True (fixtures) o actualización específica de campos sin signos,
    # no procesamos.
    if kwargs.get("raw", False):
        return

    procesar_alertas_cuna(instance)
    return
