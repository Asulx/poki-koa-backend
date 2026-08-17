"""
Pruebas unitarias para los modelos de la aplicación 'cunas'.

Verifica el comportamiento básico de los modelos Medico, Bebe y Cuna,
incluyendo sus relaciones y representaciones en texto.

Ejecutar con:
    uv run mamoru test
"""

from django.test import TestCase
from cunas.models import Medico, Bebe, Cuna


class CunasModelsTestCase(TestCase):
    """Suite de pruebas para los modelos del sistema de monitoreo de cunas."""

    def setUp(self):
        """Crea los objetos de prueba que se reutilizan en cada test."""
        # Crea un médico de prueba
        self.medico = Medico.objects.create(
            nombre_completo="Dra. María López",
            turno="Mañana"
        )

        # Crea un bebé asignado al médico anterior
        self.bebe = Bebe.objects.create(
            nombre_completo="Sofía García",
            edad_meses=3,
            sexo="F",
            medico_a_cargo=self.medico
        )

        # Crea una cuna con el bebé asignado y signos vitales de prueba
        self.cuna = Cuna.objects.create(
            identificador="Cuna 01",
            paciente=self.bebe,
            ritmo_cardiaco=120,
            spo2=98,
            estado_sueno="Dormido"
        )

    def test_representacion_texto_modelos(self):
        """Verifica que __str__ retorne el texto esperado para cada modelo."""
        self.assertEqual(str(self.medico), "Dra. María López")
        self.assertEqual(str(self.bebe), "Sofía García")
        self.assertEqual(str(self.cuna), "Cuna 01 - Sofía García")

    def test_cuna_vacia_muestra_vacia(self):
        """Verifica que una cuna sin bebé asignado se represente como 'Vacía'."""
        cuna_vacia = Cuna.objects.create(identificador="Cuna 02")
        self.assertEqual(str(cuna_vacia), "Cuna 02 - Vacía")
