# Resultados de pruebas — Entregable 2

Corrida HTTP: 2026-10-15T01:34:45.412212-03:00 (America/Santiago).
Commit base: `cc5a49d147bf6b682f12732f06023ec86d8c3346`, con cambios locales sin commit.

Entorno: Python 3.15.0, Django 6.1, Django REST Framework 3.18.0.
Base utilizada: `src/db_entregable.sqlite3`, restablecida antes de la corrida.

## Resultados comprobados

- Suite Django: 39 pruebas aprobadas, incluidos seis métodos de prueba del catálogo con subcasos de validación y una prueba de migración de pacientes existentes.
- Solicitudes HTTP contra servidor Django local: 44 casos aprobados, 0 fallos.
- Las consultas posteriores verificaron persistencia y ausencia de cambios en los rechazos.
- Comprobación de Django: sin incidencias.
- Migraciones aplicadas en la base local y de demostración; modelos y migraciones sincronizados (`makemigrations --check --dry-run --noinput`).

Detalle de solicitudes, respuestas y aserciones: [resultado-http-local.json](../../qa/entrega2/resultado-http-local.json).
Hash SHA-256 del manifiesto ejecutado: `d4dbea403c744aefc7488a38d83cf42d854659d11966d6e49c45fbd7342f2bc7`.

| Caso | Objetivo | HTTP esperado | HTTP observado | Caso completo |
|---|---|---|---|---|
| B01 | Registro válido con médico existente | 201 | 201 | PASS |
| B02 | Identificador obligatorio ausente | 400 | 400 | PASS |
| B03 | Identificador ya registrado | 400 | 400 | PASS |
| B04 | Nombre vacío | 400 | 400 | PASS |
| B05 | Nombre de 199 caracteres | 201 | 201 | PASS |
| B06 | Nombre de 200 caracteres | 201 | 201 | PASS |
| B07 | Nombre de 201 caracteres | 400 | 400 | PASS |
| B08 | Peso no numérico | 400 | 400 | PASS |
| B09 | Peso -0.01 | 400 | 400 | PASS |
| B10 | Peso 0 | 400 | 400 | PASS |
| B11 | Peso 0.01 | 201 | 201 | PASS |
| B12 | Peso y fecha opcionales nulos | 201 | 201 | PASS |
| B13 | Fecha de nacimiento: ayer | 201 | 201 | PASS |
| B14 | Fecha de nacimiento: hoy | 201 | 201 | PASS |
| B15 | Fecha de nacimiento: manana | 400 | 400 | PASS |
| B16 | Sexo fuera del catálogo | 400 | 400 | PASS |
| B17 | Médico inexistente | 400 | 400 | PASS |
| B18 | Modificar diagnóstico sin perder otros datos | 200 | 200 | PASS |
| B19 | Edición inválida no guarda ni siquiera los campos válidos | 400 | 400 | PASS |
| B20 | Consultar paciente inexistente | 404 | 404 | PASS |
| B21 | Recuperar datos para edición y relaciones | 200 | 200 | PASS |
| B22 | Eliminar paciente libera cuna y elimina medicación asociada | 204 | 204 | PASS |
| M01 | Registro válido en catálogo | 201 | 201 | PASS |
| M02 | Nombre obligatorio | 400 | 400 | PASS |
| M03 | Principio activo vacío | 400 | 400 | PASS |
| M04 | Nombre de 150 caracteres | 201 | 201 | PASS |
| M05 | Nombre de 151 caracteres | 400 | 400 | PASS |
| M06 | Principio activo de 150 caracteres | 201 | 201 | PASS |
| M07 | Principio activo de 151 caracteres | 400 | 400 | PASS |
| M08 | Dosis no numérica | 400 | 400 | PASS |
| M09 | Dosis cero | 400 | 400 | PASS |
| M10 | Dosis mínima 0.01 mg | 201 | 201 | PASS |
| M11 | Dosis con exceso de decimales | 400 | 400 | PASS |
| M12 | Stock cero | 400 | 400 | PASS |
| M13 | Stock mínimo una unidad | 201 | 201 | PASS |
| M14 | Stock fraccionario | 400 | 400 | PASS |
| M15 | Stock obligatorio | 400 | 400 | PASS |
| M16 | Dosis obligatoria | 400 | 400 | PASS |
| M17 | Consulta para precarga | 200 | 200 | PASS |
| M18 | Modificar stock y conservar otros campos | 200 | 200 | PASS |
| M19 | Edición inválida no guarda cambios parciales | 400 | 400 | PASS |
| M20 | Producto inexistente | 404 | 404 | PASS |
| M21 | Modificar todos los campos | 200 | 200 | PASS |
| M22 | PUT incompleto conserva el producto | 400 | 400 | PASS |

## Ejecución en Bruno CLI

Fecha de inicio: 2026-10-15T01:45:37-03:00 (America/Santiago). Bruno CLI 4.2.1.
Ejecutor: agente de desarrollo, mediante CLI; no corresponde a una ejecución manual
realizada por un integrante del equipo. Servidor Django temporal y base independiente
`/tmp/poki-bruno-verificacion.sqlite3`, migrada y cargada con `datos_demo.json`.

- 44 casos, 94 solicitudes aprobadas, sin errores.
- 265 pruebas de estado, valores, errores por campo, cantidades persistidas y respuestas sin cuerpo: todas aprobadas.
- Orden: B01–B22 y M01–M22; las verificaciones `.vN` siguen inmediatamente a su caso.
- [Reporte JSON](../../qa/entrega2/resultado-bruno-cli.json) con solicitudes, respuestas y resultados.
- [Reporte HTML](../../qa/entrega2/resultado-bruno-cli.html) para consulta visual.
- [Colección ejecutada](../../qa/entrega2/bruno/) y [huellas de archivos](../../qa/entrega2/ejecucion-bruno.json).

## Ejecución del equipo en Bruno de escritorio

Responsable: Ricardo (reporte y captura aportados en el chat).
Versión: usebruno v4.2.1. Entorno: `Local`.
Finalización: 2026-10-15T01:48:36.802000-03:00 (America/Santiago), según la fecha del reporte.
Servidor: `http://127.0.0.1:8000`.

| Resultado | Cantidad |
|---|---|
| Casos completos aprobados | 44 (22 por API) |
| Solicitudes aprobadas | 94 de 94 |
| Solicitudes fallidas u omitidas | 0 |
| Verificaciones aprobadas | 265 de 265 |

Evidencia: [reporte HTML exportado por el equipo](../../qa/entrega2/resultado-bruno-equipo.html).
Se contrastaron las 94 respuestas incluidas en el reporte con los métodos, rutas,
estados y aserciones de `casos.json`; todos coincidieron. Los casos B01–B22 y
M01–M22 pasaron también sus verificaciones secundarias. La tabla de resultados
HTTP anterior queda corroborada por esta ejecución en la aplicación.

El reporte no identifica el commit ni acredita por sí solo qué archivo de base
de datos usó el servidor; no se infieren esos datos de la captura.

## Cambio de herramienta

Thunder Client 2.41.7 gratuito bloqueó las colecciones. El equipo utilizó Bruno
para ejecutar y exportar las pruebas. La aceptación de esta sustitución por el
docente sigue pendiente. La ejecución de escritorio ya está acreditada por el
reporte del equipo; los resultados CLI anteriores corresponden a otra corrida.
