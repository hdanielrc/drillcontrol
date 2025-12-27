"""
Script para importar datos desde archivos CSV a la base de datos

Uso:
    python importar_datos.py <tipo> <archivo.csv>
    
Tipos disponibles:
    - clientes
    - contratos
    - cargos
    - trabajadores
    - maquinas
    - vehiculos

Ejemplos:
    python importar_datos.py clientes plantilla_clientes.csv
    python importar_datos.py contratos plantilla_contratos.csv
    python importar_datos.py trabajadores plantilla_trabajadores_nueva.csv
"""

import os
import sys
import django
import csv
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import (
    Cliente, Contrato, Cargo, Trabajador, Maquina, Vehiculo
)


def importar_clientes(archivo_csv):
    """Importar clientes desde CSV"""
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            es_activo = row['es_activo'].upper() in ['SI', 'SÍ', 'YES', 'TRUE', '1']
            
            cliente, created = Cliente.objects.get_or_create(
                nombre=row['nombre'],
                defaults={'is_active': es_activo}
            )
            
            if created:
                print(f"✓ Cliente creado: {cliente.nombre}")
                count += 1
            else:
                print(f"⚠ Cliente ya existe: {cliente.nombre}")
        
        print(f"\n✅ Total clientes importados: {count}")


def importar_contratos(archivo_csv):
    """Importar contratos desde CSV"""
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            try:
                cliente = Cliente.objects.get(nombre=row['cliente_nombre'])
                
                contrato, created = Contrato.objects.get_or_create(
                    nombre_contrato=row['nombre_contrato'],
                    cliente=cliente,
                    defaults={
                        'codigo_centro_costo': row.get('codigo_centro_costo', ''),
                        'duracion_turno': int(row.get('duracion_turno', 12)),
                        'estado': row.get('estado', 'ACTIVO')
                    }
                )
                
                if created:
                    print(f"✓ Contrato creado: {contrato.nombre_contrato} ({cliente.nombre})")
                    count += 1
                else:
                    print(f"⚠ Contrato ya existe: {contrato.nombre_contrato}")
            
            except Cliente.DoesNotExist:
                print(f"❌ Error: Cliente '{row['cliente_nombre']}' no encontrado")
        
        print(f"\n✅ Total contratos importados: {count}")


def importar_cargos(archivo_csv):
    """Importar cargos desde CSV"""
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            cargo, created = Cargo.objects.get_or_create(
                nombre=row['nombre'],
                defaults={
                    'categoria': row.get('categoria', 'LINEA_MANDO'),
                    'jerarquia': int(row.get('jerarquia', 3))
                }
            )
            
            if created:
                print(f"✓ Cargo creado: {cargo.nombre} ({cargo.categoria})")
                count += 1
            else:
                print(f"⚠ Cargo ya existe: {cargo.nombre}")
        
        print(f"\n✅ Total cargos importados: {count}")


