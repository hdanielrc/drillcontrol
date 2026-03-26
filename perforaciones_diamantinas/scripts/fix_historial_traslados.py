"""
Script de corrección: historial de trabajadores trasladados entre contratos.

Ejecutar con:
    python manage.py shell < scripts/fix_historial_traslados.py
o:
    python scripts/fix_historial_traslados.py
"""
import os
import sys
import django
from datetime import date, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import TrabajadorContratoHistorial, Trabajador, Contrato

BULK_FIX_DATE = date(2026, 2, 26)

print("=" * 60)
print("PASO 1: Revertir fecha_inicio de traslados incorrectamente")
print("        bulk-fijados a 2026-02-26")
print("=" * 60)

transferidos = TrabajadorContratoHistorial.objects.filter(
    fecha_inicio=BULK_FIX_DATE,
    motivo_cambio='Traslado detectado en sincronización automática',
)
print(f"Registros de traslado con fecha_inicio={BULK_FIX_DATE}: {transferidos.count()}")

corregidos = 0
for h in transferidos:
    prev = TrabajadorContratoHistorial.objects.filter(
        trabajador=h.trabajador,
        fecha_fin__isnull=False,
    ).order_by('-fecha_fin').first()

    if prev:
        nueva = prev.fecha_fin + timedelta(days=1)
        print(f"  {h.trabajador} → {h.contrato}: {h.fecha_inicio} → {nueva}  (cierre anterior: {prev.contrato} fin={prev.fecha_fin})")
        h.fecha_inicio = nueva
        h.save(update_fields=['fecha_inicio', 'updated_at'])
        corregidos += 1
    else:
        print(f"  {h.trabajador} → {h.contrato}: sin historial cerrado previo — NO corregido (ver PASO 2)")

print(f"\nCorregidos en PASO 1: {corregidos}")

print()
print("=" * 60)
print("PASO 2: Detectar trabajadores SIN historial del contrato anterior")
print("        (casos donde el sync no dejó registro del CC de origen)")
print("=" * 60)

sin_historial_previo = []
for h in TrabajadorContratoHistorial.objects.filter(
    motivo_cambio='Traslado detectado en sincronización automática',
).select_related('trabajador', 'contrato'):
    t = h.trabajador
    tiene_historial_anterior = TrabajadorContratoHistorial.objects.filter(
        trabajador=t,
        fecha_fin__isnull=False,
    ).exists()
    if not tiene_historial_anterior:
        sin_historial_previo.append((t, h))

if not sin_historial_previo:
    print("Ningún caso detectado.")
else:
    print(f"{len(sin_historial_previo)} trabajador(es) sin historial del contrato de origen:\n")
    for t, h in sin_historial_previo:
        fecha_contrato_anterior_fin = h.fecha_inicio - timedelta(days=1)
        fecha_inicio_retro = t.fecha_contratacion or date(2026, 2, 26)
        contrato_anterior_fk = Contrato.objects.filter(id=t.contrato_id).first() if t.contrato_id != h.contrato_id else None
        print(f"  Trabajador : {t}")
        print(f"  CC actual  : {h.contrato} (desde {h.fecha_inicio})")
        print(f"  CC anterior: {t.contrato} (FK actual)")
        print(f"  Propuesta  : crear historial CC anterior desde {fecha_inicio_retro} hasta {fecha_contrato_anterior_fin}")
        print()

print("=" * 60)
print("FIN. Revisa los casos del PASO 2 y ajusta fechas manualmente si es necesario.")
print("     Para crear un registro retroactivo manualmente:")
print("     TrabajadorContratoHistorial.objects.create(")
print("         trabajador=trabajador,")
print("         contrato=contrato_anterior,")
print("         fecha_inicio=date(YYYY, MM, DD),")
print("         fecha_fin=date(YYYY, MM, DD),")
print("         motivo_cambio='Registro retroactivo manual',")
print("         creado_automaticamente=False,")
print("     )")
