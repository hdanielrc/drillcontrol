# Generated manually to add tipo_actividad to TipoActividad
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0006_contrato_actividades_tipoactividad_descripcion_corta'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipoactividad',
            name='tipo_actividad',
            field=models.CharField(default='OTROS', max_length=32, choices=[('STAND_BY_CLIENTE', 'Stand By Cliente'), ('STAND_BY_ROCKDRILL', 'Stand By Rock Drill'), ('INOPERATIVO', 'Inoperativo'), ('OTROS', 'Otros')]),
            preserve_default=False,
        ),
    ]
