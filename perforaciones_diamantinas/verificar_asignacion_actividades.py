#!/usr/bin/env python
"""Script para verificar las asignaciones de actividades por contrato"""
import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.db import connection
from drilling.models import Contrato

print("\n" + "="*80)
print("RESUMEN DE ACTIVIDADES POR CONTRATO")
print("="*80)

contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')

with connection.cursor() as cursor:
    for contrato in contratos:
        cursor.execute(
            "SELECT COUNT(*) FROM contratos_actividades WHERE contrato_id = %s",
            [contrato.id]
        )
        count = cursor.fetchone()[0]
        
        print(f"\n📋 {contrato.nombre_contrato}")
        print(f"   Cliente: {contrato.cliente.nombre}")
        print(f"   Actividades asignadas: {count}")

print("\n" + "="*80)
