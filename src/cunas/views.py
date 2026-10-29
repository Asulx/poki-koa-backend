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

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
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

    queryset = Medico.objects.all().order_by("nombre_completo")
    serializer_class = MedicoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        busqueda = self.request.query_params.get("search")
        if busqueda:
            queryset = queryset.filter(nombre_completo__icontains=busqueda.strip())

        turno = self.request.query_params.get("turno")
        if turno:
            queryset = queryset.filter(turno__iexact=turno.strip())

        return queryset


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

        # Filtro por estado de hospitalización. Por defecto se listan todos
        # (incluidos los dados de alta) para no alterar el contrato histórico.
        activo = self.request.query_params.get("activo")
        if activo is not None:
            queryset = queryset.filter(activo=activo.lower() in {"1", "true", "si", "sí"})

        return queryset

    @action(detail=True, methods=["post"], url_path="alta")
    def alta(self, request, pk=None):
        """
        Da el alta clínica a un paciente y libera su cuna.

        Precondiciones
        --------------
        - El paciente existe y está activo.
        - Opcionalmente se recibe ``{"motivo": "Domicilio"}``.

        Postcondiciones
        ---------------
        - ``activo = False`` y ``fecha_alta`` registrada.
        - La cuna queda libre (si tenía una asignada).
        - Se registra la acción en la bitácora de auditoría.

        Errores
        -------
        - HTTP 400 si el paciente ya estaba dado de alta.
        """
        from operacion.auditoria import registrar_actividad
        from operacion.models import RegistroActividad

        bebe = self.get_object()

        if not bebe.activo:
            return Response(
                {"detail": "El paciente ya tiene el alta registrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        motivo = str(request.data.get("motivo", "") or "")[:255]

        with transaction.atomic():
            cuna_liberada = self._liberar_cuna_de(bebe, request)

            bebe.activo = False
            bebe.fecha_alta = timezone.now()
            bebe.motivo_alta = motivo
            bebe._omitir_auditoria = True
            bebe.save(update_fields=["activo", "fecha_alta", "motivo_alta"])

            registrar_actividad(
                RegistroActividad.ACCION_ALTA,
                bebe,
                descripcion=(
                    f"Alta clínica de {bebe.nombre_completo} "
                    f"({bebe.identificador})"
                    + (f": {motivo}" if motivo else "")
                ),
                metadata={"cuna_liberada": cuna_liberada, "motivo": motivo},
            )

        logger.info("Alta clínica registrada para el paciente %s", bebe.identificador)
        return Response(self.get_serializer(bebe).data, status=status.HTTP_200_OK)

    @staticmethod
    def _liberar_cuna_de(bebe, request=None):
        """
        Libera la cuna ocupada por un bebé, si existe.

        Returns
        -------
        str | None
            Identificador de la cuna liberada, o ``None`` si no tenía.
        """
        from operacion.auditoria import registrar_actividad
        from operacion.models import RegistroActividad

        try:
            cuna = bebe.cuna_asignada
        except Cuna.DoesNotExist:
            return None

        if cuna is None:
            return None

        cuna.paciente = None
        cuna._omitir_auditoria = True
        cuna.save(update_fields=["paciente", "ultima_actualizacion"])
        registrar_actividad(
            RegistroActividad.ACCION_LIBERAR,
            cuna,
            descripcion=(
                f"Cuna {cuna.identificador} liberada tras el alta de "
                f"{bebe.nombre_completo}"
            ),
            request=request,
        )
        return cuna.identificador


class CunaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Cuna.
    Proporciona operaciones CRUD completas sobre las cunas de monitoreo.
    Las respuestas incluyen datos anidados del bebé asignado (ver CunaSerializer).

    Acciones adicionales:

    - ``POST /api/cunas/{id}/asignar/``  asigna un bebé a la cuna.
    - ``POST /api/cunas/{id}/liberar/``  deja la cuna disponible.
    - ``POST /api/cunas/{id}/telemetria/`` recibe signos vitales.
    """

    queryset = Cuna.objects.all()
    serializer_class = CunaSerializer

    def get_queryset(self):
        """
        Cunas con su paciente y la marca de alerta crítica ya resueltas.

        La anotación ``alerta_critica_anotada`` evita una consulta por cuna
        al pintar el mapa completo (40 cunas = 40 consultas menos).
        """
        queryset = (
            super()
            .get_queryset()
            .select_related("paciente")
            .annotate(
                alerta_critica_anotada=Exists(
                    Alerta.objects.filter(
                        cuna=OuterRef("pk"),
                        activa=True,
                        nivel="Critica",
                    )
                )
            )
            .order_by("identificador")
        )

        params = self.request.query_params

        busqueda = params.get("search")
        if busqueda:
            queryset = queryset.filter(identificador__icontains=busqueda.strip())

        estado = params.get("estado")
        if estado == "ocupada":
            queryset = queryset.filter(paciente__isnull=False)
        elif estado == "disponible":
            queryset = queryset.filter(paciente__isnull=True, en_mantenimiento=False)
        elif estado == "mantenimiento":
            queryset = queryset.filter(paciente__isnull=True, en_mantenimiento=True)

        en_mantenimiento = params.get("en_mantenimiento")
        if en_mantenimiento is not None:
            queryset = queryset.filter(
                en_mantenimiento=en_mantenimiento.lower() in {"1", "true", "si", "sí"}
            )

        return queryset

    @action(detail=True, methods=["post"], url_path="asignar")
    def asignar(self, request, pk=None):
        """
        Asigna un paciente a esta cuna.

        Precondiciones
        --------------
        - ``paciente`` (o ``paciente_id``) en el cuerpo, apuntando a un bebé
          existente y activo.
        - La cuna debe estar libre.
        - El bebé no debe ocupar otra cuna.

        Postcondiciones
        ---------------
        - ``Cuna.paciente`` apunta al bebé.
        - Se registra la acción en la bitácora.

        Errores
        -------
        - HTTP 400 si faltan datos, la cuna está ocupada o el bebé está de alta.
        - HTTP 404 si el bebé no existe.
        - HTTP 409 si el bebé ya ocupa otra cuna.
        """
        from operacion.auditoria import registrar_actividad
        from operacion.models import RegistroActividad

        cuna = self.get_object()
        paciente_id = request.data.get("paciente") or request.data.get("paciente_id")

        if not paciente_id:
            return Response(
                {"detail": "Debes indicar el paciente a asignar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bebe = get_object_or_404(Bebe, pk=paciente_id)

        if not bebe.activo:
            return Response(
                {"detail": "El paciente tiene el alta registrada y no puede ocupar una cuna."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cuna.paciente_id:
            return Response(
                {"detail": f"La cuna {cuna.identificador} ya está ocupada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cuna.en_mantenimiento:
            return Response(
                {"detail": f"La cuna {cuna.identificador} está en mantenimiento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cuna_actual = bebe.cuna_asignada
        except Cuna.DoesNotExist:
            cuna_actual = None

        if cuna_actual is not None:
            return Response(
                {
                    "detail": (
                        f"El paciente {bebe.nombre_completo} ya ocupa la cuna "
                        f"{cuna_actual.identificador}. Libérala antes de asignarlo."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            cuna.paciente = bebe
            cuna._omitir_auditoria = True
            cuna.save(update_fields=["paciente", "ultima_actualizacion"])

            registrar_actividad(
                RegistroActividad.ACCION_ASIGNAR,
                cuna,
                descripcion=(
                    f"{bebe.nombre_completo} ({bebe.identificador}) asignado a "
                    f"la cuna {cuna.identificador}"
                ),
                request=request,
            )

        logger.info(
            "Paciente %s asignado a la cuna %s", bebe.identificador, cuna.identificador
        )
        return Response(self.get_serializer(cuna).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="liberar")
    def liberar(self, request, pk=None):
        """
        Libera la cuna y deja constancia en la bitácora.

        Es idempotente a nivel de negocio: si la cuna ya estaba libre
        responde HTTP 400 con un mensaje explicativo, porque liberar una
        cuna vacía suele ser un error de la interfaz.
        """
        from operacion.auditoria import registrar_actividad
        from operacion.models import RegistroActividad

        cuna = self.get_object()

        if not cuna.paciente_id:
            return Response(
                {"detail": f"La cuna {cuna.identificador} ya está libre."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bebe = cuna.paciente

        with transaction.atomic():
            cuna.paciente = None
            cuna._omitir_auditoria = True
            cuna.save(update_fields=["paciente", "ultima_actualizacion"])

            registrar_actividad(
                RegistroActividad.ACCION_LIBERAR,
                cuna,
                descripcion=(
                    f"Cuna {cuna.identificador} liberada "
                    f"(paciente previo: {bebe.nombre_completo})"
                ),
                metadata={"paciente_id": bebe.pk, "paciente": bebe.identificador},
                request=request,
            )

        return Response(self.get_serializer(cuna).data, status=status.HTTP_200_OK)

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
            # La telemetría se actualiza cada pocos segundos: no debe
            # generar una fila de auditoría por cada muestra.
            cuna._omitir_auditoria = True
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
    queryset = (
        Medicamento.objects.select_related("paciente")
        .all()
        .order_by("hora")
    )
    serializer_class = MedicamentoSerializer

    def get_queryset(self):
        """Filtros por paciente, estado, vía y texto del nombre."""
        queryset = super().get_queryset()
        params = self.request.query_params

        paciente = params.get("paciente") or params.get("paciente_id")
        if paciente:
            queryset = queryset.filter(paciente_id=paciente)

        estado = params.get("estado")
        if estado:
            queryset = queryset.filter(estado__iexact=estado.strip())

        via = params.get("via")
        if via:
            queryset = queryset.filter(via__iexact=via.strip())

        busqueda = params.get("search")
        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda.strip())
                | Q(paciente__nombre_completo__icontains=busqueda.strip())
            )

        return queryset

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

    queryset = PlanCuidado.objects.select_related("bebe").all().order_by("bebe_id", "area_cuidado")
    serializer_class = PlanCuidadoSerializer

    def get_queryset(self):
        """Filtros por paciente, estado y texto del área o intervención."""
        queryset = super().get_queryset()
        params = self.request.query_params

        bebe = params.get("bebe") or params.get("paciente")
        if bebe:
            queryset = queryset.filter(bebe_id=bebe)

        estado = params.get("estado")
        if estado:
            queryset = queryset.filter(estado__iexact=estado.strip())

        busqueda = params.get("search")
        if busqueda:
            queryset = queryset.filter(
                Q(area_cuidado__icontains=busqueda.strip())
                | Q(intervencion__icontains=busqueda.strip())
                | Q(bebe__nombre_completo__icontains=busqueda.strip())
            )

        return queryset


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

    def get_queryset(self):
        """
        Permite buscar por nombre o principio activo y filtrar stock bajo.

        ``?stock_bajo=true`` devuelve los productos con 5 unidades o menos,
        alineado con el umbral ``UMBRAL_STOCK_CRITICO`` de ``operacion``.
        """
        from operacion.reportes import UMBRAL_STOCK_CRITICO

        queryset = super().get_queryset()

        busqueda = self.request.query_params.get("search")
        if busqueda:
            texto = busqueda.strip()
            queryset = queryset.filter(
                Q(nombre__icontains=texto) | Q(principio_activo__icontains=texto)
            )

        stock_bajo = self.request.query_params.get("stock_bajo")
        if stock_bajo is not None and stock_bajo.lower() in {"1", "true", "si", "sí"}:
            queryset = queryset.filter(stock__lte=UMBRAL_STOCK_CRITICO)

        return queryset