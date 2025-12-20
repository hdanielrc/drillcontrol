#!/usr/bin/env python
"""Script simplificado para asignar todas las actividades a todos los contratos"""
import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato, TipoActividad, ContratoActividad

contratos = Contrato.objects.filter(estado='ACTIVO')
actividades = TipoActividad.objects.all()

print(f"\nAsignando {actividades.count()} actividades a {contratos.count()} contratos activos...\n")

total_nuevas = 0
total_existentes = 0

for contrato in contratos:
    print(f"Procesando: {contrato.nombre_contrato}...", end=" ")
    nuevas = 0
    existentes = 0
    
    for actividad in actividades:
        _, created = ContratoActividad.objects.get_or_create(
            contrato=contrato,
            tipoactividad=actividad
        )
        if created:
            nuevas += 1
        else:
            existentes += 1
    
    total_nuevas += nuevas
    total_existentes += existentes
    print(f"OK ({nuevas} nuevas, {existentes} existentes)")

print(f"\n✅ Completado:")
print(f"   Contratos: {contratos.count()}")
print(f"   Nuevas asignaciones: {total_nuevas}")
print(f"   Ya existentes: {total_existentes}")
