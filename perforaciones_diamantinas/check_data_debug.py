import os
import sys
import django

# Add the project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perforaciones_diamantinas.settings")
django.setup()

from drilling.models import Contrato, AbastecimientoArticulo, Abastecimiento, TipoComplemento
from django.db.models import Count

def run_debug():
    print("=== DEBUG: Contratos Activos ===")
    contratos = Contrato.objects.filter(estado='ACTIVO')
    for c in contratos:
        print(f"ID: {c.id}, Nombre: {c.nombre_contrato}, CC: '{c.codigo_centro_costo}'")
    
    # Check for duplicate TipoComplemento
    print("\n=== DEBUG: Duplicados en TipoComplemento ===")
    dupes = TipoComplemento.objects.values('nombre').annotate(total=Count('id')).filter(total__gt=1)
    if dupes.exists():
        print(f"WARN: Se encontraron {dupes.count()} nombres con duplicados en TipoComplemento.")
        for d in dupes[:10]:
            print(f"- '{d['nombre']}' tiene {d['total']} registros.")
    else:
        print("OK: No se encontraron duplicados en TipoComplemento.")

    print("\n=== DEBUG: Conteo AbastecimientoArticulo por Contrato y Familia ===")
    stats = AbastecimientoArticulo.objects.values(
        'contrato__nombre_contrato', 'familia'
    ).annotate(total=Count('id')).order_by('contrato__nombre_contrato', 'familia')

    for s in stats:
        print(f"Contrato: {s['contrato__nombre_contrato']}, Familia: {s['familia']}, Total: {s['total']}")
        
    print("\n=== DEBUG: Detalles PDD (Drill Bits) ===")
    # Check specifically for PDD regardless of case, or check for similar valid families
    pdd_items = AbastecimientoArticulo.objects.filter(familia='PDD')
    count = pdd_items.count()
    print(f"Total PDD items found: {count}")

    if count > 0:
        print("Muestra de 20 items PDD:")
        for item in pdd_items[:20]:
            contrato_nombre = item.contrato.nombre_contrato if item.contrato else "SIN CONTRATO"
            print(f"- CC_RAW: '{item.centro_costo}', Contrato: {contrato_nombre}, Codigo: {item.codigo}, Desc: {item.descripcion}")
    else:
        print("No se encontraron items con familia='PDD'")
        # Extra check: search for anything with 'broca' in description
        print("Buscando por descripcion 'BROCA'...")
        brocas = AbastecimientoArticulo.objects.filter(descripcion__icontains='BROCA')
        print(f"Total articulos con 'BROCA' en nombre: {brocas.count()}")
        if brocas.count() > 0:
             print("Muestra de Brocas:")
             for b in brocas[:10]:
                 print(f"Familia: {b.familia}, Desc: {b.descripcion}, Contrato: {b.contrato.nombre_contrato}")

if __name__ == "__main__":
    run_debug()
