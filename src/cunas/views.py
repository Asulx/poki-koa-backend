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
import logging

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .alertas_service import AlertaOperacionError, AlertaService
from .medicamentos import MedicamentoService, OperacionError
from .models import (
    Alerta,
    Bebe,
    Cuna,
    Medicamento,
    MedicamentoCatalogo,
    Medico,
    PlanCuidado,
)
from .repositories import DjangoMedicamentoRepository
from .repositories_alertas import DjangoAlertaRepository
from .serializers import (
    AlertaSerializer,
    BebeSerializer,
    CunaSerializer,
    MedicamentoCatalogoSerializer,
    MedicamentoSerializer,
    MedicoSerializer,
    PlanCuidadoSerializer,
)

logger = logging.getLogger(__name__)


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
    Proporciona operaciones CRUD completas sobre los pacientes (bebés),
    optimizando la carga de relaciones y permitiendo búsqueda y filtros
    mediante parámetros de consulta (?search=, ?identificador=, ?sexo=, etc.).
    """

    queryset = (
        Bebe.objects.all()
        .select_related("medico_a_cargo", "cuna_asignada")
        .prefetch_related("medicamentos", "alertas")
        .order_by("-fecha_ingreso")
    )
    serializer_class = BebeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Búsqueda por texto (nombre, identificador o ID numérico)
        search = self.request.query_params.get(
            "search"
        ) or self.request.query_params.get("q")
        if search:
            search = search.strip()
            if search.isdigit():
                queryset = queryset.filter(
                    Q(nombre_completo__icontains=search)
                    | Q(identificador__icontains=search)
                    | Q(id=int(search))
                )
            else:
                queryset = queryset.filter(
                    Q(nombre_completo__icontains=search)
                    | Q(identificador__icontains=search)
                )

        # Filtro directo por identificador del paciente
        identificador = self.request.query_params.get("identificador")
        if identificador:
            queryset = queryset.filter(identificador__icontains=identificador.strip())

        # Filtro directo por nombre
        nombre = self.request.query_params.get("nombre")
        if nombre:
            queryset = queryset.filter(nombre_completo__icontains=nombre.strip())

        # Filtro por sexo ('F' o 'M')
        sexo = self.request.query_params.get("sexo")
        if sexo:
            queryset = queryset.filter(sexo__iexact=sexo.strip())

        # Filtro por fecha de ingreso (formato YYYY-MM-DD)
        fecha_ingreso = self.request.query_params.get("fecha_ingreso")
        if fecha_ingreso:
            queryset = queryset.filter(fecha_ingreso__date=fecha_ingreso.strip())

        # Filtro por médico asignado (ID o nombre)
        medico = self.request.query_params.get(
            "medico_a_cargo"
        ) or self.request.query_params.get("medico")
        if medico:
            medico = medico.strip()
            if medico.isdigit():
                queryset = queryset.filter(medico_a_cargo_id=int(medico))
            else:
                queryset = queryset.filter(
                    medico_a_cargo__nombre_completo__icontains=medico
                )

        # Filtro por cuna
        cuna = self.request.query_params.get("cuna")
        if cuna:
            queryset = queryset.filter(
                cuna_asignada__identificador__icontains=cuna.strip()
            )

        return queryset


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

        # Registrar solo el identificador evita copiar datos clínicos al log.
        logger.info("Recibida telemetría para cuna %s", cuna.identificador)

        # Validación defensiva sistemática de telemetría clínica en la frontera HTTP (Issue #51).
        # Justificación clínica de rangos:
        # - Valores físicamente imposibles o por falla de sensor (FC <= 0 o > 260 bpm,
        #   SpO2 < 0 o > 100%, Temp < 25.0 o > 45.0 °C) se rechazan con HTTP 400 sin guardar.
        # - Valores fisiológicamente posibles pero clínicamente anormales (ej. FC = 72 bpm,
        #   SpO2 = 88%, Temp = 38.9 °C) se aceptan con HTTP 200 para que el motor de alertas
        #   (alertas.py) dispare las alertas críticas o de advertencia correspondientes.
        if "ritmo_cardiaco" in data:
            ritmo = data.get("ritmo_cardiaco")
            if type(ritmo) not in (int, float) or not (1 <= ritmo <= 260):
                logger.warning(
                    "Telemetría anómala detectada en cuna %s: ritmo cardíaco inválido (%s)",
                    cuna.identificador,
                    ritmo,
                )
                return Response(
                    {
                        "error": "El ritmo cardíaco debe ser un valor numérico positivo válido dentro del rango neonatal (1-260 bpm)."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if "spo2" in data:
            spo2 = data.get("spo2")
            if type(spo2) not in (int, float) or not (0 <= spo2 <= 100):
                logger.warning(
                    "Telemetría anómala detectada en cuna %s: SpO2 inválido (%s)",
                    cuna.identificador,
                    spo2,
                )
                return Response(
                    {
                        "error": "La saturación de oxígeno (SpO2) debe ser un porcentaje numérico válido entre 0 y 100%."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if "temperatura" in data:
            temperatura = data.get("temperatura")
            if type(temperatura) not in (int, float) or not (25.0 <= float(temperatura) <= 45.0):
                logger.warning(
                    "Telemetría anómala detectada en cuna %s: temperatura inválida (%s)",
                    cuna.identificador,
                    temperatura,
                )
                return Response(
                    {
                        "error": "La temperatura corporal debe ser un valor numérico válido dentro del rango fisiológico (25.0-45.0 °C)."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if "estado_sueno" in data:
            estado_sueno = data.get("estado_sueno")
            estados_validos = {opcion[0] for opcion in Cuna.ESTADO_SUENO_CHOICES}
            if estado_sueno not in estados_validos:
                logger.warning(
                    "Telemetría anómala detectada en cuna %s: estado_sueno inválido (%s)",
                    cuna.identificador,
                    estado_sueno,
                )
                return Response(
                    {
                        "error": "El estado de sueño debe ser 'Dormido' o 'Despierto'."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        for campo_bool in ("canula_ok", "via_iv_activa"):
            if campo_bool in data and not isinstance(data.get(campo_bool), bool):
                logger.warning(
                    "Telemetría anómala detectada en cuna %s: %s no booleano (%s)",
                    cuna.identificador,
                    campo_bool,
                    data.get(campo_bool),
                )
                return Response(
                    {
                        "error": f"El campo '{campo_bool}' debe ser un valor booleano (true/false)."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

    @action(detail=True, methods=["post"])
    def administrar(self, request, pk=None):
        """POST /api/medicamentos/{id}/administrar/ (sin cuerpo requerido)."""
        servicio = MedicamentoService(DjangoMedicamentoRepository())
        try:
            resultado = servicio.administrar(pk)
        except OperacionError as error:
            return Response({"detail": str(error)}, status=error.status_code)
        return Response(
            {
                "id": resultado.id,
                "paciente_id": resultado.paciente_id,
                "estado": resultado.estado,
            }
        )


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
        """Resuelve una alerta mediante el servicio de negocio."""
        # Conserva la búsqueda, filtros y permisos del endpoint original.
        alerta = self.get_object()
        servicio = AlertaService(DjangoAlertaRepository())

        try:
            servicio.resolver_alerta(alerta.pk)
        except AlertaOperacionError as error:
            return Response(
                {"error": str(error)},
                status=error.status_code,
            )

        # Refresca el objeto para conservar el serializador y formato original.
        alerta.refresh_from_db()
        serializer = self.get_serializer(alerta)
        return Response(
            {"mensaje": "Alerta resuelta con éxito", "alerta": serializer.data},
            status=status.HTTP_200_OK,
        )



class MedicamentoCatalogoViewSet(viewsets.ModelViewSet):
    """Registro, consulta y modificación del catálogo (issue #17)."""

    queryset = MedicamentoCatalogo.objects.all()
    serializer_class = MedicamentoCatalogoSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]