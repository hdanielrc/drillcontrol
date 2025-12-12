from django.db import migrations, models
import django.db.models.deletion


def forwards_func(apps, schema_editor):
    TurnoSondaje = apps.get_model('drilling', 'TurnoSondaje')
    # Intentamos detectar si existe la columna legacy 'sondaje_id' en la tabla 'turnos'
    conn = schema_editor.connection
    with conn.cursor() as cursor:
        try:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'turnos' AND column_name = 'sondaje_id';")
            row = cursor.fetchone()
        except Exception:
            row = None

    if not row:
        # No hay columna legacy, nada que copiar
        return

    # Si existe la columna, copiar valores no nulos a la nueva tabla
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, sondaje_id FROM turnos WHERE sondaje_id IS NOT NULL;")
        rows = cursor.fetchall()

    objs = []
    for turno_id, sondaje_id in rows:
        objs.append(TurnoSondaje(turno_id=turno_id, sondaje_id=sondaje_id))

    if objs:
        TurnoSondaje.objects.bulk_create(objs)


def reverse_func(apps, schema_editor):
    TurnoSondaje = apps.get_model('drilling', 'TurnoSondaje')
    TurnoSondaje.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0013_maquina_horometro'),
    ]

    operations = [
        migrations.CreateModel(
            name='TurnoSondaje',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('turno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='turno_sondajes', to='drilling.turno')),
                ('sondaje', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sondaje_turnos', to='drilling.sondaje')),
            ],
            options={
                'db_table': 'turno_sondaje',
            },
        ),
        migrations.AlterUniqueTogether(
            name='turnosondaje',
            unique_together={('turno', 'sondaje')},
        ),
        migrations.RunPython(forwards_func, reverse_func),
    ]
