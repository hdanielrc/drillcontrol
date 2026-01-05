import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador, Cargo

def check_groups():
    print("Checking worker groups...")
    trabajadores = Trabajador.objects.filter(estado='ACTIVO')
    
    stats = {}
    sin_grupo = []
    linea_mando = []
    
    for t in trabajadores:
        grupo = t.grupo
        if not grupo:
            grupo = 'EMPTY'
            sin_grupo.append(f"{t.nombres} {t.apellidos} ({t.cargo.nombre if t.cargo else 'No Cargo'})")
        
        if grupo == 'LINEA_MANDO':
            linea_mando.append(f"{t.nombres} {t.apellidos} ({t.cargo.nombre if t.cargo else 'No Cargo'})")
            
        stats[grupo] = stats.get(grupo, 0) + 1
        
    print("\nGroup Statistics:")
    for g, count in stats.items():
        print(f"{g}: {count}")
        
    print("\nWorkers with EMPTY group:")
    for w in sin_grupo:
        print(f"- {w}")

    print("\nWorkers in LINEA_MANDO:")
    for w in linea_mando:
        print(f"- {w}")

if __name__ == '__main__':
    check_groups()
