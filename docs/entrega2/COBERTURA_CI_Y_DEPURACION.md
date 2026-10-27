# Depuración, Suite de Regresión, Cobertura de Código e Integración Continua — Hito 2

Este documento registra la evidencia técnica, el proceso sistemático de depuración, las pruebas de regresión explícitas, los reportes persistidos de cobertura y la configuración de integración continua correspondientes a los **Criterios 1, 3, 6 y 7** de la rúbrica del Hito N.º 2.

---

## 1. Evidencia Completa del Proceso de Depuración (Criterio 1)

Para demostrar la capacidad de depuración metódica sobre el proyecto real (usando [`.vscode/launch.json`](../../.vscode/launch.json), `pdb`/`debugpy` y las trazas de `LOGGING` en [`src/poki_koa/settings.py`](../../src/poki_koa/settings.py#L126-L148)), a continuación se documenta el ciclo completo **Reproducir → Hipótesis → Breakpoints y Trazas → Inspección Paso a Paso → Causa Raíz y Corrección → Verificación** aplicado sobre el flujo de telemetría y alertas neonatales (**Issue #51**).

### Paso 1: Reproducción del comportamiento anómalo
- **Contexto:** El endpoint `POST /api/cunas/{id}/telemetria/` recibe lecturas periódicas de sensores IoT conectados a una cuna neonatal.
- **Entrada de reproducción:**
  ```bash
  curl -i -X POST "http://127.0.0.1:8000/api/cunas/1/telemetria/" \
    -H "Content-Type: application/json" \
    -d '{"ritmo_cardiaco": -15, "spo2": 140}'
  ```
- **Comportamiento defectuoso observado antes de la corrección:**
  1. El endpoint devolvía `HTTP 200 OK` en lugar de `HTTP 400 Bad Request`.
  2. La cuna persistía en SQLite valores biológicamente imposibles (`ritmo_cardiaco = -15`, `spo2 = 140`).
  3. Al ejecutarse `cuna.save()`, la señal `post_save` invocaba `procesar_alertas_cuna(cuna)` y creaba en base de datos una alerta clínica falsa: `"Bradicardia severa: -15 bpm (umbral crítico < 80 bpm)"`.

### Paso 2: Formulación de hipótesis
- **Hipótesis 1 (Frontera HTTP en `CunaViewSet.telemetria`):** La vista asigna dinámicamente los atributos del diccionario `request.data` a la instancia `cuna` mediante `setattr(cuna, campo, data[campo])` y llama a `cuna.save()` sin validar previamente el tipo ni el rango fisiológico neonatal de los campos entrantes.
- **Hipótesis 2 (Propagación por señal `post_save`):** Como Django ejecuta `cuna_post_save_alertas_handler` ([`src/cunas/signals.py:17`](../../src/cunas/signals.py#L17)) inmediatamente dentro de `cuna.save()`, cualquier número negativo o fuera de rango persiste y dispara `evaluar_signos_vitales()`, donde `-15 < 80` se interpreta erróneamente como bradicardia crítica.

### Paso 3: Colocación de Breakpoints y Trazas de Diagnóstico
Se utiliza el perfil **`Django: Depurar Suite de Pruebas (cunas)`** (o **`Django: Servidor Entregable 2`**) de [`.vscode/launch.json`](../../.vscode/launch.json) colocando tres puntos de interrupción:
1. **Breakpoint 1:** [`src/cunas/views.py` línea 164](../../src/cunas/views.py#L164) — Entrada de validación en `CunaViewSet.telemetria`.
2. **Breakpoint 2:** [`src/cunas/views.py` línea 235](../../src/cunas/views.py#L235) — Iteración de asignación `for campo in campos_actualizables:` previo a `cuna.save()`.
3. **Breakpoint 3:** [`src/cunas/alertas.py` línea 234](../../src/cunas/alertas.py#L234) — Procesamiento de anomalías y deduplicación en `procesar_alertas_cuna`.

### Paso 4: Ejecución Paso a Paso (`Step Over` / `Step Into`) e Inspección de Variables

| Punto de Parada | Acción en el Depurador | Variables Inspeccionadas (Panel Watch / `pdb`) | Hallazgo Confirmado |
| :--- | :--- | :--- | :--- |
| **BP 1:** `views.py:164` | Pausa inicial al recibir el `POST` | • `cuna.identificador` = `'C-TEST'`<br>• `cuna.ritmo_cardiaco` = `125` (valor previo sano)<br>• `data` = `{'ritmo_cardiaco': -15}`<br>• `ritmo` = `-15` | El payload llega como `int` negativo (`-15`). |
| **BP 1 → línea 166** | `Step Over (F10)` sobre la guarda `type(ritmo) not in (int, float) or not (1 <= ritmo <= 260)` | • `1 <= ritmo <= 260` evalúa a `False` | La condición defensiva atrapa el valor inválido antes de modificar `cuna`. |
| **BP 2:** `views.py:235` *(con payload válido pero crítico: `ritmo_cardiaco=72`)* | `Step Over (F10)` hasta `cuna.save()` y `Step Into (F11)` hacia la señal `post_save` | • `campos_modificados` = `['ritmo_cardiaco']`<br>• `cuna.ritmo_cardiaco` = `72` | Solo cuando todos los campos cumplen su contrato en la frontera se ejecuta `cuna.save()`. |
| **BP 3:** `alertas.py:234` | `Step Into (F11)` dentro de `procesar_alertas_cuna` | • `anomalias` = `[{'tipo': 'ritmo_cardiaco', 'nivel': 'Critica', 'valor_leido': 72.0, ...}]`<br>• `alerta_activa` = `None` (1ª vez) o `<Alerta: Critica>` (2ª vez) | Confirma la deduplicación: si ya existe alerta activa del mismo nivel, actualiza `fecha_hora` y `valor_leido` sin duplicar filas. |

### Paso 5: Localización de la Causa Raíz y Corrección Aplicada
- **Causa raíz:** Ausencia de precondiciones defensivas en la frontera HTTP (`CunaViewSet.telemetria`) antes de mutar la entidad `Cuna`. Además, en Python `isinstance(True, (int, float))` es `True` porque `bool` hereda de `int`, lo que permitía que un booleano `True` pasara como `1`.
- **Corrección implementada en [`src/cunas/views.py` líneas 163–226](../../src/cunas/views.py#L163-L226):**
  - Se reemplazó `isinstance(..., (int, float))` por `type(valor) in (int, float)` para rechazar booleanos.
  - Se agregaron guardas explícitas para todos los campos de telemetría (`ritmo_cardiaco` `1..260`, `spo2` `0..100`, `temperatura` `25.0..45.0`, `estado_sueno` en `{"Dormido", "Despierto"}` y booleanos estrictos para `canula_ok` y `via_iv_activa`).
  - Se añadieron trazas `logger.info` (sanitizada: solo registra `cuna.identificador` por privacidad clínica) y `logger.warning` para cada rechazo en la frontera.

### Paso 6: Verificación de la Solución
Ejecutando la suite de telemetría y regresión:
```bash
uv run poki_koa test cunas.tests.APITelemetriaCunaTestCase cunas.tests.RegresionSuiteTestCase -v 2
```
Se observa en consola la traza exacta y la aprobación de las pruebas sin alterar la base de datos:
```text
[INFO] 2026-10-27 20:40:50 cunas.views: Recibida telemetría para cuna C-REG-01
[WARNING] 2026-10-27 20:40:50 cunas.views: Telemetría anómala detectada en cuna C-REG-01: ritmo cardíaco inválido (-15)
test_regresion_issue_51_telemetria_anomala_no_corrompe_estado_ni_crea_alerta ... ok
```

---

## 2. Suite de Regresión y Pruebas Automatizadas (Criterios 4, 5 y 6)

El proyecto cuenta con **71 pruebas automatizadas** divididas en dos niveles:

1. **Suite de Django (`src/cunas/` — 57 pruebas):**
   - Incluye modelos, endpoints REST, contratos con `Mock`/`@patch`, restricciones SQL, migraciones y la clase explícita **`RegresionSuiteTestCase`**.
   - Comando:
     ```bash
     uv run poki_koa test -v 2
     ```
2. **Suite Unitaria Aislada de Dominio (`test/` — 14 pruebas en 0.002s):**
   - Archivos: [`test/test_operacion2.py`](../../test/test_operacion2.py) y [`test/test_operacion3.py`](../../test/test_operacion3.py), usando `RepositorioFake` en memoria sin Django ni SQLite.
   - Comando:
     ```bash
     PYTHONPATH=src uv run python -m unittest discover -s test -v
     ```

### Catálogo de Pruebas de Regresión Explícitas

Para facilitar su identificación inmediata e individual, [`src/cunas/tests.py`](../../src/cunas/tests.py#L698-L778) incluye la clase **`RegresionSuiteTestCase`** cuyos métodos llevan el prefijo `test_regresion_`:

| Prueba de Regresión | Comando Directo | Qué Defecto Histórico o Contrato Protege |
| :--- | :--- | :--- |
| `RegresionSuiteTestCase.test_regresion_issue_51_telemetria_anomala_no_corrompe_estado_ni_crea_alerta` | `uv run poki_koa test cunas.tests.RegresionSuiteTestCase.test_regresion_issue_51_telemetria_anomala_no_corrompe_estado_ni_crea_alerta -v 2` | Impide que lecturas fuera de rango (`-15 bpm`) modifiquen la cuna o disparen alertas falsas (Issue #51). |
| `RegresionSuiteTestCase.test_regresion_issue_54_doble_resolucion_alerta_retorna_409_conflict` | `uv run poki_koa test cunas.tests.RegresionSuiteTestCase.test_regresion_issue_54_doble_resolucion_alerta_retorna_409_conflict -v 2` | Impide que resolver una alerta ya inactiva devuelva `200 OK`; exige `409 Conflict` (Issue #54). |
| `RegresionSuiteTestCase.test_regresion_issue_57_doble_administracion_medicamento_retorna_409_conflict` | `uv run poki_koa test cunas.tests.RegresionSuiteTestCase.test_regresion_issue_57_doble_administracion_medicamento_retorna_409_conflict -v 2` | Impide que un medicamento `Administrado` vuelva a confirmarse (Issue #57). |
| `IdentificadorMigrationTest.test_preserva_datos_y_completa_identificadores_sin_colisiones` | `uv run poki_koa test cunas.test_migrations.IdentificadorMigrationTest -v 2` | Verifica con `MigrationExecutor` la migración `0008` → `0009` ante pacientes sin identificador o con colisiones (`BEB-MIG-1` → `BEB-MIG-1-1`). |
| `APITelemetriaCunaTestCase.test_log_telemetria_no_incluye_lecturas_clinicas` | `uv run poki_koa test cunas.tests.APITelemetriaCunaTestCase.test_log_telemetria_no_incluye_lecturas_clinicas -v 2` | Verifica con `@patch` que los logs no expongan signos vitales ni nombres de pacientes. |

---

## 3. Cobertura de Código y Artefactos Persistidos (Criterio 6)

La herramienta `coverage.py` está configurada en [`pyproject.toml`](../../pyproject.toml#L39-L60) con `branch = true` (midiendo **líneas, módulos y ramas**) y `fail_under = 85`.

### Artefactos de Cobertura Persistidos en el Repositorio

Además de generarse en local y publicarse como artefacto en GitHub Actions, el reporte completo se encuentra versionado en [`qa/entrega2/cobertura/`](../../qa/entrega2/cobertura/) como evidencia directamente inspeccionable:
- **Reporte HTML interactivo:** [`qa/entrega2/cobertura/html/index.html`](../../qa/entrega2/cobertura/html/index.html)
- **Reporte XML (Cobertura estándar CI):** [`qa/entrega2/cobertura/coverage.xml`](../../qa/entrega2/cobertura/coverage.xml)
- **Reporte JSON detallado:** [`qa/entrega2/cobertura/coverage.json`](../../qa/entrega2/cobertura/coverage.json)
- **Resumen textual de consola:** [`qa/entrega2/cobertura/reporte-cobertura.txt`](../../qa/entrega2/cobertura/reporte-cobertura.txt)

### Comandos para Regenerar y Consultar la Cobertura

```bash
uv run coverage erase
uv run coverage run src/manage.py test cunas -v 2
PYTHONPATH=src uv run coverage run -a -m unittest discover -s test -v
uv run coverage report -m --fail-under=85
uv run coverage html -d qa/entrega2/cobertura/html
```

### Tabla de Resultados (92% Global — 100% en Servicios de Dominio)

```text
Name                                Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------------
src/cunas/alertas.py                   91      6     52      5    92%   37, 120, 218, 255, 264-265, 288->291
src/cunas/alertas_service.py           35      0     12      0   100%
src/cunas/medicamentos.py              35      0     12      0   100%
src/cunas/models.py                   102      3      0      0    97%   212, 256, 369
src/cunas/repositories.py              11      1      2      1    85%   33
src/cunas/repositories_alertas.py      13      1      2      1    87%   49
src/cunas/serializers.py              117     10     20      3    88%   55, 62, 82-84, 138-139, 242-244
src/cunas/services.py                  26      0      8      0   100%
src/cunas/signals.py                    9      1      2      1    82%   25
src/cunas/urls.py                      12      0      0      0   100%
src/cunas/views.py                    150     12     58     11    88%   87, 101, 106, 116, 123-127, 134, 212->225, 255->258, 338, 350, 354
-------------------------------------------------------------------------------
TOTAL                                 601     34    168     22    92%
```

### Justificación Técnica de Exclusiones (`[tool.coverage.run] omit`)
Se omiten de la medición porcentual únicamente archivos de infraestructura o autogenerados que no contienen reglas de negocio en ejecución: `*/migrations/*` (la migración crítica `0009` tiene su propio test en `test_migrations.py`), `*/management/*` (utilidades CLI de desarrollo), `*/admin.py`, `*/apps.py` y `*/test*.py`.

---

## 4. Flujo de Integración Continua (Criterio 7)

El workflow [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) se ejecuta en cada `push` y `pull_request` y verifica automáticamente:
1. `uv sync --locked` (integridad de dependencias).
2. `uv run ruff check src test scripts` (0 errores de linter/estilo).
3. `uv run poki_koa makemigrations --check --dry-run` (consistencia de modelos vs. migraciones).
4. `uv run python scripts/verificar_entrega2.py --static` (validación de matriz de 44 casos API).
5. Ejecución de las 71 pruebas bajo `coverage`, validación de umbral `--fail-under=85` y publicación del artefacto `reporte-cobertura-hito2` (`coverage.xml` + `htmlcov/`).
