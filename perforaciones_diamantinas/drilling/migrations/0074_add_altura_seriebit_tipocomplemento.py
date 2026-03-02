from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0073_add_marca_calibre_tipocomplemento'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipocomplemento',
            name='altura',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Altura de diamantes en mm (ej: 12mm, 16mm, 20mm)',
                max_length=10,
                verbose_name='Altura',
            ),
        ),
        migrations.AddField(
            model_name='tipocomplemento',
            name='serie_bit',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Grado/serie del bit (ej: X8, X10, NG-9, UP 7-10)',
                max_length=20,
                verbose_name='Serie de Bit',
            ),
        ),
        migrations.AlterField(
            model_name='tipocomplemento',
            name='calibre',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Línea estándar del producto (HQ, NQ, BQ, PQ, HWL, NWL, etc.)',
                max_length=20,
                verbose_name='Calibre / Línea',
            ),
        ),
    ]
