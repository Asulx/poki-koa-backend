# Proceso de Depuración — Hito 2

Registro del proceso de depuración aplicado en el módulo de telemetría y alertas de cunas (`Issue #51`).

## 1. Problema detectado y cómo reproducirlo

Al enviar lecturas de sensores al endpoint `POST /api/cunas/{id}/telemetria/` con valores fuera de rango (por ejemplo, ritmo cardíaco negativo o saturación mayor a 100%), el sistema guardaba los datos igual y generaba alertas clínicas falsas.

Comando para reproducir el fallo:

```bash
curl -i -X POST "http://127.0.0.1:8000/api/cunas/1/telemetria/" \
  -H "Content-Type: application/json" \
  -d '{"ritmo_cardiaco": -15, "spo2": 140}'
```

**Qué pasaba antes del arreglo:**
- Respondía `200 OK` en vez de `400 Bad Request`.
- Guardaba `-15` y `140` en la base de datos.
- Creaba una alerta crítica diciendo `"Bradicardia severa: -15 bpm"`.

## 2. Hipótesis

1. La vista `CunaViewSet.telemetria` (`src/cunas/views.py`) estaba copiando los campos recibidos en `request.data` directamente al modelo `Cuna` y llamando a `cuna.save()` sin revisar si los números tenían sentido.
2. Como el modelo `Cuna` tiene conectada una señal `post_save` (`src/cunas/signals.py`), apenas se ejecutaba `cuna.save()` se disparaba `procesar_alertas_cuna(cuna)` con el valor `-15`, y como `-15 < 80`, el motor creaba la alerta de bradicardia.

## 3. Uso del depurador (Breakpoints e inspección)

Usamos la configuración de `.vscode/launch.json` (`Django: Depurar Pruebas (cunas)`) colocando dos breakpoints:

- **Breakpoint 1:** `src/cunas/views.py` (inicio de las validaciones en `telemetria`).
- **Breakpoint 2:** `src/cunas/alertas.py` (función `procesar_alertas_cuna`, donde se revisan las anomalías).

Al ejecutar paso a paso (`F10` / `F11`) y revisar las variables vimos lo siguiente:

| Punto | Variables revisadas | Qué comprobamos |
|---|---|---|
| `views.py` (entrada) | `data = {'ritmo_cardiaco': -15}`<br>`cuna.ritmo_cardiaco = 130` | El valor anterior en la cuna era `130`, pero `data` traía `-15`. |
| `views.py` (validación) | `ritmo = -15` | Con la validación activa, entra al `if`, registra un `logger.warning` y devuelve `400` sin llegar a `cuna.save()`. |
| `alertas.py` (cuando el valor sí es válido, ej. `72`) | `anomalias = [{'tipo': 'ritmo_cardiaco', 'nivel': 'Critica', ...}]`<br>`alerta_activa = None` | Si ya existe una alerta activa del mismo tipo y nivel, solo actualiza la hora y el valor leído para no llenar la base de datos de alertas repetidas. |

## 4. Causa y corrección

La causa era la falta de validación en la entrada del endpoint antes de guardar, además de que en Python `isinstance(True, int)` da `True` (porque `bool` hereda de `int`).

**Solución aplicada en `src/cunas/views.py`:**
- Se validan todos los campos antes de modificar la cuna (`ritmo_cardiaco` entre 1 y 260, `spo2` entre 0 y 100, `temperatura` entre 25.0 y 45.0, `estado_sueno` válido y booleanos para `canula_ok` y `via_iv_activa`), usando `type(valor) in (int, float)` para no aceptar booleanos como números.
- Se agregaron logs en consola configurados en `src/poki_koa/settings.py` (`LOGGING`):
  - `logger.info`: registra que llegó telemetría indicando solo el código de la cuna (sin datos del paciente).
  - `logger.warning`: registra cuando se rechaza un valor fuera de rango.

## 5. Verificación

Se verificó ejecutando la prueba de regresión del issue:

```bash
uv run poki_koa test cunas.tests.RegresionSuiteTestCase.test_regresion_issue_51_telemetria_anomala_no_corrompe_estado_ni_crea_alerta -v 2
```

Salida en consola:

```text
[INFO] 2026-10-27 20:40:50 cunas.views: Recibida telemetría para cuna C-REG-01
[WARNING] 2026-10-27 20:40:50 cunas.views: Telemetría anómala detectada en cuna C-REG-01: ritmo cardíaco inválido (-15)
ok
```
