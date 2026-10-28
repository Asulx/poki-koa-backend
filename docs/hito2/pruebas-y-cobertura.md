# Pruebas de Regresión y Cobertura — Hito 2

## 1. Ejecución de las suites de pruebas

El proyecto cuenta con **71 pruebas automatizadas** divididas en dos suites:

1. **Suite Django (57 pruebas en `src/cunas/`):** verifica modelos, endpoints REST, contratos con `Mock`/`@patch`, migraciones y regresión.
   ```bash
   uv run poki_koa test -v 2
   ```
2. **Suite unitaria aislada en memoria (14 pruebas en `test/`):** verifica `AlertaService` (`test/test_operacion2.py`) y `MedicamentoService` (`test/test_operacion3.py`) usando `RepositorioFake` sin iniciar Django ni usar SQLite.
   ```bash
   PYTHONPATH=src uv run python -m unittest discover -s test -v
   ```

---

## 2. Las 5 pruebas de regresión marcadas en el código

Las pruebas de regresión están marcadas en el código con comentarios `# [REGRESIÓN #1..#5]` y agrupadas además en la clase `RegresionSuiteTestCase` (`src/cunas/tests.py`):

| # | Prueba de regresión | Ubicación en código | Qué evita que vuelva a ocurrir |
|---|---|---|---|
| **1** | `test_telemetria_rechaza_ritmo_cardiaco_invalido_sin_guardar` y `RegresionSuiteTestCase.test_regresion_issue_51_...` | `src/cunas/tests.py` (líneas 350 y 731) | Que lecturas fuera de rango (`-15`, `0`, `261`, `None`) en telemetría modifiquen la cuna o creen alertas falsas (`Issue #51`). |
| **2** | `test_log_telemetria_no_incluye_lecturas_clinicas` | `src/cunas/tests.py` (línea 386) | Que los logs de telemetría vuelvan a imprimir signos vitales o datos sensibles del bebé. |
| **3** | `IdentificadorMigrationTest.test_preserva_datos_y_completa_identificadores_sin_colisiones` | `src/cunas/test_migrations.py` (línea 9) | Que la migración `0008` → `0009` falle o pierda pacientes cuando había identificadores vacíos o repetidos (`Issue #54`). |
| **4** | `test_contrato_respuesta_listado_bebes_para_frontend` | `src/cunas/tests.py` (línea 140) | Que cambios en el backend eliminen alias o campos que consume el frontend React (`Issue #14`). |
| **5** | `AlertaIntegracionTest.test_endpoint_alerta_ya_resuelta` y `RegresionSuiteTestCase.test_regresion_issue_54_...` / `57` | `src/cunas/test_operacion2_integracion.py` (línea 68) y `src/cunas/tests.py` (líneas 747 y 769) | Que resolver una alerta ya inactiva o administrar un medicamento ya dado responda `200 OK` en vez de `409 Conflict` (`Issues #54 y #57`). |

Comando para ejecutar directamente las pruebas de regresión:

```bash
uv run poki_koa test cunas.tests.RegresionSuiteTestCase cunas.test_migrations.IdentificadorMigrationTest -v 2
```

---

## 3. Cobertura de código (`coverage`)

La configuración está en `pyproject.toml` (`[tool.coverage.run]` con `branch = true` y `[tool.coverage.report]` con `fail_under = 85`).

Comandos para ejecutar y ver el reporte:

```bash
uv run coverage erase
uv run coverage run src/manage.py test cunas
PYTHONPATH=src uv run coverage run -a -m unittest discover -s test
uv run coverage report -m
uv run coverage html -d qa/hito2/cobertura/html
```

