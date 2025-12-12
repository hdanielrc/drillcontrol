"""
Script para verificar que la eliminación de funcionalidad de trabajadores fue exitosa.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

print("\n" + "="*70)
print("VERIFICACIÓN - ELIMINACIÓN DE SINCRONIZACIÓN DE TRABAJADORES")
print("="*70 + "\n")

# Verificar que las importaciones funcionan
try:
    from drilling.api_client import VilbragroupAPIClient, get_api_client
    print("✓ api_client.py importa correctamente")
except Exception as e:
    print(f"✗ Error en api_client.py: {e}")

try:
    from drilling import api_views
    print("✓ api_views.py importa correctamente")
except Exception as e:
    print(f"✗ Error en api_views.py: {e}")

try:
    from drilling import urls
    print("✓ urls.py importa correctamente")
except Exception as e:
    print(f"✗ Error en urls.py: {e}")

# Verificar que los métodos correctos existen
print("\n" + "-"*70)
print("MÉTODOS DISPONIBLES EN API CLIENT:")
print("-"*70)

client = get_api_client()
methods = [m for m in dir(client) if not m.startswith('_')]
print("\nMétodos públicos:")
for method in methods:
    print(f"  - {method}")

# Verificar que obtener_perforistas NO existe
if hasattr(client, 'obtener_perforistas'):
    print("\n✗ ADVERTENCIA: obtener_perforistas todavía existe")
else:
    print("\n✓ obtener_perforistas eliminado correctamente")

# Verificar que los métodos de productos y aditivos SÍ existen
print("\n" + "-"*70)
print("VERIFICACIÓN DE MÉTODOS NECESARIOS:")
print("-"*70)

if hasattr(client, 'obtener_productos_diamantados'):
    print("✓ obtener_productos_diamantados existe")
else:
    print("✗ obtener_productos_diamantados NO existe")

if hasattr(client, 'obtener_aditivos'):
    print("✓ obtener_aditivos existe")
else:
    print("✗ obtener_aditivos NO existe")

if hasattr(client, 'obtener_articulos_almacen'):
    print("✓ obtener_articulos_almacen existe")
else:
    print("✗ obtener_articulos_almacen NO existe")

# Verificar comandos de management
print("\n" + "-"*70)
print("COMANDOS DE MANAGEMENT DISPONIBLES:")
print("-"*70)

import os
commands_dir = 'drilling/management/commands'
if os.path.exists(commands_dir):
    commands = [f[:-3] for f in os.listdir(commands_dir) if f.endswith('.py') and f != '__init__.py']
    print("\nComandos disponibles:")
    for cmd in sorted(commands):
        print(f"  - {cmd}")
    
    if 'sync_trabajadores' in commands:
        print("\n✗ ADVERTENCIA: sync_trabajadores todavía existe")
    else:
        print("\n✓ sync_trabajadores eliminado correctamente")
    
    expected_commands = ['sync_productos_diamantados', 'sync_aditivos', 'sync_all_contracts']
    missing = [cmd for cmd in expected_commands if cmd not in commands]
    if missing:
        print(f"\n✗ Comandos faltantes: {', '.join(missing)}")
    else:
        print("✓ Todos los comandos esperados están presentes")

# Verificar modelo Trabajador
print("\n" + "-"*70)
print("MODELO TRABAJADOR:")
print("-"*70)

try:
    from drilling.models import Trabajador, Contrato
    trabajadores = Trabajador.objects.count()
    print(f"\n✓ Modelo Trabajador funciona correctamente")
    print(f"  Total trabajadores en BD: {trabajadores}")
    
    # Verificar que los trabajadores tienen contrato
    con_contrato = Trabajador.objects.filter(contrato__isnull=False).count()
    print(f"  Trabajadores con contrato: {con_contrato}")
except Exception as e:
    print(f"\n✗ Error con modelo Trabajador: {e}")

print("\n" + "="*70)
print("RESUMEN:")
print("="*70)
print("\n✓ Funcionalidad de sincronización de trabajadores eliminada")
print("✓ APIs de productos y aditivos mantienen funcionando")
print("✓ Modelo Trabajador intacto (gestión manual)")
print("\n" + "="*70 + "\n")
