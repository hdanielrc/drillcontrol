from django.db import migrations, models
import unicodedata


def _strip_accents(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.upper())
        if unicodedata.category(c) != 'Mn'
    )


def set_tabla_calificacion_ba(apps, schema_editor):
    """
    Auto-configura tabla_calificacion para los conceptos de tipos de bono
    cuyo código comience con 'BA-' (Bono Administración).
    - Secciones que contienen 'PRODUCCION' → PRODUCCION_META
    - El resto (Gestión Humana, Gestión Administrativa, Contabilidad, etc.) → INCIDENCIAS
    """
    ConceptoBono = apps.get_model('drilling', 'ConceptoBono')

    for cb in ConceptoBono.objects.filter(tipo_bono__codigo__startswith='BA-'):
        nombre_norm = _strip_accents(cb.nombre)
        if 'PRODUCCION' in nombre_norm or 'PRODUCCION' in _strip_accents(cb.codigo):
            cb.tabla_calificacion = 'PRODUCCION_META'
        else:
            cb.tabla_calificacion = 'INCIDENCIAS'
        cb.save(update_fields=['tabla_calificacion'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0102_historialbonotrabajador'),
    ]

    operations = [
        migrations.AddField(
            model_name='conceptobono',
            name='tabla_calificacion',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Criterios (checkboxes)'),
                    ('INCIDENCIAS', 'Tabla de Incidencias (0 / 1-2 / 3-4 / ≥5)'),
                    ('PRODUCCION_META', 'Tabla Producción vs Meta (≥95% / 90-94% / 85-89% / ≤84%)'),
                ],
                default='',
                help_text='Si se establece, muestra un desplegable de calificación fija en lugar de checkboxes.',
                max_length=20,
                verbose_name='Tabla de Calificación',
            ),
        ),
        migrations.RunPython(set_tabla_calificacion_ba, reverse_noop),
    ]
