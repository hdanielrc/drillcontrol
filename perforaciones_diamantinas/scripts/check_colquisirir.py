import os
import django
import sys

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Turno, Contrato, TurnoSondaje
from django.db.models import Count, Sum

# Buscar el contrato de Colquisirir
colquisirir = Contrato.objects.filter(nombre_contrato__icontains='colquisiri').first()

if not colquisirir:
    print('No se encontró contrato con "Colquisirir" en el nombre')
    print('\nContratos disponibles:')
    for c in Contrato.objects.all():
        print(f'  - {c.nombre_contrato}')
    sys.exit(1)

print(f'Contrato encontrado: {colquisirir.nombre_contrato} (ID: {colquisirir.id})')
print('=' * 70)

# Estados de turnos en Colquisirir
estados = Turno.objects.filter(contrato=colquisirir).values('estado').annotate(
    cantidad=Count('id')
).order_by('-cantidad')

print(f'\n=== ESTADOS DE TURNOS EN {colquisirir.nombre_contrato} ===')
total_turnos = 0
for estado in estados:
    print(f'{estado["estado"]}: {estado["cantidad"]} turnos')
    total_turnos += estado['cantidad']
print(f'TOTAL: {total_turnos} turnos')

# Metraje por estado
metraje_estados = TurnoSondaje.objects.filter(
    turno__contrato=colquisirir
).values('turno__estado').annotate(
    cantidad=Count('id'),
    metraje=Sum('metros_turno')
).order_by('-metraje')

print(f'\n=== METRAJE POR ESTADO EN {colquisirir.nombre_contrato} ===')
total_metraje = 0
for item in metraje_estados:
    metros = float(item['metraje']) if item['metraje'] else 0
    print(f'{item["turno__estado"]}: {item["cantidad"]} TurnoSondaje | {metros:.2f} metros')
    total_metraje += metros
print(f'TOTAL: {total_metraje:.2f} metros')

# Metraje por meses operativos
from datetime import date
print(f'\n=== DICIEMBRE 2025 (mes operativo: 26 nov - 25 dic) ===')
metraje_diciembre = TurnoSondaje.objects.filter(
    turno__contrato=colquisirir,
    turno__fecha__range=[date(2025, 11, 26), date(2025, 12, 25)],
    turno__estado__in=['COMPLETADO', 'APROBADO']
).aggregate(
    total=Sum('metros_turno'),
    cantidad=Count('id')
)
metros_diciembre = float(metraje_diciembre['total']) if metraje_diciembre['total'] else 0
print(f'Período: 26 noviembre 2025 - 25 diciembre 2025')
print(f'Turnos: {metraje_diciembre["cantidad"]} TurnoSondaje')
print(f'Metraje: {metros_diciembre:.2f} metros')

print(f'\n=== ENERO 2026 (mes operativo ACTUAL: 26 dic - 25 ene) ===')
metraje_enero = TurnoSondaje.objects.filter(
    turno__contrato=colquisirir,
    turno__fecha__range=[date(2025, 12, 26), date(2026, 1, 25)],
    turno__estado__in=['COMPLETADO', 'APROBADO']
).aggregate(
    total=Sum('metros_turno'),
    cantidad=Count('id')
)
metros_enero = float(metraje_enero['total']) if metraje_enero['total'] else 0
print(f'Período: 26 diciembre 2025 - 25 enero 2026')
print(f'Turnos: {metraje_enero["cantidad"]} TurnoSondaje')
print(f'Metraje: {metros_enero:.2f} metros')

# Verificar si hay más datos en todo el rango histórico
print(f'\n=== ANÁLISIS COMPLETO DE TODOS LOS TURNOS ===')
todos_turnos = TurnoSondaje.objects.filter(turno__contrato=colquisirir).select_related('turno')

print(f'\nTotal de TurnoSondaje registrados: {todos_turnos.count()}')
print(f'\nDetalle por fecha:')
turnos_por_fecha = todos_turnos.values('turno__fecha', 'turno__estado').annotate(
    cantidad=Count('id'),
    metraje=Sum('metros_turno')
).order_by('turno__fecha')

total_historico = 0
for item in turnos_por_fecha:
    metros = float(item['metraje']) if item['metraje'] else 0
    total_historico += metros
    print(f"  {item['turno__fecha']}: {item['cantidad']} turnos ({item['turno__estado']}) = {metros:.2f}m")

print(f'\nTOTAL HISTÓRICO: {total_historico:.2f} metros')

# Verificar todos los contratos
print(f'\n=== METRAJE POR TODOS LOS CONTRATOS ===')
metraje_contratos = TurnoSondaje.objects.values('turno__contrato__nombre_contrato').annotate(
    cantidad=Count('id'),
    metraje=Sum('metros_turno')
).order_by('-metraje')

for item in metraje_contratos:
    metros = float(item['metraje']) if item['metraje'] else 0
    print(f"{item['turno__contrato__nombre_contrato']}: {item['cantidad']} TurnoSondaje | {metros:.2f} metros")
