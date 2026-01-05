import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador, Contrato

def mover_staff():
    try:
        # Obtener contrato destino
        condestable = Contrato.objects.get(nombre_contrato__icontains='CONDESTABLE')
        print(f"Contrato destino: {condestable.nombre_contrato} (ID: {condestable.id})")
        
        # Lista de apellidos/nombres a buscar
        staff_names = ['FONSECA', 'IPARRAGUIRRE', 'CHOQUE']
        
        count = 0
        for name in staff_names:
            # Buscar trabajadores que coincidan y NO estén ya en Condestable
            workers = Trabajador.objects.filter(
                (django.db.models.Q(apellidos__icontains=name) | django.db.models.Q(nombres__icontains=name))
            ).exclude(contrato=condestable)
            
            for w in workers:
                old_contract = w.contrato.nombre_contrato if w.contrato else "Sin Contrato"
                print(f"Moviendo a: {w.nombres} {w.apellidos}")
                print(f"   - Cargo: {w.cargo.nombre if w.cargo else 'N/A'}")
                print(f"   - De: {old_contract} -> A: {condestable.nombre_contrato}")
                
                w.contrato = condestable
                w.save()
                count += 1
                print("   [OK] Movido exitosamente")
                
        print(f"\nTotal trabajadores movidos: {count}")
        
    except Contrato.DoesNotExist:
        print("Error: No se encontró el contrato CONDESTABLE")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == '__main__':
    mover_staff()
