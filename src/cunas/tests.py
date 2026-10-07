"""
Pruebas unitarias para los modelos, la API REST y los contratos de la aplicación 'cunas'.

Incluye:
- CunasModelsTestCase: verifica el comportamiento de los modelos (str, relaciones, nuevos campos).
- APIBebeValidacionTestCase: verifica las validaciones y respuestas del endpoint POST /api/bebes/.
- APIAlertaTestCase: verifica el endpoint /api/alertas/ generado con make-crud.
- APITelemetriaCunaTestCase: verifica la actualización de telemetría y emisión de alertas.
- EvaluacionSignosVitalesTestCase: comprueba la función pura de evaluación médica neonatal.
- MotorAlertasIntegrationTestCase: comprueba la deduplicación y autorresolución de alertas.
- CunaServiceContractTestCase: verifica el contrato de la Operación 1 (1 caso válido y 2 inválidos).
"""

from unittest.mock import Mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from cunas.alertas import evaluar_signos_vitales
from cunas.models import Alerta, Bebe, Cuna, Medicamento, Medico
from cunas.services import CunaService


class CunasModelsTestCase(TestCase):
    """Suite de pruebas para los modelos del sistema de monitoreo de cunas."""

    def setUp(self):
        """Crea los objetos de prueba que se reutilizan en cada test."""
        self.medico = Medico.objects.create(
            nombre_completo="Dra. María López", turno="Mañana"
        )

        self.bebe = Bebe.objects.create(
            identificador="BEBE-000",
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
            "identificador": "BEBE-001",
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

    def test_contrato_respuesta_listado_bebes_para_frontend(self):
        """Verifica que GET /api/bebes/ entregue todos los campos requeridos por el frontend (Issue #14)."""
        bebe = Bebe.objects.create(
            identificador="BEBE-002",
            nombre_completo="Lucas Silva",
            edad_meses=2,
            edad_gestacional=34.5,
            sexo="M",
            peso=2.8,
            fecha_nacimiento="2026-07-15",
            diagnostico="Dificultad respiratoria leve",
            observaciones="Paciente en fototerapia",
            medico_a_cargo=self.medico,
        )
        Cuna.objects.create(
            identificador="C05",
            paciente=bebe,
            ritmo_cardiaco=135,
            spo2=97,
            temperatura=36.8,
            canula_ok=True,
            via_iv_activa=True,
        )

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data) >= 1)

        datos = next(item for item in res.data if item["id"] == bebe.id)
        # Campos del paciente requeridos por el frontend
        self.assertIn("id", datos)
        self.assertIn("identificador", datos)
        self.assertEqual(datos["identificador"], bebe.identificador)
        self.assertEqual(datos["nombre"], "Lucas Silva")
        self.assertEqual(datos["nombre_completo"], "Lucas Silva")
        self.assertEqual(datos["sexo"], "M")
        self.assertEqual(float(datos["edad_gestacional"]), 34.5)
        self.assertEqual(float(datos["peso"]), 2.8)
        self.assertEqual(datos["fecha_nacimiento"], "2026-07-15")
        self.assertIn("fecha_ingreso", datos)
        self.assertEqual(datos["diagnostico"], "Dificultad respiratoria leve")
        self.assertEqual(datos["observaciones"], "Paciente en fototerapia")

        # Datos relacionados de médico y cuna
        self.assertEqual(datos["medico_responsable"], "Dr. Juan Pérez")
        self.assertEqual(datos["medico_nombre"], "Dr. Juan Pérez")
        self.assertEqual(datos["cuna"], "C05")
        self.assertEqual(datos["numero_cuna"], "C05")
        self.assertEqual(datos["cuna_identificador"], "C05")
        self.assertEqual(datos["estado_canula"], True)
        self.assertEqual(datos["canula_ok"], True)
        self.assertEqual(datos["via_intravenosa"], True)
        self.assertEqual(datos["via_iv_activa"], True)

    def test_busqueda_y_filtros_bebes(self):
        """Verifica búsqueda por texto (nombre e identificador) y combinación con filtros."""
        b1 = Bebe.objects.create(
            identificador="BEBE-SOFIA",
            nombre_completo="Sofía García",
            edad_meses=1,
            sexo="F",
            fecha_ingreso="2026-09-10T10:00:00Z",
            medico_a_cargo=self.medico,
        )
        b2 = Bebe.objects.create(
            identificador="BEBE-MATEO",
            nombre_completo="Mateo Rodríguez",
            edad_meses=2,
            sexo="M",
            fecha_ingreso="2026-09-15T12:00:00Z",
        )

        # Búsqueda por nombre
        res_search_nombre = self.client.get(f"{self.url}?search=Sofía")
        self.assertEqual(len(res_search_nombre.data), 1)
        self.assertEqual(res_search_nombre.data[0]["id"], b1.id)

        # Búsqueda por identificador
        res_search_id = self.client.get(f"{self.url}?search={b2.identificador}")
        self.assertEqual(len(res_search_id.data), 1)
        self.assertEqual(res_search_id.data[0]["id"], b2.id)

        # Filtro por sexo
        res_filtro_sexo = self.client.get(f"{self.url}?sexo=F")
        self.assertEqual(len(res_filtro_sexo.data), 1)
        self.assertEqual(res_filtro_sexo.data[0]["id"], b1.id)

        # Combinar búsqueda con filtro
        res_combinado = self.client.get(f"{self.url}?search=Mateo&sexo=M")
        self.assertEqual(len(res_combinado.data), 1)
        self.assertEqual(res_combinado.data[0]["id"], b2.id)

        # Búsqueda que no coincide
        res_vacio = self.client.get(f"{self.url}?search=Inexistente")
        self.assertEqual(len(res_vacio.data), 0)


