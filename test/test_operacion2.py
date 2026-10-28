
"""Pruebas unitarias de la Operación 2: gestión de alertas."""

import unittest
from dataclasses import replace
from datetime import datetime, timezone

from cunas.alertas_service import (
    AlertaEstadoNoPermitido,
    AlertaNoEncontrada,
    AlertaOperacionError,
    AlertaService,
    RegistroAlerta,
)


class RepositorioFake:
    """Simula el repositorio sin utilizar una base de datos."""

    def __init__(self, activa=True):
        self.registro = RegistroAlerta(
            id=1,
            paciente_id=10,
            cuna_id=5,
            tipo="temperatura",
            mensaje="Temperatura fuera de rango",
            nivel="Advertencia",
            fecha_hora=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc),
            activa=activa,
            valor_leido=38.5,
        )
        self.lecturas = 0
        self.escrituras = 0

    def obtener(self, alerta_id):
        self.lecturas += 1
        return self.registro if alerta_id == self.registro.id else None

    def confirmar_activa(self, alerta):
        self.escrituras += 1
        self.registro = replace(alerta, activa=False)
        return self.registro


class Operacion2Test(unittest.TestCase):

    def test_caso_valido(self):
        # PREPARAR
        repo = RepositorioFake()
        anterior = repo.registro

        # EJECUTAR
        resultado = AlertaService(repo).resolver_alerta("1")

        # VERIFICAR
        self.assertEqual(resultado, replace(anterior, activa=False))
        self.assertEqual(repo.registro, resultado)
        self.assertEqual(repo.escrituras, 1)

    def test_entrada_invalida_1_id_mal_formado(self):
        for valor in (
            None, "", " ", "abc", "01", "1.0",
            0, -1, True, 1.5, [], 2**63
        ):
            with self.subTest(valor=valor):
                repo = RepositorioFake()

                with self.assertRaises(AlertaOperacionError):
                    AlertaService(repo).resolver_alerta(valor)

                self.assertEqual(
                    (repo.lecturas, repo.escrituras),
                    (0, 0),
                )

    def test_entrada_invalida_2_ya_resuelta(self):
        repo = RepositorioFake(activa=False)
        anterior = repo.registro

        with self.assertRaises(AlertaEstadoNoPermitido):
            AlertaService(repo).resolver_alerta(1)

        self.assertEqual(repo.escrituras, 0)
        self.assertEqual(repo.registro, anterior)

    def test_alerta_no_existe(self):
        repo = RepositorioFake()

        with self.assertRaises(AlertaNoEncontrada):
            AlertaService(repo).resolver_alerta(2)

        self.assertEqual(repo.escrituras, 0)

    def test_cambio_concurrente(self):
        repo = RepositorioFake()
        repo.confirmar_activa = lambda alerta: None

        with self.assertRaises(AlertaEstadoNoPermitido):
            AlertaService(repo).resolver_alerta(1)

        self.assertTrue(repo.registro.activa)

    def test_detecta_invariante_rota(self):
        repo = RepositorioFake()

        repo.confirmar_activa = lambda alerta: replace(
            alerta,
            paciente_id=99,
            activa=False,
        )

        with self.assertRaisesRegex(
            AssertionError,
            "solo cambia el estado",
        ):
            AlertaService(repo).resolver_alerta(1)

    def test_propaga_fallo_de_dependencia(self):
        repo = RepositorioFake()

        def fallar(alerta):
            raise ConnectionError("Repositorio no disponible")

        repo.confirmar_activa = fallar

        with self.assertRaisesRegex(
            ConnectionError,
            "no disponible",
        ):
            AlertaService(repo).resolver_alerta(1)

        self.assertTrue(repo.registro.activa)


if __name__ == "__main__":
    unittest.main()
