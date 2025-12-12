import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato

print("\n" + "="*70)
print("CENTROS DE COSTO CONFIGURADOS")
print("="*70 + "\n")

contratos = Contrato.objects.filter(estado='ACTIVO')

for c in contratos:
    centro = c.codigo_centro_costo or "❌ SIN CONFIGURAR"
    print(f"{c.nombre_contrato:35} -> {centro}")

print("\n" + "="*70)
