from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0071_add_tipo_servicio_trabajador'),
    ]

    operations = [
        migrations.AddField(
            model_name='trabajador',
            name='fecha_inicio_labores',
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name='Fecha Inicio Labores',
                help_text='Fecha en que el trabajador empieza a aparecer en el tareo. Diferente a la fecha de contratación de la API.'
            ),
        ),
    ]
