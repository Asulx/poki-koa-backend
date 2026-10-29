
"""
Vistas de la aplicación 'operacion'.

Expone tres bloques funcionales:

1. **Turnos y asignaciones**
   - ``/api/turnos/``            catálogo de turnos
   - ``/api/turnos/actual/``     turno vigente según la hora local
   - ``/api/asignaciones/``      asignación de personal a turnos y cunas
   - ``/api/mis-cunas/``         cunas que cubre el usuario autenticado hoy

2. **Reportes**
   - ``/api/reportes/resumen/``       métricas del dashboard
   - ``/api/reportes/serie/``         serie diaria de ingresos y alertas
   - ``/api/reportes/distribucion/``  cunas, alertas, medicamentos y turnos

3. **Auditoría**
   - ``/api/registros/``         bitácora de solo lectura

Los endpoints de escritura administrativa exigen rol ``administrador``;
las lecturas requieren sesión autenticada. Los reportes no cambian datos.
"""

import csv
import io
import logging
from datetime import time

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cunas.models import Alerta
from usuarios.permissions import EsAdministrador

from .models import AsignacionTurno, RegistroActividad, Turno
from .reportes import (
    DIAS_SERIE_POR_DEFECTO,
    calcular_resumen,
    distribucion_alertas,
    distribucion_cunas,
    distribucion_medicamentos,
    personal_por_turno,
    serie_actividad,
)
from .serializers import (
    AsignacionTurnoSerializer,
    MisCunasSerializer,
    RegistroActividadSerializer,
    TurnoSerializer,
)

logger = logging.getLogger("operacion")


def _permisos_lectura_escritura(permiso_escritura):
    """
    Fábrica de ``get_permissions`` reutilizable.

    Parameters
    ----------
    permiso_escritura : rest_framework.permissions.BasePermission
        Permiso adicional exigido en acciones que modifican datos.

    Returns
    -------
    callable
        Función compatible con el método ``get_permissions`` de un ViewSet.
    """

    def _obtener(vista):
        if vista.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), permiso_escritura()]
        return [IsAuthenticated()]

    return _obtener


class TurnoViewSet(viewsets.ModelViewSet):
    """Catálogo de turnos de trabajo."""

    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return _permisos_lectura_escritura(EsAdministrador)(self)

    def get_queryset(self):
        queryset = super().get_queryset()
        activo = self.request.query_params.get("activo")
        if activo is not None:
            queryset = queryset.filter(activo=activo.lower() in {"1", "true", "si", "sí"})
        return queryset

    @action(detail=False, methods=["get"], url_path="actual")
    def actual(self, request):
        """
        Devuelve el turno que cubre la hora actual.

        Si ningún turno cubre el momento (por ejemplo, entre dos turnos),
        responde ``{"turno": null}`` con HTTP 200: la ausencia de turno no
        es un error, solo un estado.
        """
        ahora = timezone.localtime().time()
        turno = _buscar_turno_actual(ahora)
        if turno is None:
            return Response({"turno": None})
        return Response({"turno": TurnoSerializer(turno).data})


def _buscar_turno_actual(ahora: time):
    """
    Busca el turno activo que contiene una hora dada.

    Soporta turnos que cruzan la medianoche (por ejemplo 20:00 → 08:00).

    Parameters
    ----------
    ahora : datetime.time
        Hora local a evaluar.

    Returns
    -------
    Turno | None
        El turno que contiene la hora, o ``None`` si no hay ninguno.
    """
    for turno in Turno.objects.filter(activo=True):
        inicio, fin = turno.hora_inicio, turno.hora_fin
        if inicio <= fin:
            if inicio <= ahora < fin:
                return turno
        elif ahora >= inicio or ahora < fin:
            return turno
    return None


class AsignacionTurnoViewSet(viewsets.ModelViewSet):
    """
    Asignaciones de personal a turnos y cunas.

    Lectura: cualquier usuario autenticado (el módulo de turnos y la vista
    "Mis cunas" lo necesitan).
    Escritura: solo administradores (jefatura de turno).
    """

    queryset = AsignacionTurno.objects.select_related(
        "usuario__perfil", "turno", "cuna", "creado_por"
    ).all()
    serializer_class = AsignacionTurnoSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return _permisos_lectura_escritura(EsAdministrador)(self)

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        fecha = params.get("fecha")
        if fecha:
            queryset = queryset.filter(fecha=fecha)

        turno_id = params.get("turno")
        if turno_id:
            queryset = queryset.filter(turno_id=turno_id)

        usuario_id = params.get("usuario")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        cuna_id = params.get("cuna")
        if cuna_id:
            queryset = queryset.filter(cuna_id=cuna_id)

        return queryset

    def perform_create(self, serializer):
        """Registra como autor de la asignación al usuario autenticado."""
        serializer.save(creado_por=self.request.user)


