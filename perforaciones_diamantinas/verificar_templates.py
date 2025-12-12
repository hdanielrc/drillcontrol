import os
import sys
import django
import io

# Configurar salida UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.template import Template, Context
from django.template.loader import get_template
from pathlib import Path

# Directorio de templates
templates_dir = Path('drilling/templates/drilling')
errors_found = []
templates_checked = 0

print("Verificando sintaxis de templates Django...\n")

for template_file in templates_dir.rglob('*.html'):
    try:
        templates_checked += 1
        relative_path = template_file.relative_to('drilling/templates')
        template = get_template(str(relative_path))
        print(f"OK {relative_path}")
    except Exception as e:
        error_msg = f"ERROR {relative_path}: {str(e)}"
        errors_found.append(error_msg)
        print(error_msg)

print(f"\n{'='*80}")
print(f"Total templates verificados: {templates_checked}")
print(f"Errores encontrados: {len(errors_found)}")

if errors_found:
    print("\nERRORES DETECTADOS:")
    for error in errors_found:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("\nTodos los templates son validos!")
    sys.exit(0)
