from django.db import migrations, models, migrations
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0015_turnosondaje_metros'),
    ]

    operations = [
        migrations.AddField(
            model_name='turnocomplemento',
            name='sondaje',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='complementos_turno', to='drilling.sondaje'),
        ),
        migrations.AddField(
            model_name='turnoaditivo',
            name='sondaje',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='aditivos_turno', to='drilling.sondaje'),
        ),
    ]
