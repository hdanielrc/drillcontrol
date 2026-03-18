"""Respaldar y (opcional) eliminar todos los registros legacy de AsistenciaTrabajador.

Uso (solo backup):
    python manage.py shell < scripts/remove_legacy_asistencia.py

Eliminar después del backup (con confirmación automática via ENV):
    DELETE_LEGACY=1 python manage.py shell < scripts/remove_legacy_asistencia.py

El script genera `backup_asistencia_trabajador_all.csv` en la carpeta actual.
"""
from datetime import date
import csv
import os
import sys

OUTFILE = 'backup_asistencia_trabajador_all.csv'

print('Iniciando backup de AsistenciaTrabajador...')
try:
    from drilling.models import AsistenciaTrabajador
except Exception as e:
    print('Error importando AsistenciaTrabajador:', e)
    raise

qs = AsistenciaTrabajador.objects.all().select_related('trabajador')
count = qs.count()
print(f'Total registros a respaldar: {count}')

if count == 0:
    print('No hay registros legacy en AsistenciaTrabajador. Nada que hacer.')
    sys.exit(0)

with open(OUTFILE, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['id','trabajador_id','fecha','estado','tipo','guardia_snapshot','observaciones'])
    for a in qs.iterator():
        w.writerow([
            a.id,
            getattr(a, 'trabajador_id', None),
            a.fecha.isoformat() if getattr(a,'fecha',None) else '',
            a.estado,
            getattr(a, 'tipo', ''),
            getattr(a, 'guardia_snapshot', '') or '',
            getattr(a, 'observaciones', '') or '',
        ])

print(f'Exportado {count} registros a: {os.path.abspath(OUTFILE)}')

if os.environ.get('DELETE_LEGACY') == '1':
    print('\nVariable DELETE_LEGACY=1 encontrada. Procediendo a eliminar registros...')
    n, _ = qs.delete()
    print(f'Deleted objects count (including cascades): {n}')
else:
    print('\nNo se eliminaron registros. Para eliminar tras el backup, ejecuta:')
    print("DELETE_LEGACY=1 python manage.py shell < scripts/remove_legacy_asistencia.py")
