# Pruebas de Regresión y Cobertura — Hito 2

## 1. Ejecución de las pruebas

El proyecto tiene **71 pruebas** separadas en dos grupos:

1. **Pruebas con Django (57 tests en `src/cunas/`):** prueban modelos, endpoints, contratos con `Mock`/`@patch`, migraciones y regresión.
   ```bash
   uv run poki_koa test -v 2
   ```
2. **Pruebas unitarias en memoria (14 tests en `test/`):** prueban `AlertaService` (`test/test_operacion2.py`) y `MedicamentoService` (`test/test_operacion3.py`) usando `RepositorioFake`, sin levantar Django ni usar SQLite.
   ```bash
   PYTHONPATH=src uv run python -m unittest discover -s test -v
   ```

## 2. Pruebas de regresión

En `src/cunas/tests.py` está la clase `RegresionSuiteTestCase` con pruebas nombradas con el prefijo `test_regresion_`, además del test de migración en `src/cunas/test_migrations.py`:

- **`test_regresion_issue_51_telemetria_anomala_no_corrompe_estado_ni_crea_alerta`**: comprueba que un ritmo cardíaco inválido (`-15`) devuelva `400`, no cambie el valor guardado en la cuna y no cree alertas falsas.
- **`test_regresion_issue_54_doble_resolucion_alerta_retorna_409_conflict`**: comprueba que al intentar resolver una alerta que ya estaba inactiva responda `409 Conflict` en vez de `200 OK`.
- **`test_regresion_issue_57_doble_administracion_medicamento_retorna_409_conflict`**: comprueba que no se pueda administrar dos veces un mismo medicamento pendiente.
- **`IdentificadorMigrationTest`** (`src/cunas/test_migrations.py`): comprueba que al migrar de la migración `0008` a la `0009` no se pierdan bebés sin identificador ni ocurran choques de IDs repetidos.

Comando para correr solo la suite de regresión:

```bash
uv run poki_koa test cunas.tests.RegresionSuiteTestCase cunas.test_migrations.IdentificadorMigrationTest -v 2
```

## 3. Cobertura de código (`coverage`)

La herramienta `coverage` está configurada en `pyproject.toml` con `branch = true` para medir líneas y ramas, exigiendo un mínimo de **85%**.

Comandos para medir y ver el reporte:

```bash
uv run coverage erase
uv run coverage run src/manage.py test cunas
PYTHONPATH=src uv run coverage run -a -m unittest discover -s test
uv run coverage report -m
```

### Resultado actual (92% total)

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

Los reportes generados están guardados en `qa/hito2/cobertura/`:
- Reporte HTML: [qa/hito2/cobertura/html/index.html](../../qa/hito2/cobertura/html/index.html)
- Reporte XML: [qa/hito2/cobertura/coverage.xml](../../qa/hito2/cobertura/coverage.xml)
- Resumen en texto: [qa/hito2/cobertura/reporte-cobertura.txt](../../qa/hito2/cobertura/reporte-cobertura.txt)

**Archivos excluidos en `pyproject.toml`:** se omiten `migrations/*`, `management/*`, `admin.py`, `apps.py` y los propios archivos `test*.py` porque son archivos generados o comandos de consola, de modo que el porcentaje refleje solo la lógica de la aplicación.
