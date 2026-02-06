"""
Script para corregir los códigos de centro de costo de los contratos
según la imagen oficial de almacenes de Vilbragroup.
"""
import os
import sys
import django

# Configurar entorno Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato

def corregir_codigos():
    # Mapeo: Nombre Contrato (parcial) -> Código Correcto (según imagen)
    # NOTA: Usamos strings parciales para buscar porque los nombres en BD pueden variar ligeramente
    CORRECCIONES = [
        ('AMERICANA', '02'),
        ('ANDAYCHAGUA', '03'),
        ('CATALINA', '04'),
        ('CHUNGAR', '06'),
        ('COBRIZA', '07'),
        ('COLQUISIRI', '09'),
        ('CONDESTABLE', '10'),
        ('INMACULADA', '11'),
        ('MOROCOCHA', '12'),
        ('RAURA', '13'),
        ('ROMINA', '14'),
        ('SAN CRISTOBAL', '15'),
        ('YAULIYACU', '16'),
        ('CUCULI', '17'),
        ('ESTRELLA', '18'),
        ('COLQUIJIRCA', '19'),
        ('TICLIO', '23'),
        ('CERRO DE PASCO', '25'),
    ]

    print("Iniciando corrección de códigos de almacén...")
    
    # 1. Caso especial: Sistema Principal
    try:
        # Sistema Principal usualmente es 01
        principal = Contrato.objects.filter(nombre_contrato__icontains='Sistema Principal').first()
        if principal:
            print(f"Actualizando {principal.nombre_contrato}: Almacen -> 01")
            principal.codigo_almacen = '01'
            principal.save()
    except Exception as e:
        print(f"Error procesando Sistema Principal: {e}")

    # 2. Iterar contratos comunes
    for keyword, nuevo_codigo in CORRECCIONES:
        # Buscar contratos que contengan la palabra clave
        matches = Contrato.objects.filter(nombre_contrato__icontains=keyword)
        
        for contrato in matches:
            if contrato.codigo_almacen != nuevo_codigo:
                print(f"Actualizando {contrato.nombre_contrato}: Almacen {contrato.codigo_almacen or 'VACIO'} -> {nuevo_codigo} (CC se mantiene en {contrato.codigo_centro_costo})")
                contrato.codigo_almacen = nuevo_codigo
                contrato.save()
            else:
                print(f"OK: {contrato.nombre_contrato} ya tiene Almacen {nuevo_codigo}")

    print("\nVerificación final:")
    for c in Contrato.objects.exclude(codigo_almacen='').exclude(codigo_almacen__isnull=True):
        print(f"- {c.nombre_contrato}: CC={c.codigo_centro_costo}, Almacen={c.codigo_almacen}")

if __name__ == '__main__':
    corregir_codigos()
