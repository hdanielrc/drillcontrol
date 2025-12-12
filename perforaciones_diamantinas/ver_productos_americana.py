"""
Ver listado de productos diamantados almacenados en BD para AMERICANA
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import TipoComplemento, Contrato

# Obtener contrato AMERICANA
americana = Contrato.objects.get(nombre_contrato='AMERICANA')

# Obtener productos diamantados de AMERICANA
productos = TipoComplemento.objects.filter(contrato=americana).order_by('codigo', 'serie')

print(f"\n{'='*100}")
print(f"PRODUCTOS DIAMANTADOS ALMACENADOS EN BD - AMERICANA")
print(f"Total: {productos.count()} productos")
print(f"{'='*100}\n")

print(f"{'#':<5} {'SERIE':<15} {'CÓDIGO':<25} {'DESCRIPCIÓN':<45} {'ESTADO':<10}")
print('-' * 100)

for i, p in enumerate(productos, 1):
    print(f"{i:<5} {p.serie:<15} {p.codigo:<25} {p.nombre[:42]:<45} {p.estado:<10}")

print(f"\n{'='*100}")
print(f"Total de productos: {productos.count()}")
print(f"{'='*100}")
