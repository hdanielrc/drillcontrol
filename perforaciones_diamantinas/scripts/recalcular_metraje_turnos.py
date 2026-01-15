"""
Script para recalcular el metraje de todos los turnos existentes
considerando SOLO las brocas (categoria='BROCA'), excluyendo reamers y otros complementos.

Uso:
    python manage.py shell < scripts/recalcular_metraje_turnos.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Turno, TurnoAvance, TurnoComplemento
from django.db.models import Sum
from decimal import Decimal

def recalcular_metraje_turnos():
    """
    Recalcula el metraje de todos los turnos basándose solo en brocas
    """
    print("=" * 80)
    print("RECALCULANDO METRAJE DE TURNOS - SOLO BROCAS")
    print("=" * 80)
    
    turnos_con_avance = TurnoAvance.objects.select_related('turno').all()
    total_turnos = turnos_con_avance.count()
    actualizados = 0
    sin_cambios = 0
    errores = 0
    
    print(f"\nTotal de turnos con avance: {total_turnos}")
    print("\nProcesando...\n")
    
    for avance in turnos_con_avance:
        turno = avance.turno
        metros_anterior = avance.metros_perforados
        
        try:
            # Calcular metros solo de BROCAS
            total_brocas = TurnoComplemento.objects.filter(
                turno=turno,
                tipo_complemento__categoria='BROCA'
            ).aggregate(total=Sum('metros_turno_calc'))['total']
            
            metros_nuevo = Decimal(str(total_brocas)) if total_brocas is not None else Decimal('0.00')
            
            # Solo actualizar si hay diferencia
            if metros_anterior != metros_nuevo:
                avance.metros_perforados = metros_nuevo
                avance.save()
                actualizados += 1
                
                print(f"✓ Turno #{turno.id} ({turno.fecha})")
                print(f"  Anterior: {metros_anterior}m → Nuevo: {metros_nuevo}m")
                print(f"  Diferencia: {metros_anterior - metros_nuevo}m")
                print()
            else:
                sin_cambios += 1
                
        except Exception as e:
            errores += 1
            print(f"✗ Error en Turno #{turno.id}: {e}")
            print()
    
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Total procesados: {total_turnos}")
    print(f"Actualizados:     {actualizados}")
    print(f"Sin cambios:      {sin_cambios}")
    print(f"Errores:          {errores}")
    print("=" * 80)
    
    # Mostrar algunos ejemplos de turnos actualizados
    if actualizados > 0:
        print("\nEjemplos de turnos recalculados:")
        turnos_ejemplo = TurnoAvance.objects.select_related('turno').order_by('-turno__fecha')[:5]
        for avance in turnos_ejemplo:
            # Contar brocas vs complementos
            total_items = TurnoComplemento.objects.filter(turno=avance.turno).count()
            total_brocas = TurnoComplemento.objects.filter(
                turno=avance.turno, 
                tipo_complemento__categoria='BROCA'
            ).count()
            total_complementos = total_items - total_brocas
            
            print(f"\n  Turno #{avance.turno.id} - {avance.turno.fecha}")
            print(f"  Metraje: {avance.metros_perforados}m")
            print(f"  Items: {total_brocas} brocas, {total_complementos} complementos")

if __name__ == '__main__':
    recalcular_metraje_turnos()
