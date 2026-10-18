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
*(Pendiente de registro)*