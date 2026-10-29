"""
Pruebas de integración de la API de 'cunas'.

Complementa ``tests.py`` con los contratos agregados en esta rama:

- asignación y liberación explícita de cunas,
- alta clínica de pacientes,
- estados derivados de la cuna,
- filtros nuevos de pacientes y cunas.

Se mantiene en un archivo separado para no tocar las pruebas históricas
del proyecto (que ya cubren telemetría, medicamentos y alertas).
"""

from django.test import TestCase
from rest_framework.test import APITestCase

from operacion.models import RegistroActividad

from .models import Alerta, Bebe, Cuna


def crear_bebe(identificador="BEB-INT-1", activo=True):
    """Crea un paciente mínimo válido para las pruebas."""
    return Bebe.objects.create(
        identificador=identificador,
        nombre_completo="Emilia Fuentes",
        edad_meses=0,
        sexo="F",
        activo=activo,
    )


class CunaEstadoTests(TestCase):
    """El estado de una cuna se deriva y nunca se contradice."""

    def test_cuna_sin_paciente_es_disponible(self):
        from .serializers import CunaSerializer

        cuna = Cuna.objects.create(identificador="C01")

        self.assertEqual(CunaSerializer(cuna).data["estado"], "disponible")

    def test_cuna_con_paciente_es_ocupada(self):
        from .serializers import CunaSerializer

        bebe = crear_bebe()
        cuna = Cuna.objects.create(identificador="C01", paciente=bebe)

        self.assertEqual(CunaSerializer(cuna).data["estado"], "ocupada")

    def test_cuna_en_mantenimiento(self):
        from .serializers import CunaSerializer

        cuna = Cuna.objects.create(identificador="C01", en_mantenimiento=True)

        self.assertEqual(CunaSerializer(cuna).data["estado"], "mantenimiento")

    def test_alerta_critica_activa_marca_la_cuna(self):
        from .serializers import CunaSerializer

        cuna = Cuna.objects.create(identificador="C01")
        Alerta.objects.create(
            cuna=cuna,
            tipo="spo2",
            nivel="Critica",
            mensaje="Desaturación",
            activa=True,
        )

        self.assertTrue(CunaSerializer(cuna).data["tiene_alerta_critica"])

    def test_alerta_resuelta_no_marca_la_cuna(self):
        from .serializers import CunaSerializer

        cuna = Cuna.objects.create(identificador="C01")
        Alerta.objects.create(
            cuna=cuna,
            tipo="spo2",
            nivel="Critica",
            mensaje="Desaturación",
            activa=False,
        )

        self.assertFalse(CunaSerializer(cuna).data["tiene_alerta_critica"])


