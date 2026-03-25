from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0078_headcount_update_choices_add_nivel'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrabajadorContratoHistorial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_inicio', models.DateField(verbose_name='Fecha inicio en contrato')),
                ('fecha_fin', models.DateField(
                    blank=True, null=True,
                    verbose_name='Fecha fin en contrato',
                    help_text='Null = asignación vigente actualmente',
                )),
                ('motivo_cambio', models.CharField(blank=True, max_length=200, verbose_name='Motivo del cambio')),
                ('creado_automaticamente', models.BooleanField(
                    default=True,
                    help_text='True si fue registrado por la sincronización automática',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contrato', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='trabajador_historial',
                    to='drilling.contrato',
                    verbose_name='Contrato',
                )),
                ('trabajador', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='contrato_historial',
                    to='drilling.trabajador',
                    verbose_name='Trabajador',
                )),
            ],
            options={
                'verbose_name': 'Historial Contrato Trabajador',
                'verbose_name_plural': 'Historial Contratos Trabajadores',
                'db_table': 'trabajador_contrato_historial',
                'ordering': ['trabajador', '-fecha_inicio'],
            },
        ),
        migrations.AddIndex(
            model_name='trabajadorcontratohistorial',
            index=models.Index(fields=['trabajador', 'fecha_inicio'], name='idx_tch_trab_inicio'),
        ),
        migrations.AddIndex(
            model_name='trabajadorcontratohistorial',
            index=models.Index(fields=['contrato', 'fecha_inicio'], name='idx_tch_cont_inicio'),
        ),
        migrations.AddIndex(
            model_name='trabajadorcontratohistorial',
            index=models.Index(fields=['trabajador', 'fecha_fin'], name='idx_tch_trab_fin'),
        ),
    ]
