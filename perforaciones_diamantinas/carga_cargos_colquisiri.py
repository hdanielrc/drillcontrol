"""
Script para cargar los cargos específicos de COLQUISIRI
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.db.models import Max
from drilling.models import Cargo

def cargar_cargos_colquisiri():
    """Crear los cargos usados en COLQUISIRI"""
    
    # Obtener el máximo id_cargo actual
    max_id = Cargo.objects.aggregate(Max('id_cargo'))['id_cargo__max'] or 0
    
    cargos = [
        'Residente CTR',
        'Inspector de Seguridad',
        'Administradora',
        'Perforista DDH II - SB',
        'Perforista DDH I',
        'Ayudante DDH I',
        'Ayudante DDH II',
        'Técnico Mecánico II',
    ]
    
    print("\n" + "="*60)
    print("CARGANDO CARGOS DE COLQUISIRI")
    print("="*60 + "\n")
    
    creados = 0
    existentes = 0
    next_id = max_id + 1
    
    for nombre_cargo in cargos:
        try:
            cargo = Cargo.objects.get(nombre=nombre_cargo)
            print(f"ℹ️  Ya existe: {nombre_cargo} (ID: {cargo.id_cargo})")
            existentes += 1
        except Cargo.DoesNotExist:
            cargo = Cargo.objects.create(
                id_cargo=next_id,
                nombre=nombre_cargo,
                descripcion=f'Cargo para operaciones en COLQUISIRI'
            )
            print(f"✅ Creado: {nombre_cargo} (ID: {next_id})")
            creados += 1
            next_id += 1
    
    print("\n" + "="*60)
    print(f"Resumen:")
    print(f"  Cargos creados: {creados}")
    print(f"  Cargos existentes: {existentes}")
    print(f"  Total: {creados + existentes}")
    print("="*60 + "\n")

if __name__ == "__main__":
    cargar_cargos_colquisiri()
