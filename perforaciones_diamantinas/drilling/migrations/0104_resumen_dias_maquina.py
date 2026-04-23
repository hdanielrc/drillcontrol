import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0103_conceptobono_tabla_calificacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResumenDiasMaquina',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_dias', models.PositiveIntegerField(default=0, verbose_name='Total días asignado')),
                ('primera_asignacion', models.DateField(blank=True, null=True, verbose_name='Primera fecha')),
                ('ultima_asignacion', models.DateField(blank=True, null=True, verbose_name='Última fecha')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('maquina', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resumen_dias_trabajadores', to='drilling.maquina')),
                ('trabajador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resumen_dias_maquina', to='drilling.trabajador')),
            ],
            options={
                'verbose_name': 'Resumen Días por Máquina',
                'verbose_name_plural': 'Resumen Días por Máquina',
                'db_table': 'resumen_dias_maquina',
                'ordering': ['-total_dias'],
            },
        ),
        migrations.AddIndex(
            model_name='resumendiasmaquina',
            index=models.Index(fields=['trabajador'], name='resumen_dia_trabaja_d76e29_idx'),
        ),
        migrations.AddIndex(
            model_name='resumendiasmaquina',
            index=models.Index(fields=['maquina'], name='resumen_dia_maquina_df6b6a_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='resumendiasmaquina',
            unique_together={('trabajador', 'maquina')},
        ),
    ]
