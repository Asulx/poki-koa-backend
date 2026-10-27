# Suite de Regresión, Cobertura de Código, Integración Continua y Depuración — Hito 2

Este documento registra la configuración, los comandos reproducibles y la evidencia técnica correspondientes a los criterios de **Capacidad de Depuración (Criterio 1)**, **Suite de Regresión y Cobertura de Código (Criterio 6)** e **Integración Continua y Mantenibilidad (Criterio 7)** del Hito N.º 2.

---

## 1. Suite de Regresión y Pruebas Automatizadas

El proyecto cuenta con una suite automatizada dividida en dos niveles complementarios que suman **68 pruebas automatizadas**:

1. **Suite de Integración, Modelos, Contratos, Migraciones y Regresión (Django Test Runner — 54 pruebas):**
   - Archivos: [`src/cunas/tests.py`](../../src/cunas/tests.py), [`src/cunas/test_catalogo.py`](../../src/cunas/test_catalogo.py), [`src/cunas/test_migrations.py`](../../src/cunas/test_migrations.py) y [`src/cunas/test_operacion2_integracion.py`](../../src/cunas/test_operacion2_integracion.py).
   - Comando:
     ```bash
     uv run poki_koa test -v 2
     ```
2. **Suite Unitaria Aislada de Servicios de Dominio (`unittest` con `RepositorioFake` en memoria — 14 pruebas):**
   - Archivos: [`test/test_operacion2.py`](../../test/test_operacion2.py) (7 pruebas para `AlertaService.resolver_alerta`) y [`test/test_operacion3.py`](../../test/test_operacion3.py) (7 pruebas para `MedicamentoService.administrar`).
   - Comando:
     ```bash
     PYTHONPATH=src uv run python -m unittest discover -s test -v
     ```

### Catálogo de Pruebas de Regresión

Las siguientes pruebas protegen defectos corregidos históricamente y contratos críticos entre capas para impedir regresiones en cambios futuros:

