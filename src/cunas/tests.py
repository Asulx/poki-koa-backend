"""
Pruebas unitarias para los modelos y la API REST de la aplicación 'cunas'.

Incluye:
- CunasModelsTestCase: verifica el comportamiento de los modelos (str, relaciones, nuevos campos).
- APIBebeValidacionTestCase: verifica las validaciones y respuestas del endpoint POST /api/bebes/.
- APIAlertaTestCase: verifica el endpoint /api/alertas/ generado con make-crud.
"""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from cunas.models import (
    Alerta,
    Apoderado,
    AsignacionTurno,
    Bebe,
    Cuna,
    Medico,
    Turno,
)


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


class EscalaInstitucionalModelsTestCase(TestCase):
    """
    Pruebas unitarias para los modelos introducidos en la issue CR-402:
    Turno, AsignacionTurno y Apoderado, así como el campo matriculado en Bebe.
    """

    def setUp(self):
        self.turno = Turno.objects.create(nombre="Noche")
        self.medico = Medico.objects.create(nombre_completo="Matr. Francisca Morales", turno="Noche")
        self.bebe = Bebe.objects.create(
            nombre_completo="Agustín Tapia",
            edad_meses=1,
            sexo="M",
            matriculado=True,
        )
        self.cuna = Cuna.objects.create(identificador="C15", paciente=self.bebe)
        self.apoderado = Apoderado.objects.create(
            nombre_completo="Javiera Tapia",
            rut="18.999.888-7",
            bebe=self.bebe,
        )

    def test_representacion_modelos_escala(self):
        self.assertEqual(str(self.turno), "Noche")
        self.assertIn("Javiera Tapia", str(self.apoderado))
        self.assertIn("Agustín Tapia", str(self.apoderado))

    def test_asignacion_turno_con_subconjunto_cunas(self):
        asignacion = AsignacionTurno.objects.create(
            medico=self.medico,
            turno=self.turno,
            activo=True,
        )
        asignacion.cunas.add(self.cuna)
        self.assertEqual(asignacion.cunas.count(), 1)
        self.assertIn("Francisca Morales", str(asignacion))
        self.assertIn("Noche", str(asignacion))

    def test_bebe_matricula_defecto_true(self):
        self.assertTrue(self.bebe.matriculado)


