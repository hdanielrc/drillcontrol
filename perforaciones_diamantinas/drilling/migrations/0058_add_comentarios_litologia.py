# Generated manually 2026-01-14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0057_alter_trabajador_grupo'),
    ]

    operations = [
        migrations.AddField(
            model_name='turno',
            name='comentarios_perforistas',
            field=models.TextField(blank=True, verbose_name='Comentarios de Perforistas'),
        ),
        migrations.AddField(
            model_name='turno',
            name='litologia_general',
            field=models.TextField(blank=True, verbose_name='Litología General'),
        ),
        migrations.AddField(
            model_name='turnomaquina',
            name='comentarios_mantenimiento',
            field=models.TextField(blank=True, verbose_name='Comentarios de Mantenimiento'),
        ),
    ]
