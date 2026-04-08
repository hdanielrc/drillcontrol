"""
SCRIPT DE FIX: FieldDoesNotExist - asistenciadiaria.empleado
=============================================================

PROBLEMA:
  La migración 0087_tareoentry_tareoentryaudit_tareoperiod_and_more (rama paralela
  de desarrollo) contiene un RenameField(asistenciadiaria, 'empleado' -> 'trabajador').

  Pero la migración 0085_sondaje_desvio_cobrabilidad (rama principal) ya hace
  RemoveField('empleado') + AddField('trabajador') en el mismo modelo.

  Al reconstruir el estado de migraciones en orden topológico:
    1. 0085_sondaje_desvio_cobrabilidad corre primero (0085_s < 0087_t)
       → elimina 'empleado', agrega 'trabajador' al estado interno
    2. 0087_tareoentry intenta RenameField('empleado' → 'trabajador')
       → 'empleado' ya no existe → FieldDoesNotExist

SOLUCIÓN:
  Eliminar el operation RenameField conflictivo de 0087.
  La columna en la BD ya tiene el nombre correcto ('trabajador') porque
  0085_sondaje_desvio_cobrabilidad fue la última migración aplicada (id 140).

INSTRUCCIONES:
  Ejecutar en el servidor desde el directorio de la aplicación:
    cd /var/www/drillcontrol/app/perforaciones_diamantinas
    python fix_renombramiento_asistencia.py
"""

import os
import re
import shutil
import sys

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'drilling', 'migrations')


def find_conflicting_files():
    """Busca archivos de migración que tengan RenameField para asistenciadiaria/empleado."""
    found = []
    for fname in sorted(os.listdir(MIGRATIONS_DIR)):
        if not fname.endswith('.py') or fname == '__init__.py':
            continue
        path = os.path.join(MIGRATIONS_DIR, fname)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Buscar RenameField que mencione asistenciadiaria y empleado
        if re.search(
            r'RenameField\b.*?model_name.*?asistenciadiaria.*?old_name.*?empleado',
            content,
            re.DOTALL | re.IGNORECASE
        ):
            found.append((fname, path, content))
    return found


def remove_renamefield_block(content, fname):
    """
    Elimina el bloque RenameField(model_name='asistenciadiaria', old_name='empleado', ...).
    Retorna (new_content, was_modified).
    """
    # Patrón para encontrar el bloque completo, incluyendo la coma final opcional
    # Ejemplos de lo que puede haber:
    #   migrations.RenameField(
    #       model_name='asistenciadiaria',
    #       old_name='empleado',
    #       new_name='trabajador',
    #   ),
    pattern = re.compile(
        r'\s*migrations\.RenameField\s*\(\s*'
        r'(?:[^)]*?)'                          # any params before model_name
        r'model_name\s*=\s*[\'"]asistenciadiaria[\'"]\s*,\s*'
        r'old_name\s*=\s*[\'"]empleado[\'"]'   # the old field name
        r'[^)]*\)\s*,?',                       # close paren + optional comma
        re.DOTALL | re.IGNORECASE
    )

    matches = list(pattern.finditer(content))
    if not matches:
        # Try alternate param order
        pattern2 = re.compile(
            r'\s*migrations\.RenameField\s*\(\s*'
            r'(?:[^)]*?)'
            r'old_name\s*=\s*[\'"]empleado[\'"]'
            r'(?:[^)]*?)'
            r'model_name\s*=\s*[\'"]asistenciadiaria[\'"]'
            r'[^)]*\)\s*,?',
            re.DOTALL | re.IGNORECASE
        )
        matches = list(pattern2.finditer(content))

    if not matches:
        print(f"  [WARN] No se encontró el bloque exacto en {fname}. Intenta editarlo manualmente.")
        return content, False

    new_content = content
    # Remove matches in reverse order to preserve positions
    for m in reversed(matches):
        print(f"\n  Eliminando bloque (líneas ~{content[:m.start()].count(chr(10))+1}):")
        print("  " + "-" * 50)
        print(m.group().strip())
        print("  " + "-" * 50)
        new_content = new_content[:m.start()] + new_content[m.end():]

    return new_content, True


def main():
    print("=" * 65)
    print("FIX: FieldDoesNotExist - asistenciadiaria.empleado")
    print("=" * 65)

    if not os.path.isdir(MIGRATIONS_DIR):
        print(f"[ERROR] No se encontró el directorio: {MIGRATIONS_DIR}")
        print("Asegúrate de ejecutar el script desde perforaciones_diamantinas/")
        sys.exit(1)

    print(f"\nBuscando migraciones conflictivas en: {MIGRATIONS_DIR}")
    conflicting = find_conflicting_files()

    if not conflicting:
        print("\n[INFO] No se encontraron archivos con el RenameField conflictivo.")
        print("El error puede ser otro. Revisa el traceback completo.")
        sys.exit(0)

    print(f"\nArchivos encontrados con RenameField conflictivo: {len(conflicting)}")
    for fname, path, _ in conflicting:
        print(f"  → {fname}")

    # Mostrar advertencia
    print("\n[ADVERTENCIA] Se modificarán los archivos de migración.")
    print("Se creará un backup .backup de cada archivo afectado.")
    resp = input("\n¿Aplicar el fix? (s/N): ").strip().lower()
    if resp not in ('s', 'si', 'y', 'yes'):
        print("Operación cancelada.")
        sys.exit(0)

    fixed_count = 0
    for fname, path, content in conflicting:
        print(f"\nProcesando: {fname}")
        backup_path = path + '.backup'
        shutil.copy2(path, backup_path)
        print(f"  Backup: {backup_path}")

        new_content, modified = remove_renamefield_block(content, fname)
        if modified:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  [OK] Archivo actualizado.")
            fixed_count += 1
        else:
            print(f"  [SKIP] No se pudo parchear automáticamente.\n"
                  f"  Edita manualmente y elimina el bloque:\n"
                  f"    migrations.RenameField(\n"
                  f"        model_name='asistenciadiaria',\n"
                  f"        old_name='empleado',\n"
                  f"        new_name='trabajador',\n"
                  f"    ),")

    print(f"\n{'='*65}")
    if fixed_count > 0:
        print(f"Fix aplicado a {fixed_count} archivo(s).")
        print("\nSiguientes pasos:")
        print("  1. Verifica el estado de migraciones:")
        print("     python manage.py showmigrations drilling")
        print("  2. Ejecuta migrate:")
        print("     python manage.py migrate")
        print("\nSi migrate aún falla, restaura el backup:")
        for fname, path, _ in conflicting:
            print(f"     mv {path}.backup {path}")
    else:
        print("No se aplicó ningún fix. Edición manual requerida.")


if __name__ == '__main__':
    main()
