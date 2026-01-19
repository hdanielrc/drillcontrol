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

# Metraje por mes en enero 2025
from datetime import date
print(f'\n=== METRAJE EN ENERO 2025 (mes natural: 1-31 ene) ===')
metraje_enero = TurnoSondaje.objects.filter(
    turno__contrato=colquisirir,
    turno__fecha__range=[date(2025, 1, 1), date(2025, 1, 31)],
    turno__estado__in=['COMPLETADO', 'APROBADO']
).aggregate(
    total=Sum('metros_turno'),
    cantidad=Count('id')
)
metros_enero = float(metraje_enero['total']) if metraje_enero['total'] else 0
print(f'Período: 1 enero - 31 enero 2025')
print(f'Turnos: {metraje_enero["cantidad"]} TurnoSondaje')
print(f'Metraje: {metros_enero:.2f} metros')

print(f'\n=== METRAJE EN DICIEMBRE 2024 (mes operativo: 26 dic - 25 ene) ===')
metraje_mes_operativo = TurnoSondaje.objects.filter(
    turno__contrato=colquisirir,
    turno__fecha__range=[date(2024, 12, 26), date(2025, 1, 25)],
    turno__estado__in=['COMPLETADO', 'APROBADO']
).aggregate(
    total=Sum('metros_turno'),
    cantidad=Count('id')
)
metros_operativo = float(metraje_mes_operativo['total']) if metraje_mes_operativo['total'] else 0
print(f'Período: 26 diciembre 2024 - 25 enero 2025')
print(f'Turnos: {metraje_mes_operativo["cantidad"]} TurnoSondaje')
print(f'Metraje: {metros_operativo:.2f} metros')