class AsignacionCunaAPITests(APITestCase):
    """Contrato de ``/api/cunas/{id}/asignar/`` y ``liberar/``."""

    def setUp(self):
        self.bebe = crear_bebe()
        self.cuna = Cuna.objects.create(identificador="C01")

    def test_asignar_paciente_a_cuna_libre(self):
        """La asignación deja la cuna ocupada y registra auditoría."""
        respuesta = self.client.post(
            f"/api/cunas/{self.cuna.pk}/asignar/",
            {"paciente": self.bebe.pk},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.cuna.refresh_from_db()
        self.assertEqual(self.cuna.paciente, self.bebe)
        self.assertEqual(respuesta.data["estado"], "ocupada")
        self.assertTrue(
            RegistroActividad.objects.filter(accion="asignar", entidad="Cuna").exists()
        )

    def test_asignar_sin_paciente_devuelve_400(self):
        """El cuerpo debe indicar el paciente."""
        respuesta = self.client.post(
            f"/api/cunas/{self.cuna.pk}/asignar/", {}, format="json"
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_asignar_paciente_inexistente_devuelve_404(self):
        """Un identificador inválido no debe crear estados inconsistentes."""
        respuesta = self.client.post(
            f"/api/cunas/{self.cuna.pk}/asignar/",
            {"paciente": 999999},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_no_asignar_a_cuna_ocupada(self):
        """No se puede sobreescribir una cuna ya ocupada."""
        otro = crear_bebe("BEB-INT-2")
        self.cuna.paciente = self.bebe
        self.cuna.save()

        respuesta = self.client.post(
            f"/api/cunas/{self.cuna.pk}/asignar/",
            {"paciente": otro.pk},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_no_asignar_paciente_que_ya_ocupa_otra_cuna(self):
        """Un bebé no puede ocupar dos cunas a la vez."""
        otra_cuna = Cuna.objects.create(identificador="C02", paciente=self.bebe)

        respuesta = self.client.post(
            f"/api/cunas/{self.cuna.pk}/asignar/",
            {"paciente": self.bebe.pk},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertIn(otra_cuna.identificador, respuesta.data["detail"])

    def test_no_asignar_paciente_dado_de_alta(self):
        """Un paciente con alta no puede volver a ocupar cuna por esta vía."""
        bebe_alta = crear_bebe("BEB-INT-3", activo=False)

        respuesta = self.client.post(
            f"/api/cunas/{self.cuna.pk}/asignar/",
            {"paciente": bebe_alta.pk},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_no_asignar_a_cuna_en_mantenimiento(self):
        """Una cuna fuera de servicio no admite pacientes."""
        self.cuna.en_mantenimiento = True
        self.cuna.save()

        respuesta = self.client.post(
            f"/api/cunas/{self.cuna.pk}/asignar/",
            {"paciente": self.bebe.pk},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_liberar_cuna_ocupada(self):
        """Liberar deja la cuna disponible y registra el evento."""
        self.cuna.paciente = self.bebe
        self.cuna.save()

        respuesta = self.client.post(f"/api/cunas/{self.cuna.pk}/liberar/")

        self.assertEqual(respuesta.status_code, 200)
        self.cuna.refresh_from_db()
        self.assertIsNone(self.cuna.paciente)
        self.assertTrue(
            RegistroActividad.objects.filter(accion="liberar", entidad="Cuna").exists()
        )

    def test_liberar_cuna_vacia_devuelve_400(self):
        """Liberar dos veces es un error de uso, no un éxito silencioso."""
        respuesta = self.client.post(f"/api/cunas/{self.cuna.pk}/liberar/")

        self.assertEqual(respuesta.status_code, 400)


class AltaPacienteAPITests(APITestCase):
    """Contrato de ``POST /api/bebes/{id}/alta/``."""

    def setUp(self):
        self.bebe = crear_bebe("BEB-ALTA-1")
        self.cuna = Cuna.objects.create(identificador="C01", paciente=self.bebe)

    def test_alta_marca_paciente_y_libera_cuna(self):
        """El alta es atómica: paciente inactivo y cuna disponible."""
        respuesta = self.client.post(
            f"/api/bebes/{self.bebe.pk}/alta/",
            {"motivo": "Domicilio"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)

        self.bebe.refresh_from_db()
        self.cuna.refresh_from_db()
        self.assertFalse(self.bebe.activo)
        self.assertIsNotNone(self.bebe.fecha_alta)
        self.assertEqual(self.bebe.motivo_alta, "Domicilio")
        self.assertIsNone(self.cuna.paciente)
        self.assertTrue(
            RegistroActividad.objects.filter(accion="alta", entidad="Bebé").exists()
        )

    def test_alta_duplicada_devuelve_400(self):
        """No se puede dar de alta dos veces al mismo paciente."""
        self.client.post(f"/api/bebes/{self.bebe.pk}/alta/", {}, format="json")

        respuesta = self.client.post(f"/api/bebes/{self.bebe.pk}/alta/", {}, format="json")

        self.assertEqual(respuesta.status_code, 400)

    def test_filtro_de_pacientes_activos(self):
        """``?activo=true`` excluye a los pacientes con alta."""
        crear_bebe("BEB-ALTA-2", activo=False)

        respuesta = self.client.get("/api/bebes/", {"activo": "true"})

        self.assertEqual(respuesta.status_code, 200)
        identificadores = [fila["identificador"] for fila in respuesta.data]
        self.assertIn("BEB-ALTA-1", identificadores)
        self.assertNotIn("BEB-ALTA-2", identificadores)

    def test_filtro_de_pacientes_dados_de_alta(self):
        """``?activo=false`` devuelve solo los pacientes con alta."""
        self.client.post(f"/api/bebes/{self.bebe.pk}/alta/", {}, format="json")

        respuesta = self.client.get("/api/bebes/", {"activo": "false"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([fila["identificador"] for fila in respuesta.data], ["BEB-ALTA-1"])


class FiltrosCunaAPITests(APITestCase):
    """Filtros del mapa de cunas."""

    def setUp(self):
        bebe = crear_bebe("BEB-FILTRO-1")
        Cuna.objects.create(identificador="C01", paciente=bebe)
        Cuna.objects.create(identificador="C02")
        Cuna.objects.create(identificador="C03", en_mantenimiento=True)

    def test_filtro_por_estado_ocupada(self):
        """``?estado=ocupada`` devuelve solo cunas con paciente."""
        respuesta = self.client.get("/api/cunas/", {"estado": "ocupada"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([fila["identificador"] for fila in respuesta.data], ["C01"])

    def test_filtro_por_estado_disponible(self):
        """``?estado=disponible`` excluye ocupadas y mantenimiento."""
        respuesta = self.client.get("/api/cunas/", {"estado": "disponible"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([fila["identificador"] for fila in respuesta.data], ["C02"])

    def test_filtro_por_estado_mantenimiento(self):
        """``?estado=mantenimiento`` devuelve las cunas fuera de servicio."""
        respuesta = self.client.get("/api/cunas/", {"estado": "mantenimiento"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([fila["identificador"] for fila in respuesta.data], ["C03"])

    def test_busqueda_por_identificador(self):
        """``?search=`` busca por identificador de cuna."""
        respuesta = self.client.get("/api/cunas/", {"search": "C02"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([fila["identificador"] for fila in respuesta.data], ["C02"])

    def test_orden_estable_por_identificador(self):
        """El listado siempre se entrega ordenado para que el mapa no baile."""
        respuesta = self.client.get("/api/cunas/")

        identificadores = [fila["identificador"] for fila in respuesta.data]
        self.assertEqual(identificadores, sorted(identificadores))