| ID / Issue | Prueba de Regresión | Ubicación | Defecto o Contrato que Protege |
| :--- | :--- | :--- | :--- |
| **Issue #51** | `APITelemetriaCunaTestCase.test_telemetria_rechaza_ritmo_cardiaco_invalido_sin_guardar` | [`src/cunas/tests.py`](../../src/cunas/tests.py#L348-L356) | Evita que lecturas nulas, no numéricas, `<= 0` o `> 260 bpm` en `POST /api/cunas/{id}/telemetria/` sobrescriban el estado de la cuna o generen alertas falsas. |
| **Privacidad Clínica** | `APITelemetriaCunaTestCase.test_log_telemetria_no_incluye_lecturas_clinicas` | [`src/cunas/tests.py`](../../src/cunas/tests.py#L368-L374) | Verifica mediante `@patch("cunas.views.logger.info")` que el log de telemetría registre únicamente el identificador de la cuna y nunca datos sensibles del paciente. |
| **Issue #54 (Migración)** | `IdentificadorMigrationTest.test_preserva_datos_y_completa_identificadores_sin_colisiones` | [`src/cunas/test_migrations.py`](../../src/cunas/test_migrations.py#L8-L53) | Verifica con `MigrationExecutor` la transición `0008` → `0009` con registros previos sin identificador (`None`, `""`, `"  "`) o con colisiones (`"BEB-MIG-1"`), asegurando cero pérdida de datos e idempotencia al revertir/reaplicar. |
| **Issue #14 (Contrato UI)** | `APIBebeValidacionTestCase.test_contrato_respuesta_listado_bebes_para_frontend` | [`src/cunas/tests.py`](../../src/cunas/tests.py#L139-L192) | Asegura que `GET /api/bebes/` mantenga todos los campos y alias calculados requeridos por el frontend React (`nombre`, `medico_responsable`, `numero_cuna`, `estado_canula`, `via_intravenosa`, `signos_vitales`). |
| **Issue #54 (Alertas)** | `AlertaIntegracionTest.test_endpoint_alerta_ya_resuelta` | [`src/cunas/test_operacion2_integracion.py`](../../src/cunas/test_operacion2_integracion.py#L68-L84) | Garantiza que intentar resolver por segunda vez una alerta ya inactiva retorne `HTTP 409 Conflict` en lugar de `HTTP 200 OK`. |

---

## 2. Cobertura de Código (Líneas, Módulos y Ramas)

Se utiliza `coverage.py` (`coverage>=7.6.0`), declarado en el grupo `dev` de [`pyproject.toml`](../../pyproject.toml) con medición de **sentencias (`Stmts`) y bifurcaciones lógicas (`Branch = true`)** y un umbral mínimo obligatorio de **85%** (`fail_under = 85`).

### Comandos para Ejecutar y Generar el Reporte de Cobertura

```bash
# 1. Limpiar mediciones previas
uv run coverage erase

# 2. Medir cobertura sobre la suite de pruebas de Django (54 tests)
uv run coverage run src/manage.py test cunas

# 3. Acumular (-a) la cobertura de las pruebas unitarias aisladas (14 tests)
PYTHONPATH=src uv run coverage run -a -m unittest discover -s test

# 4. Mostrar reporte detallado en consola con líneas y ramas faltantes (-m)
uv run coverage report -m

# 5. (Opcional) Generar reporte interactivo HTML en htmlcov/index.html
uv run coverage html
```

### Resultado Actual de Cobertura (92% Global — 100% en Servicios de Dominio)

```text
Name                                Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------------
src/cunas/alertas.py                   91      5     52      4    94%   37, 218, 255, 264-265, 288->291
src/cunas/alertas_service.py           35      0     12      0   100%
src/cunas/medicamentos.py              34      0     12      0   100%
src/cunas/models.py                   102      3      0      0    97%   212, 256, 362
src/cunas/repositories.py              11      1      2      1    85%   24
src/cunas/repositories_alertas.py      13      1      2      1    87%   49
src/cunas/serializers.py              117     10     20      3    88%   55, 62, 82-84, 138-139, 242-244
src/cunas/services.py                  26      0      8      0   100%
src/cunas/signals.py                    9      1      2      1    82%   25
src/cunas/urls.py                      12      0      0      0   100%
src/cunas/views.py                    130     12     42     10    86%   87, 101, 106, 116, 123-127, 134, 196->199, 279, 291, 295
-------------------------------------------------------------------------------
TOTAL                                 580     33    152     20    92%
```

### Interpretación y Justificación Técnica de Exclusiones (`[tool.coverage.run] omit`)

En [`pyproject.toml`](../../pyproject.toml) se excluyen de la métrica porcentual únicamente archivos de infraestructura o código autogenerado que no forman parte de la lógica de negocio en tiempo de ejecución:
- `*/migrations/*`: Esquemas autogenerados por Django (la migración crítica de datos `0009` cuenta con su propia prueba dedicada en `src/cunas/test_migrations.py`).
- `*/management/*`: Comandos CLI auxiliares de desarrollo (`make_crud.py`, `simular_alertas.py`, `preparar_entregable.py`).
- `*/admin.py` y `*/apps.py`: Configuración declarativa del panel administrativo de Django.
- `*/test*.py`: Archivos de prueba (para medir exclusivamente el código productivo bajo prueba).

Los tres servicios centrales con contratos explícitos (`src/cunas/services.py`, `src/cunas/alertas_service.py` y `src/cunas/medicamentos.py`) alcanzan un **100% de cobertura tanto en líneas como en ramas**.

---

## 3. Flujo de Integración Continua (CI)

El archivo [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) define el pipeline de GitHub Actions que se ejecuta automáticamente ante cada `push` y `pull_request` sobre las ramas `main` y `desarrollo` (además de ramas `feat/**`, `feature/**` y `fix/**`).

### Etapas Verificadas Automáticamente por el Pipeline

1. **Sincronización determinista (`uv sync --locked`):** Garantiza que el entorno se construya exactamente con las versiones fijadas en `uv.lock`.
2. **Calidad estática y linter (`uv run ruff check src test scripts`):** Impide integrar código con errores de sintaxis, importaciones no usadas, problemas de zona horaria (`DTZ`) o violaciones de estilo.
3. **Integridad de migraciones (`uv run poki_koa makemigrations --check --dry-run`):** Verifica que ningún cambio en `models.py` quede sin su migración correspondiente.
4. **Validación estática de artefactos QA (`uv run python scripts/verificar_entrega2.py --static`):** Comprueba la consistencia de los 44 casos de prueba y los datos demo del Entregable 2.
5. **Ejecución de pruebas y umbral de cobertura (`coverage run` + `coverage report -m --fail-under=85`):** Ejecuta las 54 pruebas de Django y las 14 pruebas unitarias aisladas midiendo líneas y ramas; si cualquier prueba falla o la cobertura cae por debajo del 85%, el job falla y bloquea la integración.

---

## 4. Depuración y Trazabilidad (`.vscode/launch.json` y `LOGGING`)

Para facilitar la depuración interactiva con breakpoints, ejecución paso a paso e inspección de variables:

1. **Perfiles de Depuración en VS Code ([`.vscode/launch.json`](../../.vscode/launch.json)):**
   - `Django: Servidor de Desarrollo (Poki Koa)`: Levanta `manage.py runserver --noreload` con el depurador adjunto.
   - `Django: Servidor Entregable 2 (Datos Demo Aislados)`: Levanta el servidor sobre `db_entregable.sqlite3`.
   - `Django: Depurar Suite de Pruebas (cunas)`: Permite colocar breakpoints dentro de cualquier vista, servicio o test de `src/cunas/` y recorrer la ejecución paso a paso.
   - `Unittest: Depurar Pruebas Aisladas (test/)`: Permite depurar `test_operacion2.py` y `test_operacion3.py` con `RepositorioFake`.

2. **Trazas en Consola (`LOGGING` en [`src/poki_koa/settings.py`](../../src/poki_koa/settings.py#L126-L148)):**
   - Se configuró el logger `cunas` con nivel `INFO` hacia `StreamHandler` con el formato `[%(levelname)s] %(asctime)s %(name)s: %(message)s`.
   - Al recibir telemetría en `POST /api/cunas/{id}/telemetria/`, el sistema emite:
     - `[INFO] ... cunas.views: Recibida telemetría para cuna <ID>` (traza operacional sanitizada sin datos sensibles del paciente).
     - `[WARNING] ... cunas.views: Telemetría anómala detectada en cuna <ID>: ritmo cardíaco inválido (<valor>)` (cuando la validación defensiva rechaza un valor fuera del rango neonatal 1–260 bpm).
