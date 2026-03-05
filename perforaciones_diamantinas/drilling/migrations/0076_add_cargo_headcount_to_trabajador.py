from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0075_add_dia_cambio_guardia_to_contrato'),
    ]

    operations = [
        migrations.AddField(
            model_name='trabajador',
            name='cargo_headcount',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=200,
                verbose_name='Cargo para Headcount',
                help_text=(
                    'Override manual: si se especifica, este cargo se usa para cuadrar el headcount '
                    'en lugar del cargo oficial de la API. Útil cuando la persona es contratada con '
                    'un cargo distinto al puesto que cubre.'
                ),
            ),
        ),
    ]
