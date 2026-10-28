"""Migración de pacientes existentes al identificador obligatorio."""

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class IdentificadorMigrationTest(TransactionTestCase):
    # [REGRESIÓN #3 — Migración de Identificadores Issue #54]
    def test_preserva_datos_y_completa_identificadores_sin_colisiones(self):
        """PRUEBA DE REGRESIÓN (#3): Verifica que la migración 0008 -> 0009 preserve datos y resuelva colisiones de ID."""
        anterior = [("cunas", "0008_medicamentocatalogo")]
        actual = [("cunas", "0009_bebe_identificador_obligatorio")]
        executor = MigrationExecutor(connection)
        executor.migrate(anterior)
        try:
            Bebe = executor.loader.project_state(anterior).apps.get_model(
                "cunas", "Bebe"
            )
            datos = {"nombre_completo": "Paciente QA", "edad_meses": 0, "sexo": "F"}
            for pk, identificador in [
                (1, None),
                (2, ""),
                (3, "  "),
                (4, "BEB-MIG-1"),
                (5, "EXISTENTE"),
            ]:
                Bebe.objects.create(pk=pk, identificador=identificador, **datos)
            executor = MigrationExecutor(connection)
            executor.migrate(actual)
            Bebe = executor.loader.project_state(actual).apps.get_model("cunas", "Bebe")
            ids = dict(Bebe.objects.values_list("pk", "identificador"))
            self.assertEqual(ids[1], "BEB-MIG-1-1")
            self.assertEqual(ids[4], "BEB-MIG-1")
            self.assertEqual(ids[5], "EXISTENTE")
            self.assertEqual(len(set(ids.values())), 5)
            self.assertTrue(
                all(value.strip() and len(value) <= 30 for value in ids.values())
            )
            self.assertEqual(Bebe.objects.filter(**datos).count(), 5)
            for value in [None, "EXISTENTE"]:
                with (
                    self.subTest(value=value),
                    self.assertRaises(IntegrityError),
                    transaction.atomic(),
                ):
                    Bebe.objects.create(identificador=value, **datos)
            # Reaplicar tras revertir el esquema conserva los IDs ya asignados.
            executor = MigrationExecutor(connection)
            executor.migrate(anterior)
            executor = MigrationExecutor(connection)
            executor.migrate(actual)
            self.assertEqual(dict(Bebe.objects.values_list("pk", "identificador")), ids)
        finally:
            MigrationExecutor(connection).migrate(actual)
