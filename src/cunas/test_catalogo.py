"""Comprobaciones del contrato y persistencia del catálogo del issue #17."""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import MedicamentoCatalogo


class CatalogoAPITest(TestCase):
    url = "/api/catalogo-medicamentos/"

    def setUp(self):
        self.client = APIClient()
        self.data = {
            "nombre": "Producto QA",
            "principio_activo": "Sustancia QA",
            "dosis_mg": "1.00",
            "stock": 10,
        }

    def test_create_retrieve_update(self):
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, 201)
        detail = f"{self.url}{response.data['id']}/"
        self.assertEqual(self.client.get(detail).data, response.data)
        self.assertEqual(
            self.client.patch(detail, {"stock": 1}, format="json").status_code, 200
        )
        item = MedicamentoCatalogo.objects.get(pk=response.data["id"])
        self.assertEqual(item.stock, 1)
        self.assertEqual(item.dosis_mg, Decimal("1.00"))
        replacement = dict(self.data, nombre="Actualizado", dosis_mg="2.50", stock=20)
        self.assertEqual(
            self.client.put(detail, replacement, format="json").status_code, 200
        )
        item.refresh_from_db()
        self.assertEqual(item.nombre, "Actualizado")
        self.assertEqual(item.dosis_mg, Decimal("2.50"))

    def test_invalid_creation_does_not_persist(self):
        for field, values in {
            "nombre": ["", " ", None, "N" * 151],
            "principio_activo": ["", None, "P" * 151],
            "dosis_mg": [
                None,
                "abc",
                "NaN",
                "Infinity",
                "-0.01",
                "0",
                "0.001",
                "100000000.00",
            ],
            "stock": [None, True, -1, 0, 1.5, "abc", 2147483648],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    response = self.client.post(
                        self.url, dict(self.data, **{field: value}), format="json"
                    )
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.data)
                    self.assertEqual(MedicamentoCatalogo.objects.count(), 0)
        for field in self.data:
            with self.subTest(missing=field):
                response = self.client.post(
                    self.url,
                    {k: v for k, v in self.data.items() if k != field},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_inclusive_limits(self):
        for dose, stock in [("0.01", 1), ("99999999.99", 2147483647)]:
            response = self.client.post(
                self.url,
                dict(
                    self.data,
                    nombre="N" * 150,
                    principio_activo="P" * 150,
                    dosis_mg=dose,
                    stock=stock,
                ),
                format="json",
            )
            self.assertEqual(response.status_code, 201)

    def test_invalid_update_is_atomic(self):
        item = MedicamentoCatalogo.objects.create(**self.data)
        detail = f"{self.url}{item.pk}/"
        response = self.client.patch(
            detail, {"nombre": "NO GUARDAR", "stock": 0}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.nombre, self.data["nombre"])
        self.assertEqual(item.stock, 10)
        self.assertEqual(
            self.client.put(
                detail, {"nombre": "NO GUARDAR"}, format="json"
            ).status_code,
            400,
        )
        item.refresh_from_db()
        self.assertEqual(item.nombre, self.data["nombre"])

    def test_missing_product_and_unsupported_delete(self):
        self.assertEqual(self.client.get(self.url + "999999/").status_code, 404)
        item = MedicamentoCatalogo.objects.create(**self.data)
        self.assertEqual(self.client.delete(f"{self.url}{item.pk}/").status_code, 405)
        self.assertTrue(MedicamentoCatalogo.objects.filter(pk=item.pk).exists())

    def test_database_rejects_nonpositive_values(self):
        for change in [
            {"stock": 0},
            {"stock": -1},
            {"dosis_mg": "0"},
            {"dosis_mg": "-1"},
        ]:
            with (
                self.subTest(change=change),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                MedicamentoCatalogo.objects.create(**dict(self.data, **change))
