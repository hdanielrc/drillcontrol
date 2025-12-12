# Update unique_together constraint in Turno to include contrato

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0020_add_contrato_to_turno'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='turno',
            unique_together={('contrato', 'maquina', 'fecha', 'tipo_turno')},
        ),
        migrations.AddIndex(
            model_name='turno',
            index=models.Index(fields=['contrato', 'fecha'], name='turnos_contrato_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='turno',
            index=models.Index(fields=['maquina', 'fecha'], name='turnos_maquina_fecha_idx'),
        ),
    ]
