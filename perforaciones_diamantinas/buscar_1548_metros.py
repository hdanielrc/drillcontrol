import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato, TurnoAvance, Turno
from django.db.models import Sum, Q
from datetime import date

# Buscar contrato COLQUISIRI
colquisiri = Contrato.objects.filter(nombre_contrato__icontains='COLQUISIRI').first()
print(f"\n{'='*70}")
print(f"Contrato: {colquisiri}")
print(f"{'='*70}\n")

# Analizar todos los meses del año 2025
print("METROS POR MES EN 2025:")
print(f"{'Mes':<15} {'Metros (Directo)':<20} {'Metros (Dashboard)':<20} {'Diferencia'}")
print("-" * 70)

total_directo = 0
total_dashboard = 0

for mes in range(1, 13):
    # Método directo
    metros_directos = TurnoAvance.objects.filter(
        turno__contrato=colquisiri,
        turno__fecha__month=mes,
        turno__fecha__year=2025
    ).aggregate(total=Sum('metros_perforados'))
    
    # Método del dashboard
    metricas_dashboard = Contrato.objects.filter(
        id=colquisiri.id
    ).annotate(
        metros_mes_total=Sum(
            'turnos__avance__metros_perforados',
            filter=Q(turnos__fecha__month=mes, turnos__fecha__year=2025)
        )
    ).first()
    
    directo = metros_directos['total'] or 0
    dashboard = metricas_dashboard.metros_mes_total or 0
    diferencia = dashboard - directo
    
    total_directo += directo
    total_dashboard += dashboard
    
    meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    
    if directo > 0 or dashboard > 0:
        marca = "⚠️ " if diferencia != 0 else "✓ "
        print(f"{marca}{meses[mes]:<13} {directo:<20.2f} {dashboard:<20.2f} {diferencia:+.2f}")

print("-" * 70)
print(f"{'TOTAL 2025':<15} {total_directo:<20.2f} {total_dashboard:<20.2f} {total_dashboard - total_directo:+.2f}")

# Buscar si hay 1548 en algún lado
print(f"\n{'='*70}")
print("BUSCANDO EL VALOR 1548...")
print(f"{'='*70}\n")

# Verificar por año
for año in [2024, 2025]:
    metros_año = TurnoAvance.objects.filter(
        turno__contrato=colquisiri,
        turno__fecha__year=año
    ).aggregate(total=Sum('metros_perforados'))
    
    total_año = metros_año['total'] or 0
    if abs(total_año - 1548) < 1:
        print(f"✓ ENCONTRADO: Total del año {año} = {total_año:.2f} metros")
    else:
        print(f"  Año {año}: {total_año:.2f} metros")

# Verificar acumulado histórico
metros_total = TurnoAvance.objects.filter(
    turno__contrato=colquisiri
).aggregate(total=Sum('metros_perforados'))

print(f"\nTotal histórico (todos los tiempos): {metros_total['total'] or 0:.2f} metros")

if abs((metros_total['total'] or 0) - 1548) < 1:
    print("✓ ENCONTRADO: El valor 1548 corresponde al total histórico")

print(f"\n{'='*70}\n")
