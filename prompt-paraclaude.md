# Prompt para completar la Ficha de operación 3

Actúa como asistente técnico del curso Taller de Programación Avanzada. Completa únicamente la Ficha de operación 3 del DOCX original adjunto, siguiendo su plantilla. Conserva intactos las fichas 1 y 2 y el resto del documento. Si falta el DOCX, solicítalo antes de editarlo.

La Operación 3 corresponde a administración de medicación/paciente; la Operación 1 es telemetría de cunas y la Operación 2 es gestión de alertas. El backend usa Python, Django y Django REST Framework. La rama de trabajo es `feat/tarea-ficha-3`.

Usa los siguientes datos reales. No inventes mensajes, comandos ni resultados. La evidencia describe ejecuciones registradas, no una nueva ejecución realizada por ti. Entrega una copia DOCX con otro nombre y resume los campos completados.

## Ficha de Operación 3

| Elemento | Registro del equipo |
| --- | --- |
| Funcionalidad y operación | **Control de administración de medicamentos.** Clase MedicamentoService, módulo src/cunas/medicamentos.py, firma administrar(medicamento_id: int \| str) -> RegistroMedicamento. Ruta POST /api/medicamentos/{id}/administrar/, sin cuerpo requerido. |
| Propósito | Registrar que un medicamento previamente pendiente fue administrado y devolver su ID, paciente y estado Administrado. |
| Precondiciones | **1.** El ID debe ser un entero entre 1 y 9223372036854775807, o su representación decimal ASCII sin espacios, signos ni ceros iniciales. No se aceptan booleanos, nulos ni valores vacíos.  **2.** Debe existir un medicamento con ese ID.  **3.** Su estado debe ser Pendiente al leerlo y al actualizarlo. |
| Postcondiciones | **1.** Tras una ejecución exitosa se persiste el cambio de Pendiente a Administrado y se responde HTTP 200 con ese estado.  **2.** Se conservan el ID, el paciente y los demás campos del medicamento; solo se actualiza estado.  **3.** Una nueva confirmación del mismo medicamento se rechaza con HTTP 409 mientras siga administrado. |
| Invariante | El registro pertenece a un paciente con ID entero positivo y la transición conserva la identidad del medicamento y del paciente. Las aserciones comprueban la identidad entregada por el repositorio y que el resultado interno sea exactamente el registro anterior con estado Administrado. |
| Validación defensiva | **Entrada inválida 1:**medicamento_id="abc" (también None, vacío, cero, negativo, etc.).  **Respuesta:**OperacionError, HTTP 400, mensaje medicamento_id debe ser un entero positivo. No se consulta ni modifica el repositorio.  **Entrada inválida 2:** ID existente cuyo estado es Administrado.  **Respuesta:**EstadoNoPermitido, HTTP 409, mensaje Solo se puede administrar un medicamento Pendiente. No se escribe ni cambia el registro. |
| Dependencia explícita | MedicamentoRepository recibido por el constructor: MedicamentoService(repositorio). La vista inyecta DjangoMedicamentoRepository; las pruebas inyectan RepositorioFake, sin Django ni base de datos. El protocolo declara obtener y confirmar_pendiente. |
| Evidencia de ejecución | test/test_operacion3.py demuestra éxito, dos casos inválidos, ID inexistente, conflicto concurrente, invariante rota y fallo del colaborador. APIAdministrarMedicamentoTestCase en src/cunas/tests.py verifica persistencia y respuestas HTTP 200, 400, 404 y 409. Comandos y resultados registrados debajo. |

