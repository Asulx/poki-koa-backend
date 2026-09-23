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

from cunas.alertas import evaluar_signos_vitales
from cunas.models import Alerta, Bebe, Cuna, Medico


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

    def test_listar_alertas_activas_endpoint(self):
        """Verifica que el endpoint /api/alertas/activas/ solo devuelva alertas activas."""
        Alerta.objects.create(
            paciente=self.bebe,
            tipo="temperatura",
            mensaje="Alerta activa",
            nivel="Advertencia",
            activa=True,
        )
        Alerta.objects.create(
            paciente=self.bebe,
            tipo="spo2",
            mensaje="Alerta resuelta",
            nivel="Critica",
            activa=False,
        )
        url_activas = reverse("alerta-activas")
        res = self.client.get(url_activas)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["mensaje"], "Alerta activa")

    def test_resolver_alerta_endpoint(self):
        """Verifica que el endpoint POST /api/alertas/{id}/resolver/ desactive la alerta."""
        alerta = Alerta.objects.create(
            paciente=self.bebe,
            tipo="ritmo_cardiaco",
            mensaje="Bradicardia",
            nivel="Critica",
            activa=True,
        )
        url_resolver = reverse("alerta-resolver", args=[alerta.pk])
        res = self.client.post(url_resolver)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        alerta.refresh_from_db()
        self.assertFalse(alerta.activa)


class APITelemetriaCunaTestCase(TestCase):
    """Pruebas para el endpoint POST /api/cunas/{id}/telemetria/."""

    def setUp(self):
        self.client = APIClient()
        self.bebe = Bebe.objects.create(
            nombre_completo="Camila Valenzuela", edad_meses=1, sexo="F"
        )
        self.cuna = Cuna.objects.create(
            identificador="C-TEST",
            paciente=self.bebe,
            ritmo_cardiaco=125,
            spo2=98,
            temperatura=36.7,
            canula_ok=True,
        )
        self.url = reverse("cuna-telemetria", args=[self.cuna.pk])

    def test_telemetria_con_valores_anomalos_genera_alertas(self):
        payload = {
            "ritmo_cardiaco": 72,
            "spo2": 88,
            "temperatura": 39.0,
            "canula_ok": False,
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["alertas_activas"]), 4)
        self.cuna.refresh_from_db()
        self.assertEqual(self.cuna.ritmo_cardiaco, 72)
        self.assertEqual(self.cuna.spo2, 88)
        self.assertFalse(self.cuna.canula_ok)

    def test_telemetria_con_valores_normales_autorresuelve(self):
        # Primero inyectar alerta
        self.client.post(self.url, {"ritmo_cardiaco": 70}, format="json")
        self.assertEqual(Alerta.objects.filter(cuna=self.cuna, activa=True).count(), 1)

        # Ahora enviar ritmo cardíaco normal
        res = self.client.post(self.url, {"ritmo_cardiaco": 130}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["alertas_activas"]), 0)
        self.assertEqual(Alerta.objects.filter(cuna=self.cuna, activa=True).count(), 0)


