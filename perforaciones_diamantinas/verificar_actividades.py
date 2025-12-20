#!/usr/bin/env python
"""
Script para verificar las actividades cargadas
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

from drilling.models import TipoActividad

print("\n" + "="*80)
print("RESUMEN DE ACTIVIDADES CARGADAS")
print("="*80)

actividades = TipoActividad.objects.all()
print(f"\n✅ Total actividades en BD: {actividades.count()}")

print("\nActividades por tipo:")
for tipo, nombre_tipo in [
    ('OPERATIVO', 'Operativo'),
    ('INOPERATIVO', 'Inoperativo'),
    ('STAND_BY_CLIENTE', 'Stand By Cliente'),
    ('STAND_BY_ROCKDRILL', 'Stand By RockDrill'),
    ('OTROS', 'Otros')
]:
    count = actividades.filter(tipo_actividad=tipo).count()
    print(f"  - {nombre_tipo}: {count}")

print("\nActividades cobrables:")
cobrables = actividades.filter(es_cobrable=True).count()
no_cobrables = actividades.filter(es_cobrable=False).count()
print(f"  - Cobrables: {cobrables}")
print(f"  - No cobrables: {no_cobrables}")

print("\n" + "="*80)
print("DETALLE POR TIPO DE ACTIVIDAD")
print("="*80)

for tipo, nombre_tipo in [
    ('OPERATIVO', 'ACTIVIDADES OPERATIVAS'),
    ('STAND_BY_CLIENTE', 'STAND BY POR CLIENTE'),
    ('STAND_BY_ROCKDRILL', 'STAND BY ROCKDRILL'),
    ('INOPERATIVO', 'INOPERATIVO'),
]:
    acts = actividades.filter(tipo_actividad=tipo).order_by('nombre')
    if acts.exists():
        print(f"\n📋 {nombre_tipo} ({acts.count()}):")
        for act in acts:
            cobrable = "💰 COBRABLE" if act.es_cobrable else "🔹 NO COBRABLE"
            print(f"   • {act.nombre} - {cobrable}")

print("\n" + "="*80)
