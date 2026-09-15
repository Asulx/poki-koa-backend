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

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import (
    Alerta,
    Apoderado,
    AsignacionTurno,
    Bebe,
    Cuna,
    Medicamento,
    Medico,
    PlanCuidado,
    Turno,
)
from .serializers import (
    AlertaSerializer,
    ApoderadoSerializer,
    AsignacionTurnoSerializer,
    BebeSerializer,
    CunaSerializer,
    MedicamentoSerializer,
    MedicoSerializer,
    PlanCuidadoSerializer,
    TurnoSerializer,
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
    Proporciona operaciones CRUD completas sobre los pacientes (bebés) y
    aplica filtros de privacidad según el rol del solicitante.
    """

    queryset = Bebe.objects.all()
    serializer_class = BebeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.request
        rol = (
            request.query_params.get("rol")
            or request.headers.get("X-User-Role")
            or ""
        ).strip().lower()

        if rol in ["apoderado", "tutor", "padre", "madre", "familia"]:
            apoderado_id = (
                request.query_params.get("apoderado_id")
                or request.headers.get("X-Apoderado-Id")
            )
            rut = (
                request.query_params.get("rut")
                or request.headers.get("X-Apoderado-Rut")
            )
            apoderado_qs = Apoderado.objects.select_related("bebe")
            if apoderado_id:
                apoderado = apoderado_qs.filter(id=apoderado_id).first()
            elif rut:
                apoderado = apoderado_qs.filter(rut=rut).first()
            else:
                return queryset.none()

            if not apoderado or not apoderado.bebe.matriculado:
                return queryset.none()

            return queryset.filter(id=apoderado.bebe_id)

        return queryset


class CunaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Cuna.
    Proporciona operaciones CRUD y filtrado de visibilidad institucional según rol:
    - Directora: Visibilidad completa sobre la totalidad de cunas de la unidad (40 cunas).
    - Personal Clínico / Matronas en turno: Ve el subconjunto de cunas asignado a su turno rotativo.
    - Apoderado: Ve una sola cuna (la de su hijo) y solo mientras mantenga matrícula activa.
    """

    queryset = Cuna.objects.all().order_by("identificador")
    serializer_class = CunaSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.request

        rol = (
            request.query_params.get("rol")
            or request.headers.get("X-User-Role")
            or ""
        ).strip().lower()

        if not rol:
            return queryset

        # 1. Rol Directora / Administrador: ve todo
        if rol in ["directora", "director", "admin", "administrador"]:
            return queryset

        # 2. Rol Personal Clínico / Matronas / Médicos: subconjunto de cunas según turno
        if rol in ["medico", "doctor", "matrona", "enfermera", "educadora", "personal"]:
            medico_id = (
                request.query_params.get("medico_id")
                or request.headers.get("X-Medico-Id")
            )
            turno = (
                request.query_params.get("turno")
                or request.query_params.get("turno_id")
                or request.headers.get("X-Turno")
            )

            asignaciones = AsignacionTurno.objects.filter(activo=True)
            if medico_id:
                asignaciones = asignaciones.filter(medico_id=medico_id)
            if turno:
                if str(turno).isdigit():
                    asignaciones = asignaciones.filter(turno_id=int(turno))
                else:
                    asignaciones = asignaciones.filter(turno__nombre__iexact=str(turno))

            return queryset.filter(asignaciones_turno__in=asignaciones).distinct()

        # 3. Rol Apoderado: ve solo la cuna de su hijo y únicamente si está matriculado
        if rol in ["apoderado", "tutor", "padre", "madre", "familia"]:
            apoderado_id = (
                request.query_params.get("apoderado_id")
                or request.headers.get("X-Apoderado-Id")
            )
            rut = (
                request.query_params.get("rut")
                or request.headers.get("X-Apoderado-Rut")
            )

            apoderado_qs = Apoderado.objects.select_related("bebe")
            if apoderado_id:
                apoderado = apoderado_qs.filter(id=apoderado_id).first()
            elif rut:
                apoderado = apoderado_qs.filter(rut=rut).first()
            else:
                return queryset.none()

            if not apoderado:
                return queryset.none()

            # Restricción: solo mientras su hijo esté matriculado
            if not apoderado.bebe.matriculado:
                return queryset.none()

            return queryset.filter(paciente=apoderado.bebe)

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """
        Control de acceso a nivel de detalle (/api/cunas/{id}/).
        Asegura que apoderados y personal clínico respeten los límites de acceso.
        """
        instance = self.get_object()
        rol = (
            request.query_params.get("rol")
            or request.headers.get("X-User-Role")
            or ""
        ).strip().lower()

        if rol in ["apoderado", "tutor", "padre", "madre", "familia"]:
            apoderado_id = (
                request.query_params.get("apoderado_id")
                or request.headers.get("X-Apoderado-Id")
            )
            rut = (
                request.query_params.get("rut")
                or request.headers.get("X-Apoderado-Rut")
            )
            apoderado_qs = Apoderado.objects.select_related("bebe")
            if apoderado_id:
                apoderado = apoderado_qs.filter(id=apoderado_id).first()
            elif rut:
                apoderado = apoderado_qs.filter(rut=rut).first()
            else:
                raise PermissionDenied("Debe identificar al apoderado para consultar el detalle de la cuna.")

            if not apoderado:
                raise PermissionDenied("Apoderado no encontrado en el sistema.")

            if not apoderado.bebe.matriculado:
                raise PermissionDenied(
                    "El apoderado no tiene acceso a la cuna porque el paciente no cuenta con matrícula activa."
                )

            if not instance.paciente or instance.paciente_id != apoderado.bebe_id:
                raise PermissionDenied(
                    "Acceso restringido: El apoderado solo puede visualizar la cuna asignada a su propio hijo."
                )

        elif rol in ["medico", "doctor", "matrona", "enfermera", "educadora", "personal"]:
            medico_id = (
                request.query_params.get("medico_id")
                or request.headers.get("X-Medico-Id")
            )
            if medico_id:
                cunas_asignadas_ids = Cuna.objects.filter(
                    asignaciones_turno__medico_id=medico_id,
                    asignaciones_turno__activo=True,
                ).values_list("id", flat=True)
                if instance.id not in cunas_asignadas_ids:
                    raise PermissionDenied(
                        "Acceso restringido: Esta cuna no forma parte del subconjunto asignado a su turno."
                    )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


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
    Proporciona operaciones CRUD completas.
    """

    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer


class TurnoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Turno.
    Proporciona operaciones CRUD sobre los turnos de trabajo rotativos.
    """

    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer


class AsignacionTurnoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo AsignacionTurno.
    Permite gestionar y consultar la asignación rotativa de subconjuntos de cunas
    a cada profesional según el turno.
    """

    queryset = AsignacionTurno.objects.all()
    serializer_class = AsignacionTurnoSerializer


class ApoderadoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Apoderado.
    Permite gestionar el registro de apoderados y sus vínculos con pacientes.
    """

    queryset = Apoderado.objects.all()
    serializer_class = ApoderadoSerializer

