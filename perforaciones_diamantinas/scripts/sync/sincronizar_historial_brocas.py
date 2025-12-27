#!/usr/bin/env python
"""
Script para sincronizar el historial de brocas a partir de los datos existentes en TurnoComplemento.
Útil para poblar HistorialBroca con datos históricos después de crear el modelo.
"""
import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import TurnoComplemento, HistorialBroca
from django.db.models import Sum, Count, Min, Max
from django.db import transaction

def sincronizar_historial():
    """
    Sincroniza el historial de brocas a partir de los datos en TurnoComplemento.
    """
    
    print("\n" + "="*80)
    print("SINCRONIZACIÓN DE HISTORIAL DE BROCAS")
    print("="*80)
    
    # Contar registros existentes
    total_usos = TurnoComplemento.objects.count()
    historiales_existentes = HistorialBroca.objects.count()
    
    print(f"\nEstado actual:")
    print(f"  - Registros en TurnoComplemento: {total_usos}")
    print(f"  - Historiales existentes: {historiales_existentes}")
    
    if total_usos == 0:
        print("\n⚠️ No hay datos de productos diamantados para sincronizar")
        print("   El historial se creará automáticamente cuando se registren turnos")
        return
    
    # Agrupar por serie y obtener estadísticas
    print("\n📊 Analizando datos por serie...")
    
    brocas_stats = TurnoComplemento.objects.values('codigo_serie').annotate(
        total_usos=Count('id'),
        metraje_total=Sum('metros_turno_calc'),
        primer_uso=Min('turno__fecha'),
        ultimo_uso=Max('turno__fecha')
    )
    
    print(f"   Brocas únicas encontradas: {brocas_stats.count()}")
    
    # Confirmar antes de proceder
    respuesta = input("\n¿Desea sincronizar el historial? (S/N): ").strip().upper()
    if respuesta != 'S':
        print("\n❌ Operación cancelada")
        return
    
    print("\n🔄 Sincronizando...")
    
    creados = 0
    actualizados = 0
    errores = 0
    
    with transaction.atomic():
        for broca_stat in brocas_stats:
            serie = broca_stat['codigo_serie']
            
            try:
                # Obtener el primer uso para obtener tipo_complemento y contrato
                primer_uso = TurnoComplemento.objects.filter(
                    codigo_serie=serie
                ).select_related('tipo_complemento', 'turno__contrato').order_by('turno__fecha').first()
                
                if not primer_uso:
                    print(f"⚠️  Serie {serie}: No se encontró primer uso, saltando...")
                    errores += 1
                    continue
                
                # Crear o actualizar historial
                historial, created = HistorialBroca.objects.update_or_create(
                    serie=serie,
                    defaults={
                        'tipo_complemento': primer_uso.tipo_complemento,
                        'contrato_actual': primer_uso.turno.contrato,
                        'metraje_acumulado': broca_stat['metraje_total'] or 0,
                        'numero_usos': broca_stat['total_usos'],
                        'fecha_primer_uso': broca_stat['primer_uso'],
                        'fecha_ultimo_uso': broca_stat['ultimo_uso'],
                        'estado': 'EN_USO' if broca_stat['total_usos'] > 0 else 'NUEVA'
                    }
                )
                
                if created:
                    creados += 1
                    print(f"✓ {serie}: Creado - {broca_stat['metraje_total']:.2f}m en {broca_stat['total_usos']} usos")
                else:
                    actualizados += 1
                    print(f"↻ {serie}: Actualizado - {broca_stat['metraje_total']:.2f}m en {broca_stat['total_usos']} usos")
            
            except Exception as e:
                errores += 1
                print(f"❌ {serie}: Error - {e}")
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE SINCRONIZACIÓN")
    print("="*80)
    print(f"✓ Historiales creados:      {creados}")
    print(f"↻ Historiales actualizados: {actualizados}")
    print(f"❌ Errores:                  {errores}")
    print(f"\nTotal en HistorialBroca:    {HistorialBroca.objects.count()}")
    print("="*80)
    
    if creados > 0 or actualizados > 0:
        print("\n✅ Sincronización completada exitosamente")
        print("   A partir de ahora, el historial se actualizará automáticamente")
    else:
        print("\n⚠️ No se sincronizaron datos")

if __name__ == '__main__':
    sincronizar_historial()
