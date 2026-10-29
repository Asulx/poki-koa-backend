"""
Servicio de métricas y reportes de la aplicación 'operacion'.

Se implementa como un módulo de funciones puras sobre el ORM (sin vistas ni
serializadores) para poder probarlo de forma aislada y reutilizarlo desde
el dashboard, la exportación y los tests.

Contrato general
----------------
- Todas las funciones son **de solo lectura**: no escriben en la base de
  datos ni modifican querysets globales.
- Todos los valores retornados son tipos primitivos serializables a JSON
  (``int``, ``float``, ``str``, ``list``, ``dict``).
- Nunca retornan ``None``: cuando no hay datos devuelven ``0`` o ``[]``,
  de modo que el frontend no tenga que defenderse de nulos.
"""

from dataclasses import asdict, dataclass
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from cunas.models import (
    Alerta,
    Bebe,
    Cuna,
    Medicamento,
    MedicamentoCatalogo,
    PlanCuidado,
)

from .models import AsignacionTurno, Turno

Usuario = get_user_model()

# Umbral de inventario por debajo del cual se considera stock crítico.
UMBRAL_STOCK_CRITICO = 5

# Días que abarca la serie temporal por defecto.
DIAS_SERIE_POR_DEFECTO = 14


@dataclass(frozen=True)
class ResumenOperacion:
    """
    Métricas principales del dashboard.

    Es un ``dataclass`` inmutable: una vez calculado, el resumen no puede
    alterarse por accidente desde la vista o el serializador.
    """

    total_pacientes: int
    pacientes_activos: int
    pacientes_dados_de_alta: int
    total_cunas: int
    cunas_ocupadas: int
    cunas_disponibles: int
    cunas_mantenimiento: int
    ocupacion_porcentaje: float
    total_medicamentos: int
    medicamentos_pendientes: int
    medicamentos_administrados: int
    medicamentos_stock_critico: int
    alertas_activas: int
    alertas_criticas: int
    planes_activos: int
    personal_activo: int
    turnos_activos: int
    asignaciones_hoy: int
    generado_en: str

    def como_diccionario(self) -> dict:
        """Devuelve el resumen como diccionario listo para serializar."""
        return asdict(self)


def _porcentaje(parte: int, total: int) -> float:
    """
    Calcula un porcentaje redondeado a un decimal.

    Parameters
    ----------
    parte : int
        Valor parcial. Debe ser mayor o igual a cero.
    total : int
        Valor total. Si es cero, el porcentaje es ``0.0``.
    """
    if total <= 0:
        return 0.0
    return round((parte / total) * 100, 1)


def calcular_resumen() -> ResumenOperacion:
    """
    Calcula el resumen operacional completo.

    Returns
    -------
    ResumenOperacion
        Métricas consistentes calculadas sobre el estado actual de la base
        de datos.

    Notes
    -----
    ``cunas_disponibles`` se calcula por resta para que siempre se cumpla
    ``disponibles + ocupadas + mantenimiento == total_cunas``, incluso si
    una cuna tuviera datos inconsistentes.
    """
    total_cunas = Cuna.objects.count()
    cunas_ocupadas = Cuna.objects.filter(paciente__isnull=False).count()
    cunas_mantenimiento = Cuna.objects.filter(
        paciente__isnull=True, en_mantenimiento=True
    ).count()
    cunas_disponibles = max(0, total_cunas - cunas_ocupadas - cunas_mantenimiento)

    pacientes_activos = Bebe.objects.filter(activo=True).count()
    pacientes_dados_de_alta = Bebe.objects.filter(activo=False).count()

    medicamentos_por_estado = dict(
        Medicamento.objects.values_list("estado").annotate(total=Count("id"))
    )

    alertas_activas = Alerta.objects.filter(activa=True).count()
    alertas_criticas = Alerta.objects.filter(activa=True, nivel="Critica").count()

    return ResumenOperacion(
        total_pacientes=pacientes_activos + pacientes_dados_de_alta,
        pacientes_activos=pacientes_activos,
        pacientes_dados_de_alta=pacientes_dados_de_alta,
        total_cunas=total_cunas,
        cunas_ocupadas=cunas_ocupadas,
        cunas_disponibles=cunas_disponibles,
        cunas_mantenimiento=cunas_mantenimiento,
        ocupacion_porcentaje=_porcentaje(cunas_ocupadas, total_cunas),
        total_medicamentos=sum(medicamentos_por_estado.values()),
        medicamentos_pendientes=medicamentos_por_estado.get("Pendiente", 0),
        medicamentos_administrados=medicamentos_por_estado.get("Administrado", 0),
        medicamentos_stock_critico=MedicamentoCatalogo.objects.filter(
            stock__lte=UMBRAL_STOCK_CRITICO
        ).count(),
        alertas_activas=alertas_activas,
        alertas_criticas=alertas_criticas,
        planes_activos=PlanCuidado.objects.filter(estado="Activo").count(),
        personal_activo=Usuario.objects.filter(is_active=True).count(),
        turnos_activos=Turno.objects.filter(activo=True).count(),
        asignaciones_hoy=AsignacionTurno.objects.filter(
            fecha=timezone.localdate()
        ).count(),
        generado_en=timezone.localtime().isoformat(),
    )


