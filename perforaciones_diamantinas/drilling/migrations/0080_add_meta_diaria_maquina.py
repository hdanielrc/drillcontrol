from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0079_trabajadorcontratohistorial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MetaDiariaMaquina',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_vigencia', models.DateField(
                    verbose_name='Fecha de vigencia',
                    help_text='La meta aplica desde este día en adelante (hasta que se registre otra)'
                )),
                ('meta_metros_dia', models.DecimalField(
                    max_digits=8,
                    decimal_places=2,
                    validators=[django.core.validators.MinValueValidator(Decimal('0'))],
                    verbose_name='Meta metros/día',
                    help_text='Metros por día que debe perforar esta máquina'
                )),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('maquina', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='metas_diarias',
                    to='drilling.maquina',
                    verbose_name='Máquina'
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='metas_diarias_creadas',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Creado por'
                )),
            ],
            options={
                'verbose_name': 'Meta Diaria por Máquina',
                'verbose_name_plural': 'Metas Diarias por Máquina',
                'db_table': 'meta_diaria_maquina',
                'ordering': ['maquina', 'fecha_vigencia'],
            },
        ),
        migrations.AddIndex(
            model_name='metadiariamaquina',
            index=models.Index(fields=['maquina', 'fecha_vigencia'], name='meta_diaria_maquina_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='metadiariamaquina',
            unique_together={('maquina', 'fecha_vigencia')},
        ),
    ]
