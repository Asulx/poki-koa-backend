"""
Pruebas unitarias para los modelos y la API REST de la aplicación 'cunas'.

Incluye:
- CunasModelsTestCase: verifica el comportamiento de los modelos (str, relaciones).
- APIBebeValidacionTestCase: verifica las validaciones del endpoint POST /api/bebes/,
  incluyendo peso inválido, fecha futura y el caso feliz (dato válido).

Ejecutar con:
    uv run mamoru test
"""

import datetime

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

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


class APIBebeValidacionTestCase(TestCase):
    """
    Pruebas de integración para el endpoint POST /api/bebes/.

    Verifica que las validaciones del BebeSerializer funcionen correctamente
    rechazando datos inválidos (400) y aceptando datos válidos (201).
    """

    def setUp(self):
        """Prepara el cliente API y el médico de referencia para los tests."""
        self.client = APIClient()
        self.url = reverse('bebe-list')

        # Médico necesario para asignar al bebé en los tests
        self.medico = Medico.objects.create(
            nombre_completo="Dr. Juan Pérez",
            turno="Tarde"
        )

        # Payload base con datos válidos que se reutiliza en cada test
        self.payload_valido = {
            "nombre_completo": "Mateo Rodríguez",
            "edad_meses": 1,
            "sexo": "M",
            "peso": 3.5,
            "fecha_nacimiento": "2026-08-01",
            "medico_a_cargo": self.medico.pk,
        }

    # ------------------------------------------------------------------
    # Casos de error esperados (deben devolver 400)
    # ------------------------------------------------------------------

    def test_peso_negativo_retorna_400(self):
        """Un peso negativo debe ser rechazado con HTTP 400."""
        payload = {**self.payload_valido, "peso": -1.0}
        respuesta = self.client.post(self.url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("peso", respuesta.data)
        self.assertIn("El peso debe ser mayor a 0.", str(respuesta.data["peso"]))

    def test_peso_cero_retorna_400(self):
        """Un peso igual a 0 debe ser rechazado con HTTP 400."""
        payload = {**self.payload_valido, "peso": 0}
        respuesta = self.client.post(self.url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("peso", respuesta.data)
        self.assertIn("El peso debe ser mayor a 0.", str(respuesta.data["peso"]))

    def test_fecha_nacimiento_futura_retorna_400(self):
        """Una fecha de nacimiento futura debe ser rechazada con HTTP 400."""
        fecha_futura = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        payload = {**self.payload_valido, "fecha_nacimiento": fecha_futura}
        respuesta = self.client.post(self.url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_nacimiento", respuesta.data)
        self.assertIn(
            "La fecha de nacimiento no puede ser una fecha futura.",
            str(respuesta.data["fecha_nacimiento"])
        )

    # ------------------------------------------------------------------
    # Caso feliz: datos válidos deben seguir funcionando (201)
    # ------------------------------------------------------------------

    def test_bebe_valido_se_crea_correctamente(self):
        """Un POST con datos válidos debe crear el bebé y devolver HTTP 201."""
        respuesta = self.client.post(self.url, self.payload_valido, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bebe.objects.count(), 1)
        self.assertEqual(respuesta.data["nombre_completo"], "Mateo Rodríguez")
        self.assertEqual(float(respuesta.data["peso"]), 3.5)

    def test_bebe_sin_peso_ni_fecha_se_crea_correctamente(self):
        """
        Los campos peso y fecha_nacimiento son opcionales.
        Un POST sin ellos debe seguir creando el bebé con HTTP 201.
        """
        payload = {
            "nombre_completo": "Ana Torres",
            "edad_meses": 2,
            "sexo": "F",
            "medico_a_cargo": self.medico.pk,
        }
        respuesta = self.client.post(self.url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(respuesta.data["peso"])
        self.assertIsNone(respuesta.data["fecha_nacimiento"])
