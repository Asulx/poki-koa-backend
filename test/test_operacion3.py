"""Pruebas aisladas del servicio, sin inicializar Django ni usar base de datos.

Ejecutar: PYTHONPATH=src uv run --locked python -m unittest discover -s test -v
"""

import unittest
from dataclasses import replace

from cunas.medicamentos import (
    EstadoNoPermitido,
    MedicamentoNoEncontrado,
    MedicamentoService,
    OperacionError,
    RegistroMedicamento,
)


class RepositorioFake:
    def __init__(self, estado="Pendiente"):
        self.registro = RegistroMedicamento(1, 10, estado)
        self.lecturas = 0
        self.escrituras = 0

    def obtener(self, medicamento_id):
        self.lecturas += 1
        return self.registro if medicamento_id == self.registro.id else None

    def confirmar_pendiente(self, medicamento):
        self.escrituras += 1
        self.registro = replace(medicamento, estado="Administrado")
        return self.registro


class Operacion3Test(unittest.TestCase):
    def test_caso_valido(self):
        repo = RepositorioFake()
        resultado = MedicamentoService(repo).administrar("1")
        self.assertEqual(resultado, RegistroMedicamento(1, 10, "Administrado"))
        self.assertEqual(repo.registro, resultado)
        self.assertEqual(repo.escrituras, 1)

    def test_entrada_invalida_1_id_mal_formado(self):
        for valor in (None, "", " ", "abc", "01", "1.0", 0, -1, True, 1.5, [], 2**63):
            with self.subTest(valor=valor):
                repo = RepositorioFake()
                with self.assertRaisesRegex(OperacionError, "entero positivo"):
                    MedicamentoService(repo).administrar(valor)
                self.assertEqual((repo.lecturas, repo.escrituras), (0, 0))
                self.assertEqual(repo.registro.estado, "Pendiente")

    def test_entrada_invalida_2_ya_administrado(self):
        repo = RepositorioFake("Administrado")
        anterior = repo.registro
        with self.assertRaisesRegex(EstadoNoPermitido, "Solo se puede"):
            MedicamentoService(repo).administrar(1)
        self.assertEqual(repo.escrituras, 0)
        self.assertEqual(repo.registro, anterior)

    def test_no_existe(self):
        repo = RepositorioFake()
        with self.assertRaises(MedicamentoNoEncontrado):
            MedicamentoService(repo).administrar(2)
        self.assertEqual(repo.escrituras, 0)

    def test_cambio_concurrente(self):
        repo = RepositorioFake()
        repo.confirmar_pendiente = lambda registro: None
        with self.assertRaisesRegex(EstadoNoPermitido, "recargue"):
            MedicamentoService(repo).administrar(1)
        self.assertEqual(repo.registro.estado, "Pendiente")

    def test_detecta_invariante_rota(self):
        repo = RepositorioFake()
        repo.confirmar_pendiente = lambda registro: replace(registro, paciente_id=99)
        with self.assertRaisesRegex(AssertionError, "conservando ID y paciente"):
            MedicamentoService(repo).administrar(1)

    def test_propaga_fallo_de_dependencia(self):
        repo = RepositorioFake()

        def fallar(registro):
            raise ConnectionError("Repositorio no disponible")

        repo.confirmar_pendiente = fallar
        with self.assertRaisesRegex(ConnectionError, "no disponible"):
            MedicamentoService(repo).administrar(1)
        self.assertEqual(repo.registro.estado, "Pendiente")


if __name__ == "__main__":
    unittest.main()
