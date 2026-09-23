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

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Alerta, Bebe, Cuna, Medicamento, Medico, PlanCuidado
from .serializers import (
    AlertaSerializer,
    BebeSerializer,
    CunaSerializer,
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


class BebeViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Bebe.
    Proporciona operaciones CRUD completas sobre los pacientes (bebés).
    """

    queryset = Bebe.objects.all()
    serializer_class = BebeSerializer


class CunaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Cuna.
    Proporciona operaciones CRUD completas sobre las cunas de monitoreo.
    Las respuestas incluyen datos anidados del bebé asignado (ver CunaSerializer).
    """

    queryset = Cuna.objects.all()
    serializer_class = CunaSerializer

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
    Proporciona operaciones CRUD completas sobre el control y
    administración de fármacos a los pacientes.
    """

    # Si quieres que la API envíe los datos ordenados por hora por defecto,
    # puedes cambiar .all() por .all().order_by('hora')
    queryset = Medicamento.objects.all()
    serializer_class = MedicamentoSerializer


class PlanCuidadoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo PlanCuidado.
    Proporciona operaciones CRUD completas sobre los protocolos
    de atención asignados a los pacientes.
    """

    queryset = PlanCuidado.objects.all()
    serializer_class = PlanCuidadoSerializer


class AlertaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Alerta.
    Proporciona operaciones CRUD y acciones para listar alertas activas y resolverlas.
    """

    queryset = Alerta.objects.all().order_by("-fecha_hora")
    serializer_class = AlertaSerializer

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

