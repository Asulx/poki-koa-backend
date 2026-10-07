# Ejercicio 2.2: Construcción para la Verificación en el Proyecto

**Proyecto:** Poki-Koa — Sistema de Monitoreo Neonatal  
**Rama:** `feature/54-construccion-para-verificacion`  
**Issue:** #54  

---

## Ficha de Operación 1

| Elemento | Registro del equipo |
| :--- | :--- |
| **Funcionalidad y operación** | **Funcionalidad:** Registro y actualización de telemetría de constantes vitales en cunas neonatales.<br>**Clase, módulo y firma:** `src/cunas/services.py` → `CunaService.actualizar_telemetria(cuna_id: str, ritmo_cardiaco: int, spo2: int, temperatura: float) -> Cuna` |
| **Propósito** | Actualizar de forma segura las constantes fisiológicas de una cuna en monitoreo activo, garantizando que los datos recibidos desde los sensores sean biológicamente válidos antes de persistirlos. |
| **Precondiciones** | 1. `cuna_id` debe ser una cadena no vacía correspondiente a una cuna existente.<br>2. `ritmo_cardiaco` debe estar entre 30 y 250 bpm; `spo2` debe ser un porcentaje entero entre 50 y 100; `temperatura` debe ser un número entre 30.0 y 45.0 °C. |
| **Postcondiciones** | 1. La cuna persiste los nuevos valores en base de datos junto con su marca de tiempo en `ultima_actualizacion`.<br>2. Se retorna la instancia de la cuna con los datos actualizados y confirmados. |
| **Invariante** | Una cuna persistida en el sistema nunca puede tener un `spo2` superior al 100% ni inferior al 0%, y siempre debe conservar un `id` primario asignado. |
| **Validación defensiva** | • **Entrada inválida 1:** `spo2 = 110` → **Respuesta:** Lanza `ValueError("SpO2 inválido: 110. Debe ser un porcentaje entre 50% y 100%.")`<br>• **Entrada inválida 2:** `cuna_id = ""` o `None` → **Respuesta:** Lanza `ValueError("cuna_id es obligatorio y no puede estar vacío.")` |
| **Dependencia explícita** | Se inyecta la clase del modelo o repositorio (`cuna_model`) mediante el constructor `CunaService(cuna_model=Cuna)`. En entornos de prueba, se reemplaza por un `Mock()` para verificar la lógica sin tocar la base de datos real ni acoplarse al ORM. |
| **Evidencia de ejecución** | **Comando ejecutado:**<br>`python src/manage.py test cunas`<br><br>**Salida de ejecución en consola:**<br>```text<br>Found 11 test(s).<br>Creating test database for alias 'default'...<br>System check identified no issues (0 silenced).<br>...........<br>----------------------------------------------------------------------<br>Ran 11 tests in 0.076s<br><br>OK<br>Destroying test database for alias 'default'...<br>```<br>Pruebas específicas de contrato verificadas:<br>• `test_caso_valido_actualizacion_exitosa`: Actualización de telemetría válida.<br>• `test_caso_invalido_spo2_fuera_de_rango`: Rechazo con `ValueError` por SpO2 > 100.<br>• `test_caso_invalido_cuna_id_vacio`: Rechazo con `ValueError` por identificador vacío. |

---

## Ficha de Operación 2
*(Pendiente de registro)*

---

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

La simulación con `git merge-tree --write-tree origin/feature/54-construccion-para-verificacion HEAD` finaliza sin conflictos y produce el mismo árbol que esta rama. Esta verificación cubre integrar primero la PR de la Operación 1 mediante un merge que conserve sus commits. Si se usa squash o rebase, se debe volver a sincronizar con `desarrollo` después de esa integración: la simulación squash detectó conflictos en este documento y en `src/cunas/tests.py`.
