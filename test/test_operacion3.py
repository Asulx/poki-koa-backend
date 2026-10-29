"""Pruebas aisladas del servicio de medicamentos para la Operación 3 en Poki Koa.

Sin inicializar Django ni usar base de datos.
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
    """Simula el repositorio de medicamentos sin utilizar una base de datos real."""

    """Inicializa el repositorio fake con un registro de medicamento configurable en estado pendiente o administrado.

    @param estado - Cadena que representa el estado inicial del medicamento (por defecto "Pendiente").
    @returns None
    """

    def __init__(self, estado: str = "Pendiente") -> None:
        self.registro = RegistroMedicamento(1, 10, estado)
        self.lecturas = 0
        self.escrituras = 0

    """Obtiene un registro de medicamento simulado por su identificador único.

    @param medicamento_id - Identificador del medicamento solicitado.
    @returns RegistroMedicamento o None - El registro encontrado o None si no existe.
    """

    def obtener(self, medicamento_id):
        self.lecturas += 1
        return self.registro if medicamento_id == self.registro.id else None

    """Confirma y persiste de forma simulada la administración del medicamento cambiando su estado.

    @param medicamento - Instancia de RegistroMedicamento a actualizar.
    @returns RegistroMedicamento - El registro actualizado con estado "Administrado".
    """

    def confirmar_pendiente(self, medicamento):
        self.escrituras += 1
        self.registro = replace(medicamento, estado="Administrado")
        return self.registro


class Operacion3Test(unittest.TestCase):
    """Suite de pruebas unitarias aisladas para validar el servicio de control y administración de fármacos."""

    """Verifica que un caso válido administre correctamente el medicamento y actualice las escrituras.

    @returns None
    """

    def test_caso_valido(self) -> None:
        repo = RepositorioFake()
        resultado = MedicamentoService(repo).administrar("1")
        self.assertEqual(resultado, RegistroMedicamento(1, 10, "Administrado"))
        self.assertEqual(repo.registro, resultado)
        self.assertEqual(repo.escrituras, 1)

    """Verifica que IDs mal formados o inválidos lancen OperacionError sin realizar lecturas ni escrituras.

    @returns None
    """

    def test_entrada_invalida_1_id_mal_formado(self) -> None:
        for valor in (None, "", " ", "abc", "01", "1.0", 0, -1, True, 1.5, [], 2**63):
            with self.subTest(valor=valor):
                repo = RepositorioFake()
                with self.assertRaisesRegex(OperacionError, "entero positivo"):
                    MedicamentoService(repo).administrar(valor)
                self.assertEqual((repo.lecturas, repo.escrituras), (0, 0))
                self.assertEqual(repo.registro.estado, "Pendiente")

    """Verifica que intentar administrar un medicamento ya administrado lance EstadoNoPermitido.

    @returns None
    """

    def test_entrada_invalida_2_ya_administrado(self) -> None:
        repo = RepositorioFake("Administrado")
        anterior = repo.registro
        with self.assertRaisesRegex(EstadoNoPermitido, "Solo se puede"):
            MedicamentoService(repo).administrar(1)
        self.assertEqual(repo.escrituras, 0)
        self.assertEqual(repo.registro, anterior)

    """Verifica que buscar un medicamento con un ID inexistente lance MedicamentoNoEncontrado.

    @returns None
    """

    def test_no_existe(self) -> None:
        repo = RepositorioFake()
        with self.assertRaises(MedicamentoNoEncontrado):
            MedicamentoService(repo).administrar(2)
        self.assertEqual(repo.escrituras, 0)

    """Verifica el comportamiento ante un cambio concurrente durante la confirmación.

    @returns None
    """

    def test_cambio_concurrente(self) -> None:
        repo = RepositorioFake()
        repo.confirmar_pendiente = lambda registro: None
        with self.assertRaisesRegex(EstadoNoPermitido, "recargue"):
            MedicamentoService(repo).administrar(1)
        self.assertEqual(repo.registro.estado, "Pendiente")

    """Verifica que se detecte una violación de invariantes si el repositorio altera campos protegidos.

    @returns None
    """

    def test_detecta_invariante_rota(self) -> None:
        repo = RepositorioFake()
        repo.confirmar_pendiente = lambda registro: replace(registro, paciente_id=99)
        with self.assertRaisesRegex(AssertionError, "conservando ID y paciente"):
            MedicamentoService(repo).administrar(1)

    """Verifica que las excepciones y fallos de infraestructura del repositorio se propaguen adecuadamente.

    @returns None
    """

    def test_propaga_fallo_de_dependencia(self) -> None:
        repo = RepositorioFake()

        def fallar(registro):
            raise ConnectionError("Repositorio no disponible")

        repo.confirmar_pendiente = fallar
        with self.assertRaisesRegex(ConnectionError, "no disponible"):
            MedicamentoService(repo).administrar(1)
        self.assertEqual(repo.registro.estado, "Pendiente")


if __name__ == "__main__":
    unittest.main()
