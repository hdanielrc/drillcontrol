import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0105_estructurasalarial_maquina'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AsignacionEstructuraSalarial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_inicio', models.DateField(verbose_name='Fecha de Inicio')),
                ('fecha_fin', models.DateField(blank=True, help_text='Dejar vacío si la asignación está vigente', null=True, verbose_name='Fecha de Fin')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contrato', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='asignaciones_estructura_salarial', to='drilling.contrato', verbose_name='Contrato')),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='asignaciones_estructura_salarial_creadas', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('estructura_salarial', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='asignaciones', to='drilling.estructurasalarial', verbose_name='Estructura Salarial')),
                ('trabajador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='asignaciones_estructura_salarial', to='drilling.trabajador', verbose_name='Trabajador')),
            ],
            options={
                'verbose_name': 'Asignación Estructura Salarial',
                'verbose_name_plural': 'Asignaciones Estructura Salarial',
                'db_table': 'payroll_asignacion_estructura_salarial',
                'ordering': ['trabajador__apepat', 'trabajador__nombres', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='asignacionestructurasalarial',
            index=models.Index(fields=['contrato', 'activo'], name='payroll_asi_contrat_activo_idx'),
        ),
        migrations.AddIndex(
            model_name='asignacionestructurasalarial',
            index=models.Index(fields=['trabajador', 'activo'], name='payroll_asi_trabaja_activo_idx'),
        ),
        migrations.AddConstraint(
            model_name='asignacionestructurasalarial',
            constraint=models.UniqueConstraint(condition=models.Q(activo=True), fields=['trabajador'], name='unique_asignacion_activa_por_trabajador'),
        ),
    ]
