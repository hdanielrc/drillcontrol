#!/usr/bin/env python3
"""Analiza la respuesta JSON de la API de trabajadores y detecta anomalías comunes.

Uso:
  python analyze_trabajadores_api.py --url "<API_URL>" --out anomalies.csv

El script intenta detectar DNIs mal formados, nombres/apellidos mezclados,
centro_costo inconsistente y otros problemas y escribe un CSV con las filas
anómalas para revisión.
"""
import argparse
import requests
import csv
import json
import os
import sys
import re
from datetime import datetime


def analyze(workers, expected_cc=None):
    anomalies = []
    counts = {'total': 0, 'missing_dni': 0, 'dni_non_digits': 0, 'dni_short': 0, 'name_comma': 0, 'cc_mismatch': 0}

    for i, w in enumerate(workers, 1):
        counts['total'] += 1
        issues = []
        dni_orig = w.get('dni')
        nombres = (w.get('nombres') or '').strip()
        apepat = (w.get('apepat') or '').strip()
        apemat = (w.get('apemat') or '').strip()
        centro_costo = w.get('centro_costo') or w.get('centro') or w.get('centroCosto') or ''

        if dni_orig in (None, '', []):
            counts['missing_dni'] += 1
            issues.append('missing_dni')
            dni_digits = ''
        else:
            s = str(dni_orig).strip()
            digits = re.sub(r"\D", "", s)
            dni_digits = digits
            if not digits:
                counts['dni_non_digits'] += 1
                issues.append('dni_non_digits')
            if 0 < len(digits) < 8:
                counts['dni_short'] += 1
                issues.append('dni_short')

        # nombres starting with comma or containing leading comma
        if nombres.startswith(',') or nombres.startswith('.') or nombres.startswith(';'):
            counts['name_comma'] += 1
            issues.append('name_leading_punct')

        # nombres contains comma meaning maybe "APELLIDO, NOMBRES"
        if (',' in nombres) and not apepat:
            issues.append('comma_in_nombres_possibly_apellidos')

        # Centro costo mismatch
        if expected_cc and centro_costo and str(centro_costo).strip() != str(expected_cc).strip():
            counts['cc_mismatch'] += 1
            issues.append('centro_costo_mismatch')

        # cargo empty
        if not (w.get('cargo') or '').strip():
            issues.append('cargo_empty')

        if issues:
            anomalies.append({
                'idx': i,
                'dni_orig': dni_orig,
                'dni_digits': dni_digits,
                'nombres': nombres,
                'apepat': apepat,
                'apemat': apemat,
                'centro_costo': centro_costo,
                'cargo': w.get('cargo'),
                'issues': ';'.join(issues),
                'raw': json.dumps(w, ensure_ascii=False)[:200]
            })

    return anomalies, counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='URL completa de la API que devuelve trabajadores')
    parser.add_argument('--out', default='trabajadores_api_anomalies.csv', help='Archivo CSV de salida')
    parser.add_argument('--centro-costo', default=None, help='Centro costo esperado para filtrar/mismatch')
    args = parser.parse_args()

    try:
        resp = requests.get(args.url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Error descargando la API: {e}")
        sys.exit(2)

    if isinstance(data, dict) and 'trabajadores' in data:
        workers = data['trabajadores']
    elif isinstance(data, list):
        workers = data
    else:
        print('Formato inesperado de la respuesta JSON; mostraré raw')
        print(json.dumps(data)[:1000])
        sys.exit(3)

    anomalies, counts = analyze(workers, expected_cc=args.centro_costo)

    # Escribir CSV
    out_file = args.out
    os.makedirs(os.path.dirname(out_file) or '.', exist_ok=True)
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['idx','dni_orig','dni_digits','nombres','apepat','apemat','centro_costo','cargo','issues','raw'])
        writer.writeheader()
        for a in anomalies:
            writer.writerow(a)

    print('Resumen:')
    for k,v in counts.items():
        print(f'  {k}: {v}')
    print(f'Anomalías detectadas y guardadas en: {out_file}')


if __name__ == '__main__':
    main()
