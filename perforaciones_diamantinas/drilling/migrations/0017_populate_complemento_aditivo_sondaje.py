from django.db import migrations


def forwards_func(apps, schema_editor):
    TurnoComplemento = apps.get_model('drilling', 'TurnoComplemento')
    TurnoAditivo = apps.get_model('drilling', 'TurnoAditivo')
    TurnoSondaje = apps.get_model('drilling', 'TurnoSondaje')

    # Asignar sondaje a complementos/aditivos cuando el turno tenga exactamente 1 sondaje asociado
    # Recorremos los turnos con complementos/aditivos sin sondaje
    # Nota: dejamos nulos los casos con múltiples sondajes para revisión manual

    # Complementos
    updated_comp = 0
    for comp in TurnoComplemento.objects.filter(sondaje__isnull=True):
        turno_id = comp.turno_id
        sondajes = list(TurnoSondaje.objects.filter(turno_id=turno_id).values_list('sondaje_id', flat=True))
        if len(sondajes) == 1:
            comp.sondaje_id = sondajes[0]
            comp.save(update_fields=['sondaje'])
            updated_comp += 1

    # Aditivos
    updated_ad = 0
    for ad in TurnoAditivo.objects.filter(sondaje__isnull=True):
        turno_id = ad.turno_id
        sondajes = list(TurnoSondaje.objects.filter(turno_id=turno_id).values_list('sondaje_id', flat=True))
        if len(sondajes) == 1:
            ad.sondaje_id = sondajes[0]
            ad.save(update_fields=['sondaje'])
            updated_ad += 1

    print(f"[mig 0017] complementos actualizados: {updated_comp}, aditivos actualizados: {updated_ad}")


def reverse_func(apps, schema_editor):
    # No revertimos los datos automáticamente (podríamos poner a NULL, pero eso borraría información original).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0016_add_sondaje_to_complemento_aditivo'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
