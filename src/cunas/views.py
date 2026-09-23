"""
Vistas (controladores) de la API REST para la aplicación 'cunas'.


Cada ViewSet expone automáticamente los endpoints CRUD completos
para su modelo correspondiente gracias a Django REST Framework:


    GET    /api/medicos/         → lista todos los médicos
    POST   /api/medicos/         → crea un nuevo médico
    GET    /api/medicos/{id}/    → detalle de un médico
    PUT    /api/medicos/{id}/    → actualiza un médico
    DELETE /api/medicos/{id}/    → elimina un médico


(Las mismas operaciones aplican para /api/bebes/, /api/cunas/ y /api/medicamentos/)
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Alerta, Bebe, Cuna, Medicamento, Medico, PlanCuidado
from .serializers import (
    AlertaSerializer,
    BebeSerializer,
    CunaSerializer,
    DashboardResumenSerializer,
    HistorialSignosVitalesSerializer,
    MedicamentoSerializer,
    MedicoSerializer,
    PlanCuidadoSerializer,
)


class MedicoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Medico.
    Proporciona operaciones CRUD completas sobre los médicos del sistema.
    """

    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer
    search_fields = ("nombre_completo", "turno")
    filterset_fields = ("turno",)
    ordering_fields = ("nombre_completo", "turno")


class BebeViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Bebe.
    Proporciona operaciones CRUD completas sobre los pacientes (bebés).
    Soporta búsqueda por texto (?search=...) y filtros por sexo o médico.
    """

    queryset = Bebe.objects.all()
    serializer_class = BebeSerializer
    search_fields = ("nombre_completo", "diagnostico")
    filterset_fields = ("sexo", "medico_a_cargo")
    ordering_fields = ("nombre_completo", "fecha_ingreso", "peso", "edad_meses")


class CunaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Cuna.
    Proporciona operaciones CRUD completas sobre las cunas de monitoreo.
    Las respuestas incluyen datos anidados del bebé asignado (ver CunaSerializer).
    """

    queryset = Cuna.objects.all()
    serializer_class = CunaSerializer
    search_fields = ("identificador", "paciente__nombre_completo")
    filterset_fields = ("estado_sueno", "canula_ok", "via_iv_activa")
    ordering_fields = ("identificador", "ultima_actualizacion")

    @extend_schema(
        responses=HistorialSignosVitalesSerializer(many=True),
        summary="Serie temporal de signos vitales para gráficos",
        description="Retorna las lecturas históricas de la cuna en orden cronológico para visualización en gráficos.",
    )
    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        """
        Retorna la serie temporal de lecturas de signos vitales para graficar (US-06).
        Parámetro opcional: ?limit=50 (por defecto 30).
        Retorna las lecturas ordenadas cronológicamente (más antigua a más reciente).
        """
        cuna = self.get_object()
        limit = int(request.query_params.get("limit", 30))
        lecturas = cuna.historial_signos.all()[:limit]
        lecturas_cronologicas = list(reversed(lecturas))
        serializer = HistorialSignosVitalesSerializer(
            lecturas_cronologicas, many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="telemetria")
    def telemetria(self, request, pk=None):
        """
        Endpoint para recibir datos de telemetría de sensores IoT o simuladores.
        Actualiza los signos vitales de la cuna y procesa automáticamente las alertas.
        """
        cuna = self.get_object()
        data = request.data

        campos_actualizables = [
            "ritmo_cardiaco",
            "spo2",
            "temperatura",
            "estado_sueno",
            "canula_ok",
            "via_iv_activa",
        ]
        campos_modificados = []

        for campo in campos_actualizables:
            if campo in data:
                setattr(cuna, campo, data[campo])
                campos_modificados.append(campo)

        if campos_modificados:
            cuna.save()

        alertas_activas = Alerta.objects.filter(cuna=cuna, activa=True).order_by(
            "-fecha_hora"
        )
        serializer_alertas = AlertaSerializer(alertas_activas, many=True)

        return Response(
            {
                "mensaje": "Telemetría procesada exitosamente",
                "cuna": cuna.identificador,
                "paciente": cuna.paciente.nombre_completo if cuna.paciente else None,
                "signos_actuales": {
                    "ritmo_cardiaco": cuna.ritmo_cardiaco,
                    "spo2": cuna.spo2,
                    "temperatura": cuna.temperatura,
                    "estado_sueno": cuna.estado_sueno,
                    "canula_ok": cuna.canula_ok,
                    "via_iv_activa": cuna.via_iv_activa,
                },
                "alertas_activas": serializer_alertas.data,
            },
            status=status.HTTP_200_OK,
        )


class MedicamentoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Medicamento.
    Proporciona operaciones CRUD y acción rápida para marcar como administrado.
    """

    queryset = Medicamento.objects.all().order_by("hora")
    serializer_class = MedicamentoSerializer
    search_fields = ("nombre", "paciente__nombre_completo")
    filterset_fields = ("paciente", "estado", "via")
    ordering_fields = ("hora", "nombre", "estado")

    @extend_schema(
        responses=MedicamentoSerializer,
        summary="Marcar medicamento como administrado (US-02, US-03)",
        description="Actualiza el estado del medicamento a 'Administrado'.",
    )
    @action(detail=True, methods=["post"], url_path="administrar")
    def administrar(self, request, pk=None):
        """
        Marca rápidamente un medicamento prescrito como 'Administrado' (US-02, US-03).
        """
        medicamento = self.get_object()
        medicamento.estado = "Administrado"
        medicamento.save(update_fields=["estado"])
        serializer = self.get_serializer(medicamento)
        return Response(
            {
                "mensaje": f"Medicamento {medicamento.nombre} administrado exitosamente",
                "medicamento": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class PlanCuidadoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo PlanCuidado.
    Proporciona operaciones CRUD completas sobre los protocolos
    de atención asignados a los pacientes.
    """

    queryset = PlanCuidado.objects.all()
    serializer_class = PlanCuidadoSerializer
    search_fields = ("area_cuidado", "intervencion", "bebe__nombre_completo")
    filterset_fields = ("bebe", "estado", "area_cuidado")
    ordering_fields = ("area_cuidado", "estado")


class AlertaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Alerta.
    Proporciona operaciones CRUD y acciones para listar alertas activas y resolverlas.
    """

    queryset = Alerta.objects.all().order_by("-fecha_hora")
    serializer_class = AlertaSerializer
    search_fields = ("mensaje", "paciente__nombre_completo", "cuna__identificador")
    filterset_fields = ("activa", "nivel", "tipo", "paciente", "cuna")
    ordering_fields = ("fecha_hora", "nivel")

    def get_queryset(self):
        queryset = super().get_queryset()
        activa = self.request.query_params.get("activa")
        if activa is not None:
            if activa.lower() in ["true", "1"]:
                queryset = queryset.filter(activa=True)
            elif activa.lower() in ["false", "0"]:
                queryset = queryset.filter(activa=False)

        nivel = self.request.query_params.get("nivel")
        if nivel:
            queryset = queryset.filter(nivel=nivel)

        tipo = self.request.query_params.get("tipo")
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        paciente_id = self.request.query_params.get("paciente")
        if paciente_id:
            queryset = queryset.filter(paciente_id=paciente_id)

        cuna_id = self.request.query_params.get("cuna")
        if cuna_id:
            queryset = queryset.filter(cuna_id=cuna_id)

        return queryset

    @action(detail=False, methods=["get"], url_path="activas")
    def activas(self, request):
        """Lista todas las alertas que se encuentran activas en el sistema."""
        alertas = self.get_queryset().filter(activa=True)
        serializer = self.get_serializer(alertas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="resolver")
    def resolver(self, request, pk=None):
        """Marca una alerta activa como resuelta."""
        alerta = self.get_object()
        alerta.activa = False
        alerta.save(update_fields=["activa"])
        serializer = self.get_serializer(alerta)
        return Response(
            {"mensaje": "Alerta resuelta con éxito", "alerta": serializer.data},
            status=status.HTTP_200_OK,
        )


class DashboardResumenView(APIView):
    """
    Endpoint consolidado de KPIs para el Dashboard principal de Poki Koa (US-06).
    Retorna métricas globales de ocupación de cunas, alertas activas y fármacos.
    """

    @extend_schema(
        responses=DashboardResumenSerializer,
        summary="KPIs y métricas consolidadas del Dashboard",
        description="Retorna indicadores agregados en tiempo real (cunas ocupadas/libres, alertas activas, fármacos).",
    )
    def get(self, request):
        cunas_totales = Cuna.objects.count()
        cunas_ocupadas = Cuna.objects.filter(paciente__isnull=False).count()
        cunas_disponibles = cunas_totales - cunas_ocupadas
        pacientes_activos = Bebe.objects.count()
        alertas_activas = Alerta.objects.filter(activa=True)
        alertas_criticas = alertas_activas.filter(nivel="Critica").count()
        alertas_advertencia = alertas_activas.filter(nivel="Advertencia").count()
        medicamentos_pendientes = Medicamento.objects.filter(
            estado="Pendiente"
        ).count()
        medicamentos_administrados = Medicamento.objects.filter(
            estado="Administrado"
        ).count()

        data = {
            "cunas_totales": cunas_totales,
            "cunas_ocupadas": cunas_ocupadas,
            "cunas_disponibles": cunas_disponibles,
            "pacientes_activos": pacientes_activos,
            "alertas_activas_total": alertas_activas.count(),
            "alertas_criticas": alertas_criticas,
            "alertas_advertencia": alertas_advertencia,
            "medicamentos_pendientes": medicamentos_pendientes,
            "medicamentos_administrados": medicamentos_administrados,
        }
        serializer = DashboardResumenSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

