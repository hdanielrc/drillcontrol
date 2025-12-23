import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato, TurnoAvance, Turno
from django.db.models import Sum, Q, Count
from datetime import date

hoy = date.today()

# Buscar contrato COLQUISIRI
colquisiri = Contrato.objects.filter(nombre_contrato__icontains='COLQUISIRI').first()
print(f"\n{'='*60}")
print(f"Contrato: {colquisiri}")
print(f"{'='*60}\n")

# Metros directos de TurnoAvance
metros_directos = TurnoAvance.objects.filter(
    turno__contrato=colquisiri,
    turno__fecha__month=hoy.month,
    turno__fecha__year=hoy.year
).aggregate(total=Sum('metros_perforados'))

print(f"MÉTODO 1 - Consulta directa a TurnoAvance:")
print(f"  Metros del mes: {metros_directos['total'] or 0}")

# Método usado en el dashboard (con annotate)
metricas_dashboard = Contrato.objects.filter(
    id=colquisiri.id
).annotate(
    metros_mes_total=Sum(
        'turnos__avance__metros_perforados',
        filter=Q(turnos__fecha__month=hoy.month, turnos__fecha__year=hoy.year)
    )
).first()

print(f"\nMÉTODO 2 - Query del dashboard (con annotate):")
print(f"  Metros del mes: {metricas_dashboard.metros_mes_total or 0}")

# Verificar si hay duplicados por sondajes múltiples
turnos_mes = Turno.objects.filter(
    contrato=colquisiri,
    fecha__month=hoy.month,
    fecha__year=hoy.year
).prefetch_related('sondajes')

print(f"\nANÁLISIS DE TURNOS DEL MES:")
print(f"  Total de turnos: {turnos_mes.count()}")

total_calculado = 0
for turno in turnos_mes:
    sondajes_count = turno.sondajes.count()
    try:
        metros = turno.avance.metros_perforados
    except:
        metros = 0
    
    if sondajes_count > 1:
        print(f"  ⚠️  Turno #{turno.id} - {turno.fecha} - {sondajes_count} sondajes - {metros} metros")
    
    total_calculado += metros

print(f"\n  Total metros calculados manualmente: {total_calculado}")

# Verificar la query problemática con distinct
metricas_con_distinct = Contrato.objects.filter(
    id=colquisiri.id
).annotate(
    turnos_count=Count('turnos', filter=Q(turnos__fecha__month=hoy.month, turnos__fecha__year=hoy.year), distinct=True),
    # Sin distinct
    turnos_count_sin_distinct=Count('turnos', filter=Q(turnos__fecha__month=hoy.month, turnos__fecha__year=hoy.year))
).first()

print(f"\nCOMPARACIÓN DE COUNTS:")
print(f"  Turnos con DISTINCT: {metricas_con_distinct.turnos_count}")
print(f"  Turnos SIN distinct: {metricas_con_distinct.turnos_count_sin_distinct}")
print(f"  Ratio: {metricas_con_distinct.turnos_count_sin_distinct / metricas_con_distinct.turnos_count if metricas_con_distinct.turnos_count > 0 else 0:.2f}x")

print(f"\n{'='*60}")
print("CONCLUSIÓN:")
if metricas_con_distinct.turnos_count_sin_distinct > metricas_con_distinct.turnos_count:
    print("⚠️  HAY DUPLICACIÓN: Los turnos se están contando múltiples veces")
    print("    Causa probable: Relación ManyToMany con sondajes")
    print(f"    Metros mostrados (incorrecto): {metricas_dashboard.metros_mes_total or 0}")
    print(f"    Metros reales: {metros_directos['total'] or 0}")
else:
    print("✓ No hay duplicación detectada")
print(f"{'='*60}\n")
