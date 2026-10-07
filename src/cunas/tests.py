"""
Pruebas unitarias para los modelos y la API REST de la aplicación 'cunas'.

Incluye:
- CunasModelsTestCase: verifica el comportamiento de los modelos (str, relaciones, nuevos campos).
- APIBebeValidacionTestCase: verifica las validaciones y respuestas del endpoint POST /api/bebes/.
- APIAlertaTestCase: verifica el endpoint /api/alertas/ generado con make-crud.
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from cunas.models import Alerta, Bebe, Cuna, Medicamento, Medico


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


class APIAdministrarMedicamentoTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        bebe = Bebe.objects.create(nombre_completo="Ana", edad_meses=1, sexo="F")
        self.medicamento = Medicamento.objects.create(
            paciente=bebe, nombre="Vitamina K", dosis="1 mg", via="IM",
            hora="10:00", estado="Pendiente",
        )
        self.url = reverse("medicamento-administrar", args=[self.medicamento.pk])

    def test_administra_y_rechaza_repeticion(self):
        respuesta = self.client.post(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["estado"], "Administrado")
        self.medicamento.refresh_from_db()
        self.assertEqual(self.medicamento.estado, "Administrado")
        self.assertEqual(respuesta.data["paciente_id"], self.medicamento.paciente_id)
        respuesta = self.client.post(self.url)
        self.assertEqual(respuesta.status_code, 409)
        self.medicamento.refresh_from_db()
        self.assertEqual(self.medicamento.estado, "Administrado")

    def test_id_invalido(self):
        url = reverse("medicamento-administrar", args=["abc"])
        self.assertEqual(self.client.post(url).status_code, 400)
        self.medicamento.refresh_from_db()
        self.assertEqual(self.medicamento.estado, "Pendiente")

    def test_id_inexistente(self):
        url = reverse("medicamento-administrar", args=[self.medicamento.pk + 1])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.medicamento.refresh_from_db()
        self.assertEqual(self.medicamento.estado, "Pendiente")