class APIAlertaTestCase(TestCase):
    """Pruebas para el endpoint CRUD /api/alertas/ generado con make-crud."""

    def setUp(self):
        self.client = APIClient()
        self.bebe = Bebe.objects.create(
            identificador="BEBE-LUCAS",
            nombre_completo="Lucas Silva",
            edad_meses=2,
            sexo="M",
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
            identificador="BEBE-CAMILA",
            nombre_completo="Camila Valenzuela",
            edad_meses=1,
            sexo="F",
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
        self.client.post(self.url, {"ritmo_cardiaco": 70}, format="json")
        self.assertEqual(Alerta.objects.filter(cuna=self.cuna, activa=True).count(), 1)

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
            identificador="BEBE-IGNACIO",
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
        self.cuna.temperatura = 38.2
        self.cuna.save()
        self.assertEqual(
            Alerta.objects.filter(
                cuna=self.cuna, tipo="temperatura", activa=True
            ).count(),
            1,
        )

        self.cuna.temperatura = 36.8
        self.cuna.save()

        self.assertEqual(
            Alerta.objects.filter(
                cuna=self.cuna, tipo="temperatura", activa=True
            ).count(),
            0,
        )
        alerta_resuelta = Alerta.objects.filter(
            cuna=self.cuna, tipo="temperatura"
        ).first()
        self.assertFalse(alerta_resuelta.activa)

    def test_deduplicacion_evita_spam(self):
        self.cuna.spo2 = 87
        self.cuna.save()
        self.cuna.save()

        alertas_spo2 = Alerta.objects.filter(cuna=self.cuna, tipo="spo2", activa=True)
        self.assertEqual(alertas_spo2.count(), 1)


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
        resultado = service.actualizar_telemetria("Cuna 01", 130, 98, 36.8)

        self.assertEqual(resultado.spo2, 98)
        self.assertEqual(resultado.ritmo_cardiaco, 130)
        self.assertEqual(resultado.temperatura, 36.8)
        mock_cuna.save.assert_called_once()

    def test_caso_invalido_spo2_fuera_de_rango(self):
        """
        Caso Inválido 1: SpO2 superior al 100% debe ser rechazado en la frontera
        por violación de precondición biológica.
        """
        service = CunaService(cuna_model=Mock())
        with self.assertRaises(ValueError) as context:
            service.actualizar_telemetria("Cuna 01", 130, 110, 36.8)

        self.assertIn("SpO2 inválido", str(context.exception))

    def test_caso_invalido_cuna_id_vacio(self):
        """
        Caso Inválido 2: identificador de cuna vacío debe ser rechazado
        inmediatamente por validación defensiva.
        """
        service = CunaService(cuna_model=Mock())
        with self.assertRaises(ValueError) as context:
            service.actualizar_telemetria("", 130, 98, 36.8)

        self.assertIn("cuna_id es obligatorio", str(context.exception))


class APIAdministrarMedicamentoTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        bebe = Bebe.objects.create(
            identificador="BEBE-MEDICACION",
            nombre_completo="Ana",
            edad_meses=1,
            sexo="F",
        )
        self.medicamento = Medicamento.objects.create(
            paciente=bebe,
            nombre="Vitamina K",
            dosis="1 mg",
            via="IM",
            hora="10:00",
            estado="Pendiente",
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
