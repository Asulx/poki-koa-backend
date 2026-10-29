"""
Auditoría automática del sistema.

Conecta señales de Django para registrar en ``RegistroActividad`` cada
creación, actualización y eliminación de las entidades relevantes. La
bitácora permite responder "quién cambió qué y cuándo", requisito habitual
en software clínico.

Decisiones
----------
- **No se audita la telemetría.** ``CunaViewSet.telemetria`` marca la
  instancia con ``_omitir_auditoria = True`` para no generar una fila por
  cada muestra de sensores.
- **Los fallos de auditoría nunca rompen la operación principal.** Si la
  escritura del registro falla (por ejemplo, durante una migración), se
  ignora y se deja constancia en el log.
- **Sin recursión.** ``RegistroActividad`` no está en la lista de modelos
  auditados y existe además una bandera por hilo.
"""

import logging

from django.db import DatabaseError
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from cunas.models import (
    Alerta,
    Bebe,
    Cuna,
    Medicamento,
    MedicamentoCatalogo,
    Medico,
    PlanCuidado,
)

from .middleware import get_client_ip, get_current_user
from .models import RegistroActividad

logger = logging.getLogger("operacion")

# Modelos auditados y su etiqueta legible.
ENTIDADES_AUDITADAS = {
    Bebe: "Bebé",
    Cuna: "Cuna",
    Medico: "Médico",
    Medicamento: "Medicamento",
    MedicamentoCatalogo: "Medicamento (catálogo)",
    PlanCuidado: "Plan de cuidado",
    Alerta: "Alerta",
}

# Redacción natural de cada verbo para la descripción automática.
VERBOS_NARRATIVOS = {
    "crear": "Se registró",
    "actualizar": "Se actualizó",
    "eliminar": "Se eliminó",
    "asignar": "Se asignó",
    "liberar": "Se liberó",
    "administrar": "Se administró",
    "alta": "Se dio de alta",
    "resolver": "Se resolvió",
    "login": "Inició sesión",
    "logout": "Cerró sesión",
}


def describir(instance) -> str:
    """
    Construye una descripción breve y segura de una instancia.

    Se evita ``str(instance)`` cuando puede lanzar excepciones por
    relaciones no cargadas; se priorizan atributos simples.
    """
    for atributo in (
        "nombre_completo",
        "identificador",
        "nombre",
        "mensaje",
        "intervencion",
    ):
        valor = getattr(instance, atributo, None)
        if valor:
            return str(valor)[:200]

    try:
        return str(instance)[:200]
    except Exception:  # noqa: BLE001  # pragma: no cover - protección defensiva
        return f"{instance.__class__.__name__} #{instance.pk}"


def registrar_actividad(accion, instance, descripcion=None, metadata=None, usuario=None, request=None):
    """
    Escribe una entrada en la bitácora.

    Parameters
    ----------
    accion : str
        Verbo normalizado; debe pertenecer a ``RegistroActividad.ACCION_CHOICES``.
    instance : django.db.models.Model
        Objeto afectado. Se usan su clase y su clave primaria.
    descripcion : str | None
        Texto legible. Si se omite, se genera con ``describir``.
    metadata : dict | None
        Información adicional serializable a JSON.
    usuario : User | None
        Usuario responsable. Si se omite, se toma de la petición actual.
    request : HttpRequest | None
        Petición de origen. Si se omite, se toma del contexto del hilo.

    Returns
    -------
    RegistroActividad | None
        El registro creado, o ``None`` si la escritura falló.
    """
    etiqueta = ENTIDADES_AUDITADAS.get(type(instance), instance.__class__.__name__)
    verbo = VERBOS_NARRATIVOS.get(accion, accion.capitalize())

    try:
        return RegistroActividad.objects.create(
            usuario=usuario if usuario is not None else get_current_user(),
            accion=accion,
            entidad=etiqueta,
            entidad_id=str(instance.pk or ""),
            descripcion=descripcion or f"{verbo} {etiqueta}: {describir(instance)}",
            metadata=metadata or {},
            ip_address=get_client_ip(request),
        )
    except DatabaseError:  # pragma: no cover - depende del estado de la BD
        logger.warning(
            "No se pudo registrar la auditoría de %s #%s",
            etiqueta,
            getattr(instance, "pk", None),
            exc_info=True,
        )
        return None


def _al_guardar(sender, instance, created, **kwargs):
    """
    Registra creación o actualización de una entidad auditada.

    Caso especial: cuando un ``Medicamento`` pasa de ``Pendiente`` a
    ``Administrado`` se registra con el verbo ``administrar`` en lugar de
    ``actualizar``, para que la bitácora refleje el evento clínico real.
    """
    if kwargs.get("raw"):
        return

    # La marca permite que una vista registre el evento con un verbo propio
    # (asignar, liberar, alta) sin que la señal genere además un "actualizar".
    if getattr(instance, "_omitir_auditoria", False):
        return

    if created:
        accion = RegistroActividad.ACCION_CREAR
    elif (
        isinstance(instance, Medicamento)
        and instance.estado == "Administrado"
        and getattr(instance, "_estado_anterior", None) != "Administrado"
    ):
        accion = RegistroActividad.ACCION_ADMINISTRAR
    else:
        accion = RegistroActividad.ACCION_ACTUALIZAR

    registrar_actividad(accion, instance)


def _al_eliminar(sender, instance, **kwargs):
    """Registra la eliminación de una entidad auditada."""
    registrar_actividad(RegistroActividad.ACCION_ELIMINAR, instance)


@receiver(pre_save, sender=Medicamento)
def _recordar_estado_medicamento(sender, instance, **kwargs):
    """
    Guarda el estado previo del medicamento antes de actualizarlo.

    Permite distinguir una edición cualquiera de una administración real
    sin consultar la base de datos dos veces durante el guardado.
    """
    if not instance.pk:
        instance._estado_anterior = None
        return

    instance._estado_anterior = (
        Medicamento.objects.filter(pk=instance.pk)
        .values_list("estado", flat=True)
        .first()
    )


for _modelo in ENTIDADES_AUDITADAS:
    post_save.connect(
        _al_guardar,
        sender=_modelo,
        dispatch_uid=f"auditoria_save_{_modelo.__name__}",
    )
    post_delete.connect(
        _al_eliminar,
        sender=_modelo,
        dispatch_uid=f"auditoria_delete_{_modelo.__name__}",
    )
