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
from .models import Medico, Bebe, Cuna, Medicamento, Alerta
from .serializers import (
    MedicoSerializer, 
    BebeSerializer, 
    CunaSerializer, 
    MedicamentoSerializer,
    AlertaSerializer
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





class AlertaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Alerta.
    Proporciona operaciones CRUD completas.
    """
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
