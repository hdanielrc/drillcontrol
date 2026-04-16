# Generated manually — Conceptos Globales de Contrato

from django.db import migrations, models
import django.core.validators


def seed_conceptos_globales(apps, schema_editor):
    """Crea los 5 conceptos globales del sistema."""
    ConceptoGlobal = apps.get_model('drilling', 'ConceptoGlobal')

    conceptos = [
        {
            'codigo': 'PRODUCCION',
            'nombre': 'Producción',
            'tipo': 'PRODUCCION',
            'descripcion': 'Cumplimiento de metros: metros_acumulados / meta_programada. '
                           'El % de bono depende del rango de cumplimiento y la cantidad de máquinas.',
            'es_sistema': True,
            'activo': True,
            'orden': 1,
        },
        {
            'codigo': 'SEGURIDAD',
            'nombre': 'Seguridad',
            'tipo': 'SEGURIDAD',
            'descripcion': '0 accidentes incapacitantes = 100% bono, 1+ = 0%.',
            'es_sistema': True,
            'activo': True,
            'orden': 2,
        },
        {
            'codigo': 'VALORIZACION',
            'nombre': 'Valorización',
            'tipo': 'VALORIZACION',
            'descripcion': 'Eficiencia de cobro >= 99.7% = 100% bono, < 99.7% = 0%.',
            'es_sistema': True,
            'activo': True,
            'orden': 3,
        },
        {
            'codigo': 'CXM',
            'nombre': 'Costo por Metro',
            'tipo': 'CXM',
            'descripcion': 'Desviación del costo por metro vs meta programada. '
                           '<=0% → 100%, 0-10% → 70%, 11-15% → 50%, >15% → 0%.',
            'es_sistema': True,
            'activo': True,
            'orden': 4,
        },
        {
            'codigo': 'RESULTADO_OPERATIVO',
            'nombre': 'Resultado Operativo',
            'tipo': 'RESULTADO_OPERATIVO',
            'descripcion': 'Rentabilidad >= 25% = 100% bono, < 25% = 0%.',
            'es_sistema': True,
            'activo': True,
            'orden': 5,
        },
    ]

    for data in conceptos:
        ConceptoGlobal.objects.get_or_create(
            codigo=data['codigo'],
            defaults=data,
        )


def reverse_seed(apps, schema_editor):
    ConceptoGlobal = apps.get_model('drilling', 'ConceptoGlobal')
    ConceptoGlobal.objects.filter(
        codigo__in=['PRODUCCION', 'SEGURIDAD', 'VALORIZACION', 'CXM', 'RESULTADO_OPERATIVO']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0093_add_nominas_role'),
    ]

    operations = [
        # ConceptoGlobal
        migrations.CreateModel(
            name='ConceptoGlobal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=30, unique=True, verbose_name='Código')),
                ('nombre', models.CharField(max_length=200, verbose_name='Nombre')),
                ('tipo', models.CharField(
                    max_length=30,
                    choices=[
                        ('PRODUCCION', 'Producción — Cumplimiento de Metros'),
                        ('SEGURIDAD', 'Seguridad — Accidentes Incapacitantes'),
                        ('VALORIZACION', 'Valorización — Eficiencia de Cobro'),
                        ('CXM', 'Costo por Metro — Desviación CXM'),
                        ('RESULTADO_OPERATIVO', 'Resultado Operativo — Rentabilidad'),
                        ('CUSTOM', 'Personalizado'),
                    ],
                    verbose_name='Tipo de Cálculo',
                )),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('es_sistema', models.BooleanField(default=False, help_text='Los conceptos del sistema no se pueden eliminar')),
                ('activo', models.BooleanField(default=True)),
                ('orden', models.PositiveSmallIntegerField(default=0, verbose_name='Orden')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'payroll_concepto_global',
                'ordering': ['orden', 'codigo'],
                'verbose_name': 'Concepto Global',
                'verbose_name_plural': 'Conceptos Globales',
            },
        ),
        # ConceptoGlobalPeriodo
        migrations.CreateModel(
            name='ConceptoGlobalPeriodo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio', models.PositiveSmallIntegerField(verbose_name='Año')),
                ('mes', models.PositiveSmallIntegerField(
                    verbose_name='Mes',
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(12),
                    ],
                )),
                ('metros_acumulados', models.DecimalField(
                    max_digits=12, decimal_places=2, default=0,
                    verbose_name='Metros Acumulados',
                    help_text='Total metraje acumulado por todas las máquinas del contrato',
                )),
                ('meta_programada', models.DecimalField(
                    max_digits=12, decimal_places=2, default=0,
                    verbose_name='Meta Programada',
                    help_text='Meta propuesta por cada máquina desde control de proyectos',
                )),
                ('cantidad_maquinas', models.PositiveSmallIntegerField(
                    default=0, verbose_name='Cantidad de Máquinas',
                    help_text='Cantidad de máquinas en el contrato',
                )),
                ('accidentes_incapacitantes', models.PositiveSmallIntegerField(
                    default=0, verbose_name='Accidentes Incapacitantes',
                )),
                ('eficiencia_cobro', models.DecimalField(
                    max_digits=6, decimal_places=2, default=0,
                    verbose_name='Eficiencia de Cobro (%)',
                    help_text='Porcentaje de eficiencia en el cobro',
                )),
                ('total_abastecido', models.DecimalField(
                    max_digits=14, decimal_places=2, default=0,
                    verbose_name='Total Abastecido ($)',
                    help_text='Monto total de materiales abastecidos al centro de costo',
                )),
                ('meta_cxm_programada', models.DecimalField(
                    max_digits=10, decimal_places=2, default=0,
                    verbose_name='Meta CXM Programada',
                    help_text='Meta de costo por metro por contrato',
                )),
                ('rentabilidad', models.DecimalField(
                    max_digits=6, decimal_places=2, default=0,
                    verbose_name='Rentabilidad (%)',
                    help_text='Porcentaje de rentabilidad del contrato',
                )),
                ('valor_calculado', models.DecimalField(
                    max_digits=12, decimal_places=4, default=0,
                    verbose_name='Valor Calculado',
                    help_text='Métrica intermedia (cumplimiento %, desviación %, etc.)',
                )),
                ('porcentaje_bono', models.DecimalField(
                    max_digits=6, decimal_places=2, default=0,
                    verbose_name='% de Bono Resultante',
                    help_text='Porcentaje de bono resultante según reglas (0-150%)',
                )),
                ('observaciones', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('concepto', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='periodos',
                    to='drilling.conceptoglobal',
                )),
                ('contrato', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='conceptos_globales_periodo',
                    to='drilling.contrato',
                )),
            ],
            options={
                'db_table': 'payroll_concepto_global_periodo',
                'ordering': ['anio', 'mes', 'concepto__orden'],
                'verbose_name': 'Concepto Global por Período',
                'verbose_name_plural': 'Conceptos Globales por Período',
                'unique_together': {('contrato', 'concepto', 'anio', 'mes')},
            },
        ),
        # Seed data
        migrations.RunPython(seed_conceptos_globales, reverse_seed),
    ]
