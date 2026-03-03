#!/usr/bin/env python
"""
Script de verificacion: muestra muestra de productos con los nuevos campos
categoria, marca y calibre correctamente llenados.
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import TipoComplemento
from django.db.models import Count

SEP = "=" * 80

print(SEP)
print("VERIFICACION DE CAMPOS: categoria / marca / calibre")
print(SEP)

# Totales por categoria
print("\n[DISTRIBUCION POR TIPO]")
for row in TipoComplemento.objects.values('categoria').annotate(n=Count('id')).order_by('categoria'):
    cat = row['categoria'] or '(sin tipo)'
    print(f"  {cat:<20}  {row['n']:>5} productos")

# ----------------------------------------------------------------
# Muestra de 4 productos de cada categoria
# ----------------------------------------------------------------
CATEGORIAS = [
    ('BROCA',         'Brocas Diamantadas'),
    ('ZAPATA',        'Zapatas'),
    ('REAMING_SHELL', 'Reaming Shells'),
    ('CORE_LIFTER',   'Core Lifters'),
]

for cat_key, cat_label in CATEGORIAS:
    total = TipoComplemento.objects.filter(categoria=cat_key).count()
    print(f"\n{SEP}")
    print(f"  {cat_label.upper()}  ({total} registros en BD)")
    print(SEP)
    # 4 muestras con calibre / sin calibre
    muestras = TipoComplemento.objects.filter(categoria=cat_key).order_by('calibre', 'marca')[:4]
    if not muestras:
        print("  (sin datos)")
        continue
    for p in muestras:
        print(f"  Serie   : {p.serie or '--'}")
        print(f"  Nombre  : {p.nombre[:75]}")
        print(f"  Calibre : [{p.calibre or '(vacio)'}]")
        print(f"  Marca   : [{p.marca or '(vacio)'}]")
        print()

# ----------------------------------------------------------------
# Cobertura de marca y calibre
# ----------------------------------------------------------------
total = TipoComplemento.objects.count()
con_marca    = TipoComplemento.objects.exclude(marca='').count()
con_calibre  = TipoComplemento.objects.exclude(calibre='').count()
sin_marca    = total - con_marca
sin_calibre  = total - con_calibre

print(SEP)
print("COBERTURA DE CAMPOS")
print(SEP)
print(f"  Total productos       : {total}")
print(f"  Con marca             : {con_marca}  ({100*con_marca//total}%)  Sin marca: {sin_marca}")
print(f"  Con calibre           : {con_calibre}  ({100*con_calibre//total}%)  Sin calibre: {sin_calibre}")

# Marcas
print("\n[MARCAS DETECTADAS]")
for row in TipoComplemento.objects.exclude(marca='').values('marca').annotate(n=Count('id')).order_by('-n'):
    print(f"  {row['marca']:<30} {row['n']:>5} prods")

# Calibres
print("\n[CALIBRES DETECTADOS]")
for row in TipoComplemento.objects.exclude(calibre='').values('calibre').annotate(n=Count('id')).order_by('-n'):
    print(f"  {row['calibre']:<10} {row['n']:>5} prods")

print(f"\n{SEP}")
print("OK - Verificacion completada")
print(SEP)
