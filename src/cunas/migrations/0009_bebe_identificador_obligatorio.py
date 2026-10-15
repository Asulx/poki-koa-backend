from django.db import migrations, models


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
