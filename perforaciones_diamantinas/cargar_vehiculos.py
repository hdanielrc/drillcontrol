"""
Script para cargar vehículos de ejemplo al contrato
Ejecutar: python cargar_vehiculos.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Vehiculo, Contrato

def cargar_vehiculos():
    """Cargar vehículos de ejemplo"""
    
    # Obtener el primer contrato activo
    contrato = Contrato.objects.filter(estado='ACTIVO').first()
    
    if not contrato:
        print("❌ No hay contratos activos")
        return
    
    print(f"✅ Trabajando con contrato: {contrato.nombre_contrato}")
    
    # Lista de vehículos de ejemplo
    vehiculos_ejemplo = [
        {
            'placa': 'ABC-123',
            'tipo': 'CAMION',
            'marca': 'Volvo',
            'modelo': 'FH16',
            'año': 2020,
            'capacidad_pasajeros': 3,
            'kilometraje_actual': 45000,
            'estado': 'OPERATIVO',
            'proximo_mantenimiento_km': 50000
        },
        {
            'placa': 'DEF-456',
            'tipo': 'CAMIONETA',
            'marca': 'Toyota',
            'modelo': 'Hilux',
            'año': 2021,
            'capacidad_pasajeros': 5,
            'kilometraje_actual': 32000,
            'estado': 'OPERATIVO',
            'proximo_mantenimiento_km': 40000
        },
        {
            'placa': 'GHI-789',
            'tipo': 'COMBI',
            'marca': 'Mercedes Benz',
            'modelo': 'Sprinter',
            'año': 2019,
            'capacidad_pasajeros': 16,
            'kilometraje_actual': 78000,
            'estado': 'OPERATIVO',
            'proximo_mantenimiento_km': 80000
        },
        {
            'placa': 'JKL-012',
            'tipo': 'PICKUP',
            'marca': 'Ford',
            'modelo': 'Ranger',
            'año': 2022,
            'capacidad_pasajeros': 5,
            'kilometraje_actual': 15000,
            'estado': 'OPERATIVO',
            'proximo_mantenimiento_km': 20000
        },
        {
            'placa': 'MNO-345',
            'tipo': 'MINIBUS',
            'marca': 'Hyundai',
            'modelo': 'County',
            'año': 2020,
            'capacidad_pasajeros': 25,
            'kilometraje_actual': 52000,
            'estado': 'OPERATIVO',
            'proximo_mantenimiento_km': 55000
        },
        {
            'placa': 'PQR-678',
            'tipo': 'STATION_WAGON',
            'marca': 'Toyota',
            'modelo': 'Land Cruiser',
            'año': 2021,
            'capacidad_pasajeros': 7,
            'kilometraje_actual': 28000,
            'estado': 'OPERATIVO',
            'proximo_mantenimiento_km': 30000
        },
    ]
    
    creados = 0
    existentes = 0
    
    for vehiculo_data in vehiculos_ejemplo:
        placa = vehiculo_data['placa']
        
        # Verificar si ya existe
        if Vehiculo.objects.filter(placa=placa).exists():
            print(f"⚠️  Vehículo {placa} ya existe, omitiendo...")
            existentes += 1
            continue
        
        # Crear vehículo
        vehiculo = Vehiculo.objects.create(
            contrato=contrato,
            **vehiculo_data
        )
        print(f"✅ Vehículo creado: {vehiculo.placa} - {vehiculo.get_tipo_display()} ({vehiculo.marca} {vehiculo.modelo})")
        creados += 1
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN:")
    print(f"   - Vehículos creados: {creados}")
    print(f"   - Vehículos existentes (omitidos): {existentes}")
    print(f"   - Total en base de datos: {Vehiculo.objects.filter(contrato=contrato).count()}")
    print(f"{'='*60}")

if __name__ == '__main__':
    print("🚗 Iniciando carga de vehículos...\n")
    cargar_vehiculos()
    print("\n✅ Proceso completado!")
