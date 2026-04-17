"""
Data migration: Para cada Contrato que tenga codigo_centro_costo (campo principal)
y NO tenga un ContratoServicio con ese mismo código, crea un ContratoServicio DDH.

Esto unifica todos los centros de costo en la tabla contrato_servicios,
sin romper los procesos existentes que leen Contrato.codigo_centro_costo.
"""
from django.db import migrations


def crear_servicio_ddh_principal(apps, schema_editor):
    """
    Para cada contrato con codigo_centro_costo principal, verificar si ya existe
    un ContratoServicio con ese código. Si no, crearlo como tipo DDH.
    """
    Contrato = apps.get_model('drilling', 'Contrato')
    ContratoServicio = apps.get_model('drilling', 'ContratoServicio')

    contratos = Contrato.objects.exclude(
        codigo_centro_costo__isnull=True
    ).exclude(codigo_centro_costo='')

    creados = 0
    for contrato in contratos:
        cc = contrato.codigo_centro_costo
        ya_existe = ContratoServicio.objects.filter(
            contrato=contrato,
            codigo_centro_costo=cc
        ).exists()

        if not ya_existe:
            ContratoServicio.objects.create(
                contrato=contrato,
                tipo_servicio='DDH',
                codigo_centro_costo=cc,
                codigo_almacen=contrato.codigo_almacen or '',
                descripcion=f'CTR {contrato.nombre_contrato} - DDH (migrado automáticamente)',
                activo=True,
            )
            creados += 1

    if creados:
        print(f'\n  ✅ Creados {creados} ContratoServicio DDH desde campo principal de Contrato')


def revertir(apps, schema_editor):
    """
    Revertir: eliminar ContratoServicio que fueron creados automáticamente
    por esta migración (los que tienen la descripción de migrado).
    """
    ContratoServicio = apps.get_model('drilling', 'ContratoServicio')
    eliminados = ContratoServicio.objects.filter(
        descripcion__contains='migrado automáticamente'
    ).delete()[0]
    if eliminados:
        print(f'\n  ↩ Eliminados {eliminados} ContratoServicio DDH migrados')


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0095_delete_metadiariamaquina'),
    ]

    operations = [
        migrations.RunPython(crear_servicio_ddh_principal, revertir),
    ]