class EvaluacionSignosVitalesTestCase(TestCase):
    """Pruebas unitarias para la función pura de evaluación de umbrales clínicos neonatales."""

    def test_signos_vitales_normales_no_generan_alertas(self):
        anomalias = evaluar_signos_vitales(
            ritmo_cardiaco=130, spo2=98, temperatura=36.8, canula_ok=True
        )
        self.assertEqual(len(anomalias), 0)

    def test_bradicardia_critica(self):
        anomalias = evaluar_signos_vitales(ritmo_cardiaco=75)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "ritmo_cardiaco")
        self.assertEqual(anomalias[0]["nivel"], "Critica")
        self.assertIn("Bradicardia severa", anomalias[0]["mensaje"])

    def test_bradicardia_moderada(self):
        anomalias = evaluar_signos_vitales(ritmo_cardiaco=92)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "ritmo_cardiaco")
        self.assertEqual(anomalias[0]["nivel"], "Advertencia")
        self.assertIn("Bradicardia moderada", anomalias[0]["mensaje"])

    def test_taquicardia_moderada(self):
        anomalias = evaluar_signos_vitales(ritmo_cardiaco=170)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "ritmo_cardiaco")
        self.assertEqual(anomalias[0]["nivel"], "Advertencia")
        self.assertIn("Taquicardia moderada", anomalias[0]["mensaje"])

    def test_taquicardia_critica(self):
        anomalias = evaluar_signos_vitales(ritmo_cardiaco=195)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "ritmo_cardiaco")
        self.assertEqual(anomalias[0]["nivel"], "Critica")
        self.assertIn("Taquicardia severa", anomalias[0]["mensaje"])

    def test_desaturacion_critica(self):
        anomalias = evaluar_signos_vitales(spo2=86)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "spo2")
        self.assertEqual(anomalias[0]["nivel"], "Critica")
        self.assertIn("Desaturación de oxígeno crítica", anomalias[0]["mensaje"])

    def test_hipoxemia_moderada(self):
        anomalias = evaluar_signos_vitales(spo2=92)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "spo2")
        self.assertEqual(anomalias[0]["nivel"], "Advertencia")
        self.assertIn("Saturación de oxígeno baja", anomalias[0]["mensaje"])

    def test_hipotermia_critica(self):
        anomalias = evaluar_signos_vitales(temperatura=35.5)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "temperatura")
        self.assertEqual(anomalias[0]["nivel"], "Critica")
        self.assertIn("Hipotermia severa", anomalias[0]["mensaje"])

    def test_hipotermia_moderada(self):
        anomalias = evaluar_signos_vitales(temperatura=36.2)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "temperatura")
        self.assertEqual(anomalias[0]["nivel"], "Advertencia")
        self.assertIn("Hipotermia leve", anomalias[0]["mensaje"])

    def test_fiebre_advertencia(self):
        anomalias = evaluar_signos_vitales(temperatura=38.0)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "temperatura")
        self.assertEqual(anomalias[0]["nivel"], "Advertencia")
        self.assertIn("Fiebre detectada", anomalias[0]["mensaje"])

    def test_hipertermia_critica(self):
        anomalias = evaluar_signos_vitales(temperatura=39.2)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "temperatura")
        self.assertEqual(anomalias[0]["nivel"], "Critica")
        self.assertIn("Hipertermia crítica", anomalias[0]["mensaje"])

    def test_canula_desconectada_critica(self):
        anomalias = evaluar_signos_vitales(canula_ok=False)
        self.assertEqual(len(anomalias), 1)
        self.assertEqual(anomalias[0]["tipo"], "canula")
        self.assertEqual(anomalias[0]["nivel"], "Critica")
        self.assertIn("Desconexión de cánula", anomalias[0]["mensaje"])


class MotorAlertasIntegrationTestCase(TestCase):
    """Pruebas de integración del motor de alertas activado por cambios en el modelo Cuna."""

    def setUp(self):
        self.medico = Medico.objects.create(nombre_completo="Dra. Vega", turno="Mañana")
        self.bebe = Bebe.objects.create(
            nombre_completo="Ignacio Morales",
            edad_meses=1,
            sexo="M",
            medico_a_cargo=self.medico,
        )
        self.cuna = Cuna.objects.create(
            identificador="C-10",
            paciente=self.bebe,
            ritmo_cardiaco=120,
            spo2=98,
            temperatura=36.7,
            canula_ok=True,
        )

    def test_actualizacion_cuna_crea_alerta_automaticamente(self):
        # Al actualizar el ritmo cardíaco a valor crítico, se genera la alerta vía señal
        self.cuna.ritmo_cardiaco = 72
        self.cuna.save()

        alertas = Alerta.objects.filter(cuna=self.cuna, activa=True)
        self.assertEqual(alertas.count(), 1)
        alerta = alertas.first()
        self.assertEqual(alerta.tipo, "ritmo_cardiaco")
        self.assertEqual(alerta.nivel, "Critica")
        self.assertEqual(alerta.paciente, self.bebe)
        self.assertEqual(alerta.valor_leido, 72.0)

    def test_normalizacion_de_signos_autorresuelve_alerta(self):
        # 1. Disparar alerta de fiebre
        self.cuna.temperatura = 38.2
        self.cuna.save()
        self.assertEqual(
            Alerta.objects.filter(cuna=self.cuna, tipo="temperatura", activa=True).count(),
            1,
        )

        # 2. Normalizar temperatura
        self.cuna.temperatura = 36.8
        self.cuna.save()

        # Debe marcarse como no activa
        self.assertEqual(
            Alerta.objects.filter(cuna=self.cuna, tipo="temperatura", activa=True).count(),
            0,
        )
        alerta_resuelta = Alerta.objects.filter(
            cuna=self.cuna, tipo="temperatura"
        ).first()
        self.assertFalse(alerta_resuelta.activa)

    def test_deduplicacion_evita_spam(self):
        # Enviar dos veces el mismo signo anómalo
        self.cuna.spo2 = 87
        self.cuna.save()
        self.cuna.save()

        alertas_spo2 = Alerta.objects.filter(cuna=self.cuna, tipo="spo2", activa=True)
        self.assertEqual(alertas_spo2.count(), 1)
