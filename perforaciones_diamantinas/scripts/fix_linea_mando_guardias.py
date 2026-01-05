import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador

def limpiar_guardias_linea_mando():
    print("Limpiando guardias asignadas a LINEA_MANDO...")
    
    # Buscar trabajadores de linea de mando que tengan guardia asignada
    trabajadores = Trabajador.objects.filter(
        grupo='LINEA_MANDO',
        guardia_asignada__isnull=False
    )
    
    count = trabajadores.count()
    print(f"Encontrados {count} trabajadores de Línea de Mando con guardia asignada.")
    
    if count > 0:
        updated = trabajadores.update(guardia_asignada=None)
        print(f"Se actualizaron {updated} registros. Ahora tienen guardia_asignada=None")
    else:
        print("No se requieren cambios.")

if __name__ == '__main__':
    limpiar_guardias_linea_mando()
