from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0101_bonotrabajador_metraje_acumulado'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HistorialBonoTrabajador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monto_calculado', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monto Calculado (S/)')),
                ('monto_ajuste', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Ajuste Manual (S/)')),
                ('monto_final', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monto Final (S/)')),
                ('dias_trabajados', models.PositiveSmallIntegerField(default=0, verbose_name='Días Trabajados')),
                ('dias_base', models.PositiveSmallIntegerField(default=0, verbose_name='Días Operativos')),
                ('fuente', models.CharField(
                    choices=[
                        ('CALCULO', 'Cálculo automático (vista cuadro)'),
                        ('GUARDAR', 'Guardado manual por usuario'),
                        ('RECALC',  'Recalcular (botón)'),
                        ('API',     'API / importación'),
                    ],
                    default='CALCULO', max_length=10, verbose_name='Fuente',
                )),
                ('observacion', models.TextField(blank=True, verbose_name='Observación')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')),
                ('bono_trabajador', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='historial',
                    to='drilling.bonotrabajador',
                    verbose_name='Bono Trabajador',
                )),
                ('periodo', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='drilling.periodobono',
                    verbose_name='Período',
                )),
                ('tipo_bono', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='drilling.tipobono',
                    verbose_name='Tipo de Bono',
                )),
                ('trabajador', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='drilling.trabajador',
                    verbose_name='Trabajador',
                )),
                ('registrado_por', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historial_bonos_registrados',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Registrado por',
                )),
            ],
            options={
                'verbose_name': 'Historial Bono Trabajador',
                'verbose_name_plural': 'Historial Bonos Trabajadores',
                'db_table': 'payroll_historial_bono_trabajador',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='historialbonotrabajador',
            index=models.Index(fields=['bono_trabajador', '-created_at'], name='payroll_hist_bono_trab_date_idx'),
        ),
        migrations.AddIndex(
            model_name='historialbonotrabajador',
            index=models.Index(fields=['trabajador', 'tipo_bono', '-created_at'], name='payroll_hist_trab_tipo_date_idx'),
        ),
        migrations.AddIndex(
            model_name='historialbonotrabajador',
            index=models.Index(fields=['periodo', 'tipo_bono'], name='payroll_hist_periodo_tipo_idx'),
        ),
    ]
