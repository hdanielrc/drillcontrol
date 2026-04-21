#!/usr/bin/env python
"""
Comprueba la secuencia de estados de un trabajador desde el día anterior
al periodo operativo hasta el cierre del mes y muestra bloques consecutivos
para validar cumplimiento del régimen (14x7, etc.).

Uso:
    python scripts/check_regimen_worker.py <contrato_id> "<apellido>" "<nombre>" [anio] [mes]

Ejemplo:
    python scripts/check_regimen_worker.py 3 "GONZALES" "DANIEL" 2026 3

"""
import sys
import os
from datetime import date, timedelta, datetime

# Asegurar settings
# Añadir la carpeta padre del proyecto (..../app) al sys.path para que
# `import perforaciones_diamantinas` funcione cuando se ejecute este script
# desde dentro de `perforaciones_diamantinas/scripts/`.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
import django
django.setup()

from drilling.models import Trabajador
from drilling.utils.tareo_service import TareoService
from drilling.tareo_compat import AsistenciaDiaria, NEW_TAREO


def usage_and_exit():
    print("Uso: python scripts/check_regimen_worker.py <contrato_id> \"<apellido>\" \"<nombre>\" [anio] [mes]")
    sys.exit(1)


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        usage_and_exit()

    contrato_id = int(args[0])
    apellido = args[1]
    nombre = args[2]
    today = datetime.today().date()
    anio = int(args[3]) if len(args) > 3 else today.year
    mes  = int(args[4]) if len(args) > 4 else today.month

    # periodo operativo: 26 del mes anterior .. 25 del mes
    mes_anterior = mes - 1 if mes > 1 else 12
    anio_anterior = anio if mes > 1 else anio - 1
    primer_dia = date(anio_anterior, mes_anterior, 26)
    ultimo_dia = date(anio, mes, 25)
    dia_anterior = primer_dia - timedelta(days=1)

    t = Trabajador.objects.filter(contrato_id=contrato_id, apepat__icontains=apellido, nombres__icontains=nombre).first()
    if not t:
        print("Trabajador no encontrado con esos filtros.")
        sys.exit(2)

    print(f"Trabajador: {t.nombres} {t.apepat} {t.apemat} (id={t.id})")
    print(f"Periodo operativo: {primer_dia} .. {ultimo_dia} (dia anterior: {dia_anterior})")

    # Detectar dinámicamente el nombre del FK en AsistenciaDiaria (compatibilidad esquema)
    try:
        field_names = [f.name for f in AsistenciaDiaria._meta.get_fields()]
        if 'trabajador' in field_names:
            emp_field = 'trabajador'
        elif 'empleado' in field_names:
            emp_field = 'empleado'
        else:
            emp_field = 'trabajador'
    except Exception:
        emp_field = 'trabajador'

    filter_kwargs = {f"fecha__gte": dia_anterior, f"fecha__lte": ultimo_dia, f"{emp_field}__id": t.id}
    qs = AsistenciaDiaria.objects.filter(**filter_kwargs).order_by('fecha')

    rows = [(r.fecha, getattr(r, 'estado', None) or (r.get_estado_display() if hasattr(r, 'get_estado_display') else None)) for r in qs]

    print("\nFecha\t\tEstado")
    for fecha, estado in rows:
        print(f"{fecha}\t{estado}")

    # contar máximos consecutivos de trabajo (TD/TN/TRABAJO)
    work_states = ('TD','TN','TRABAJO')
    span_start = dia_anterior
    span_end = ultimo_dia
    d = span_start
    max_consec = 0
    current = 0
    consec_segments = []


    
    # build a dict for fast lookup
    row_map = {f: s for (f, s) in rows}
    while d <= span_end:
        est = row_map.get(d)
        if est in work_states:
            current += 1
        else:
            if current > 0:
                consec_segments.append((d - timedelta(days=current), current))
            max_consec = max(max_consec, current)
            current = 0
        d += timedelta(days=1)
    if current > 0:
        consec_segments.append((d - timedelta(days=current), current))
        max_consec = max(max_consec, current)

    print("\nSegmentos consecutivos de trabajo (inicio, dias):")
    for start, count in consec_segments:
        print(f"{start} -> {count} días")
    print(f"\nMáximo consecutivo detectado (incluyendo día anterior): {max_consec} días")

    dias_trabajo, dias_descanso = TareoService.REGIMEN_CONFIG.get(t.regimen_laboral or '14x7', (14,7))
    print(f"Régimen del trabajador: {t.regimen_laboral or '14x7'} (dias trabajo={dias_trabajo}, dias descanso={dias_descanso})")
    if max_consec > dias_trabajo:
        print("ATENCIÓN: Se detectó un bloque de trabajo mayor que los días de trabajo del régimen.")
    else:
        print("OK: No se detectaron bloques de trabajo mayores al régimen.")


if __name__ == '__main__':
    main()
