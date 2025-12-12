import os
import django
import csv

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Cargo

def cargar_cargos():
    csv_file = 'carga_cargos.csv'
    
    print(f"Cargando cargos desde {csv_file}...")
    
    creados = 0
    actualizados = 0
    errores = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            # Usar punto y coma como delimitador
            reader = csv.DictReader(file, delimiter=';')
            
            for row in reader:
                try:
                    id_cargo = int(row['id_Cargo'])
                    nombre = row['nombre'].strip()
                    descripcion = row['descripcion'].strip()
                    is_active = row['is_active'].strip().lower() in ['true', '1', 'yes', 'si']
                    
                    # Usar update_or_create para crear o actualizar
                    cargo, created = Cargo.objects.update_or_create(
                        id_cargo=id_cargo,
                        defaults={
                            'nombre': nombre,
                            'descripcion': descripcion,
                            'is_active': is_active
                        }
                    )
                    
                    if created:
                        creados += 1
                        print(f"✓ Creado: {id_cargo} - {nombre}")
                    else:
                        actualizados += 1
                        print(f"↻ Actualizado: {id_cargo} - {nombre}")
                        
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
