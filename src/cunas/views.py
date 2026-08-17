"""
Vistas (controladores) de la API REST para la aplicación 'cunas'.

Cada ViewSet expone automáticamente los endpoints CRUD completos
para su modelo correspondiente gracias a Django REST Framework:

    GET    /api/medicos/         → lista todos los médicos
    POST   /api/medicos/         → crea un nuevo médico
    GET    /api/medicos/{id}/    → detalle de un médico
    PUT    /api/medicos/{id}/    → actualiza un médico
    DELETE /api/medicos/{id}/    → elimina un médico

(Las mismas operaciones aplican para /api/bebes/ y /api/cunas/)
"""

from rest_framework import viewsets
from .models import Medico, Bebe, Cuna
from .serializers import MedicoSerializer, BebeSerializer, CunaSerializer


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