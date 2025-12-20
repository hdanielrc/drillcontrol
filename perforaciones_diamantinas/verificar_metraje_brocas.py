#!/usr/bin/env python
"""
Script para verificar qué datos de metraje de brocas se están guardando actualmente
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

from drilling.models import TurnoComplemento
from django.db.models import Sum, Count, Max, Min, F
from decimal import Decimal

def analizar_metraje_brocas():
    """
    Analiza los datos actuales de metraje de brocas en TurnoComplemento
    """
    
    print("\n" + "="*80)
    print("ANÁLISIS DE METRAJE DE BROCAS - DATOS ACTUALES")
    print("="*80)
    
    # Total de registros
    total_registros = TurnoComplemento.objects.count()
    print(f"\nTotal de registros en TurnoComplemento: {total_registros}")
    
    if total_registros == 0:
        print("\n⚠️ No hay datos de productos diamantados registrados aún")
        print("\nEstructura actual del modelo TurnoComplemento:")
        print("  - turno: FK al turno donde se usó")
        print("  - sondaje: FK al sondaje")
        print("  - tipo_complemento: FK al tipo de producto")
        print("  - codigo_serie: Campo de texto con el código/serie")
        print("  - metros_inicio: Metros iniciales ✓")
        print("  - metros_fin: Metros finales ✓")
        print("  - metros_turno_calc: Metros del turno (calculado automáticamente) ✓")
        print("\n✅ Los campos de metraje YA EXISTEN y se están guardando")
        print("\n❌ PROBLEMA: No se acumula el metraje total por serie de broca")
        return
    
    # Análisis por código de serie
    print("\n" + "-"*80)
    print("ANÁLISIS POR CÓDIGO DE SERIE")
    print("-"*80)
    
    # Agrupar por código_serie y calcular estadísticas
    brocas = TurnoComplemento.objects.values('codigo_serie').annotate(
        total_usos=Count('id'),
        metraje_total=Sum('metros_turno_calc'),
        metraje_promedio=Sum('metros_turno_calc') / Count('id'),
        primer_uso=Min('turno__fecha'),
        ultimo_uso=Max('turno__fecha')
    ).order_by('-metraje_total')[:20]  # Top 20 brocas más usadas
    
    if brocas:
        print(f"\nTop 20 brocas con más metraje acumulado:\n")
        print(f"{'#':<4} {'Serie':<12} {'Usos':<6} {'Metraje Total':<15} {'Promedio/Uso':<15} {'Primer Uso':<12} {'Último Uso':<12}")
        print("-"*90)
        
        for i, broca in enumerate(brocas, 1):
            serie = broca['codigo_serie'][:10]  # Truncar si es muy largo
            usos = broca['total_usos']
            total = broca['metraje_total'] or Decimal('0')
            promedio = broca['metraje_promedio'] or Decimal('0')
            primer = broca['primer_uso'].strftime('%Y-%m-%d') if broca['primer_uso'] else 'N/A'
            ultimo = broca['ultimo_uso'].strftime('%Y-%m-%d') if broca['ultimo_uso'] else 'N/A'
            
            print(f"{i:<4} {serie:<12} {usos:<6} {total:>12.2f} m  {promedio:>12.2f} m  {primer:<12} {ultimo:<12}")
    
    # Verificar si hay brocas con múltiples usos
    brocas_multiples_usos = TurnoComplemento.objects.values('codigo_serie').annotate(
        usos=Count('id')
    ).filter(usos__gt=1).count()
    
    print("\n" + "-"*80)
    print("ESTADÍSTICAS GENERALES")
    print("-"*80)
    print(f"Brocas únicas (diferentes series):    {TurnoComplemento.objects.values('codigo_serie').distinct().count()}")
    print(f"Brocas con múltiples usos:             {brocas_multiples_usos}")
    print(f"Metraje total perforado:               {TurnoComplemento.objects.aggregate(total=Sum('metros_turno_calc'))['total'] or 0:.2f} m")
    
    # Ejemplo de consulta que tendríamos que hacer CADA VEZ para ver el historial de una broca
    print("\n" + "-"*80)
    print("PROBLEMA ACTUAL")
    print("-"*80)
    print("""
❌ Para obtener el metraje total de una broca específica, hay que:
   1. Hacer una consulta agregada cada vez: 
      TurnoComplemento.objects.filter(codigo_serie='409381').aggregate(Sum('metros_turno_calc'))
   2. No hay campo de estado (Nueva, En Uso, Desgastada, Quemada)
   3. No hay forma rápida de saber cuántos usos tiene una broca
   4. No se puede hacer seguimiento del ciclo de vida

✅ SOLUCIÓN PROPUESTA: Modelo HistorialBroca
   - Acumula metraje automáticamente al guardar TurnoComplemento
   - Campo 'estado' para seguimiento de vida útil
   - Campos 'numero_usos' y 'metraje_acumulado' pre-calculados
   - Consultas instantáneas sin agregaciones pesadas
    """)
    
    # Mostrar ejemplo detallado de una broca específica
    print("\n" + "-"*80)
    print("EJEMPLO: Historial detallado de una broca")
    print("-"*80)
    
    # Tomar la broca con más usos
    broca_ejemplo = TurnoComplemento.objects.values('codigo_serie').annotate(
        usos=Count('id')
    ).order_by('-usos').first()
    
    if broca_ejemplo:
        serie_ejemplo = broca_ejemplo['codigo_serie']
        print(f"\nSerie: {serie_ejemplo}")
        print(f"Total de usos: {broca_ejemplo['usos']}\n")
        
        usos = TurnoComplemento.objects.filter(
            codigo_serie=serie_ejemplo
        ).select_related('turno', 'tipo_complemento').order_by('turno__fecha')[:10]
        
        print(f"{'Fecha':<12} {'Turno ID':<10} {'Producto':<30} {'M.Inicio':<10} {'M.Fin':<10} {'M.Turno':<10}")
        print("-"*90)
        
        metraje_acum = Decimal('0')
        for uso in usos:
            fecha = uso.turno.fecha.strftime('%Y-%m-%d')
            turno_id = uso.turno.id
            producto = uso.tipo_complemento.nombre[:28]
            m_inicio = uso.metros_inicio
            m_fin = uso.metros_fin
            m_turno = uso.metros_turno_calc
            metraje_acum += m_turno
            
            print(f"{fecha:<12} {turno_id:<10} {producto:<30} {m_inicio:>8.2f}  {m_fin:>8.2f}  {m_turno:>8.2f}")
        
        if usos.count() > 10:
            print(f"... y {usos.count() - 10} registros más")
        
        print(f"\nMetraje acumulado: {metraje_acum:.2f} m")
        print("\n💡 Con HistorialBroca, este metraje estaría pre-calculado y disponible instantáneamente")

if __name__ == '__main__':
    analizar_metraje_brocas()
