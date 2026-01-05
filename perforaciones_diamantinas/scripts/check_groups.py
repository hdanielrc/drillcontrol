import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador, Cargo

def check_groups():
    print("Checking specific management personnel...")
    
    names_to_check = ['FONSECA', 'IPARRAGUIRRE', 'CHOQUE']
    
    for name in names_to_check:
        workers = Trabajador.objects.filter(apellidos__icontains=name) | Trabajador.objects.filter(nombres__icontains=name)
        for w in workers:
            print(f"\nWorker: {w.nombres} {w.apellidos}")
            print(f"  Cargo: {w.cargo.nombre if w.cargo else 'None'}")
            print(f"  Grupo: {w.grupo}")
            print(f"  Contrato: {w.contrato.nombre_contrato if w.contrato else 'None'}")
            print(f"  Estado: {w.estado}")

if __name__ == '__main__':
    check_groups()

if __name__ == '__main__':
    check_groups()