**Separación de responsabilidades**
Los comentarios # PRE:, # POST: y # INV: usan la sintaxis de Python. Las entradas externas y estados no permitidos se rechazan con excepciones controladas; no dependen de assert. Las aserciones detectan errores de programación o incumplimientos del contrato del repositorio. Python puede deshabilitarlas con -O; por eso no validan entradas externas.
La vista traduce solo OperacionError y sus subclases. Un ID inexistente produce HTTP 404 (El medicamento no existe.). Los errores de almacenamiento se propagan sin ocultar su causa; las aserciones tampoco se convierten en errores del cliente.
El adaptador usa una actualización condicional por ID, paciente y estado Pendiente. Si otra solicitud modifica o elimina el registro entre lectura y escritura, no se actualiza y se responde HTTP 409 (El medicamento cambió; recargue antes de administrar.). No requiere migraciones. El contrato corresponde a esta operación; los endpoints CRUD existentes mantienen su comportamiento y pueden modificar el estado por separado.
**Evidencia de ejecución**
Ejecutado desde la raíz del repositorio en la rama feat/tarea-ficha-3.
Prueba aislada, solo biblioteca estándar:
PYTHONPATH=src python -m unittest discover -s test -v

test_cambio_concurrente ... ok
test_caso_valido ... ok
test_detecta_invariante_rota ... ok
test_entrada_invalida_1_id_mal_formado ... ok
test_entrada_invalida_2_ya_administrado ... ok
test_no_existe ... ok
test_propaga_fallo_de_dependencia ... ok
Ran 7 tests
OK

El caso válido administra el medicamento 1 del paciente 10 y comprueba una sola escritura. Los inválidos comprueban tanto la excepción como la ausencia de escrituras y la conservación del estado anterior.
Suite Django, incluyendo pruebas existentes y las tres nuevas pruebas de API:
# Preparación en un entorno nuevo:
python -m venv .venv
.venv/bin/python -m pip install -e .
# Ejecución:
.venv/bin/python src/manage.py test cunas -v 1

Creating test database for alias 'default'...
...................................
Ran 35 tests in 0.086s
OK
Destroying test database for alias 'default'...
Found 35 test(s).
System check identified no issues (0 silenced).

Django crea una base de datos de pruebas separada. La ejecución local utilizó Python 3.15, Django 6.1.2 y Django REST Framework 3.18.3, versiones compatibles con los rangos declarados en pyproject.toml; no se modificó uv.lock.
**Sustitución de la dependencia en pruebas unitarias**
El constructor recibe el repositorio; el servicio no crea el cliente de base de datos. Para verificarlo sin Django, se inyecta el RepositorioFake definido en test/test_operacion3.py, que implementa obtener y confirmar_pendiente y mantiene un registro en memoria:
from cunas.medicamentos import MedicamentoService, RegistroMedicamento
from test.test_operacion3 import RepositorioFake

repositorio = RepositorioFake()
servicio = MedicamentoService(repositorio)
resultado = servicio.administrar("1")

assert resultado == RegistroMedicamento(1, 10, "Administrado")
assert repositorio.escrituras == 1

Para el caso de estado inválido se usa RepositorioFake("Administrado"); la prueba verifica la excepción y cero escrituras. Para simular un conflicto, se sustituye confirmar_pendiente por una función que devuelve None. También puede usarse un mock con los mismos dos métodos, configurando sus resultados y comprobando que la escritura no se invoque ante datos inválidos.

### Verificación de integración con la Operación 1

Base integrada: `feature/54-construccion-para-verificacion`, commit `6c909e1`, que ya contiene `desarrollo` en `6e1e532`. Se conservan `CunaService` en `src/cunas/services.py`, la Ficha 1 y las pruebas de telemetría; `MedicamentoService` se ubica en `src/cunas/medicamentos.py` para que las pruebas aisladas sigan funcionando sin Django.

Resultado de la ejecución combinada: 7 pruebas aisladas y 35 pruebas Django aprobadas. El dato de 11 pruebas de la Ficha 1 corresponde a la evidencia original de su autor.

La comprobación `makemigrations --check --dry-run` detecta un cambio pendiente de `Bebe.identificador` (nullable/blank). Esa diferencia ya existe entre el modelo y la migración 0007 de `desarrollo` y de la rama de la Operación 1; esta operación de medicación no modifica modelos ni migraciones.

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
"""Pruebas sin Django ni base de datos: PYTHONPATH=src python -m unittest discover -s test -v."""

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
