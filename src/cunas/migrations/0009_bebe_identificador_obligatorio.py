"""Migración de datos para completar identificadores de pacientes en Poki Koa.

Asegura que todos los registros existentes del modelo Bebe posean un identificador
único antes de aplicar la restricción de unicidad y obligatoriedad en el campo.
"""

from django.db import migrations, models

"""Rellena de forma iterativa y segura los identificadores vacíos en la tabla Bebe.

@param apps - Registro de modelos históricos de Django para acceso seguro a versiones previas.
@param schema_editor - Gestor de esquema de la base de datos para operaciones de conexión y transacciones.
@returns None - La función opera por efectos secundarios actualizando el registro de base de datos.
"""


def completar_identificadores(apps, schema_editor):
    Bebe = apps.get_model("cunas", "Bebe")
    pacientes = Bebe.objects.using(schema_editor.connection.alias)
    for paciente in pacientes.order_by("pk").iterator():
        if paciente.identificador and paciente.identificador.strip():
            continue
        base = f"BEB-MIG-{paciente.pk}"
        candidato = base
        intento = 0
        while pacientes.filter(identificador=candidato).exists():
            intento += 1
            sufijo = f"-{intento}"
            candidato = base[: 30 - len(sufijo)] + sufijo
        pacientes.filter(pk=paciente.pk).update(identificador=candidato)


class Migration(migrations.Migration):
    """Ejecuta la migración de datos y ajusta la restricción del campo identificador.

    Ejecuta la función auxiliar para poblar identificadores faltantes en pacientes
    y posteriormente modifica el campo para establecerlo como único en el esquema.
    """

    dependencies = [("cunas", "0008_medicamentocatalogo")]

    operations = [
        migrations.RunPython(completar_identificadores, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="bebe",
            name="identificador",
            field=models.CharField(
                help_text="Identificador único del paciente, ej: BEB-0001",
                max_length=30,
                unique=True,
            ),
        ),
    ]