class MisCunasView(APIView):
    """
    Cunas que el usuario autenticado tiene asignadas para hoy.

    Es la vista que consume el personal de enfermería al iniciar sesión:
    evita que tenga que buscar entre las 40 cunas de la unidad.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        hoy = timezone.localdate()
        asignaciones = (
            AsignacionTurno.objects.filter(
                usuario=request.user,
                fecha=hoy,
                cuna__isnull=False,
            )
            .select_related("turno", "cuna__paciente")
            .order_by("turno__hora_inicio", "cuna__identificador")
        )

        datos = []
        for asignacion in asignaciones:
            cuna = asignacion.cuna
            paciente = cuna.paciente
            datos.append(
                {
                    "cuna_id": cuna.pk,
                    "cuna_identificador": cuna.identificador,
                    "turno": asignacion.turno.nombre,
                    "hora_inicio": asignacion.turno.hora_inicio,
                    "hora_fin": asignacion.turno.hora_fin,
                    "paciente_id": paciente.pk if paciente else None,
                    "paciente_nombre": paciente.nombre_completo if paciente else None,
                    "paciente_identificador": paciente.identificador if paciente else None,
                    "ritmo_cardiaco": cuna.ritmo_cardiaco,
                    "spo2": cuna.spo2,
                    "temperatura": cuna.temperatura,
                    "alertas_activas": Alerta.objects.filter(
                        cuna=cuna, activa=True
                    ).count(),
                }
            )

        serializador = MisCunasSerializer(datos, many=True)
        return Response(
            {
                "fecha": hoy.isoformat(),
                "total": len(datos),
                "cunas": serializador.data,
            }
        )


class RegistroActividadViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Bitácora de auditoría en modo solo lectura.

    Solo administradores pueden consultar la actividad global del sistema,
    porque contiene información sobre usuarios y pacientes.
    """

    queryset = RegistroActividad.objects.select_related("usuario__perfil").all()
    serializer_class = RegistroActividadSerializer
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        accion = params.get("accion")
        if accion:
            queryset = queryset.filter(accion=accion)

        entidad = params.get("entidad")
        if entidad:
            queryset = queryset.filter(entidad__iexact=entidad)

        usuario_id = params.get("usuario")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        desde = params.get("desde")
        if desde:
            queryset = queryset.filter(creado_en__date__gte=desde)

        hasta = params.get("hasta")
        if hasta:
            queryset = queryset.filter(creado_en__date__lte=hasta)

        busqueda = params.get("search")
        if busqueda:
            queryset = queryset.filter(descripcion__icontains=busqueda)

        return queryset

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        """
        Cuenta los registros agrupados por acción.

        Se calcula sobre el queryset filtrado, de modo que los filtros de
        la vista se reflejen en las tarjetas de resumen del frontend.
        """
        from django.db.models import Count

        conteo = self.get_queryset().values("accion").annotate(total=Count("id"))
        return Response(list(conteo))


class ResumenReporteView(APIView):
    """Métricas principales del dashboard (una sola petición)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(calcular_resumen().como_diccionario())


class SerieReporteView(APIView):
    """Serie diaria de ingresos y alertas para las gráficas."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            dias = int(request.query_params.get("dias", DIAS_SERIE_POR_DEFECTO))
        except (TypeError, ValueError):
            return Response(
                {"detail": "El parámetro 'dias' debe ser un número entero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not 1 <= dias <= 90:
            return Response(
                {"detail": "El parámetro 'dias' debe estar entre 1 y 90."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"dias": dias, "serie": serie_actividad(dias)})


class DistribucionReporteView(APIView):
    """Distribuciones agregadas usadas por las tarjetas y gráficos."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "cunas": distribucion_cunas(),
                "alertas": distribucion_alertas(),
                "medicamentos": distribucion_medicamentos(),
                "personal": personal_por_turno(),
            }
        )


class ExportarReporteView(APIView):
    """
    Exporta el resumen operacional en CSV.

    Se entrega con BOM UTF-8 para que Excel reconozca los acentos sin
    configuración adicional. El nombre incluye la fecha para evitar
    sobrescrituras al descargar varias veces.
    """

    permission_classes = [IsAuthenticated]

    COLUMNAS = [
        ("Métrica", "metrica"),
        ("Valor", "valor"),
    ]

    def get(self, request):
        resumen = calcular_resumen().como_diccionario()
        fecha = timezone.localdate().isoformat()

        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=";")
        escritor.writerow([columna[0] for columna in self.COLUMNAS])
        for clave, valor in resumen.items():
            escritor.writerow([clave, valor])

        respuesta = HttpResponse(
            "\ufeff" + buffer.getvalue(),
            content_type="text/csv; charset=utf-8",
        )
        respuesta["Content-Disposition"] = (
            f'attachment; filename="reporte-poki-koa-{fecha}.csv"'
        )
        logger.info(
            "Exportación CSV del resumen solicitada por '%s' a las %s",
            request.user.username,
            timezone.now().isoformat(timespec="seconds"),
        )
        return respuesta
