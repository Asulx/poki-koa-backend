Actúa como un asistente técnico de ingeniería de software para el curso "Taller de Programación Avanzada".

Te he adjuntado el archivo DOCX entregado por el profesor: `Guia_Ejercicio_Construccion_para_la_Verificacion_en_el_Proyecto.docx`.

Necesito que modifiques directamente este documento completando los campos vacíos de la sección "Ficha de operación 3".
Debes preservar intacto todo el resto del documento (incluyendo la Ficha 1 y la Ficha 2 para mis compañeros).

A continuación se incluyen los datos verificados del repositorio `poki-koa-backend`, rama `feat/tarea-ficha-3`. El backend utiliza Python, Django y Django REST Framework: Koa forma parte del nombre del proyecto y no corresponde al framework Node.js. No conviertas el código a JavaScript ni inventes firmas, mensajes, pruebas o resultados.

La operación asignada es la Operación 3: administración de medicación/paciente. No corresponde a telemetría (Operación 1) ni a gestión de alertas (Operación 2).

La documentación del ejercicio está en `docs/ejercicio-2-2.md`. Usa los siguientes datos para completar únicamente la Ficha de operación 3 del DOCX adjunto. Conserva el formato y todo el contenido restante, especialmente las fichas 1 y 2. Si el DOCX no está adjunto, solicítalo antes de editarlo; no afirmes haber generado un archivo sin producirlo.

## Datos completos para la Ficha 3

## Ficha de operación 3

| Elemento | Registro del equipo |
| --- | --- |
| Funcionalidad y operación | **Control de administración de medicamentos.** Clase `MedicamentoService`, módulo `src/cunas/services.py`, firma `administrar(medicamento_id: int \| str) -> RegistroMedicamento`. Ruta `POST /api/medicamentos/{id}/administrar/`, sin cuerpo requerido. |
| Propósito | Registrar que un medicamento previamente pendiente fue administrado y devolver su ID, paciente y estado `Administrado`. |
| Precondiciones | **1.** El ID debe ser un entero entre 1 y 9223372036854775807, o su representación decimal ASCII sin espacios, signos ni ceros iniciales. No se aceptan booleanos, nulos ni valores vacíos. **2.** Debe existir un medicamento con ese ID. **3.** Su estado debe ser `Pendiente` al leerlo y al actualizarlo. |
| Postcondiciones | **1.** Tras una ejecución exitosa se persiste el cambio de `Pendiente` a `Administrado` y se responde HTTP 200 con ese estado. **2.** Se conservan el ID, el paciente y los demás campos del medicamento; solo se actualiza `estado`. **3.** Una nueva confirmación del mismo medicamento se rechaza con HTTP 409 mientras siga administrado. |
| Invariante | El registro pertenece a un paciente con ID entero positivo y la transición conserva la identidad del medicamento y del paciente. Las aserciones comprueban la identidad entregada por el repositorio y que el resultado interno sea exactamente el registro anterior con estado `Administrado`. |
| Validación defensiva | **Entrada inválida 1:** `medicamento_id="abc"` (también `None`, vacío, cero, negativo, etc.). **Respuesta:** `OperacionError`, HTTP 400, mensaje `medicamento_id debe ser un entero positivo.` No se consulta ni modifica el repositorio. **Entrada inválida 2:** ID existente cuyo estado es `Administrado`. **Respuesta:** `EstadoNoPermitido`, HTTP 409, mensaje `Solo se puede administrar un medicamento Pendiente.` No se escribe ni cambia el registro. |
| Dependencia explícita | `MedicamentoRepository` recibido por el constructor: `MedicamentoService(repositorio)`. La vista inyecta `DjangoMedicamentoRepository`; las pruebas inyectan `RepositorioFake`, sin Django ni base de datos. El protocolo declara `obtener` y `confirmar_pendiente`. |
| Evidencia de ejecución | `test/test_operacion3.py` demuestra éxito, dos casos inválidos, ID inexistente, conflicto concurrente, invariante rota y fallo del colaborador. `APIAdministrarMedicamentoTestCase` en `src/cunas/tests.py` verifica persistencia y respuestas HTTP 200, 400, 404 y 409. Comandos y resultados registrados debajo. |

