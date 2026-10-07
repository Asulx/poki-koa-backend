# Prompt para completar la Ficha de operación 3

Actúa como asistente técnico del curso Taller de Programación Avanzada. Completa únicamente la Ficha de operación 3 del DOCX original adjunto con los datos siguientes. Conserva intactas las fichas 1 y 2 y el resto del documento. Si falta el DOCX, solicítalo antes de editarlo. Entrega una copia con otro nombre.

La Operación 3 corresponde a administración de medicación/paciente; la Operación 1 es telemetría y la Operación 2 es gestión de alertas. El backend usa Python, Django y Django REST Framework. El servicio de medicación está en `src/cunas/medicamentos.py` y recibe el repositorio por constructor. La rama es `feat/tarea-ficha-3`.

Usa solo los contratos, mensajes y resultados registrados aquí. No inventes una ejecución nueva. Se sincronizó el entorno con `uv sync --locked` y se ejecutaron ambas suites mediante `uv run --locked`, sin modificar `uv.lock`: 7 pruebas unitarias y 35 pruebas Django aprobadas. Versiones verificadas: Python 3.15.0rc3, Django 6.1 y Django REST Framework 3.18.0. El resultado de 11 pruebas de la Ficha 1 corresponde a la evidencia histórica de su autor y debe preservarse.

## Ficha de Operación 3

| Elemento | Registro del equipo |
| :--- | :--- |
| **Funcionalidad y operación** | **Funcionalidad:** Confirmación de administración de medicamentos.<br>**Clase, módulo y firma:** `src/cunas/medicamentos.py` → `MedicamentoService.administrar(medicamento_id: int \| str) -> RegistroMedicamento`.<br>**Ruta:** `POST /api/medicamentos/{id}/administrar/`, sin cuerpo requerido. |
| **Propósito** | Registrar un medicamento pendiente como `Administrado` y devolver su ID, paciente y estado mediante HTTP 200. |
| **Precondiciones** | 1. El ID debe ser un entero entre 1 y `2**63 - 1`, o una cadena decimal ASCII equivalente sin espacios, signos ni ceros iniciales; no se aceptan nulos, vacíos ni booleanos.<br>2. El medicamento debe existir y estar `Pendiente` al consultar y actualizar. |
| **Postcondiciones** | 1. Se persiste el estado `Administrado` y se devuelve el registro actualizado.<br>2. Se conservan el ID, el paciente y los demás campos; una confirmación repetida se rechaza con HTTP 409 mientras siga administrado. |
| **Invariante** | El medicamento pertenece a un paciente con ID entero positivo y conserva ambas identidades durante la transición. Las aserciones verifican estas reglas internas y el resultado `Administrado`. |
| **Validación defensiva** | **Entrada inválida 1:** `medicamento_id="abc"` → `OperacionError("medicamento_id debe ser un entero positivo.")`, HTTP 400, sin consultar ni escribir.<br>**Entrada inválida 2:** medicamento ya `Administrado` → `EstadoNoPermitido("Solo se puede administrar un medicamento Pendiente.")`, HTTP 409, sin modificar el registro. |
| **Dependencia explícita** | El constructor `MedicamentoService(repositorio)` recibe un `MedicamentoRepository` con los métodos `obtener` y `confirmar_pendiente`. La vista inyecta `DjangoMedicamentoRepository`; las pruebas usan `RepositorioFake` en memoria, sin Django ni base de datos. |
| **Evidencia de ejecución** | **Preparación:** `uv sync --locked` (usa las versiones de `uv.lock`).<br>**Prueba aislada:** `PYTHONPATH=src uv run --locked python -m unittest discover -s test -v` → 7 pruebas, `OK`.<br>**Archivo:** `test/test_operacion3.py`; verifica éxito, ID inválido y estado ya administrado, incluyendo conservación del estado ante rechazos.<br>**Integración:** `uv run --locked python src/manage.py test cunas -v 1` → 35 pruebas, `OK`, incluyendo las pruebas de la Operación 1 y `APIAdministrarMedicamentoTestCase`. |

## Código real del servicio

```python
"""Contratos de negocio independientes de Django y del almacenamiento."""

from dataclasses import dataclass, replace
from typing import Protocol


class OperacionError(Exception):
    status_code = 400


class MedicamentoNoEncontrado(OperacionError):
    status_code = 404


class EstadoNoPermitido(OperacionError):
    status_code = 409


@dataclass(frozen=True)
class RegistroMedicamento:
    id: int
    paciente_id: int
    estado: str


class MedicamentoRepository(Protocol):
    def obtener(self, medicamento_id: int) -> RegistroMedicamento | None: ...

    def confirmar_pendiente(
        self, medicamento: RegistroMedicamento
    ) -> RegistroMedicamento | None:
        """Actualiza solo si sigue pendiente y conserva paciente e ID.

        Retorna None si otro proceso cambió o eliminó el registro.
        """
        ...


class MedicamentoService:
    def __init__(self, repositorio: MedicamentoRepository):
        self._repositorio = repositorio

    def administrar(self, medicamento_id: int | str) -> RegistroMedicamento:
        # PRE: ID entero positivo (o cadena decimal canónica), hasta 2**63 - 1.
        # Validación externa: no usar assert; bool tampoco es un ID válido.
        if isinstance(medicamento_id, str):
            if (
                not medicamento_id.isascii()
                or not medicamento_id.isdecimal()
                or medicamento_id.startswith("0")
                or len(medicamento_id) > 19
            ):
                raise OperacionError("medicamento_id debe ser un entero positivo.")
            medicamento_id = int(medicamento_id)
        if type(medicamento_id) is not int or not 0 < medicamento_id <= 2**63 - 1:
            raise OperacionError("medicamento_id debe ser un entero positivo.")

        # PRE: el medicamento existe y su estado es Pendiente.
        actual = self._repositorio.obtener(medicamento_id)
        if actual is None:
            raise MedicamentoNoEncontrado("El medicamento no existe.")
        if actual.estado != "Pendiente":
            raise EstadoNoPermitido(
                "Solo se puede administrar un medicamento Pendiente."
            )

        # INV: el repositorio entrega la identidad solicitada y un paciente válido.
        assert actual.id == medicamento_id, "Invariante: identidad del medicamento."
        assert type(actual.paciente_id) is int and actual.paciente_id > 0, (
            "Invariante: el medicamento pertenece a un paciente válido."
        )
        resultado = self._repositorio.confirmar_pendiente(actual)
        if resultado is None:
            raise EstadoNoPermitido(
                "El medicamento cambió; recargue antes de administrar."
            )

        # POST: estado Administrado; INV: se conservan ID y paciente.
        assert resultado == replace(actual, estado="Administrado"), (
            "Invariante: solo cambia Pendiente a Administrado, conservando ID y paciente."
        )
        return resultado
```

## Pruebas unitarias reales

```python
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
```
