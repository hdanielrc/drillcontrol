import os
import django
import csv
from io import StringIO

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Maquina, Contrato

def cargar_maquinas():
    csv_file = 'plantilla_maquinas.csv'
    
    print(f"Cargando máquinas desde {csv_file}...")
    
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
        reader = csv.DictReader(StringIO(file_content), delimiter=';')
        
        for row in reader:
            try:
                contrato_nombre = row['contrato_nombre'].strip()
                nombre = row['nombre'].strip()
                tipo = row['tipo'].strip()
                estado = row['estado'].strip()
                
                # Buscar el contrato
                try:
                    contrato = Contrato.objects.get(nombre_contrato=contrato_nombre)
                except Contrato.DoesNotExist:
                    print(f"⚠ Advertencia: Contrato '{contrato_nombre}' no encontrado, omitiendo máquina {nombre}")
                    errores += 1
                    continue
                
                # Buscar si ya existe la máquina por nombre
                maquina_existente = Maquina.objects.filter(nombre=nombre).first()
                
                if maquina_existente:
                    # Actualizar máquina existente
                    maquina_existente.contrato = contrato
                    maquina_existente.tipo = tipo
                    maquina_existente.estado = estado
                    maquina_existente.save()
                    actualizados += 1
                    print(f"↻ Actualizado: {nombre} ({tipo}) - {contrato_nombre}")
                else:
                    # Crear nueva máquina
                    maquina = Maquina.objects.create(
                        contrato=contrato,
                        nombre=nombre,
                        tipo=tipo,
                        estado=estado
                    )
                    creados += 1
                    print(f"✓ Creado: {nombre} ({tipo}) - {contrato_nombre}")
                    
            except Exception as e:
                errores += 1
                print(f"✗ Error en fila {reader.line_num}: {e}")
                print(f"  Datos: {row}")
        
        print("\n" + "="*60)
        print(f"Resumen:")
        print(f"  Máquinas creadas: {creados}")
        print(f"  Máquinas actualizadas: {actualizados}")
        print(f"  Errores: {errores}")
        print(f"  Total procesado: {creados + actualizados}")
        print("="*60)
        
    except FileNotFoundError:
        print(f"✗ Error: No se encontró el archivo '{csv_file}'")
        print(f"  Asegúrate de que el archivo esté en la misma carpeta que este script")
    except Exception as e:
        print(f"✗ Error inesperado: {e}")

if __name__ == '__main__':
    cargar_maquinas()
