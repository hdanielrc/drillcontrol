"""
Importar headcount desde un archivo Excel/CSV.

Uso:
  python manage.py shell < scripts/import_headcount_excel.py -- file=headcount_input.xlsx

O ejecutable directo (configura DJANGO_SETTINGS_MODULE si hace falta):
  python scripts/import_headcount_excel.py headcount_input.xlsx --dry-run

Este script preserva exactamente los valores de `CARGO` y `NIVEL` tal como vienen
en el Excel (solo hace strip de espacios), agrupa por la clave única y crea/actualiza
registros `HeadCount` usando el ORM de Django.
"""
import sys
import os
import argparse
import pandas as pd
from collections import defaultdict

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Importar HeadCount desde Excel/CSV')
    parser.add_argument('input', nargs='?', default=None, help='Ruta al archivo Excel o CSV (por defecto: plantillas/HEADCOUNT.csv o .xlsx si existe)')
    parser.add_argument('--dry-run', action='store_true', help='No escribir en la BD')
    parser.add_argument('--sheet', default=None, help='Nombre o índice de hoja (opcional para Excel)')
    parser.add_argument('--clear-existing', action='store_true', help='Borrar headcounts existentes para los contratos detectados antes de insertar')
    args = parser.parse_args()

    # Configurar entorno Django (asume que el script se ejecuta desde la raíz del proyecto)
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, BASE)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')

    import django
    django.setup()

    from drilling.models import HeadCount, Contrato

    input_path = args.input
    # Si no se proporcionó ruta, preferir CSV si existe, sino XLSX
    if not input_path:
        csv_path = os.path.join('plantillas', 'HEADCOUNT.csv')
        xlsx_path = os.path.join('plantillas', 'HEADCOUNT.xlsx')
        if os.path.exists(csv_path):
            input_path = csv_path
        elif os.path.exists(xlsx_path):
            input_path = xlsx_path
        else:
            # fallback to csv path (will error later if missing)
            input_path = csv_path
    print(f'Leyendo archivo: {input_path}')

    # Leer archivo (CSV o Excel).
    def _read_csv_with_fallback(path):
        encodings = ['utf-8', 'latin-1', 'cp1252']
        last_exc = None
        for enc in encodings:
            try:
                # Detect delimiter from first line
                with open(path, 'rb') as fh:
                    sample = fh.read(4096)
                text = sample.decode(enc)
                first_line = text.splitlines()[0] if text.splitlines() else ''
                sep = ';' if ';' in first_line else ','
                df_tmp = pd.read_csv(path, dtype=str, sep=sep, encoding=enc)
                return df_tmp
            except Exception as e:
                last_exc = e
                continue
        # If all encodings fail, raise last exception
        raise last_exc

    if input_path.lower().endswith('.csv'):
        df = _read_csv_with_fallback(input_path)
    else:
        # Excel (openpyxl engine)
        df = pd.read_excel(input_path, sheet_name=args.sheet, dtype=str, engine='openpyxl')

    # Normalizar nombres de columnas (buscar variantes)
    def find_col(df, candidates):
        cols = {c.lower().strip(): c for c in df.columns}
        for cand in candidates:
            key = cand.lower().strip()
            if key in cols:
                return cols[key]
        # buscar sin acentos y espacios
        import unicodedata
        def norm(s):
            return unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower().replace(' ', '')
        norm_map = {norm(k): v for k, v in cols.items()}
        for cand in candidates:
            if norm(cand) in norm_map:
                return norm_map[norm(cand)]
        return None

    col_ctr = find_col(df, ['CTR', 'CONTRATO', 'CONTRATO_NOMBRE'])
    col_serv = find_col(df, ['SERVICIO', 'SERVICE'])
    col_cat = find_col(df, ['CATEGORÍA', 'CATEGORIA', 'CATEGORIE'])
    col_ub = find_col(df, ['UBICACIÓN', 'UBICACION', 'UBIC'])
    col_cargo = find_col(df, ['CARGO'])
    col_nivel = find_col(df, ['NIVEL', 'LEVEL'])
    col_cant = find_col(df, ['CANTIDAD', 'QUANTITY', 'CANT'])

    required = {
        'contrato': col_ctr,
        'servicio': col_serv,
        'categoria': col_cat,
        'ubicacion': col_ub,
        'cargo': col_cargo,
        'cantidad': col_cant,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        print('Columnas requeridas faltantes en el archivo:', missing)
        sys.exit(1)

    # Limpiar y preparar filas
    df = df.fillna('')

    def clean_val(x):
        return x.strip() if isinstance(x, str) else x

    df['__contrato_raw'] = df[col_ctr].apply(clean_val)
    df['__servicio_raw'] = df[col_serv].apply(lambda x: clean_val(x).upper())
    df['__categoria_raw'] = df[col_cat].apply(lambda x: clean_val(x).upper())
    df['__ubicacion_raw'] = df[col_ub].apply(lambda x: clean_val(x).upper())
    # Importante: conservar EXACTO el valor de cargo y nivel, solo strip
    df['__cargo_raw'] = df[col_cargo].apply(lambda x: clean_val(x))
    if col_nivel:
        df['__nivel_raw'] = df[col_nivel].apply(lambda x: clean_val(x))
    else:
        df['__nivel_raw'] = ''

    # Cantidad como entero (si falla, marcar fila inválida)
    def to_int(x):
        try:
            if x == '':
                return 0
            return int(float(str(x)))
        except Exception:
            return None

    df['__cantidad_raw'] = df[col_cant].apply(to_int)

    invalid_rows = []
    groups = defaultdict(int)
    rows_info = {}

    # Validar contratos y agrupar
    for idx, r in df.iterrows():
        contrato_name = r['__contrato_raw']
        if not contrato_name:
            invalid_rows.append((idx, 'contrato_vacio'))
            continue
        contrato = Contrato.objects.filter(nombre_contrato__iexact=contrato_name).first()
        if not contrato:
            invalid_rows.append((idx, f'contrato_no_encontrado: {contrato_name}'))
            continue

        servicio = r['__servicio_raw'] or 'DDH'
        categoria = r['__categoria_raw'] or ''
        ubicacion = r['__ubicacion_raw'] or 'GENERAL'
        cargo = r['__cargo_raw']
        nivel = r['__nivel_raw'] or None
        cantidad = r['__cantidad_raw']
        if cantidad is None or cantidad < 0:
            invalid_rows.append((idx, f'cantidad_invalida: {r[col_cant]}'))
            continue

        key = (contrato.id, servicio, categoria, ubicacion, cargo, nivel)
        groups[key] += cantidad
        rows_info[key] = {
            'contrato': contrato,
            'servicio': servicio,
            'categoria': categoria,
            'ubicacion': ubicacion,
            'cargo': cargo,
            'nivel': nivel,
        }

    print(f'Filas inválidas detectadas: {len(invalid_rows)}')
    if invalid_rows:
        for i, reason in invalid_rows[:10]:
            print(f' - fila {i+2}: {reason}')

    # Preparar acciones de DB
    created = 0
    updated = 0
    skipped = 0

    if args.dry_run:
        print('Dry run activo — no se escribirán cambios en la BD')

    # Si se solicita, borrar headcounts existentes para los contratos detectados
    contrato_ids = set(k[0] for k in groups.keys())
    if args.clear_existing and contrato_ids:
        contratos = [rows_info[k]['contrato'] for k in rows_info.keys()]
        unique_contratos = {c.id: c for c in contratos}
        if args.dry_run:
            print('[DRY] Se borrarán headcounts para los siguientes contratos:')
            for cid, cobj in unique_contratos.items():
                print(f' - {cobj.nombre_contrato} (id={cid})')
        else:
            try:
                del_qs = HeadCount.objects.filter(contrato_id__in=list(unique_contratos.keys()))
                deleted_count = del_qs.count()
                del_qs.delete()
                print(f'Se eliminaron {deleted_count} headcount(s) existentes para los contratos detectados')
            except Exception as e:
                print('Error al borrar headcounts existentes:', e)
                # continuar intentando insertar (pero probablemente fallará si hay FK/locks)

    for key, total_cant in groups.items():
        info = rows_info[key]
        contrato = info['contrato']
        servicio = info['servicio']
        categoria = info['categoria']
        ubicacion = info['ubicacion']
        cargo = info['cargo']
        nivel = info['nivel']

        # Nivel: si está vacío convertimos a None para coincidir con el modelo
        nivel_db = nivel if nivel not in (None, '') else None

        if args.dry_run:
            print(f'[DRY] {contrato.nombre_contrato} | {servicio} | {categoria} | {ubicacion} | {cargo} | {nivel_db} => {total_cant}')
            continue

        try:
            obj, created_flag = HeadCount.objects.update_or_create(
                contrato=contrato,
                servicio=servicio,
                categoria=categoria,
                ubicacion=ubicacion,
                cargo=cargo,
                nivel=nivel_db,
                defaults={
                    'cantidad_requerida': total_cant,
                    'activo': True,
                    'observaciones': 'Importado desde Excel',
                }
            )
            if created_flag:
                created += 1
            else:
                updated += 1
        except Exception as e:
            print('Error al crear/actualizar:', e)
            skipped += 1

    print('--- Resumen ---')
    print('Total grupos procesados:', len(groups))
    print('Creados:', created)
    print('Actualizados:', updated)
    print('Saltados (errores):', skipped)

    # Exportar filas inválidas para revisión
    if invalid_rows:
        invalid_out = []
        for idx, reason in invalid_rows:
            row = df.iloc[idx].to_dict()
            row['__invalid_reason'] = reason
            invalid_out.append(row)
        pd.DataFrame(invalid_out).to_csv('headcount_invalid_rows.csv', index=False)
        print('Filas inválidas exportadas a headcount_invalid_rows.csv')
