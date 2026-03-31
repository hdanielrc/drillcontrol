from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0080_add_meta_diaria_maquina'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgramacionMes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('año', models.IntegerField(verbose_name='Año')),
                ('mes', models.IntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(12),
                    ],
                    verbose_name='Mes',
                    help_text='Mes del día 25 (fin del período).'
                )),
                ('meta_metros', models.DecimalField(
                    max_digits=10,
                    decimal_places=2,
                    validators=[django.core.validators.MinValueValidator(Decimal('0'))],
                    verbose_name='Meta metros (mensual)'
                )),
                ('dia_inicio', models.DateField(verbose_name='Día de inicio')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('maquina', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='programaciones_mes',
                    to='drilling.maquina',
                    verbose_name='Máquina'
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='programaciones_creadas',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Creado por'
                )),
            ],
            options={
                'verbose_name': 'Programación Mensual',
                'verbose_name_plural': 'Programaciones Mensuales',
                'db_table': 'programacion_mes',
                'ordering': ['-año', '-mes', 'maquina__contrato', 'maquina__nombre'],
            },
        ),
        migrations.AddIndex(
            model_name='programacionmes',
            index=models.Index(fields=['año', 'mes'], name='prog_mes_anio_mes_idx'),
        ),
        migrations.AddIndex(
            model_name='programacionmes',
            index=models.Index(fields=['maquina', 'año', 'mes'], name='prog_mes_maquina_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='programacionmes',
            unique_together={('maquina', 'año', 'mes')},
        ),
    ]
