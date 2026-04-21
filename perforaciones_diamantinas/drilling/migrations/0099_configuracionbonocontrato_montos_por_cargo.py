from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0098_configuracionbonocontrato_cargos_aplicables'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionbonocontrato',
            name='montos_por_cargo',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Monto base mensual específico por cargo. Ej: {"RESIDENTE": 1500.00, "ASISTENTE DE RESIDENTE": 800.00}. Sobreescribe monto_base_mensual para ese cargo.',
                verbose_name='Montos por Cargo',
            ),
        ),
    ]
