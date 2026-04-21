from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0099_configuracionbonocontrato_montos_por_cargo'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionbonocontrato',
            name='tipo_calculo_por_trabajador',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'DNI → "metraje" | "cumplimiento". '
                    'Ej: {"12345678": "metraje"}. '
                    'Vacío o sin clave = trabajador calcula por cumplimiento KPI.'
                ),
                verbose_name='Tipo de Cálculo por Trabajador',
            ),
        ),
    ]
