"""
Script para cargar todos los datos desde los archivos CSV a la base de datos
"""
import os
import sys
import django
import csv

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Cliente, Contrato, Cargo
from django.db import models

def cargar_clientes():
    print("\n" + "="*80)
    print("CARGANDO CLIENTES")
    print("="*80)
    
    archivo = 'plantilla_clientes.csv'
    if not os.path.exists(archivo):
        print(f"❌ No se encontró el archivo {archivo}")
        return 0
    
    count = 0
    with open(archivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            cliente, created = Cliente.objects.get_or_create(
                nombre=row['nombre'],
                defaults={'is_active': row['es_activo'].upper() == 'SI'}
            )
            if created:
                print(f"✅ Cliente creado: {cliente.nombre}")
                count += 1
            else:
                print(f"⚠️  Cliente ya existe: {cliente.nombre}")
    
    print(f"\n✅ Total clientes en BD: {Cliente.objects.count()}")
    print(f"   Nuevos creados: {count}")
    return count

def cargar_contratos():
    print("\n" + "="*80)
    print("CARGANDO CONTRATOS")
    print("="*80)
    
    archivo = 'plantilla_contratos.csv'
    if not os.path.exists(archivo):
        print(f"❌ No se encontró el archivo {archivo}")
        return 0
    
    count = 0
    with open(archivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            try:
                cliente = Cliente.objects.get(nombre=row['cliente_nombre'])
                
                # Formatear codigo_centro_costo con ceros a la izquierda
                codigo_cc = str(row['codigo_centro_costo']).zfill(6)
                
                contrato, created = Contrato.objects.get_or_create(
                    nombre_contrato=row['nombre_contrato'],
                    defaults={
                        'cliente': cliente,
                        'codigo_centro_costo': codigo_cc,
                        'duracion_turno': float(row['duracion_turno']),
                        'estado': row['estado']
                    }
                )
                if created:
                    print(f"✅ Contrato creado: {contrato.nombre_contrato} (CC: {codigo_cc})")
                    count += 1
                else:
                    print(f"⚠️  Contrato ya existe: {contrato.nombre_contrato}")
            except Cliente.DoesNotExist:
                print(f"❌ Cliente no encontrado: {row['cliente_nombre']}")
            except Exception as e:
                print(f"❌ Error al crear contrato {row['nombre_contrato']}: {str(e)}")
    
    print(f"\n✅ Total contratos en BD: {Contrato.objects.count()}")
    print(f"   Nuevos creados: {count}")
    return count

def cargar_cargos():
    print("\n" + "="*80)
    print("CARGANDO CARGOS")
    print("="*80)
    
    archivo = 'plantilla_cargos.csv'
    if not os.path.exists(archivo):
        print(f"❌ No se encontró el archivo {archivo}")
        return 0
    
    count = 0
    encodings = ['utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    
    # Primero obtener el máximo ID existente
    max_id = Cargo.objects.aggregate(max_id=models.Max('id_cargo'))['max_id'] or 0
    next_id = max_id + 1
    
    for encoding in encodings:
        try:
            with open(archivo, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    # Mapeo de jerarquia del CSV a nivel_jerarquico del modelo
                    jerarquia_csv = int(row['jerarquia'])
                    
                    cargo, created = Cargo.objects.get_or_create(
                        nombre=row['nombre'],
                        defaults={
                            'id_cargo': next_id,
                            'nivel_jerarquico': jerarquia_csv
                        }
                    )
                    if created:
                        print(f"✅ Cargo creado: {cargo.nombre} (Nivel: {cargo.nivel_jerarquico})")
                        count += 1
                        next_id += 1
                    else:
                        print(f"⚠️  Cargo ya existe: {cargo.nombre}")
            break  # Si funciona, salir del loop
        except UnicodeDecodeError:
            if encoding == encodings[-1]:
                print(f"❌ No se pudo leer el archivo con ninguna codificación")
                return 0
            continue
    
    print(f"\n✅ Total cargos en BD: {Cargo.objects.count()}")
    print(f"   Nuevos creados: {count}")
    return count

def main():
    print("="*80)
    print("INICIO DE CARGA DE DATOS DESDE CSV")
    print("="*80)
    
    clientes = cargar_clientes()
    contratos = cargar_contratos()
    cargos = cargar_cargos()
    
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print(f"Clientes nuevos: {clientes}")
    print(f"Contratos nuevos: {contratos}")
    print(f"Cargos nuevos: {cargos}")
    print("="*80)
    print("✅ CARGA COMPLETADA")
    print("="*80)

if __name__ == "__main__":
    main()
