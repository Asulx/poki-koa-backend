"""Pruebas unitarias de la Operación 2: gestión de alertas en Poki Koa."""

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
    """Simula el repositorio de alertas sin utilizar una base de datos real para pruebas unitarias."""

    """Inicializa el repositorio fake con un registro de alerta de prueba configurable en estado activo o inactivo.

    @param activa - Booleano que indica si la alerta inicia activa (por defecto True).
    @returns None
    """

    def __init__(self, activa: bool = True) -> None:
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

    """Obtiene un registro de alerta simulado por su identificador único.

    @param alerta_id - Identificador de la alerta solicitada.
    @returns RegistroAlerta o None - La alerta encontrada o None si no existe.
    """

    def obtener(self, alerta_id):
        self.lecturas += 1
        return self.registro if alerta_id == self.registro.id else None

    """Confirma y persiste de forma simulada el paso de la alerta a estado inactivo.

    @param alerta - Instancia de RegistroAlerta a actualizar.
    @returns RegistroAlerta - El registro actualizado con activa=False.
    """

    def confirmar_activa(self, alerta):
        self.escrituras += 1
        self.registro = replace(alerta, activa=False)
        return self.registro


class Operacion2Test(unittest.TestCase):
    """Suite de pruebas unitarias para validar las reglas de negocio y restricciones del servicio de resolución de alertas."""

    """Verifica que un caso válido resuelva correctamente la alerta activa y actualice las escrituras.

    @returns None
    """

    def test_caso_valido(self) -> None:
        # PREPARAR
        repo = RepositorioFake()
        anterior = repo.registro

        # EJECUTAR
        resultado = AlertaService(repo).resolver_alerta("1")

        # VERIFICAR
        self.assertEqual(resultado, replace(anterior, activa=False))
        self.assertEqual(repo.registro, resultado)
        self.assertEqual(repo.escrituras, 1)

    """Verifica que identificadores mal formados o inválidos lancen AlertaOperacionError sin realizar lecturas ni escrituras.

    @returns None
    """

    def test_entrada_invalida_1_id_mal_formado(self) -> None:
        for valor in (None, "", " ", "abc", "01", "1.0", 0, -1, True, 1.5, [], 2**63):
            with self.subTest(valor=valor):
                repo = RepositorioFake()

                with self.assertRaises(AlertaOperacionError):
                    AlertaService(repo).resolver_alerta(valor)

                self.assertEqual(
                    (repo.lecturas, repo.escrituras),
                    (0, 0),
                )

    """Verifica que intentar resolver una alerta que ya se encuentra inactiva lance AlertaEstadoNoPermitido.

    @returns None
    """

    def test_entrada_invalida_2_ya_resuelta(self) -> None:
        repo = RepositorioFake(activa=False)
        anterior = repo.registro

        with self.assertRaises(AlertaEstadoNoPermitido):
            AlertaService(repo).resolver_alerta(1)

        self.assertEqual(repo.escrituras, 0)
        self.assertEqual(repo.registro, anterior)

    """Verifica que buscar una alerta con un ID inexistente lance AlertaNoEncontrada.

    @returns None
    """

    def test_alerta_no_existe(self) -> None:
        repo = RepositorioFake()

        with self.assertRaises(AlertaNoEncontrada):
            AlertaService(repo).resolver_alerta(2)

        self.assertEqual(repo.escrituras, 0)

    """Verifica el comportamiento ante un cambio concurrente donde la confirmación falla o se anula.

    @returns None
    """

    def test_cambio_concurrente(self) -> None:
        repo = RepositorioFake()
        repo.confirmar_activa = lambda alerta: None

        with self.assertRaises(AlertaEstadoNoPermitido):
            AlertaService(repo).resolver_alerta(1)

        self.assertTrue(repo.registro.activa)

    """Verifica que se detecte una violación de invariantes si el repositorio altera campos no permitidos durante la confirmación.

    @returns None
    """

    def test_detecta_invariante_rota(self) -> None:
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

    """Verifica que las excepciones y fallos de infraestructura del repositorio se propaguen adecuadamente.

    @returns None
    """

    def test_propaga_fallo_de_dependencia(self) -> None:
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
