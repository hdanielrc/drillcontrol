from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0014_turno_sondaje'),
    ]

    operations = [
        migrations.AddField(
            model_name='turnosondaje',
            name='metros_turno',
            field=models.DecimalField(default=0, max_digits=8, decimal_places=2),
        ),
    ]
