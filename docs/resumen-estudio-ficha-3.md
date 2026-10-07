# Resumen de estudio: implementación y Ficha de operación 3

## 1. Qué pedía la tarea

La guía de la Unidad 2.2 del curso Taller de Programación Avanzada pide aplicar construcción para la verificación a operaciones reales del proyecto:

- Declarar precondiciones, postcondiciones e invariantes.
- Rechazar entradas incorrectas temprano mediante validación defensiva.
- Usar aserciones para comprobar supuestos internos.
- Hacer explícita una dependencia para sustituirla durante las pruebas.
- Demostrar una ejecución válida y al menos dos inválidas.

Este trabajo cubre la **Ficha de operación 3: administración de medicación/paciente**. Telemetría (Ficha 1) y alertas (Ficha 2) quedan fuera de esta entrega. Se realizó en la rama `feat/tarea-ficha-3`.

## 2. Cómo se eligió la operación

Primero se revisaron la guía DOCX, las diapositivas y el código del repositorio. Aunque el proyecto se llama Poki Koa, su backend utiliza **Python, Django y Django REST Framework**. Se adaptó la solución a esas tecnologías, tal como permite la guía.

Se eligió una operación del dominio existente: **confirmar la administración de un medicamento pendiente**. El modelo `Medicamento` ya tenía los estados `Pendiente` y `Administrado`.

El comportamiento implementado es:

```text
POST /api/medicamentos/{id}/administrar/
Pendiente → Administrado
```

La solicitud no requiere cuerpo. Si tiene éxito, devuelve HTTP 200 con `id`, `paciente_id` y `estado`.

## 3. Qué se implementó y dónde

| Archivo | Responsabilidad |
| --- | --- |
| `src/cunas/services.py` | Servicio de negocio, contrato del repositorio, registro inmutable y errores controlados. |
| `src/cunas/repositories.py` | Adaptador que consulta y actualiza el modelo Django. |
| `src/cunas/views.py` | Endpoint que inyecta el repositorio y traduce errores del servicio a respuestas HTTP. |
| `test/test_operacion3.py` | Pruebas unitarias del servicio con un repositorio fake. |
| `src/cunas/tests.py` | Pruebas de integración del endpoint con la base de datos de pruebas. |

El recorrido de la solicitud es:

```text
Cliente → Vista DRF → MedicamentoService → DjangoMedicamentoRepository → Base de datos
```

La operación del servicio tiene esta firma:

```python
def administrar(self, medicamento_id: int | str) -> RegistroMedicamento:
```

## 4. Cómo se definió el contrato

Un contrato describe condiciones concretas que permiten revisar el comportamiento sin depender de todos los detalles del código.

| Parte | Pregunta que responde | Aplicación en esta operación |
| --- | --- | --- |
| Precondición | ¿Qué debe cumplirse antes de realizar el cambio? | ID válido, medicamento existente y estado `Pendiente`. |
| Postcondición | ¿Qué garantiza una ejecución exitosa? | Estado persistido como `Administrado`; se conservan ID, paciente y demás campos. |
| Invariante | ¿Qué regla interna debe mantenerse? | El medicamento pertenece a un paciente con ID entero positivo y la transición conserva ambas identidades. |

El ID aceptado es un entero entre 1 y `2**63 - 1`, o una cadena decimal ASCII equivalente sin espacios, signos ni ceros iniciales. Se rechazan booleanos, nulos y valores vacíos.

En Python los comentarios se escribieron como `# PRE:`, `# POST:` y `# INV:`.

## 5. Validación defensiva y aserciones

La validación defensiva comprueba datos externos y condiciones de uso antes de modificar el estado. Utiliza excepciones controladas, con mensajes que explican el rechazo.

| Situación | Excepción | HTTP | Mensaje exacto |
| --- | --- | --- | --- |
| ID mal formado, por ejemplo `"abc"` | `OperacionError` | 400 | `medicamento_id debe ser un entero positivo.` |
| Medicamento inexistente | `MedicamentoNoEncontrado` | 404 | `El medicamento no existe.` |
| Estado diferente de `Pendiente` | `EstadoNoPermitido` | 409 | `Solo se puede administrar un medicamento Pendiente.` |
| Registro cambiado o eliminado entre lectura y actualización | `EstadoNoPermitido` | 409 | `El medicamento cambió; recargue antes de administrar.` |

Un ID inválido se rechaza antes de consultar el repositorio. Un estado no permitido se rechaza antes de escribir.

Las aserciones comprueban supuestos internos después de obtener datos del colaborador: que el ID corresponda al solicitado, que el paciente tenga un ID válido y que el resultado conserve las identidades y tenga estado `Administrado`.

```python
assert resultado == replace(actual, estado="Administrado"), (
    "Invariante: solo cambia Pendiente a Administrado, conservando ID y paciente."
)
```

Si esta aserción falla, indica un incumplimiento interno del contrato. No representa una entrada incorrecta del cliente. Python puede deshabilitar las aserciones con `-O`; por eso las validaciones externas usan `if` y `raise`.

## 6. Cómo se hizo explícita la dependencia

El servicio recibe el repositorio por constructor:

```python
class MedicamentoService:
    def __init__(self, repositorio: MedicamentoRepository):
        self._repositorio = repositorio
```

