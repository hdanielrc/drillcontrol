import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from drilling.models import TipoComplemento

print("="*80)
print("VERIFICACIÓN DE PRODUCTOS CARGADOS")
print("="*80)

total = TipoComplemento.objects.count()
print(f"\nTotal productos en BD: {total}")

# Buscar el producto específico 409381 por SERIE (no por código)
prod_409381 = TipoComplemento.objects.filter(serie='409381').first()
if prod_409381:
    print(f"\n✅ Producto 409381 ENCONTRADO:")
    print(f"   ID: {prod_409381.id}")
    print(f"   Código: {prod_409381.codigo}")
    print(f"   Serie: {prod_409381.serie}")
    print(f"   Nombre: {prod_409381.nombre}")
    print(f"   Estado: {prod_409381.estado}")
else:
    print("\n❌ Producto 409381 NO ENCONTRADO")

# Listar algunos productos cargados (únicos por serie)
print(f"\n📋 Primeros 10 productos únicos:")
productos_vistos = set()
for prod in TipoComplemento.objects.all().order_by('serie'):
    if prod.serie not in productos_vistos:
        print(f"   {prod.serie} - {prod.nombre[:60]}")
        productos_vistos.add(prod.serie)
        if len(productos_vistos) >= 10:
            break
