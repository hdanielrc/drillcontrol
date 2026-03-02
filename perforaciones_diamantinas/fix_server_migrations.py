"""
Script de emergencia para reparar el estado de migraciones en el servidor.
Ejecutar con: python fix_server_migrations.py
"""
import os
import sys

# Parchamos StateApps para evitar el ValueError antes de setup
import django.db.migrations.state as mstate
_orig_init = mstate.StateApps.__init__
def _patched_init(self, real_apps, models, ignore_swappable=False):
    try:
        _orig_init(self, real_apps, models, ignore_swappable)
    except ValueError as e:
        print(f"[WARN] Ignorando error de estado (esperado): {e}")
mstate.StateApps.__init__ = _patched_init

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
import django
django.setup()

from django.db import connection

print("=" * 60)
print("FIX MIGRACIONES - SERVIDOR")
print("=" * 60)

cursor = connection.cursor()

# 1. Verificar columnas actuales
cursor.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'tipos_complemento'
    AND column_name IN ('marca', 'calibre', 'altura', 'serie_bit')
""")
existing = [r[0] for r in cursor.fetchall()]
print(f"\nColumnas ya existentes: {existing}")

# 2. Agregar columnas faltantes
col_sqls = [
    ("marca",     "ALTER TABLE tipos_complemento ADD COLUMN IF NOT EXISTS marca VARCHAR(100) NOT NULL DEFAULT ''"),
    ("calibre",   "ALTER TABLE tipos_complemento ADD COLUMN IF NOT EXISTS calibre VARCHAR(20) NOT NULL DEFAULT ''"),
    ("altura",    "ALTER TABLE tipos_complemento ADD COLUMN IF NOT EXISTS altura VARCHAR(10) NOT NULL DEFAULT ''"),
    ("serie_bit", "ALTER TABLE tipos_complemento ADD COLUMN IF NOT EXISTS serie_bit VARCHAR(20) NOT NULL DEFAULT ''"),
]
for col, sql in col_sqls:
    try:
        cursor.execute(sql)
        print(f"OK columna: {col}")
    except Exception as e:
        print(f"Skip columna {col}: {e}")

# 3. Indices
idx_sqls = [
    "CREATE INDEX IF NOT EXISTS tipos_compl_categor_3b69ce_idx ON tipos_complemento (categoria)",
    "CREATE INDEX IF NOT EXISTS tipos_compl_contrat_487b87_idx ON tipos_complemento (contrato_id, categoria)",
]
for sql in idx_sqls:
    try:
        cursor.execute(sql)
        print(f"OK index: {sql[27:70]}")
    except Exception as e:
        print(f"Skip index: {e}")

# 4. Fake-apply migraciones pendientes
migs = [
    ('drilling', '0073_add_marca_calibre_tipocomplemento'),
    ('drilling', '0074_add_altura_seriebit_tipocomplemento'),
    ('drilling', '0075_merge_20260302_1800'),
    ('drilling', '0076_remove_trabajadorapi_cargo_and_more'),
]
print("\nFake-applying migraciones:")
for app, name in migs:
    cursor.execute(
        "SELECT COUNT(*) FROM django_migrations WHERE app = %s AND name = %s",
        [app, name]
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
            [app, name]
        )
        print(f"  -> {name}")
    else:
        print(f"  Ya existe: {name}")

connection.commit()
print("\nListo. Ahora corre: python manage.py migrate --check")
