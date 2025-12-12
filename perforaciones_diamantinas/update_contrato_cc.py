"""
Script para actualizar el código de centro de costo en un contrato
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato

# Listar contratos disponibles
print("=" * 60)
print("CONTRATOS DISPONIBLES")
print("=" * 60)

contratos = Contrato.objects.all()
for contrato in contratos:
    print(f"\nID: {contrato.id}")
    print(f"Cliente: {contrato.cliente.nombre}")
    print(f"Nombre: {contrato.nombre_contrato}")
    print(f"Estado: {contrato.estado}")
    print(f"Centro de Costo Actual: {contrato.codigo_centro_costo or '(no asignado)'}")

# Mapeo de contratos a centros de costo según la imagen proporcionada
mapeo_centros_costo = {
    'AMERICANA': '000002',
    'CONDESTABLE': '000003',
    'CHUNGAR': '000004',
    'MOROCOCHA': '000023',
    'SAN CRISTOBAL': '000035',
    'YAULIYACU': '000053',
    'COLQUISIRI': '000037',
}

print("\n" + "=" * 60)
print("ACTUALIZANDO CENTROS DE COSTO")
print("=" * 60)

actualizados = 0
no_encontrados = []

for nombre_contrato, codigo_cc in mapeo_centros_costo.items():
    contrato = Contrato.objects.filter(nombre_contrato=nombre_contrato).first()
    if contrato:
        contrato.codigo_centro_costo = codigo_cc
        contrato.save()
        print(f"✓ {nombre_contrato}: {codigo_cc}")
        actualizados += 1
    else:
        print(f"✗ {nombre_contrato}: No encontrado")
        no_encontrados.append(nombre_contrato)

print(f"\n{actualizados} contratos actualizados")
if no_encontrados:
    print(f"No encontrados: {', '.join(no_encontrados)}")