### Separación de responsabilidades

Los comentarios `# PRE:`, `# POST:` y `# INV:` usan la sintaxis de Python. Las entradas externas y estados no permitidos se rechazan con excepciones controladas; no dependen de `assert`. Las aserciones detectan errores de programación o incumplimientos del contrato del repositorio. Python puede deshabilitarlas con `-O`; por eso no validan entradas externas.

La vista traduce solo `OperacionError` y sus subclases. Un ID inexistente produce HTTP 404 (`El medicamento no existe.`). Los errores de almacenamiento se propagan sin ocultar su causa; las aserciones tampoco se convierten en errores del cliente.

El adaptador usa una actualización condicional por ID, paciente y estado `Pendiente`. Si otra solicitud modifica o elimina el registro entre lectura y escritura, no se actualiza y se responde HTTP 409 (`El medicamento cambió; recargue antes de administrar.`). No requiere migraciones. El contrato corresponde a esta operación; los endpoints CRUD existentes mantienen su comportamiento y pueden modificar el estado por separado.

### Evidencia de ejecución

Ejecutado desde la raíz del repositorio en la rama `feat/tarea-ficha-3`.

Prueba aislada, solo biblioteca estándar:

```bash
PYTHONPATH=src python -m unittest discover -s test -v
```

```text
test_cambio_concurrente ... ok
test_caso_valido ... ok
test_detecta_invariante_rota ... ok
test_entrada_invalida_1_id_mal_formado ... ok
test_entrada_invalida_2_ya_administrado ... ok
test_no_existe ... ok
test_propaga_fallo_de_dependencia ... ok
Ran 7 tests
OK
```

El caso válido administra el medicamento 1 del paciente 10 y comprueba una sola escritura. Los inválidos comprueban tanto la excepción como la ausencia de escrituras y la conservación del estado anterior.

Suite Django, incluyendo pruebas existentes y las tres nuevas pruebas de API:

```bash
# Preparación en un entorno nuevo:
python -m venv .venv
.venv/bin/python -m pip install -e .
# Ejecución:
.venv/bin/python src/manage.py test cunas -v 1
```

```text
Creating test database for alias 'default'...
...........
Ran 11 tests in 0.036s
OK
Destroying test database for alias 'default'...
Found 11 test(s).
System check identified no issues (0 silenced).
```

Django crea una base de datos de pruebas separada. La ejecución local utilizó Python 3.15, Django 6.1.2 y Django REST Framework 3.18.3, versiones compatibles con los rangos declarados en `pyproject.toml`; no se modificó `uv.lock`.

### Sustitución de la dependencia en pruebas unitarias

El constructor recibe el repositorio; el servicio no crea el cliente de base de datos. Para verificarlo sin Django, se inyecta el `RepositorioFake` definido en `test/test_operacion3.py`, que implementa `obtener` y `confirmar_pendiente` y mantiene un registro en memoria:

```python
from cunas.services import MedicamentoService, RegistroMedicamento
from test.test_operacion3 import RepositorioFake

repositorio = RepositorioFake()
servicio = MedicamentoService(repositorio)
resultado = servicio.administrar("1")

assert resultado == RegistroMedicamento(1, 10, "Administrado")
assert repositorio.escrituras == 1
```

Para el caso de estado inválido se usa `RepositorioFake("Administrado")`; la prueba verifica la excepción y cero escrituras. Para simular un conflicto, se sustituye `confirmar_pendiente` por una función que devuelve `None`. También puede usarse un mock con los mismos dos métodos, configurando sus resultados y comprobando que la escritura no se invoque ante datos inválidos.

## Código implementado de referencia