def importar_trabajadores(archivo_csv):
    """Importar trabajadores desde CSV"""
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        errors = []
        
        for row in reader:
            try:
                # Buscar contrato
                contrato = Contrato.objects.get(nombre_contrato=row['contrato_nombre'])
                
                # Buscar o crear cargo
                cargo, _ = Cargo.objects.get_or_create(
                    nombre=row['cargo_nombre'],
                    defaults={'categoria': 'LINEA_MANDO', 'jerarquia': 3}
                )
                
                # Parsear fecha de ingreso
                fecha_ingreso = None
                if row.get('fecha_ingreso'):
                    try:
                        fecha_ingreso = datetime.strptime(row['fecha_ingreso'], '%Y-%m-%d').date()
                    except:
                        pass
                
                # Crear trabajador
                trabajador, created = Trabajador.objects.get_or_create(
                    dni=row['dni'],
                    defaults={
                        'contrato': contrato,
                        'nombres': row['nombres'],
                        'apellidos': row.get('apellidos', ''),
                        'cargo': cargo,
                        'area': row.get('area', ''),
                        'telefono': row.get('telefono', ''),
                        'email': row.get('email', ''),
                        'fecha_ingreso': fecha_ingreso,
                        'guardia_asignada': row.get('guardia', ''),
                        'estado': row.get('estado', 'ACTIVO'),
                        'subestado': row.get('subestado', 'EN_OPERACION')
                    }
                )
                
                if created:
                    # Asignar grupo automático
                    trabajador.grupo = trabajador.asignar_grupo_automatico()
                    trabajador.save()
                    print(f"✓ Trabajador creado: {trabajador.nombres} {trabajador.apellidos} ({trabajador.cargo.nombre})")
                    count += 1
                else:
                    print(f"⚠ Trabajador ya existe: {trabajador.dni} - {trabajador.nombres}")
            
            except Contrato.DoesNotExist:
                error_msg = f"❌ Error línea {reader.line_num}: Contrato '{row['contrato_nombre']}' no encontrado"
                print(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"❌ Error línea {reader.line_num}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        print(f"\n✅ Total trabajadores importados: {count}")
        if errors:
            print(f"⚠ Errores encontrados: {len(errors)}")


def importar_maquinas(archivo_csv):
    """Importar máquinas desde CSV"""
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            try:
                contrato = Contrato.objects.get(nombre_contrato=row['contrato_nombre'])
                
                maquina, created = Maquina.objects.get_or_create(
                    nombre=row['nombre'],
                    contrato=contrato,
                    defaults={
                        'tipo': row['tipo'],
                        'estado': row.get('estado', 'OPERATIVO'),
                        'horometro': float(row.get('horometro_inicial', 0))
                    }
                )
                
                if created:
                    print(f"✓ Máquina creada: {maquina.nombre} ({maquina.tipo})")
                    count += 1
                else:
                    print(f"⚠ Máquina ya existe: {maquina.nombre}")
            
            except Contrato.DoesNotExist:
                print(f"❌ Error: Contrato '{row['contrato_nombre']}' no encontrado")
        
        print(f"\n✅ Total máquinas importadas: {count}")


def importar_vehiculos(archivo_csv):
    """Importar vehículos desde CSV"""
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            try:
                contrato = Contrato.objects.get(nombre_contrato=row['contrato_nombre'])
                
                vehiculo, created = Vehiculo.objects.get_or_create(
                    placa=row['placa'],
                    defaults={
                        'contrato': contrato,
                        'tipo': row['tipo'],
                        'marca': row.get('marca', ''),
                        'modelo': row.get('modelo', ''),
                        'año': int(row['año']) if row.get('año') else None,
                        'kilometraje_actual': float(row.get('kilometraje_inicial', 0)),
                        'capacidad_pasajeros': int(row['capacidad_pasajeros']) if row.get('capacidad_pasajeros') else None,
                        'estado': row.get('estado', 'OPERATIVO')
                    }
                )
                
                if created:
                    print(f"✓ Vehículo creado: {vehiculo.placa} ({vehiculo.tipo} {vehiculo.marca} {vehiculo.modelo})")
                    count += 1
                else:
                    print(f"⚠ Vehículo ya existe: {vehiculo.placa}")
            
            except Contrato.DoesNotExist:
                print(f"❌ Error: Contrato '{row['contrato_nombre']}' no encontrado")
        
        print(f"\n✅ Total vehículos importados: {count}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    tipo = sys.argv[1].lower()
    archivo = sys.argv[2]
    
    if not os.path.exists(archivo):
        print(f"❌ Error: Archivo '{archivo}' no encontrado")
        sys.exit(1)
    
    print(f"📥 Importando {tipo} desde {archivo}...\n")
    
    if tipo == 'clientes':
        importar_clientes(archivo)
    elif tipo == 'contratos':
        importar_contratos(archivo)
    elif tipo == 'cargos':
        importar_cargos(archivo)
    elif tipo == 'trabajadores':
        importar_trabajadores(archivo)
    elif tipo == 'maquinas':
        importar_maquinas(archivo)
    elif tipo == 'vehiculos':
        importar_vehiculos(archivo)
    else:
        print(f"❌ Error: Tipo '{tipo}' no reconocido")
        print(__doc__)
        sys.exit(1)
    
    print("\n✅ Importación completada")


if __name__ == '__main__':
    main()
