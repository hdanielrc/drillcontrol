import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from drilling.models import TipoAditivo, Contrato

print("="*80)
print("VERIFICACIÓN DE ADITIVOS CARGADOS")
print("="*80)

contrato = Contrato.objects.filter(nombre_contrato__icontains='COLQUISIRI').first()
if contrato:
    aditivos = TipoAditivo.objects.filter(contrato=contrato)
    print(f"\nContrato: {contrato.nombre_contrato}")
    print(f"Total aditivos: {aditivos.count()}\n")
    
    print("📋 Aditivos cargados:")
    for aditivo in aditivos:
        categoria = aditivo.categoria if aditivo.categoria else "Sin categoría"
        print(f"   {aditivo.codigo or 'Sin código'} - {aditivo.nombre[:60]} ({categoria})")
else:
    print("\n❌ No se encontró el contrato COLQUISIRI")