class EscalaInstitucionalVisibilidadTestCase(TestCase):
    """
    Pruebas de integración para verificar la regla de negocio de CR-402:
    1. La directora ve la totalidad de las 40 cunas.
    2. El profesional en turno ve únicamente su subconjunto asignado de cunas.
    3. El apoderado ve solo la cuna de su hijo y únicamente si está matriculado.
    """

    def setUp(self):
        self.client = APIClient()
        self.url_cunas = reverse("cuna-list")

        # Crear Turnos
        self.turno_manana = Turno.objects.create(nombre="Mañana")
        self.turno_tarde = Turno.objects.create(nombre="Tarde")

        # Crear 40 cunas
        self.cunas = [
            Cuna.objects.create(identificador=f"C{i:02d}")
            for i in range(1, 41)
        ]

        # Crear profesional con asignación de 10 cunas en turno Mañana (C01 a C10)
        self.medico_manana = Medico.objects.create(nombre_completo="Dra. Lorena Soto", turno="Mañana")
        self.asig_manana = AsignacionTurno.objects.create(
            medico=self.medico_manana,
            turno=self.turno_manana,
            activo=True,
        )
        self.asig_manana.cunas.set(self.cunas[:10])

        # Bebé 1 en Cuna C01: matriculado=True
        self.bebe_matriculado = Bebe.objects.create(
            nombre_completo="Bebé Activo",
            edad_meses=2,
            sexo="F",
            matriculado=True,
        )
        self.cunas[0].paciente = self.bebe_matriculado
        self.cunas[0].save()

        # Apoderado 1: asociado a Bebé 1
        self.apoderado_activo = Apoderado.objects.create(
            nombre_completo="Rodrigo Activo",
            rut="12.345.678-9",
            bebe=self.bebe_matriculado,
        )

        # Bebé 2 en Cuna C02: matriculado=False
        self.bebe_egresado = Bebe.objects.create(
            nombre_completo="Bebé Egresado",
            edad_meses=4,
            sexo="M",
            matriculado=False,
        )
        self.cunas[1].paciente = self.bebe_egresado
        self.cunas[1].save()

        # Apoderado 2: asociado a Bebé 2
        self.apoderado_inactivo = Apoderado.objects.create(
            nombre_completo="Valeria Inactiva",
            rut="14.555.666-7",
            bebe=self.bebe_egresado,
        )

    def test_directora_ve_todas_las_40_cunas(self):
        """La directora ve la totalidad de cunas del establecimiento."""
        res = self.client.get(self.url_cunas, {"rol": "directora"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 40)

    def test_profesional_ve_unicamente_su_subconjunto_de_cunas(self):
        """Un profesional en turno rotativo ve únicamente las cunas bajo su responsabilidad."""
        res = self.client.get(
            self.url_cunas,
            {"rol": "medico", "medico_id": self.medico_manana.id, "turno": "Mañana"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 10)
        identificadores = [c["identificador"] for c in res.data]
        self.assertIn("C01", identificadores)
        self.assertIn("C10", identificadores)
        self.assertNotIn("C11", identificadores)

    def test_profesional_no_puede_consultar_cuna_fuera_de_su_turno(self):
        """El detalle /{id}/ rechaza acceso si la cuna no pertenece al turno asignado."""
        cuna_fuera = self.cunas[25]  # C26 no está asignada
        url_detalle = reverse("cuna-detail", args=[cuna_fuera.id])
        res = self.client.get(
            url_detalle,
            {"rol": "medico", "medico_id": self.medico_manana.id},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("no forma parte del subconjunto", str(res.data))

    def test_apoderado_ve_una_sola_cuna_con_matricula_activa(self):
        """El apoderado ve exactamente una cuna si su hijo está matriculado."""
        res = self.client.get(
            self.url_cunas,
            {"rol": "apoderado", "apoderado_id": self.apoderado_activo.id},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["identificador"], "C01")

        # Acceso directo al detalle de su cuna
        url_detalle = reverse("cuna-detail", args=[self.cunas[0].id])
        res_det = self.client.get(
            url_detalle,
            {"rol": "apoderado", "apoderado_id": self.apoderado_activo.id},
        )
        self.assertEqual(res_det.status_code, status.HTTP_200_OK)

    def test_apoderado_no_ve_cuna_si_matricula_esta_inactiva(self):
        """Si el bebé no está matriculado, el apoderado no ve ninguna cuna."""
        res = self.client.get(
            self.url_cunas,
            {"rol": "apoderado", "apoderado_id": self.apoderado_inactivo.id},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

        # Acceso directo al detalle debe retornar 403
        url_detalle = reverse("cuna-detail", args=[self.cunas[1].id])
        res_det = self.client.get(
            url_detalle,
            {"rol": "apoderado", "apoderado_id": self.apoderado_inactivo.id},
        )
        self.assertEqual(res_det.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("matrícula activa", str(res_det.data))

    def test_apoderado_no_puede_ver_cuna_ajena(self):
        """El apoderado no puede ver cunas de otros pacientes."""
        cuna_ajena = self.cunas[5]  # C06
        url_detalle = reverse("cuna-detail", args=[cuna_ajena.id])
        res = self.client.get(
            url_detalle,
            {"rol": "apoderado", "apoderado_id": self.apoderado_activo.id},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("solo puede visualizar la cuna asignada a su propio hijo", str(res.data))

    def test_comando_poblar_escala_ejecucion(self):
        """Verifica que el comando poblar_escala cree el conjunto institucional esperado."""
        call_command("poblar_escala", "--limpiar")
        self.assertEqual(Cuna.objects.count(), 40)
        self.assertEqual(Medico.objects.count(), 12)
        self.assertEqual(Turno.objects.count(), 3)
        self.assertGreaterEqual(AsignacionTurno.objects.count(), 12)

