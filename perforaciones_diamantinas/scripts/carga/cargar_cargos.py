import os
import django
import csv

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Cargo
from django.db import models

def cargar_cargos():
    csv_file = 'plantilla_cargos.csv'
    
    print(f"Cargando cargos desde {csv_file}...")
    
    creados = 0
    actualizados = 0
    errores = 0
    
    try:
        # Intentar diferentes codificaciones
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        file_content = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(csv_file, 'r', encoding=encoding) as file:
                    file_content = file.read()
                used_encoding = encoding
                print(f"✓ Archivo leído con codificación: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if file_content is None:
            print("✗ Error: No se pudo leer el archivo con ninguna codificación")
            return
        
        # Procesar el contenido
        from io import StringIO
        reader = csv.DictReader(StringIO(file_content), delimiter=';')
        
        for row in reader:
                try:
                    nombre = row['nombre'].strip()
                    jerarquia = int(row['jerarquia'])
                    
                    # Buscar si ya existe el cargo por nombre
                    cargo_existente = Cargo.objects.filter(nombre=nombre).first()
                    
                    if cargo_existente:
                        # Actualizar cargo existente
                        cargo_existente.nivel_jerarquico = jerarquia
                        cargo_existente.is_active = True
                        cargo_existente.save()
                        actualizados += 1
                        print(f"↻ Actualizado: {nombre} (ID: {cargo_existente.id_cargo}, Jerarquía: {jerarquia})")
                    else:
                        # Obtener el próximo ID disponible
                        max_id = Cargo.objects.aggregate(models.Max('id_cargo'))['id_cargo__max']
                        next_id = (max_id or 0) + 1
                        
                        # Crear nuevo cargo
                        cargo = Cargo.objects.create(
                            id_cargo=next_id,
                            nombre=nombre,
                            nivel_jerarquico=jerarquia,
                            descripcion=nombre,
                            is_active=True
                        )
                        creados += 1
                        print(f"✓ Creado: {nombre} (ID: {next_id}, Jerarquía: {jerarquia})")
                        
                except Exception as e:
                    errores += 1
                    print(f"✗ Error en fila {reader.line_num}: {e}")
                    print(f"  Datos: {row}")
        
        print("\n" + "="*60)
        print(f"Resumen:")
        print(f"  Cargos creados: {creados}")
        print(f"  Cargos actualizados: {actualizados}")
        print(f"  Errores: {errores}")
        print(f"  Total procesado: {creados + actualizados}")
        print("="*60)
        
    except FileNotFoundError:
        print(f"✗ Error: No se encontró el archivo '{csv_file}'")
        print(f"  Asegúrate de que el archivo esté en la misma carpeta que este script")
    except Exception as e:
        print(f"✗ Error inesperado: {e}")

if __name__ == '__main__':
    cargar_cargos()
