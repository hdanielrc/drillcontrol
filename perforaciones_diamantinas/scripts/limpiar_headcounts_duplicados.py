"""
Script para desactivar headcounts duplicados
Mantiene el más reciente y desactiva los demás
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import HeadCount
from django.db.models import Count

def limpiar_duplicados():
    """Desactivar headcounts duplicados, manteniendo el más reciente"""
    
    # Buscar duplicados agrupando por contrato, cargo, maquina
    duplicados = []
    
    # Obtener todos los headcounts activos
    headcounts = HeadCount.objects.filter(activo=True).order_by('contrato', 'cargo', 'maquina', '-created_at')
    
    # Agrupar manualmente por contrato, cargo, maquina
    grupos = {}
    for hc in headcounts:
        key = (hc.contrato_id, hc.cargo_id, hc.maquina_id)
        if key not in grupos:
            grupos[key] = []
        grupos[key].append(hc)
    
    # Procesar grupos con más de 1 elemento
    desactivados = 0
    for key, items in grupos.items():
        if len(items) > 1:
            print(f"\n🔍 Duplicados encontrados:")
            print(f"   Contrato ID: {key[0]}, Cargo ID: {key[1]}, Máquina ID: {key[2]}")
            print(f"   Total registros: {len(items)}")
            
            # Mantener el primero (más reciente), desactivar los demás
            mantener = items[0]
            print(f"   ✅ Mantener: ID {mantener.id} (creado: {mantener.created_at})")
            
            for hc in items[1:]:
                print(f"   ❌ Desactivar: ID {hc.id} (creado: {hc.created_at})")
                hc.activo = False
                hc.save()
                desactivados += 1
    
    print(f"\n✅ Proceso completado. {desactivados} headcount(s) desactivado(s)")
    
    # Mostrar resumen
    print("\n📊 Resumen final:")
    activos = HeadCount.objects.filter(activo=True).count()
    inactivos = HeadCount.objects.filter(activo=False).count()
    print(f"   Activos: {activos}")
    print(f"   Inactivos: {inactivos}")

if __name__ == '__main__':
    print("🧹 Limpiando headcounts duplicados...")
    limpiar_duplicados()
