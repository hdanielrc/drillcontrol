# Generated migration to add contrato FK to Turno

from django.db import migrations, models
import django.db.models.deletion


def populate_turno_contrato(apps, schema_editor):
    """Llenar contrato_id en turnos existentes desde su máquina asociada"""
    Turno = apps.get_model('drilling', 'Turno')
    
    # Actualizar todos los turnos sin contrato asignado
    # usando la relación Turno.maquina.contrato
    turnos_sin_contrato = Turno.objects.filter(contrato__isnull=True)
    
    for turno in turnos_sin_contrato:
        if turno.maquina and turno.maquina.contrato:
            turno.contrato = turno.maquina.contrato
            turno.save(update_fields=['contrato'])


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0019_contratoactividad_alter_contrato_actividades'),
    ]

    operations = [
        # Paso 1: Agregar la columna contrato_id a la tabla turnos como NULL
        migrations.AddField(
            model_name='turno',
            name='contrato',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='turnos', to='drilling.contrato'),
        ),
        # Paso 2: Ejecutar datos históricos - llenar contrato_id desde maquina.contrato_id
        migrations.RunPython(
            code=populate_turno_contrato,
            reverse_code=migrations.RunPython.noop,
        ),
        # Paso 3: Hacer el campo contrato_id NOT NULL después de llenar datos
        migrations.AlterField(
            model_name='turno',
            name='contrato',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='turnos', to='drilling.contrato'),
        ),
    ]
