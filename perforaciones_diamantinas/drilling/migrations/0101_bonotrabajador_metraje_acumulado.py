from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0100_configuracionbonocontrato_tipo_calculo_por_trabajador'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonotrabajador',
            name='metraje_acumulado',
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text='Metros perforados acumulados en el período. Solo para trabajadores de tipo metraje.',
                max_digits=10,
                null=True,
                verbose_name='Metraje Acumulado (m)',
            ),
        ),
    ]
