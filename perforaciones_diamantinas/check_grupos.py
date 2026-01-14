import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import AsistenciaTrabajador
from datetime import date

fecha = date(2026, 1, 13)

print(f"\n=== ANÁLISIS DE GRUPOS PARA {fecha} ===\n")

# Ver todos los registros
asistencias = AsistenciaTrabajador.objects.filter(fecha=fecha)
print(f"Total de registros de asistencia: {asistencias.count()}")

# Ver grupos únicos con sus estados
grupos_estados = asistencias.values('guardia_snapshot', 'estado').distinct()
print(f"\nGrupos y estados encontrados:")
for item in grupos_estados:
    guardia = item['guardia_snapshot']
    estado = item['estado']
    count = asistencias.filter(guardia_snapshot=guardia, estado=estado).count()
    print(f"  Guardia: {guardia or '(sin guardia)'}, Estado: {estado}, Cantidad: {count}")

# Ver grupos con trabajadores en estado TRABAJADO
print(f"\n=== GRUPOS CON TRABAJADORES EN ESTADO 'TRABAJADO' ===")
grupos_trabajando = asistencias.filter(
    estado='TRABAJADO',
    guardia_snapshot__isnull=False
).exclude(
    guardia_snapshot=''
).values_list('guardia_snapshot', flat=True).distinct().order_by('guardia_snapshot')

print(f"Grupos disponibles: {list(grupos_trabajando)}")

# Detalle por grupo
for grupo in grupos_trabajando:
    trabajadores = asistencias.filter(guardia_snapshot=grupo, estado='TRABAJADO')
    print(f"\nGuardia {grupo}: {trabajadores.count()} trabajadores")
    for t in trabajadores[:5]:  # Mostrar solo 5 primeros
        print(f"  - {t.trabajador.nombres} {t.trabajador.apellido_paterno}")
