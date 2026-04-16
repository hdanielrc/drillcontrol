from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0094_conceptos_globales'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MetaDiariaMaquina',
        ),
    ]
