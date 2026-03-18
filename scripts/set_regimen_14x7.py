import os
import sys
from django.db import transaction

# Ajustar ruta para que el proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Añadir la carpeta que contiene `manage.py` al path para poder importar el settings
PROJECT_DIR = os.path.join(BASE_DIR, 'perforaciones_diamantinas')
sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')

import django
django.setup()

from perforaciones_diamantinas.drilling.models import Trabajador
from django.db.models import Q

@transaction.atomic
def main():
    qs = Trabajador.objects.filter(Q(regimen_laboral__isnull=True) | Q(regimen_laboral=''))
    total = qs.count()
    if total == 0:
        print('No hay trabajadores sin régimen.')
        return
    updated = qs.update(regimen_laboral='14x7')
    print(f'Actualizados {updated} trabajadores a regimen 14x7')

if __name__ == '__main__':
    main()
