
"""Pruebas de integración de la Operación 2: resolver alertas."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .alertas_service import AlertaService
from .models import Alerta
from .repositories_alertas import DjangoAlertaRepository


class AlertaIntegracionTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.alerta = Alerta.objects.create(
            tipo="temperatura",
            mensaje="Temperatura fuera de rango",
            nivel="Advertencia",
            activa=True,
            valor_leido=38.5,
        )

    def test_resolver_alerta_actualiza_base_de_datos(self):
        """El repositorio debe persistir la resolución."""
        servicio = AlertaService(DjangoAlertaRepository())

        resultado = servicio.resolver_alerta(self.alerta.pk)

        self.alerta.refresh_from_db()

        self.assertFalse(self.alerta.activa)
        self.assertFalse(resultado.activa)

    def test_resolver_alerta_conserva_otros_campos(self):
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

    def test_endpoint_resolver_alerta_activa(self):
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
    def test_endpoint_alerta_ya_resuelta(self):
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

    def test_endpoint_alerta_inexistente(self):
        """Una alerta inexistente debe devolver HTTP 404."""
        url = reverse("alerta-resolver", args=[999999])

        respuesta = self.client.post(url)

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_404_NOT_FOUND,
        )
