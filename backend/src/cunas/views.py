from rest_framework import viewsets
from .models import Medico, Bebe, Cuna
from .serializers import MedicoSerializer, BebeSerializer, CunaSerializer

class MedicoViewSet(viewsets.ModelViewSet):
    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer

class BebeViewSet(viewsets.ModelViewSet):
    queryset = Bebe.objects.all()
    serializer_class = BebeSerializer

class CunaViewSet(viewsets.ModelViewSet):
    queryset = Cuna.objects.all()
    serializer_class = CunaSerializer