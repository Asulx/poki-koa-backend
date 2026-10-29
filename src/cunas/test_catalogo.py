"""Comprobaciones del contrato y persistencia del catálogo del issue #17."""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import MedicamentoCatalogo


class CatalogoAPITest(TestCase):
    """Pruebas de integración y contrato para la API REST del catálogo farmacéutico (Issue #17).

    Verifica la correcta creación, recuperación, actualización parcial y total,
    gestión de límites inclusivos, atomicidad ante errores y restricciones a nivel de base de datos.
    """

    url = "/api/catalogo-medicamentos/"

    """Configura el cliente de pruebas de la API y los datos base para las solicitudes.

    @returns None
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.data = {
            "nombre": "Producto QA",
            "principio_activo": "Sustancia QA",
            "dosis_mg": "1.00",
            "stock": 10,
        }

    """Verifica el flujo completo de creación, consulta por ID, actualización parcial (PATCH) y total (PUT).

    @returns None
    """

    def test_create_retrieve_update(self) -> None:
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

    """Valida que los datos inválidos o incompletos rechacen la petición (HTTP 400) sin alterar la persistencia.

    @returns None
    """

    def test_invalid_creation_does_not_persist(self) -> None:
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

    """Valida que se acepten correctamente los valores límite inclusivos permitidos por el modelo.

    @returns None
    """

    def test_inclusive_limits(self) -> None:
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

    """Comprueba que las actualizaciones fallidas mantengan la atomicidad sin modificar el registro previo.

    @returns None
    """

    def test_invalid_update_is_atomic(self) -> None:
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

    """Verifica el manejo de recursos inexistentes (404) y la no soporte para borrados físicos (405).

    @returns None
    """

    def test_missing_product_and_unsupported_delete(self) -> None:
        self.assertEqual(self.client.get(self.url + "999999/").status_code, 404)
        item = MedicamentoCatalogo.objects.create(**self.data)
        self.assertEqual(self.client.delete(f"{self.url}{item.pk}/").status_code, 405)
        self.assertTrue(MedicamentoCatalogo.objects.filter(pk=item.pk).exists())

    """Comprueba que la base de datos rechace estrictamente valores no positivos a nivel de restricciones SQL.

    @returns None
    """

    def test_database_rejects_nonpositive_values(self) -> None:
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
