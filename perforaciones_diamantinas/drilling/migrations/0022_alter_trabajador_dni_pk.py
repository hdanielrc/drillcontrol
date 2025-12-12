# Migration to make Trabajador.dni the primary key
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0021_alter_turno_unique_together_add_indexes'),
    ]

    operations = [
        # En lugar de convertir `dni` en PRIMARY KEY (riesgoso si existe `id` y FKs),
        # dejamos `id` como PK y hacemos `dni` UNIQUE para identificación.
        migrations.AlterField(
            model_name='trabajador',
            name='dni',
            field=models.CharField(max_length=20, unique=True),
        ),
    ]
