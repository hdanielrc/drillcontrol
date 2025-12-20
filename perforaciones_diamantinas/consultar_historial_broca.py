#!/usr/bin/env python
"""
Script para consultar el historial de una broca específica por serie
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

from drilling.models import HistorialBroca, TurnoComplemento

def consultar_broca(serie):
    """Consulta el historial completo de una broca"""
    
    print("\n" + "="*80)
    print(f"HISTORIAL DE BROCA: {serie}")
    print("="*80)
    
    try:
        historial = HistorialBroca.objects.get(serie=serie)
    except HistorialBroca.DoesNotExist:
        print(f"\n❌ No se encontró historial para la serie {serie}")
        print("\nVerificando en TurnoComplemento...")
        
        usos = TurnoComplemento.objects.filter(codigo_serie=serie).count()
        if usos > 0:
            print(f"⚠️  Encontrados {usos} usos en TurnoComplemento pero sin historial consolidado")
            print("   Ejecute: python sincronizar_historial_brocas.py")
        else:
            print("   No hay registros de uso para esta serie")
        return
    
    # Información general
    print(f"\n📋 INFORMACIÓN GENERAL")
    print("-" * 80)
    print(f"Serie:                {historial.serie}")
    print(f"Producto:             {historial.tipo_complemento.nombre}")
    print(f"Estado:               {historial.get_estado_display()}")
    print(f"Contrato actual:      {historial.contrato_actual.nombre_contrato}")
    
    # Métricas
    print(f"\n📊 MÉTRICAS DE USO")
    print("-" * 80)
    print(f"Metraje acumulado:    {historial.metraje_acumulado:,.2f} m")
    print(f"Número de usos:       {historial.numero_usos}")
    print(f"Promedio por uso:     {historial.metraje_promedio_por_uso():,.2f} m")
    
    # Fechas
    print(f"\n📅 FECHAS")
    print("-" * 80)
    if historial.fecha_primer_uso:
        print(f"Primer uso:           {historial.fecha_primer_uso.strftime('%d/%m/%Y')}")
        dias_uso = historial.dias_desde_primer_uso()
        if dias_uso is not None:
            print(f"Días desde 1er uso:   {dias_uso} días")
    
    if historial.fecha_ultimo_uso:
        print(f"Último uso:           {historial.fecha_ultimo_uso.strftime('%d/%m/%Y')}")
        dias_sin_uso = historial.dias_sin_uso()
        if dias_sin_uso is not None:
            print(f"Días sin usar:        {dias_sin_uso} días")
    
    if historial.fecha_baja:
        print(f"Fecha de baja:        {historial.fecha_baja.strftime('%d/%m/%Y')}")
    
    # Observaciones
    if historial.observaciones:
        print(f"\n💬 OBSERVACIONES")
        print("-" * 80)
        print(historial.observaciones)
    
    # Historial detallado
    print(f"\n📝 HISTORIAL DETALLADO DE USOS")
    print("-" * 80)
    
    usos = historial.obtener_historial_detallado()
    
    if usos.exists():
        print(f"\n{'#':<4} {'Fecha':<12} {'Turno':<8} {'Máquina':<15} {'Sondaje':<20} {'M.Inicio':<10} {'M.Fin':<10} {'M.Turno':<10}")
        print("-" * 100)
        
        metraje_acum = 0
        for i, uso in enumerate(usos, 1):
            fecha = uso.turno.fecha.strftime('%d/%m/%Y')
            turno_id = f"#{uso.turno.id}"
            maquina = uso.turno.maquina.nombre[:13]
            sondaje = uso.sondaje.nombre_sondaje[:18] if uso.sondaje else 'N/A'
            m_inicio = uso.metros_inicio
            m_fin = uso.metros_fin
            m_turno = uso.metros_turno_calc
            metraje_acum += m_turno
            
            print(f"{i:<4} {fecha:<12} {turno_id:<8} {maquina:<15} {sondaje:<20} {m_inicio:>8.2f}  {m_fin:>8.2f}  {m_turno:>8.2f}")
        
        print("-" * 100)
        print(f"{'TOTAL':<68} {metraje_acum:>8.2f} m")
    else:
        print("No hay registros detallados de uso")
    
    print("\n" + "="*80)

def listar_brocas_activas():
    """Lista todas las brocas activas"""
    
    print("\n" + "="*80)
    print("BROCAS ACTIVAS")
    print("="*80)
    
    brocas = HistorialBroca.objects.filter(
        estado__in=['NUEVA', 'EN_USO', 'DESGASTADA']
    ).order_by('-metraje_acumulado')[:50]
    
    if not brocas:
        print("\n⚠️ No hay brocas activas en el historial")
        return
    
    print(f"\n{'#':<4} {'Serie':<12} {'Estado':<15} {'Metraje':<12} {'Usos':<8} {'Último Uso':<12}")
    print("-" * 80)
    
    for i, broca in enumerate(brocas, 1):
        serie = broca.serie[:10]
        estado = broca.get_estado_display()
        metraje = f"{broca.metraje_acumulado:.2f} m"
        usos = broca.numero_usos
        ultimo = broca.fecha_ultimo_uso.strftime('%d/%m/%Y') if broca.fecha_ultimo_uso else 'N/A'
        
        print(f"{i:<4} {serie:<12} {estado:<15} {metraje:<12} {usos:<8} {ultimo:<12}")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Consultar broca específica
        serie = sys.argv[1]
        consultar_broca(serie)
    else:
        # Listar brocas activas
        listar_brocas_activas()
        print("\nPara ver el historial de una broca específica:")
        print("  python consultar_historial_broca.py <serie>")
        print("\nEjemplo:")
        print("  python consultar_historial_broca.py 409381")
