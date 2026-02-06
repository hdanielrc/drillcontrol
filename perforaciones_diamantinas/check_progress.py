import os
import django
import sys
from django.db.models import Count
from django.db.models.functions import TruncMonth

# Configurar entorno Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perforaciones_diamantinas.settings")
django.setup()

from drilling.models import AbastecimientoArticulo

print("\n=== REPORTE DE PROGRESO: SINCRONIZACIÓN 2025 ===\n")

# Filtrar solo registros de 2025
qs = AbastecimientoArticulo.objects.filter(fecha__year=2025)

# Agrupar por mes
summary = qs.annotate(month=TruncMonth('fecha')).values('month').annotate(count=Count('id')).order_by('month')

total = 0
if not summary:
    print("⚠️  Aún no se han guardado registros para el año 2025.")
    print("   (Es posible que el script siga procesando o que los primeros meses no tengan datos)")
else:
    print(f"{'MES':<15} | {'CANTIDAD REGISTROS'}")
    print("-" * 35)
    for entry in summary:
        if entry['month']:
            m = entry['month']
            c = entry['count']
            total += c
            print(f"{m.strftime('%Y-%m'):<15} | {c}")
    print("-" * 35)
    print(f"TOTAL GENERAL   : {total}")
print("\n==============================================\n")
