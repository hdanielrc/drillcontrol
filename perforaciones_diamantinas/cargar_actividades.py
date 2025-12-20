#!/usr/bin/env python
"""
Script para cargar tipos de actividades desde el archivo plantilla_actividades.csv
"""
import os
import sys
import django
import csv
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import TipoActividad

def cargar_actividades():
    """Carga las actividades desde el archivo CSV."""
    csv_file = BASE_DIR / 'plantilla_actividades.csv'
    
    if not csv_file.exists():
        print(f"❌ Error: No se encuentra el archivo {csv_file}")
        return
    
    print(f"📁 Leyendo archivo: {csv_file}")
    
    # Intentar con diferentes encodings
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    data = None
    
    for encoding in encodings:
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                content = f.read()
                data = content
                print(f"✅ Archivo leído con encoding: {encoding}")
                break
        except UnicodeDecodeError:
            continue
    
    if data is None:
        print("❌ No se pudo leer el archivo con ningún encoding")
        return
    
    # Procesar el CSV
    lines = data.strip().split('\n')
    reader = csv.DictReader(lines, delimiter=';')
    
    actividades_creadas = 0
    actividades_actualizadas = 0
    
    for row in reader:
        nombre = row['nombre'].strip()
        descripcion = row['descripcion'].strip()
        descripcion_corta = row['descripcion_corta'].strip()
        tipo_actividad = row['tipo_actividad'].strip()
        es_cobrable_str = row['es_cobrable'].strip().upper()
        
        # Convertir string a boolean
        es_cobrable = es_cobrable_str in ['TRUE', '1', 'SI', 'SÍ', 'YES']
        
        # Validar tipo_actividad
        tipos_validos = ['STAND_BY_CLIENTE', 'STAND_BY_ROCKDRILL', 'INOPERATIVO', 'OPERATIVO', 'OTROS']
        if tipo_actividad not in tipos_validos:
            print(f"⚠️ Advertencia: Tipo de actividad inválido '{tipo_actividad}' para '{nombre}'. Usando 'OTROS'")
            tipo_actividad = 'OTROS'
        
        # Crear o actualizar la actividad
        actividad, created = TipoActividad.objects.update_or_create(
            nombre=nombre,
            defaults={
                'descripcion': descripcion,
                'descripcion_corta': descripcion_corta,
                'tipo_actividad': tipo_actividad,
                'es_cobrable': es_cobrable
            }
        )
        
        if created:
            actividades_creadas += 1
            print(f"✅ Actividad creada: {nombre} (Tipo: {tipo_actividad}, Cobrable: {es_cobrable})")
        else:
            actividades_actualizadas += 1
            print(f"🔄 Actividad actualizada: {nombre} (Tipo: {tipo_actividad}, Cobrable: {es_cobrable})")
    
    print("\n" + "="*80)
    print(f"✅ Carga completada:")
    print(f"   - Actividades creadas: {actividades_creadas}")
    print(f"   - Actividades actualizadas: {actividades_actualizadas}")
    print(f"   - Total procesadas: {actividades_creadas + actividades_actualizadas}")
    print("="*80)

if __name__ == '__main__':
    print("🚀 Iniciando carga de tipos de actividades...")
    print("="*80)
    cargar_actividades()
