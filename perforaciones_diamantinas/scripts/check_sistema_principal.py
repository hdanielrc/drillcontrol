"""
Script para verificar datos de SISTEMA PRINCIPAL
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.db.models import Sum, Count
from drilling.models import Contrato, Turno, TurnoAvance, Trabajador, Maquina, Sondaje
from datetime import datetime, timedelta

print("=" * 80)
print("DIAGNÓSTICO: SISTEMA PRINCIPAL")
print("=" * 80)

# Buscar contrato
try:
    contrato = Contrato.objects.get(nombre_contrato="SISTEMA PRINCIPAL")
    print(f"\n✓ Contrato encontrado: {contrato.nombre_contrato} (ID: {contrato.id})")
except Contrato.DoesNotExist:
    print("\n✗ Contrato SISTEMA PRINCIPAL no encontrado")
    sys.exit(1)

# Verificar recursos
trabajadores = Trabajador.objects.filter(contrato=contrato).count()
maquinas = Maquina.objects.filter(contrato=contrato).count()
sondajes = Sondaje.objects.filter(contrato=contrato).count()

print(f"\nRECURSOS:")
print(f"  - Trabajadores: {trabajadores}")
print(f"  - Máquinas: {maquinas}")
print(f"  - Sondajes: {sondajes}")

# Verificar turnos
turnos_total = Turno.objects.filter(contrato=contrato).count()
print(f"\nTURNOS:")
print(f"  - Total: {turnos_total}")

if turnos_total > 0:
    # Por estado
    estados = Turno.objects.filter(contrato=contrato).values('estado').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')
    
    print(f"\n  Por estado:")
    for e in estados:
        print(f"    - {e['estado']}: {e['cantidad']}")
    
    # Rango de fechas
    primer_turno = Turno.objects.filter(contrato=contrato).order_by('fecha').first()
    ultimo_turno = Turno.objects.filter(contrato=contrato).order_by('-fecha').first()
    print(f"\n  Rango fechas: {primer_turno.fecha} → {ultimo_turno.fecha}")
    
    # TurnoAvance
    avances_total = TurnoAvance.objects.filter(turno__contrato=contrato).count()
    metros_total = TurnoAvance.objects.filter(turno__contrato=contrato).aggregate(
        total=Sum('metros_perforados')
    )['total'] or 0
    
    print(f"\nTURNO AVANCE:")
    print(f"  - Registros: {avances_total}")
    print(f"  - Metros totales: {metros_total:.2f} m")
    
    # Mes operativo actual (26 dic - 25 ene)
    hoy = datetime.now().date()
    if hoy.day >= 26:
        fecha_inicio = hoy.replace(day=26)
        if hoy.month == 12:
            fecha_fin = hoy.replace(year=hoy.year + 1, month=1, day=25)
        else:
            fecha_fin = hoy.replace(month=hoy.month + 1, day=25)
    else:
        if hoy.month == 1:
            fecha_inicio = hoy.replace(year=hoy.year - 1, month=12, day=26)
        else:
            fecha_inicio = hoy.replace(month=hoy.month - 1, day=26)
        fecha_fin = hoy.replace(day=25)
    
    print(f"\nMES OPERATIVO ACTUAL ({fecha_inicio} → {fecha_fin}):")
    
    turnos_mes = Turno.objects.filter(
        contrato=contrato,
        fecha__range=[fecha_inicio, fecha_fin]
    ).count()
    
    turnos_mes_completados = Turno.objects.filter(
        contrato=contrato,
        fecha__range=[fecha_inicio, fecha_fin],
        estado__in=['COMPLETADO', 'APROBADO']
    ).count()
    
    avances_mes = TurnoAvance.objects.filter(
        turno__contrato=contrato,
        turno__fecha__range=[fecha_inicio, fecha_fin]
    ).count()
    
    metros_mes = TurnoAvance.objects.filter(
        turno__contrato=contrato,
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).aggregate(total=Sum('metros_perforados'))['total'] or 0
    
    print(f"  - Turnos: {turnos_mes} total | {turnos_mes_completados} COMPLETADO/APROBADO")
    print(f"  - TurnoAvance: {avances_mes}")
    print(f"  - Metros (COMPLETADO/APROBADO): {metros_mes:.2f} m")
    
    # Últimos 7 días
    hace_7_dias = hoy - timedelta(days=7)
    turnos_7dias = Turno.objects.filter(
        contrato=contrato,
        fecha__gte=hace_7_dias
    ).count()
    
    metros_7dias = TurnoAvance.objects.filter(
        turno__contrato=contrato,
        turno__fecha__gte=hace_7_dias,
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).aggregate(total=Sum('metros_perforados'))['total'] or 0
    
    print(f"\nÚLTIMOS 7 DÍAS ({hace_7_dias} → {hoy}):")
    print(f"  - Turnos: {turnos_7dias}")
    print(f"  - Metros: {metros_7dias:.2f} m")

print("\n" + "=" * 80)
