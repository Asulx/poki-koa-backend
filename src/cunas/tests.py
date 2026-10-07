"""
Pruebas unitarias para los modelos, la API REST y los contratos de la aplicación 'cunas'.

Incluye:
- CunasModelsTestCase: verifica el comportamiento de los modelos (str, relaciones, nuevos campos).
- APIBebeValidacionTestCase: verifica las validaciones y respuestas del endpoint POST /api/bebes/.
- APIAlertaTestCase: verifica el endpoint /api/alertas/ generado con make-crud.
- CunaServiceContractTestCase: verifica el contrato de la Operación 1 (1 caso válido y 2 inválidos).
"""

from unittest.mock import Mock
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from cunas.models import Alerta, Bebe, Cuna, Medico
from cunas.services import CunaService


class CunasModelsTestCase(TestCase):
    """Suite de pruebas para los modelos del sistema de monitoreo de cunas."""

    def setUp(self):
        """Crea los objetos de prueba que se reutilizan en cada test."""
        self.medico = Medico.objects.create(
            nombre_completo="Dra. María López", turno="Mañana"
        )

        self.bebe = Bebe.objects.create(
            nombre_completo="Sofía García",
            edad_meses=3,
            sexo="F",
            medico_a_cargo=self.medico,
            diagnostico="Dificultad respiratoria leve",
            plan_cuidados="Monitoreo continuo de SPO2",
        )

        self.cuna = Cuna.objects.create(
            identificador="Cuna 01",
            paciente=self.bebe,
            ritmo_cardiaco=120,
            spo2=98,
            temperatura=36.7,
            estado_sueno="Dormido",
        )

        self.alerta = Alerta.objects.create(
            paciente=self.bebe,
            tipo="spo2",
            mensaje="Saturación por debajo de 90%",
            nivel="Critica",
        )

    def test_representacion_texto_modelos(self):
        """Verifica que __str__ retorne el texto esperado para cada modelo."""
        self.assertEqual(str(self.medico), "Dra. María López")
        self.assertEqual(str(self.bebe), "Sofía García")
        self.assertEqual(str(self.cuna), "Cuna 01 - Sofía García")
        self.assertIn("Sofía García", str(self.alerta))
        self.assertIn("Critica", str(self.alerta))

    def test_cuna_vacia_muestra_vacia(self):
        """Verifica que una cuna sin bebé asignado se represente como 'Vacía'."""
        cuna_vacia = Cuna.objects.create(identificador="Cuna 02")
        self.assertEqual(str(cuna_vacia), "Cuna 02 - Vacía")

    def test_nuevos_campos_bebe_y_cuna(self):
        """Verifica que los nuevos campos requeridos almacenen datos correctamente."""
        self.assertEqual(self.bebe.diagnostico, "Dificultad respiratoria leve")
        self.assertEqual(self.bebe.plan_cuidados, "Monitoreo continuo de SPO2")
        self.assertEqual(self.cuna.temperatura, 36.7)


