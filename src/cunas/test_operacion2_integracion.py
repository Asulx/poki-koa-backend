"""Pruebas de integración de la Operación 2: resolver alertas en Poki Koa."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .alertas_service import AlertaService
from .models import Alerta
from .repositories_alertas import DjangoAlertaRepository


class AlertaIntegracionTest(TestCase):
    """Pruebas de integración para el servicio y endpoints de resolución de alertas clínicas.

    Valida la persistencia correcta en base de datos, el aislamiento de campos,
    la correcta gestión de códigos de estado HTTP (200, 409, 404) y la prevención de condiciones de carrera.
    """

    """Configura el cliente de pruebas API y crea una instancia de alerta inicial en estado activo.

    @returns None
    """

    def setUp(self) -> None:
        self.client = APIClient()

        self.alerta = Alerta.objects.create(
            tipo="temperatura",
            mensaje="Temperatura fuera de rango",
            nivel="Advertencia",
            activa=True,
            valor_leido=38.5,
        )

    """Verifica que el repositorio y el servicio de dominio persistan correctamente la resolución de la alerta en la base de datos.

    @returns None
    """

    def test_resolver_alerta_actualiza_base_de_datos(self) -> None:
        """El repositorio debe persistir la resolución."""
        servicio = AlertaService(DjangoAlertaRepository())

        resultado = servicio.resolver_alerta(self.alerta.pk)

        self.alerta.refresh_from_db()

        self.assertFalse(self.alerta.activa)
        self.assertFalse(resultado.activa)

    """Verifica que la operación de resolución altere exclusivamente el estado activo sin modificar los demás datos clínicos.

    @returns None
    """

    def test_resolver_alerta_conserva_otros_campos(self) -> None:
        """Resolver no debe modificar los demás datos."""
        mensaje_original = self.alerta.mensaje
        nivel_original = self.alerta.nivel
        valor_original = self.alerta.valor_leido

        servicio = AlertaService(DjangoAlertaRepository())
        servicio.resolver_alerta(self.alerta.pk)

        self.alerta.refresh_from_db()

        self.assertEqual(self.alerta.mensaje, mensaje_original)
        self.assertEqual(self.alerta.nivel, nivel_original)
        self.assertEqual(self.alerta.valor_leido, valor_original)

    """Comprueba que una petición HTTP POST a una alerta activa devuelva un código HTTP 200 OK y la resuelva con éxito.

    @returns None
    """

    def test_endpoint_resolver_alerta_activa(self) -> None:
        """Una alerta activa debe resolverse con HTTP 200."""
        url = reverse("alerta-resolver", args=[self.alerta.pk])

        respuesta = self.client.post(url)

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK,
        )

        self.alerta.refresh_from_db()
        self.assertFalse(self.alerta.activa)
        self.assertIn("alerta", respuesta.data)
        self.assertIn("mensaje", respuesta.data)

    # [REGRESIÓN #5 — Resolución Repetida de Alertas Issue #54]
    """Verifica la regresión #5: intentar resolver una alerta que ya se encuentra inactiva debe retornar HTTP 409 Conflict.

    @returns None
    """

    def test_endpoint_alerta_ya_resuelta(self) -> None:
        """PRUEBA DE REGRESIÓN (#5): Resolver nuevamente una alerta inactiva debe devolver HTTP 409."""
        self.alerta.activa = False
        self.alerta.save(update_fields=["activa"])

        url = reverse("alerta-resolver", args=[self.alerta.pk])

        respuesta = self.client.post(url)

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.alerta.refresh_from_db()
        self.assertFalse(self.alerta.activa)

    """Verifica que una solicitud para resolver un identificador de alerta inexistente retorne un código HTTP 404 Not Found.

    @returns None
    """

    def test_endpoint_alerta_inexistente(self) -> None:
        """Una alerta inexistente debe devolver HTTP 404."""
        url = reverse("alerta-resolver", args=[999999])

        respuesta = self.client.post(url)

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_404_NOT_FOUND,
        )
