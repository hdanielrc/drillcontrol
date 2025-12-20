#!/usr/bin/env python
"""Script para asignar actividades usando SQL directo"""
import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.db import connection
from drilling.models import Contrato, TipoActividad

contratos = Contrato.objects.filter(estado='ACTIVO')
actividades = TipoActividad.objects.all()

print(f"\n✅ Asignando {actividades.count()} actividades a {contratos.count()} contratos activos...\n")

total_nuevas = 0
total_existentes = 0

with connection.cursor() as cursor:
    for contrato in contratos:
        print(f"📋 {contrato.nombre_contrato}...", end=" ")
        nuevas = 0
        existentes = 0
        
        for actividad in actividades:
            # Verificar si ya existe
            cursor.execute(
                "SELECT COUNT(*) FROM contratos_actividades WHERE contrato_id = %s AND tipoactividad_id = %s",
                [contrato.id, actividad.id]
            )
            existe = cursor.fetchone()[0] > 0
            
            if not existe:
                # Insertar nueva relación
                cursor.execute(
                    "INSERT INTO contratos_actividades (contrato_id, tipoactividad_id) VALUES (%s, %s)",
                    [contrato.id, actividad.id]
                )
                nuevas += 1
            else:
                existentes += 1
        
        total_nuevas += nuevas
        total_existentes += existentes
        
        # Obtener total actual del contrato
        cursor.execute(
            "SELECT COUNT(*) FROM contratos_actividades WHERE contrato_id = %s",
            [contrato.id]
        )
        total_contrato = cursor.fetchone()[0]
        
        print(f"OK ({nuevas} nuevas, {total_contrato} total)")

print(f"\n" + "="*80)
print("✅ PROCESO COMPLETADO")
print("="*80)
print(f"   Contratos procesados: {contratos.count()}")
print(f"   Nuevas asignaciones: {total_nuevas}")
print(f"   Ya existentes: {total_existentes}")
print(f"   Total asignaciones: {total_nuevas + total_existentes}")
print("="*80)
