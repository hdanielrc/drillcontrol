from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0097_estructurasalarial_historialestructurasalarial_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionbonocontrato',
            name='cargos_aplicables',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Lista de cargos a los que aplica este bono en este contrato. Vacío = todos los del tipo de bono.',
                verbose_name='Cargos Aplicables',
            ),
        ),
    ]