`MedicamentoRepository` es un protocolo con dos métodos: `obtener` y `confirmar_pendiente`. El servicio usa ese contrato sin crear el repositorio ni importar los modelos Django.

En la vista se conecta la implementación real:

```python
servicio = MedicamentoService(DjangoMedicamentoRepository())
```

En las pruebas se conecta una implementación en memoria:

```python
repositorio = RepositorioFake()
servicio = MedicamentoService(repositorio)
resultado = servicio.administrar("1")
```

El fake definido en `test/test_operacion3.py` guarda un registro y cuenta lecturas y escrituras. Así se comprueba el resultado y también que un rechazo no haya modificado el estado, sin iniciar Django ni conectarse a una base de datos.

## 7. Cómo se evita una doble confirmación concurrente

Leer `Pendiente` y guardar después deja un intervalo en el que otra solicitud podría cambiar el registro. El repositorio realiza una actualización condicional:

```python
Medicamento.objects.filter(
    pk=medicamento.id,
    paciente_id=medicamento.paciente_id,
    estado="Pendiente",
).update(estado="Administrado")
```

La escritura ocurre solo si el registro todavía cumple esas condiciones. Si ninguna fila se actualiza, el repositorio devuelve `None` y el servicio responde con un conflicto controlado.

Esta protección corresponde a la operación implementada. Los endpoints CRUD existentes conservan su comportamiento y pueden cambiar el estado por separado. No se requirieron migraciones.

## 8. Cómo se verificó

Desde la raíz del repositorio, las pruebas aisladas se ejecutan con:

```bash
PYTHONPATH=src python -m unittest discover -s test -v
```

El resultado registrado fue **7 pruebas aprobadas**. Cubren:

1. ID válido: cambia a `Administrado`, conserva paciente e ID y realiza una escritura.
2. IDs inválidos: lanza `OperacionError` sin lecturas ni escrituras.
3. Medicamento ya administrado: lanza `EstadoNoPermitido` sin escribir.
4. Medicamento inexistente: lanza `MedicamentoNoEncontrado`.
5. Conflicto entre lectura y actualización: rechaza el cambio.
6. Colaborador que devuelve un resultado inconsistente: detecta la invariante rota.
7. Fallo del repositorio: propaga la excepción sin ocultarla.

Las pruebas de integración se ejecutan con las dependencias instaladas en `.venv`:

```bash
.venv/bin/python src/manage.py test cunas -v 1
```

El resultado registrado fue **11 pruebas aprobadas en total**, incluyendo las existentes y tres nuevas de API. Las nuevas verifican HTTP 200, 400, 404 y 409, la persistencia y la conservación del estado ante rechazos. Django usa una base de datos de pruebas separada.

## 9. Cómo se completó la ficha y el documento

Cada campo de la plantilla se rellenó con el comportamiento real del código:

- **Funcionalidad y operación:** nombre del proceso, clase, módulo, firma y endpoint.
- **Propósito:** resultado observable para quien llama a la API.
- **Precondiciones:** formato y rango del ID, existencia y estado permitido.
- **Postcondiciones:** cambio persistido y conservación de identidad y demás campos.
- **Invariante:** paciente válido e identidades conservadas.
- **Validación defensiva:** dos entradas inválidas con excepciones, mensajes y respuestas HTTP exactos.
- **Dependencia explícita:** repositorio recibido por constructor y sustitución por fake.
- **Evidencia:** archivos de prueba, comandos y resultados obtenidos.

La documentación quedó en [ejercicio-2-2.md](ejercicio-2-2.md). También se completó [prompt-paraclaude.md](../prompt-paraclaude.md) con los datos técnicos, el código y las instrucciones para preservar las otras fichas.

Después se editó directamente una copia del DOCX original: se localizaron la tabla de la Ficha 3 y sus ocho celdas de respuesta, y se sustituyeron únicamente sus textos. Se verificó que el XML fuera válido, que el archivo DOCX no tuviera errores de integridad y que el contenido fuera de esa tabla y los demás componentes del archivo permanecieran intactos. No se verificó visualmente la paginación en un procesador de textos.

Documento resultante: [Guía con Ficha 3 completa](Guia_Construccion_para_la_Verificacion_ficha-3-completa.docx). El original y las fichas 1 y 2 se conservaron.

## 10. Preguntas para repasar

- **¿Por qué usar un servicio?** Para concentrar las reglas de la operación y verificarlas sin depender de HTTP ni de Django.
- **¿Por qué inyectar el repositorio?** Para hacer visible el colaborador y sustituirlo por una implementación controlada en pruebas.
- **¿Por qué no usar `assert` para el ID recibido?** Porque es una entrada externa que requiere un rechazo controlado incluso si se deshabilitan las aserciones.
- **¿Qué demuestra un caso inválido además de la excepción?** Que no hubo una escritura indebida y que el estado anterior se conservó.
- **¿Cómo distinguir una postcondición de una invariante?** La postcondición describe el resultado exitoso de la acción; la invariante describe una regla que debe conservar el componente entre operaciones visibles.
- **¿Por qué actualizar con un filtro por estado?** Para comprobar el estado permitido en el momento de escribir, incluso si hubo otra solicitud después de la lectura.
