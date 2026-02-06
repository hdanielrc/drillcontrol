import os
import django
import sys

# Setup Django environment
# The project root is actually inside perforaciones_diamantinas
# But manage.py adds the inner folder to path.
# Let's adjust sys.path correctly.

sys.path.append(os.path.join(os.getcwd(), 'perforaciones_diamantinas'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import TipoComplemento, Contrato

serie_to_check = "408375"
print(f"--- Checking Drill Bit: {serie_to_check} ---")

try:
    bits = TipoComplemento.objects.filter(serie__icontains=serie_to_check)
    if not bits.exists():
        print("No drill bits found with that series.")
    else:
        for bit in bits:
            print(f"ID: {bit.id}")
            print(f"Name: {bit.nombre}")
            print(f"Serie: {bit.serie}")
            print(f"Estado: '{bit.estado}'")
            print(f"Categoria: {bit.categoria}")
            if bit.contrato:
                print(f"Contrato ID: {bit.contrato.id}")
                print(f"Contrato Name: {bit.contrato.nombre_contrato}")
            else:
                print("Contrato: None")
            print("-" * 20)

except Exception as e:
    print(f"Error: {e}")