### Resultado actual (92% total — 100% en los 3 servicios de dominio)

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
src/cunas/views.py                    150     12     58     11    88%   87, 101, 106, 116, 123-127, 134, 218->231, 261->264, 344, 356, 360
src/poki_koa/settings.py               22      0      0      0   100%
src/poki_koa/urls.py                    3      0      0      0   100%
-------------------------------------------------------------------------------
TOTAL                                 626     34    168     22    92%
```

### Reportes guardados en el repositorio (`qa/hito2/cobertura/`)
- **Reporte HTML navegable:** [`qa/hito2/cobertura/html/index.html`](../../qa/hito2/cobertura/html/index.html)
- **Reporte XML:** [`qa/hito2/cobertura/coverage.xml`](../../qa/hito2/cobertura/coverage.xml)
- **Reporte JSON:** [`qa/hito2/cobertura/coverage.json`](../../qa/hito2/cobertura/coverage.json)
- **Resumen en texto:** [`qa/hito2/cobertura/reporte-cobertura.txt`](../../qa/hito2/cobertura/reporte-cobertura.txt)

**Exclusiones (`omit` en `pyproject.toml`):** se excluyen `migrations/*`, `management/*`, `admin.py`, `apps.py` y `test*.py` para medir únicamente el código de negocio de la aplicación.

---

## 4. Referencia cruzada entre la matriz de casos (Bruno) y las pruebas automatizadas

Los casos de borde y error definidos en la matriz de pruebas de API ([`docs/entrega2/MATRIZ_CASOS.md`](../entrega2/MATRIZ_CASOS.md)) también están respaldados por pruebas automatizadas en Python:

| Casos de la matriz (`MATRIZ_CASOS.md`) | Regla o escenario verificado | Clase y método en las pruebas automatizadas |
|---|---|---|
| **B01, B11–B14, B18, B21** | Creación válida de paciente, pesos/fechas válidas y contrato de respuesta con relaciones | `APIBebeValidacionTestCase.test_bebe_valido_se_crea_correctamente` y `test_contrato_respuesta_listado_bebes_para_frontend` (`src/cunas/tests.py`) |
| **B02–B03** | Identificador obligatorio y único sin colisiones | `IdentificadorMigrationTest.test_preserva_datos_y_completa_identificadores_sin_colisiones` (`src/cunas/test_migrations.py`) |
| **B08–B10** | Rechazo de peso `0` o negativo (`<= 0`) con HTTP 400 | `APIBebeValidacionTestCase.test_peso_cero_retorna_400` y `test_peso_negativo_retorna_400` (`src/cunas/tests.py`) |
| **B15** | Rechazo de fecha de nacimiento futura (`mañana`) con HTTP 400 | `APIBebeValidacionTestCase.test_fecha_nacimiento_futura_retorna_400` (`src/cunas/tests.py`) |
| **M01, M17, M18, M21** | Creación, consulta, `PATCH` y `PUT` en `/api/catalogo-medicamentos/` | `CatalogoAPITest.test_create_retrieve_update` (`src/cunas/test_catalogo.py`) |
| **M04, M06, M10, M13** | Valores límite válidos: largo `150`, `dosis_mg = 0.01`, `stock = 1` y máximos | `CatalogoAPITest.test_inclusive_limits` (`src/cunas/test_catalogo.py`) |
| **M02, M03, M05, M07–M09, M11, M12, M14–M16** | Campos vacíos, largo `151`, dosis `0`/`-0.01`/`0.001`/no numérica, stock `0`/`-1`/decimal/booleano | `CatalogoAPITest.test_invalid_creation_does_not_persist` y `test_database_rejects_nonpositive_values` (`src/cunas/test_catalogo.py`) |
| **M19, M22** | Edición inválida (`PATCH`/`PUT`) es atómica y no guarda cambios parciales | `CatalogoAPITest.test_invalid_update_is_atomic` (`src/cunas/test_catalogo.py`) |
| **M20 + bloqueo DELETE** | Producto inexistente (`404`) y prohibición de borrado (`405`) | `CatalogoAPITest.test_missing_product_and_unsupported_delete` (`src/cunas/test_catalogo.py`) |
