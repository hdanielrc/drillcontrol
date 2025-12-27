"""
Script para sincronizar productos diamantados (PDD) y aditivos (ADIT) 
para el contrato CONDESTABLE desde la API de Vilbragroup.

Ejecutar después de aplicar las migraciones:
    python sync_condestable.py
"""

import os
import django
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato

def main():
    print("\n" + "="*70)
    print("SINCRONIZACIÓN DE INVENTARIO - CONDESTABLE")
    print("="*70 + "\n")
    
    # Buscar el contrato CONDESTABLE
    try:
        contrato = Contrato.objects.get(nombre_contrato__icontains='CONDESTABLE')
        print(f"✓ Contrato encontrado: {contrato.nombre_contrato}")
        print(f"  Cliente: {contrato.cliente.nombre}")
        print(f"  Centro de Costo: {contrato.codigo_centro_costo}")
        print(f"  ID: {contrato.id}")
    except Contrato.DoesNotExist:
        print("✗ ERROR: No se encontró el contrato CONDESTABLE")
        print("\nContratos disponibles:")
        for c in Contrato.objects.all():
            print(f"  - {c.nombre_contrato} (ID: {c.id})")
        sys.exit(1)
    except Contrato.MultipleObjectsReturned:
        print("✗ ERROR: Se encontraron múltiples contratos con 'CONDESTABLE' en el nombre")
        contratos = Contrato.objects.filter(nombre_contrato__icontains='CONDESTABLE')
        print("\nContratos encontrados:")
        for c in contratos:
            print(f"  - {c.nombre_contrato} (ID: {c.id})")
        print("\nEdita este script y usa el ID específico del contrato correcto")
        sys.exit(1)
    
    if not contrato.codigo_centro_costo:
        print(f"\n✗ ERROR: El contrato {contrato.nombre_contrato} no tiene código de centro de costo configurado")
        print("Configura el código de centro de costo antes de sincronizar")
        sys.exit(1)
    
    print("\n" + "-"*70)
    print("PASO 1: Sincronizar Productos Diamantados (PDD)")
    print("-"*70 + "\n")
    
    # Importar aquí para evitar errores si Django no está configurado
    from django.core.management import call_command
    
    try:
        call_command(
            'sync_productos_diamantados',
            contrato_id=contrato.id,
            verbosity=2
        )
    except Exception as e:
        print(f"\n✗ ERROR al sincronizar PDD: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "-"*70)
    print("PASO 2: Sincronizar Aditivos de Perforación (ADIT)")
    print("-"*70 + "\n")
    
    try:
        call_command(
            'sync_aditivos',
            contrato_id=contrato.id,
            verbosity=2
        )
    except Exception as e:
        print(f"\n✗ ERROR al sincronizar ADIT: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("SINCRONIZACIÓN COMPLETADA")
    print("="*70 + "\n")
    
    # Mostrar resumen
    from drilling.models import TipoComplemento, TipoAditivo
    
    pdd_count = TipoComplemento.objects.filter(contrato=contrato).count()
    pdd_nuevo = TipoComplemento.objects.filter(contrato=contrato, estado='NUEVO').count()
    adit_count = TipoAditivo.objects.filter(contrato=contrato).count()
    
    print("RESUMEN:")
    print(f"  Productos Diamantados (PDD): {pdd_count} total ({pdd_nuevo} NUEVOS)")
    print(f"  Aditivos (ADIT): {adit_count} total")
    print()

if __name__ == '__main__':
    main()