def serie_actividad(dias: int = DIAS_SERIE_POR_DEFECTO) -> list[dict]:
    """
    Construye una serie diaria de ingresos y alertas.

    Parameters
    ----------
    dias : int
        Cantidad de días hacia atrás, incluido hoy. Se acota al rango
        ``1..90`` para evitar consultas desmedidas desde la API.

    Returns
    -------
    list[dict]
        Un elemento por día con las claves ``fecha`` (``YYYY-MM-DD``),
        ``ingresos`` y ``alertas``. Los días sin datos aparecen en cero,
        de modo que una gráfica no presente huecos.
    """
    dias = max(1, min(int(dias or DIAS_SERIE_POR_DEFECTO), 90))
    hoy = timezone.localdate()
    desde = hoy - timedelta(days=dias - 1)

    ingresos = dict(
        Bebe.objects.filter(fecha_ingreso__date__gte=desde)
        .values_list("fecha_ingreso__date")
        .annotate(total=Count("id"))
    )
    alertas = dict(
        Alerta.objects.filter(fecha_hora__date__gte=desde)
        .values_list("fecha_hora__date")
        .annotate(total=Count("id"))
    )

    serie = []
    for desplazamiento in range(dias):
        dia = desde + timedelta(days=desplazamiento)
        serie.append(
            {
                "fecha": dia.isoformat(),
                "ingresos": ingresos.get(dia, 0),
                "alertas": alertas.get(dia, 0),
            }
        )
    return serie


def distribucion_cunas() -> list[dict]:
    """
    Distribución de cunas por estado operativo.

    Returns
    -------
    list[dict]
        Elementos ``{"estado": str, "cantidad": int}`` para las tres
        categorías posibles: ``ocupada``, ``mantenimiento`` y ``disponible``.
    """
    total = Cuna.objects.count()
    ocupadas = Cuna.objects.filter(paciente__isnull=False).count()
    mantenimiento = Cuna.objects.filter(
        paciente__isnull=True, en_mantenimiento=True
    ).count()
    disponibles = max(0, total - ocupadas - mantenimiento)

    return [
        {"estado": "ocupada", "cantidad": ocupadas},
        {"estado": "disponible", "cantidad": disponibles},
        {"estado": "mantenimiento", "cantidad": mantenimiento},
    ]


def distribucion_alertas() -> list[dict]:
    """
    Conteo de alertas activas agrupadas por tipo de signo vital.

    Returns
    -------
    list[dict]
        Elementos ``{"tipo": str, "etiqueta": str, "cantidad": int}``.
    """
    etiquetas = dict(Alerta.TIPO_CHOICES)
    conteo = (
        Alerta.objects.filter(activa=True)
        .values("tipo")
        .annotate(cantidad=Count("id"))
        .order_by("-cantidad")
    )
    return [
        {
            "tipo": fila["tipo"],
            "etiqueta": etiquetas.get(fila["tipo"], fila["tipo"]),
            "cantidad": fila["cantidad"],
        }
        for fila in conteo
    ]


def distribucion_medicamentos() -> list[dict]:
    """
    Conteo de prescripciones agrupadas por estado de administración.

    Returns
    -------
    list[dict]
        Elementos ``{"estado": str, "cantidad": int}``.
    """
    conteo = (
        Medicamento.objects.values("estado")
        .annotate(cantidad=Count("id"))
        .order_by("estado")
    )
    return [{"estado": fila["estado"], "cantidad": fila["cantidad"]} for fila in conteo]


def personal_por_turno() -> list[dict]:
    """
    Cantidad de asignaciones por turno para el día de hoy.

    Returns
    -------
    list[dict]
        Elementos ``{"turno": str, "cantidad": int, "hora_inicio": str,
        "hora_fin": str}`` ordenados por hora de inicio.
    """
    hoy = timezone.localdate()
    conteo = dict(
        AsignacionTurno.objects.filter(fecha=hoy)
        .values_list("turno__nombre")
        .annotate(total=Count("id"))
    )
    return [
        {
            "turno": turno.nombre,
            "cantidad": conteo.get(turno.nombre, 0),
            "hora_inicio": turno.hora_inicio.strftime("%H:%M"),
            "hora_fin": turno.hora_fin.strftime("%H:%M"),
        }
        for turno in Turno.objects.filter(activo=True).order_by("hora_inicio")
    ]