class APIBebeValidacionTestCase(TestCase):
    """
    Pruebas de integración para el endpoint /api/bebes/.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("bebe-list")

        self.medico = Medico.objects.create(
            nombre_completo="Dr. Juan Pérez", turno="Tarde"
        )

        self.payload_valido = {
            "nombre_completo": "Mateo Rodríguez",
            "edad_meses": 1,
            "sexo": "M",
            "peso": 3.5,
            "fecha_nacimiento": "2026-08-01",
            "diagnostico": "Observación",
            "plan_cuidados": "Control de temperatura cada 4h",
            "medico_a_cargo": self.medico.pk,
        }

    def test_peso_negativo_retorna_400(self):
        payload = {**self.payload_valido, "peso": -1.0}
        respuesta = self.client.post(self.url, payload, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("peso", respuesta.data)
        self.assertIn("El peso debe ser mayor a 0.", str(respuesta.data["peso"]))

    def test_peso_cero_retorna_400(self):
        payload = {**self.payload_valido, "peso": 0}
        respuesta = self.client.post(self.url, payload, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("peso", respuesta.data)

    def test_fecha_nacimiento_futura_retorna_400(self):
        fecha_futura = (timezone.now().date() + timezone.timedelta(days=1)).isoformat()
        payload = {**self.payload_valido, "fecha_nacimiento": fecha_futura}
        respuesta = self.client.post(self.url, payload, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_nacimiento", respuesta.data)

    def test_bebe_valido_se_crea_correctamente(self):
        respuesta = self.client.post(self.url, self.payload_valido, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bebe.objects.count(), 1)
        self.assertEqual(respuesta.data["nombre_completo"], "Mateo Rodríguez")
        self.assertEqual(respuesta.data["diagnostico"], "Observación")
        self.assertEqual(float(respuesta.data["peso"]), 3.5)


class APIAlertaTestCase(TestCase):
    """Pruebas para el endpoint CRUD /api/alertas/ generado con make-crud."""

    def setUp(self):
        self.client = APIClient()
        self.bebe = Bebe.objects.create(
            nombre_completo="Lucas Silva", edad_meses=2, sexo="M"
        )
        self.url = reverse("alerta-list")

    def test_crear_y_listar_alerta(self):
        payload = {
            "paciente": self.bebe.pk,
            "tipo": "temperatura",
            "mensaje": "Fiebre detectada (38.5 °C)",
            "nivel": "Advertencia",
        }
        res_post = self.client.post(self.url, payload, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)

        res_get = self.client.get(self.url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_get.data), 1)
        self.assertEqual(res_get.data[0]["mensaje"], "Fiebre detectada (38.5 °C)")
        self.assertEqual(res_get.data[0]["paciente_nombre"], "Lucas Silva")


class CunaServiceContractTestCase(TestCase):
    """
    Pruebas de verificación de contrato para CunaService (Unidad 2.2).
    Comprueba el cumplimiento de precondiciones, postcondiciones,
    invariantes y la capacidad de sustituir dependencias.
    """

    def test_caso_valido_actualizacion_exitosa(self):
        """
        Caso Válido: telemetría dentro de rangos normales actualiza la cuna
        y preserva las invariantes del objeto.
        """
        mock_model = Mock()
        mock_cuna = Mock(
            id=1,
            identificador="Cuna 01",
            ritmo_cardiaco=120,
            spo2=95,
            temperatura=36.5,
        )
        mock_model.objects.get.return_value = mock_cuna

        service = CunaService(cuna_model=mock_model)
        resultado = service.actualizar_telemetria(
            cuna_id="Cuna 01",
            ritmo_cardiaco=135,
            spo2=98,
            temperatura=36.8,
        )

        self.assertEqual(resultado.ritmo_cardiaco, 135)
        self.assertEqual(resultado.spo2, 98)
        self.assertEqual(resultado.temperatura, 36.8)
        mock_model.objects.get.assert_called_once_with(identificador="Cuna 01")
        mock_cuna.save.assert_called_once()

    def test_caso_invalido_spo2_fuera_de_rango(self):
        """
        Caso Inválido 1: SpO2 mayor al límite biológico (100%) es rechazado en la frontera.
        """
        service = CunaService(cuna_model=Mock())

        with self.assertRaises(ValueError) as context:
            service.actualizar_telemetria(
                cuna_id="Cuna 01",
                ritmo_cardiaco=120,
                spo2=112,
                temperatura=36.6,
            )

        self.assertIn("SpO2 inválido", str(context.exception))

    def test_caso_invalido_cuna_id_vacio(self):
        """
        Caso Inválido 2: identificador de cuna vacío o en blanco es rechazado inmediatamente.
        """
        service = CunaService(cuna_model=Mock())

        with self.assertRaises(ValueError) as context:
            service.actualizar_telemetria(
                cuna_id="   ",
                ritmo_cardiaco=120,
                spo2=97,
                temperatura=36.6,
            )

        self.assertIn("cuna_id es obligatorio", str(context.exception))