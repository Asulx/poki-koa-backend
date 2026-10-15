# Conversación con Clarita Reviews

[Chat compartido](https://chatgpt.com/share/6ad05d09-6e64-83e9-8e7e-b441ce2b35c6)

### Usuario

Te entregaremos distintas historias de usuario para que realices una revisión a cada una, realiza las observaciones necesarias y comenta lo que tenga que aplicarse.  

Primera:

#### US-01 — Issue #15
Desarrollar formulario de gestión de pacientes (Registro y Edición)
Última actualización del issue: 2026-09-29T08:08:01Z.
Descripcion Historia
Como usuario del sistema (personal médico o administrativo) quiero contar con un formulario validado para el registro y edición de pacientes para poder ingresar y mantener actualizada su información sin cometer errores en los datos.
Criterios de aceptación
- Se implementó el componente del formulario para el registro de nuevos pacientes.
- Se adaptó el mismo formulario (o se creó uno equivalente) para la edición, el cual permite precargar los datos de un paciente existente.
- Se aplicaron validaciones en tiempo real (ej. campos obligatorios, formato correcto de correo electrónico, formato de RUT/DNI o teléfono).
 La interfaz muestra mensajes de error claros debajo de cada campo cuando no se cumple una validación.
 El botón de "Guardar" se deshabilita mientras existan errores en el formulario o mientras se esté procesando la petición (loading state).
…

### Clarita

¡Hola! Soy Clarita Reviews. Gracias por compartir la primera historia de usuario, US-01 — Issue #15: Gestión de pacientes.

He identificado tanto la historia de usuario como sus cinco criterios de aceptación.
Revisión preliminar

La historia presenta una estructura adecuada: identifica un rol, una necesidad y un beneficio. Además, los criterios de aceptación contemplan funcionalidades importantes, como el registro, la edición y la validación de información.

Antes de realizar la revisión completa, hay algunos aspectos que conviene considerar:

- Rol: Se mencionan usuarios médicos y administrativos. Será importante confirmar si ambos tienen los mismos permisos y necesidades.

- Alcance: La historia reúne el registro y la edición de pacientes. Conviene evaluar si representan una única necesidad funcional o si deberían abordarse por separado.

- Criterios de aceptación: Están redactados principalmente como tareas implementadas. Será necesario revisar si expresan comportamientos verificables desde la perspectiva del usuario.

Información necesaria para continuar

Para evaluar correctamente la historia, necesito conocer el modelo verbal de la solución informática.

Este modelo debe describir cómo el sistema de gestión de pacientes funcionará, qué procesos permitirá realizar y cómo interactuarán con él los distintos usuarios.

Es importante porque nos permitirá determinar si la US-01 y sus criterios de aceptación son coherentes con el alcance real del proyecto, siguiendo los lineamientos de los documentos de referencia.

¿Ya tienen definido el modelo verbal de la solución informática? Si lo comparten, podremos revisar esta primera historia con observaciones concretas y recomendaciones de mejora, y después continuar con las siguientes.

### Usuario

Ya tenemos definido el modelo verbal de gestión de pacientes de Poki Koa. Te lo resumo para que revisemos la US-01:

¿Qué hace?
 Centraliza los datos clínicos y demográficos de los recién nacidos en la UCI Neonatal. Cada bebé registrado es el eje del sistema: a él se asocian su cuna con telemetría en tiempo real, su neonatólogo responsable y su esquema de medicación.

¿Qué permite hacer?

- Admisión: registrar al bebé con ID único (ej. BEB-0001), nombre, sexo, edad, edad gestacional, peso al nacer y fecha de ingreso.
- Actualización: editar peso, diagnóstico, observaciones y plan de cuidados.
- Asignación: vincular o reasignar médico y cuna.
- Consulta: ver estado, signos vitales, alertas y medicamentos administrados.
- Egreso: cerrar la internación, liberar la cuna y conservar el historial.

¿Quién lo usa y para qué?

- Admisión: ingresa los datos de filiación. El sistema valida campos obligatorios, ID no duplicado y peso positivo.
- Neonatólogos: consultan sus pacientes y registran diagnósticos y plan de cuidados.
- Enfermería y matronas: verifican la identidad del bebé antes de medicar o asociarlo a los sensores de la cuna.

¿Cómo se implementa?

- Frontend (React SPA): formularios con validación en tiempo real, estados de carga, guardado deshabilitado si hay errores y mensajes claros.
- Backend (Django REST): endpoints en /api/bebes/ (POST, GET, PATCH/PUT, DELETE), con validación de unicidad y formato, y respuestas HTTP estándar (201, 400, 404).

…

### Clarita

¡Perfecto! Ahora contamos con el modelo verbal de la solución informática de Poki Koa, por lo que podemos revisar la US-01 considerando las funcionalidades, los roles y las reglas de negocio del sistema.
Revisión de US-01 — Issue #15

Título actual: Desarrollar formulario de gestión de pacientes (Registro y Edición)
Requiere ajustes

La historia tiene una intención funcional clara y un beneficio identificable. Sin embargo, presenta algunas oportunidades de mejora para alinearse con el modelo verbal.
#### 1. Observaciones sobre la historia de usuario

| Aspecto | Observación |
| --- | --- |
| Título | Es demasiado extenso y está orientado al desarrollo de una interfaz. Se recomienda utilizar nombres funcionales breves, como Registrar paciente o Editar paciente. |
| Rol | "Usuario del sistema (personal médico o administrativo)" es demasiado general. El modelo verbal establece responsabilidades diferentes para admisión y neonatólogos. |
| Funcionalidad | Se agrupan dos acciones: registrar y editar pacientes. Conviene evaluar si pueden convertirse en historias independientes. |
| Beneficio | Es comprensible, pero podría enfocarse más en el valor clínico o administrativo de mantener información confiable. |
| Alcance | No se distingue qué información puede registrar o modificar cada rol. |

Recomendación principal: Evaluar la separación del registro y la edición de pacientes, ya que tienen objetivos, permisos y escenarios de validación diferentes.
#### 2. Observaciones sobre los criterios de aceptación

| Criterio | Evaluación | Observación |
| --- | --- | --- |
| CA1. Formulario de registro | Mejorar | Describe una tarea implementada, pero no especifica qué debe ocurrir cuando se registra correctamente un bebé. |
| CA2. Formulario de edición | Mejorar | La precarga es pertinente, pero falta verificar que las modificaciones se guarden y puedan consultarse posteriormente. |
| CA3. Validaciones | Mejorar | Los ejemplos de correo, RUT/DNI y teléfono no coinciden necesariamente con los datos del recién nacido definidos en el modelo verbal. |
| CA4. Mensajes de error | Adecuado | Es verificable. Conviene relacionar cada mensaje con la validación correspondiente. |
| CA5. Botón Guardar | Adecuado | Es verificable y coherente con el modelo. Conviene precisar cuándo vuelve a habilitarse. |

#### 3. Escenarios que faltan considerar

Según el modelo verbal, sería conveniente revisar la cobertura de los siguientes comportamientos:

- Identificación única: impedir el registro de bebés con identificadores duplicados.

- Peso válido: rechazar valores de peso iguales o inferiores a cero.

- Campos obligatorios: identificar exactamente cuáles son necesarios durante la admisión.

- Registro exitoso: confirmar que los datos del recién nacido quedaron almacenados correctamente.

- Actualización exitosa: verificar que los cambios autorizados se conserven.

- Errores de guardado: definir el comportamiento cuando el sistema no consigue registrar o actualizar la información.

Estos escenarios pueden expresarse utilizando la estructura Dado – Cuando – Entonces, que facilita comprobar los resultados esperados.
#### 4. Coherencia con Poki Koa

Hay dos decisiones funcionales que deberían aclararse antes de aprobar esta historia.

Primera: el modelo verbal distingue la admisión inicial de la actualización clínica. Por ello, es importante establecer si el personal administrativo puede modificar información clínica o si esa responsabilidad corresponde exclusivamente a los neonatólogos.

Segunda: los criterios actuales mencionan datos genéricos de pacientes, mientras que Poki Koa está orientado específicamente a recién nacidos de la UCI Neonatal. Las validaciones deben corresponder a esa población y a los campos realmente definidos.
Resultado de la revisión

Historia de usuario
Requiere ajustes

Criterios de aceptación
Requieren ajustes

Coherencia con el modelo verbal
Parcialmente alineada

Conclusión: La US-01 tiene una base funcional adecuada, pero todavía no está lista para considerarse completamente validada. Las principales mejoras son delimitar los roles, revisar la separación entre registro y edición, y completar los escenarios de aceptación con las reglas específicas de Poki Koa.

Una pregunta para continuar: ¿Prefieren mantener el registro y la edición de pacientes en una sola historia de usuario o están dispuestos a separarlos en dos historias independientes?

### Usuario

En una sola historia.

### Clarita

¡Perfecto! Mantendremos el registro y la edición de pacientes en una sola historia de usuario (US-01).

Esta decisión es válida, ya que ambas funcionalidades trabajan sobre la información de un mismo paciente y pueden compartir el formulario.
Ajustes recomendados para la US-01

1. Título: Simplificarlo a Gestionar pacientes, utilizando un verbo en infinitivo y un objeto directo.

2. Rol: Precisar qué usuarios pueden registrar y editar información. Según el modelo verbal, admisión y neonatólogos tienen responsabilidades diferentes.

3. Descripción: Mantener ambas funcionalidades, pero enfocarse en la necesidad del usuario y no en la implementación del formulario.

#### 4. Criterios de aceptación: Conservar los cinco criterios existentes, ajustando su redacción para que describan comportamientos verificables mediante el formato Dado – Cuando – Entonces.

5. Cobertura funcional: Incorporar los escenarios de registro exitoso, edición exitosa, campos obligatorios, identificadores duplicados, peso inválido y errores al guardar.
Resultado

US-01: Aprobada en alcance, pendiente de ajustes de redacción y criterios de aceptación.

No es necesario dividirla, aunque conviene comprobar que su tamaño permita desarrollarla y probarla dentro de un sprint.

Antes de cerrar la revisión: ¿El personal de admisión podrá registrar y editar todos los datos del paciente, o los neonatólogos serán los únicos autorizados para modificar la información clínica?

### Usuario

Solo el personal medico, neonatólogos/matronas

### Clarita

¡Perfecto! Con esta aclaración podemos precisar mejor el alcance de la US-01 — Gestionar pacientes de Poki Koa.
Ajuste de la revisión

Rol: El personal médico, específicamente neonatólogos y matronas, será el responsable del registro y la edición de pacientes.

Esto permite resolver una de las principales observaciones de la historia original: el rol era demasiado general.
Observaciones que todavía deben aplicarse

1. Descripción de la HU: Sustituir el rol genérico por los roles médicos autorizados. El beneficio de mantener información actualizada y evitar errores es adecuado.

#### 2. Criterios de aceptación: Incorporar la validación de permisos para impedir que usuarios no autorizados registren o editen pacientes.

3. Validaciones: Alinear los campos obligatorios con los datos neonatales definidos en el modelo verbal, especialmente el identificador único y el peso positivo.

4. Registro y edición: Mantener ambas operaciones dentro de la misma historia, diferenciando sus escenarios de aceptación.
Estado actualizado

US-01 — Gestionar pacientes
Pendiente de ajustes menores

La historia ya tiene un alcance definido y roles identificados. Solo queda mejorar la precisión de sus criterios de aceptación para que sean completamente verificables.

¿Deseas que demos por finalizada la revisión de la US-01 con estas observaciones y continuemos con la US-02?

### Usuario

Continuamos con la siguiente issue, desde ahora en adelante, solo realiza una revisión concreta para aplicarla de inmediato sin preguntas constantes (me voy a quedar sin tokens):
#### US-02 — Issue #17
Desarrollar formulario de gestión de medicamentos (Registro y Modificación)
Última actualización del issue: 2026-09-02T20:36:57Z.
Descripcion Historia
Como usuario del sistema (farmacéutico o administrador), quiero contar con un formulario interactivo y validado para registrar y modificar medicamentos para mantener el catálogo actualizado y evitar errores críticos en el ingreso de datos (como dosis o stock incorrecto).
Criterios de aceptación
- Se implementó el componente de formulario para el registro de un nuevo medicamento, incluyendo los campos clave (ej. nombre, principio activo, miligramos/dosis, cantidad en stock).
- Se adaptó el formulario para permitir la modificación de un medicamento existente, precargando correctamente sus datos actuales.
- Se aplicaron validaciones de datos en tiempo real (ej. campos obligatorios, números positivos para el stock y dosis).
 La interfaz despliega mensajes de error claros y específicos debajo de los campos que no superan la validación.
 El botón de acción ("Guardar" o "Registrar") se deshabilita si el formulario contiene errores o si se encuentra en estado de carga (loading).
…

### Clarita

Revisión US-02 — Issue #17: Gestión de medicamentos

Estado: Requiere ajustes.
#### 1. Historia de usuario

- Título: Simplificar a Gestionar medicamentos.

- Rol: Precisar si farmacéuticos y administradores están autorizados para registrar y modificar medicamentos. Estos roles no aparecen definidos en el modelo verbal compartido de Poki Koa.

- Descripción: Evitar centrarse en el formulario interactivo. La necesidad principal es registrar y actualizar información de medicamentos.

- Beneficio: Es claro y pertinente, ya que busca mantener información confiable y prevenir errores.

- Alcance: Se pueden mantener registro y modificación en una misma HU, siempre que ambos procesos sean verificables.

#### 2. Criterios de aceptación

| CA | Observación para aplicar |
| --- | --- |
| CA1 | Especificar los campos obligatorios y el resultado esperado de un registro exitoso. |
| CA2 | Verificar que los datos se precarguen y que las modificaciones se almacenen correctamente. |
| CA3 | Definir las reglas exactas de validación. Aclarar si el stock admite cero y qué unidades corresponden a las dosis. |
| CA4 | Mantener el criterio, pero especificar que los mensajes indiquen claramente el error y cómo corregirlo. |
| CA5 | Mantener el criterio y definir cuándo se habilita nuevamente el botón. |

#### 3. Criterios faltantes

Se recomienda incorporar escenarios para:

- Registro exitoso y confirmación al usuario.

- Modificación exitosa de un medicamento.

- Prevención de medicamentos duplicados, si corresponde a las reglas del catálogo.

- Rechazo de dosis inválidas y cantidades de stock negativas.

- Manejo de errores cuando no se puede guardar la información.

- Restricción de registro y modificación según los permisos autorizados.

Los criterios deben describir comportamientos verificables mediante Dado – Cuando – Entonces, evitando expresiones como «Se implementó» o «Se adaptó».
#### 4. Coherencia con Poki Koa

El modelo verbal confirma que el sistema gestiona esquemas de medicación y permite consultar medicamentos administrados. Sin embargo, no especifica todavía la administración del catálogo, el control de stock ni los roles farmacéutico y administrador.

Por tanto, es necesario confirmar que estas funcionalidades forman parte del alcance de Poki Koa antes de aprobar la historia.
Resultado final

US-02: Pendiente de ajustes.

Prioridad de corrección: Validar la coherencia con el modelo verbal, precisar los roles autorizados, definir las reglas de validación y completar los escenarios de registro y modificación.

La historia tiene una base adecuada, pero requiere mayor precisión funcional para considerarse lista para desarrollo y pruebas.

### Usuario

#### US-03 — Issue #16
Desarrollo del listado de medicamentos
Última actualización del issue: 2026-09-02T20:44:13Z.
##Descripcion Historia
Como usuario del sistema (personal de farmacia o médico), quiero visualizar un listado estructurado de todos los medicamentos registrados para consultar rápidamente el catálogo, verificar el stock disponible y acceder a sus opciones de edición.
Criterios de aceptación
- Se implementó una vista principal con una tabla (Data Grid) o listado de tarjetas para mostrar los medicamentos.
 La tabla incluye las columnas con la información clave (ej. Nombre, Principio activo, Dosis, Stock actual).
 Los datos se consumen de manera dinámica utilizando el Servicio de medicamentos (desarrollado en el Issue #21#21).
- Se implementó paginación o scroll infinito para evitar la sobrecarga de la interfaz al mostrar muchos registros.
 Cada registro de la lista cuenta con un botón de acciones (ej. un ícono de "Editar") que redirige al formulario de modificación (Issue #17#17).
- Se implementó un estado de carga (loading spinner o skeleton) que se muestra mientras se obtienen los datos del servidor.hacer el listado de medicamentos
…

### Clarita

Revisión US-03 — Issue #16: Listado de medicamentos

Estado: Requiere ajustes menores.
#### 1. Historia de usuario

- Título: Simplificar a Listar medicamentos.

- Rol: Precisar los permisos del personal de farmacia y médico, especialmente respecto a la edición de medicamentos.

- Descripción: La necesidad y el beneficio son claros. Sin embargo, conviene separar la consulta del catálogo de los detalles sobre cómo se presenta la información.

- Alcance: Mantener el listado, la consulta de stock y el acceso a edición dentro de la misma historia, siempre que estén contemplados en los permisos del usuario.

#### 2. Criterios de aceptación

| CA | Observación para aplicar |
| --- | --- |
| CA1 | Evitar especificar componentes técnicos como Data Grid. Enfocarse en que el usuario pueda visualizar el listado. |
| CA2 | Especificar qué información debe mostrarse obligatoriamente por medicamento. |
| CA3 | Retirar la referencia técnica al servicio y al Issue #21 del criterio funcional. Documentarla como dependencia técnica. |
| CA4 | Definir un comportamiento concreto de paginación o desplazamiento, evitando dejar dos alternativas abiertas. |
| CA5 | Verificar que la opción de edición aparezca únicamente para usuarios autorizados y permita acceder al medicamento seleccionado. |
| CA6 | Mantener el estado de carga, pero describir el comportamiento esperado sin imponer un componente visual específico. |

#### 3. Criterios faltantes

Se recomienda incorporar escenarios para:

- Listado vacío: informar cuando no existan medicamentos registrados.

- Error de consulta: mostrar un mensaje cuando no sea posible obtener los medicamentos.

- Stock disponible: asegurar que la cantidad mostrada corresponda a la información actualizada del catálogo.

- Permisos: permitir la consulta según los roles autorizados y restringir la edición cuando corresponda.

Redactar los criterios utilizando Dado – Cuando – Entonces, describiendo resultados verificables en lugar de tareas de implementación.
#### 4. Coherencia con Poki Koa

La consulta de medicamentos es coherente con el sistema. Sin embargo, el modelo verbal compartido todavía no define explícitamente un catálogo general de medicamentos, la gestión de inventario ni los permisos del personal de farmacia.

Es importante confirmar estos aspectos para asegurar la consistencia entre US-02 y US-03.
Resultado final

US-03: Pendiente de ajustes menores.

Prioridad de corrección: Eliminar detalles técnicos de los criterios funcionales, definir los permisos de edición y agregar escenarios de listado vacío y errores de consulta.

La historia está bien orientada y presenta criterios relevantes. Con estos ajustes podrá ser más clara, verificable y consistente con las demás historias de medicamentos.
