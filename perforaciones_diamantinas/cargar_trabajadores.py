import os
import django
import csv
import sys
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador, Contrato, Cargo

def parse_date(date_str):
    """Convierte string de fecha a objeto date, retorna None si está vacío"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        # Intentar formato YYYY-MM-DD
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except ValueError:
        try:
            # Intentar formato DD/MM/YYYY
            return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
        except ValueError:
            return None

def cargar_trabajadores(csv_file=None):
    # Si no se proporciona archivo, usar el por defecto
    if csv_file is None:
        csv_file = 'carga_trabajadores_sancristobal.csv'
    
    print(f"Cargando trabajadores desde {csv_file}...")
    
    creados = 0
    actualizados = 0
    errores = 0
    
    try:
        # Intentar diferentes codificaciones
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        file_content = None
        
        for encoding in encodings:
            try:
                with open(csv_file, 'r', encoding=encoding) as file:
                    file_content = file.read()
                print(f"✓ Archivo leído con codificación: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if file_content is None:
            print("✗ No se pudo leer el archivo con ninguna codificación conocida")
            return
        
        # Procesar el CSV
        from io import StringIO
        # Detectar el delimitador
        delimiter = ';' if ';' in file_content.split('\n')[0] else ','
        print(f"✓ Delimitador detectado: '{delimiter}'")
        reader = csv.DictReader(StringIO(file_content), delimiter=delimiter)
        
        for row in reader:
                try:
                    # Obtener contrato
                    contrato_nombre = row['contrato'].strip()
                    try:
                        contrato = Contrato.objects.get(nombre_contrato__iexact=contrato_nombre)
                    except Contrato.DoesNotExist:
                        print(f"✗ Error: Contrato '{contrato_nombre}' no existe")
                        errores += 1
                        continue
                    
                    # Obtener cargo por nombre
                    cargo_nombre = row['cargo'].strip()
                    try:
                        cargo = Cargo.objects.get(nombre__iexact=cargo_nombre)
                    except Cargo.DoesNotExist:
                        print(f"✗ Error: Cargo '{cargo_nombre}' no existe en la tabla Cargo")
                        print(f"  Sugerencia: Verifica que el cargo esté cargado o usa un cargo existente")
                        errores += 1
                        continue
                    
                    # Preparar datos
                    dni = row['dni'].strip()
                    # NOTA: En el CSV los campos están invertidos, nombres tiene apellidos y viceversa
                    nombres = row['apellidos'].strip()  # apellidos del CSV son en realidad los nombres
                    apellidos = row['nombres'].strip()  # nombres del CSV son en realidad los apellidos
                    area = row.get('area', '').strip()
                    telefono = row.get('telefono', '').strip()
                    email = row.get('email', '').strip()
                    estado = row['estado'].strip().upper()  # Asegurar mayúsculas
                    subestado = row['subestado'].strip().upper().replace(' ', '_')  # Normalizar
                    emo_estado = row.get('emo_estado', '').strip()
                    
                    # Fechas opcionales
                    fecha_ingreso = parse_date(row.get('fecha_ingreso', ''))
                    fotocheck_fecha_emision = parse_date(row.get('fotocheck_fecha_emision', ''))
                    fotocheck_fecha_caducidad = parse_date(row.get('fotocheck_fecha_caducidad', ''))
                    emo_fecha_realizado = parse_date(row.get('emo_fecha_realizado', ''))
                    emo_fecha_vencimiento = parse_date(row.get('emo_fecha_vencimiento', ''))
                    emo_programacion = parse_date(row.get('emo_programacion', ''))
                    
                    # Crear o actualizar trabajador
                    trabajador, created = Trabajador.objects.update_or_create(
                        dni=dni,
                        defaults={
                            'contrato': contrato,
                            'nombres': nombres,
                            'apellidos': apellidos,
                            'cargo': cargo,
                            'area': area,
                            'telefono': telefono,
                            'email': email,
                            'fecha_ingreso': fecha_ingreso,
                            'estado': estado,
                            'subestado': subestado,
                            'fotocheck_fecha_emision': fotocheck_fecha_emision,
                            'fotocheck_fecha_caducidad': fotocheck_fecha_caducidad,
                            'emo_fecha_realizado': emo_fecha_realizado,
                            'emo_fecha_vencimiento': emo_fecha_vencimiento,
                            'emo_programacion': emo_programacion,
                            'emo_estado': emo_estado,
                        }
                    )
                    
                    if created:
                        creados += 1
                        print(f"✓ Creado: {dni} - {nombres} {apellidos} ({cargo.nombre})")
                    else:
                        actualizados += 1
                        print(f"↻ Actualizado: {dni} - {nombres} {apellidos} ({cargo.nombre})")
                        
                except Exception as e:
                    errores += 1
                    print(f"✗ Error procesando fila: {e}")
                    print(f"  Datos: {row}")
        
        print("\n" + "="*60)
        print(f"Resumen:")
        print(f"  Trabajadores creados: {creados}")
        print(f"  Trabajadores actualizados: {actualizados}")
        print(f"  Errores: {errores}")
        print(f"  Total procesado: {creados + actualizados}")
        print("="*60)
        
    except FileNotFoundError:
        print(f"✗ Error: No se encontró el archivo '{csv_file}'")
        print(f"  Asegúrate de que el archivo esté en la misma carpeta que este script")
    except Exception as e:
        print(f"✗ Error inesperado: {e}")

if __name__ == '__main__':
    # Permitir pasar el nombre del archivo como argumento
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        cargar_trabajadores(csv_file)
    else:
        print("Uso: python cargar_trabajadores.py <archivo.csv>")
        print("Ejemplo: python cargar_trabajadores.py carga_trabajadores_americana.csv")
        print("\nSi no especificas archivo, se usará: carga_trabajadores_sancristobal.csv")
        cargar_trabajadores()
