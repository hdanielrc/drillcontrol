from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0081_add_programacion_mes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MetaTurno',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(verbose_name='Fecha')),
                ('meta_metros', models.DecimalField(
                    max_digits=8,
                    decimal_places=2,
                    validators=[django.core.validators.MinValueValidator(Decimal('0'))],
                    verbose_name='Meta metros'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('maquina', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='metas_turno',
                    to='drilling.maquina',
                    verbose_name='Máquina'
                )),
                ('tipo_turno', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='metas_turno',
                    to='drilling.tipoturno',
                    verbose_name='Tipo de turno'
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='metas_turno_creadas',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Creado por'
                )),
            ],
            options={
                'verbose_name': 'Meta por Turno',
                'verbose_name_plural': 'Metas por Turno',
                'db_table': 'meta_turno',
                'ordering': ['maquina', 'fecha', 'tipo_turno'],
            },
        ),
        migrations.AddIndex(
            model_name='metaturno',
            index=models.Index(fields=['maquina', 'fecha'], name='meta_turno_maq_fecha_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='metaturno',
            unique_together={('maquina', 'fecha', 'tipo_turno')},
        ),
    ]
