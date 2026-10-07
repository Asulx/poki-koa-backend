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
| :--- | :--- |
| **Funcionalidad y operación** | **Funcionalidad:** Confirmación de administración de medicamentos.<br>**Clase, módulo y firma:** `src/cunas/medicamentos.py` → `MedicamentoService.administrar(medicamento_id: int \| str) -> RegistroMedicamento`.<br>**Ruta:** `POST /api/medicamentos/{id}/administrar/`, sin cuerpo requerido. |
| **Propósito** | Registrar un medicamento pendiente como `Administrado` y devolver su ID, paciente y estado mediante HTTP 200. |
| **Precondiciones** | 1. El ID debe ser un entero entre 1 y `2**63 - 1`, o una cadena decimal ASCII equivalente sin espacios, signos ni ceros iniciales; no se aceptan nulos, vacíos ni booleanos.<br>2. El medicamento debe existir y estar `Pendiente` al consultar y actualizar. |
| **Postcondiciones** | 1. Se persiste el estado `Administrado` y se devuelve el registro actualizado.<br>2. Se conservan el ID, el paciente y los demás campos; una confirmación repetida se rechaza con HTTP 409 mientras siga administrado. |
| **Invariante** | El medicamento pertenece a un paciente con ID entero positivo y conserva ambas identidades durante la transición. Las aserciones verifican estas reglas internas y el resultado `Administrado`. |
| **Validación defensiva** | **Entrada inválida 1:** `medicamento_id="abc"` → `OperacionError("medicamento_id debe ser un entero positivo.")`, HTTP 400, sin consultar ni escribir.<br>**Entrada inválida 2:** medicamento ya `Administrado` → `EstadoNoPermitido("Solo se puede administrar un medicamento Pendiente.")`, HTTP 409, sin modificar el registro. |
| **Dependencia explícita** | El constructor `MedicamentoService(repositorio)` recibe un `MedicamentoRepository` con los métodos `obtener` y `confirmar_pendiente`. La vista inyecta `DjangoMedicamentoRepository`; las pruebas usan `RepositorioFake` en memoria, sin Django ni base de datos. |
| **Evidencia de ejecución** | **Preparación:** `uv sync --locked` (usa las versiones de `uv.lock`).<br>**Prueba aislada:** `PYTHONPATH=src uv run --locked python -m unittest discover -s test -v` → 7 pruebas, `OK`.<br>**Archivo:** `test/test_operacion3.py`; verifica éxito, ID inválido y estado ya administrado, incluyendo conservación del estado ante rechazos.<br>**Integración:** `uv run --locked python src/manage.py test cunas -v 1` → 35 pruebas, `OK`, incluyendo las pruebas de la Operación 1 y `APIAdministrarMedicamentoTestCase`. |
