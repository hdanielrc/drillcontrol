"""Script para exportar registros de asistencia anteriores al inicio histórico del tareo.

Uso:
    Desde la carpeta que contiene `manage.py` ejecuta:

    python manage.py shell < perforaciones_diamantinas/scripts/check_prehistoric_asistencias.py

Crea `pre_historic_asistencias.csv` en la carpeta actual con los detalles.
"""
from datetime import date
import csv
import os

HISTORICO_START = date(2026, 2, 26)

print('Inicio búsqueda de asistencias anteriores a', HISTORICO_START)

# Importar modelos dentro del contexto de Django shell
try:
    from drilling.tareo_compat import AsistenciaDiaria
    from drilling.models import AsistenciaTrabajador
except Exception as e:
    print('Error importando modelos:', e)
    raise

out_file = 'pre_historic_asistencias.csv'
rows = []

# Buscar en AsistenciaDiaria (V2)
qs_v2 = AsistenciaDiaria.objects.filter(fecha__lt=HISTORICO_START).select_related('trabajador', 'maquina_snapshot')
print('AsistenciaDiaria encontrados:', qs_v2.count())
for a in qs_v2:
    trab = getattr(a, 'trabajador', None)
    trab_id = getattr(a, 'trabajador_id', None)
    guard_snap = getattr(a, 'guardia_snapshot', None)
    trab_guard = getattr(trab, 'guardia_asignada', None) if trab else None
    tipo = getattr(a, 'tipo', None)
    es_proy = getattr(a, 'es_proyeccion', None) if hasattr(a, 'es_proyeccion') else (tipo == 'PROY')
    rows.append({
        'modelo': 'AsistenciaDiaria',
        'id': a.id,
        'trabajador_id': trab_id,
        'fecha': a.fecha.isoformat(),
        'estado': a.estado,
        'es_proyeccion': bool(es_proy),
        'guardia_snapshot': guard_snap or '',
        'trabajador_guardia_actual': trab_guard or '',
        'maquina_snapshot_id': getattr(a, 'maquina_snapshot_id', None),
        'observaciones': getattr(a, 'observaciones', '') or '',
    })

# Buscar en AsistenciaTrabajador (V1)
qs_v1 = AsistenciaTrabajador.objects.filter(fecha__lt=HISTORICO_START).select_related('trabajador')
print('AsistenciaTrabajador encontrados:', qs_v1.count())
for a in qs_v1:
    trab = getattr(a, 'trabajador', None)
    rows.append({
        'modelo': 'AsistenciaTrabajador',
        'id': a.id,
        'trabajador_id': getattr(a, 'trabajador_id', None),
        'fecha': a.fecha.isoformat(),
        'estado': a.estado,
        'es_proyeccion': False,
        'guardia_snapshot': getattr(a, 'guardia_snapshot', '') or '',
        'trabajador_guardia_actual': getattr(trab, 'guardia_asignada', None) if trab else '',
        'maquina_snapshot_id': None,
        'observaciones': getattr(a, 'observaciones', '') or '',
    })

# Escribir CSV
if rows:
    keys = ['modelo','id','trabajador_id','fecha','estado','es_proyeccion','guardia_snapshot','trabajador_guardia_actual','maquina_snapshot_id','observaciones']
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f'Exportado {len(rows)} registros a: {os.path.abspath(out_file)}')
else:
    print('No se encontraron registros anteriores al inicio histórico.')