### `src/cunas/services.py`

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
            raise EstadoNoPermitido("Solo se puede administrar un medicamento Pendiente.")

        # INV: el repositorio entrega la identidad solicitada y un paciente válido.
        assert actual.id == medicamento_id, "Invariante: identidad del medicamento."
        assert type(actual.paciente_id) is int and actual.paciente_id > 0, (
            "Invariante: el medicamento pertenece a un paciente válido."
        )
        resultado = self._repositorio.confirmar_pendiente(actual)
        if resultado is None:
            raise EstadoNoPermitido("El medicamento cambió; recargue antes de administrar.")

        # POST: estado Administrado; INV: se conservan ID y paciente.
        assert resultado == replace(actual, estado="Administrado"), (
            "Invariante: solo cambia Pendiente a Administrado, conservando ID y paciente."
        )
        return resultado

```

### `src/cunas/repositories.py`

```python
"""Adaptador de persistencia para la operación de administración."""

from .models import Medicamento
from .services import RegistroMedicamento


class DjangoMedicamentoRepository:
    def obtener(self, medicamento_id):
        datos = Medicamento.objects.filter(pk=medicamento_id).values(
            "id", "paciente_id", "estado"
        ).first()
        return RegistroMedicamento(**datos) if datos else None

    def confirmar_pendiente(self, medicamento):
        # Compare-and-set: dos solicitudes concurrentes no confirman dos veces.
        filas = Medicamento.objects.filter(
            pk=medicamento.id,
            paciente_id=medicamento.paciente_id,
            estado="Pendiente",
        ).update(estado="Administrado")
        if filas == 0:
            return None
        return RegistroMedicamento(
            medicamento.id, medicamento.paciente_id, "Administrado"
        )

```

### `test/test_operacion3.py`

```python
"""Pruebas sin Django ni base de datos: PYTHONPATH=src python -m unittest discover -s test -v."""
import unittest
from dataclasses import replace
from cunas.services import (
    EstadoNoPermitido, MedicamentoNoEncontrado, MedicamentoService,
    OperacionError, RegistroMedicamento,
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

La integración está en `MedicamentoViewSet.administrar`, en `src/cunas/views.py`: crea `MedicamentoService(DjangoMedicamentoRepository())`, ejecuta `administrar(pk)`, traduce `OperacionError` a JSON con `detail` y su `status_code`, y devuelve HTTP 200 con `id`, `paciente_id` y `estado` en caso exitoso. Las pruebas de API están en `APIAdministrarMedicamentoTestCase`, en `src/cunas/tests.py`.

## Instrucciones de entrega

Instrucciones para el llenado de la Ficha de operación 3 dentro del .docx:
1. Completa cada campo de la Ficha 3 en sus líneas correspondientes:
   - Funcionalidad o necesidad: (Nombre claro y objetivo de la funcionalidad en el proyecto).
   - Clase, módulo y firma o ruta: (Archivo y método/ruta exactos).
   - Propósito: (Resultado observable que obtiene el usuario/cliente).
   - Precondiciones: (Listar 1 y 2 con condiciones concretas, tipos, rangos o estados).
   - Postcondiciones: (Listar 1 y 2 con las garantías verificables tras la ejecución).
   - Invariante: (Regla de negocio o estado interno que nunca se quiebra).
   - Validación defensiva: (Detallar Entrada inválida 1 y Respuesta; Entrada inválida 2 y Respuesta).
   - Dependencia explícita: (Colaborador inyectado por constructor/parámetro y cómo se reemplaza por un mock/fake).
   - Evidencia de ejecución: (Mencionar el comando/archivo de prueba ejecutado y el resumen del caso válido y los 2 inválidos).
2. Usa un lenguaje formal, técnico y conciso. Evita términos ambiguos como "funciona bien" o "datos correctos".
3. Devuélveme el archivo .docx actualizado listo para descargar.

La evidencia incluida corresponde a una ejecución ya realizada. No la describas como una ejecución nueva hecha por ti. Si vuelves a ejecutar los comandos, registra sus resultados reales. Entrega el DOCX con un nombre diferente del original y resume únicamente los campos completados de la Ficha 3.
