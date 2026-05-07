from django.db import migrations


def set_ba_usa_periodo_operativo(apps, schema_editor):
    TipoBono = apps.get_model('drilling', 'TipoBono')
    updated = TipoBono.objects.filter(
        codigo__startswith='BA-'
    ).update(usa_periodo_operativo_tareo=True)
    print(f'  Updated {updated} TipoBono registros BA- → usa_periodo_operativo_tareo=True')


def unset_ba_usa_periodo_operativo(apps, schema_editor):
    TipoBono = apps.get_model('drilling', 'TipoBono')
    TipoBono.objects.filter(
        codigo__startswith='BA-'
    ).update(usa_periodo_operativo_tareo=False)


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0109_add_tipo_calculo_default_config_bono'),
    ]

    operations = [
        migrations.RunPython(
            set_ba_usa_periodo_operativo,
            reverse_code=unset_ba_usa_periodo_operativo,
        ),
    ]
