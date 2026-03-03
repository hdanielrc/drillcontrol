"""
Muestra nombres reales para identificar patrones de marca, linea, altura y serie de bit
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import TipoComplemento

print("=" * 100)
print("MUESTRA DE 200 NOMBRES REALES (primeras 100 chars) - sin duplicar nombre")
print("=" * 100)

vistos = set()
for p in TipoComplemento.objects.all().order_by('nombre'):
    clave = p.nombre[:80]
    if clave in vistos:
        continue
    vistos.add(clave)
    print(f"  [{p.categoria or '?':15}] [{p.calibre or '':5}]  {p.nombre[:95]}")
    if len(vistos) >= 200:
        break
