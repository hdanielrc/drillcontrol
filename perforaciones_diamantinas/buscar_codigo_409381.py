#!/usr/bin/env python
"""
Script para buscar el código 409381 en la API y en la base de datos
"""
import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato, TipoComplemento
from drilling.api_client import VilbragroupAPIClient

def buscar_codigo():
    """Busca el código 409381 en API y BD"""
    
    codigo_buscado = "409381"
    
    print("\n" + "="*80)
    print(f"BÚSQUEDA DEL CÓDIGO: {codigo_buscado}")
    print("="*80)
    
    # 1. Buscar en la base de datos (TipoComplemento)
    print("\n1. BÚSQUEDA EN BASE DE DATOS (TipoComplemento)")
    print("-" * 80)
    
    # Buscar por serie
    complementos_serie = TipoComplemento.objects.filter(serie__icontains=codigo_buscado)
    print(f"\nBúsqueda por campo 'serie': {complementos_serie.count()} resultados")
    for comp in complementos_serie:
        print(f"  ✓ ID: {comp.id}")
        print(f"    Serie: {comp.serie}")
        print(f"    Nombre: {comp.nombre}")
        print(f"    Descripción: {comp.descripcion or 'N/A'}")
        print()
    
    # Buscar por nombre o descripción
    complementos_texto = TipoComplemento.objects.filter(
        nombre__icontains=codigo_buscado
    ) | TipoComplemento.objects.filter(
        descripcion__icontains=codigo_buscado
    )
    if complementos_texto.count() > 0:
        print(f"Búsqueda por nombre/descripción: {complementos_texto.count()} resultados")
        for comp in complementos_texto:
            print(f"  ✓ Serie: {comp.serie}, Nombre: {comp.nombre}")
    
    # 2. Buscar en la API de Colquisiri
    print("\n2. BÚSQUEDA EN API VILBRAGROUP (Colquisiri)")
    print("-" * 80)
    
    try:
        contrato = Contrato.objects.get(nombre_contrato__icontains='COLQUISIRI')
        print(f"Contrato: {contrato.nombre_contrato}")
        print(f"Centro de Costo: {contrato.codigo_centro_costo}")
        
        api_client = VilbragroupAPIClient()
        productos = api_client.obtener_productos_diamantados(contrato.codigo_centro_costo)
        
        print(f"\nTotal productos en API: {len(productos) if productos else 0}")
        
        if productos:
            # Buscar el código en los productos
            encontrados = []
            for prod in productos:
                # Buscar en serie, código_producto o descripción
                serie = str(prod.get('serie', ''))
                codigo = str(prod.get('codigo_producto', ''))
                descripcion = str(prod.get('descripcion', ''))
                
                if (codigo_buscado in serie or 
                    codigo_buscado in codigo or 
                    codigo_buscado in descripcion):
                    encontrados.append(prod)
            
            if encontrados:
                print(f"\n✅ ENCONTRADO {len(encontrados)} producto(s) en la API:")
                for prod in encontrados:
                    print(f"\n  📦 Producto:")
                    print(f"     Serie: {prod.get('serie', 'N/A')}")
                    print(f"     Código: {prod.get('codigo_producto', 'N/A')}")
                    print(f"     Descripción: {prod.get('descripcion', 'Sin descripción')}")
                    print(f"     Familia: {prod.get('familia', 'N/A')}")
                    print(f"     Stock: {prod.get('cantidad', 0)}")
                    print(f"     Unidad: {prod.get('unidad_medida', 'N/A')}")
            else:
                print(f"\n❌ No se encontró el código {codigo_buscado} en la API")
                print("\nMostrando primeros 5 productos para verificar estructura:")
                for i, prod in enumerate(productos[:5], 1):
                    print(f"\n  {i}. Serie: {prod.get('serie', 'N/A')}")
                    print(f"     Descripción: {prod.get('descripcion', 'N/A')[:80]}")
    
    except Contrato.DoesNotExist:
        print("❌ No se encontró el contrato COLQUISIRI")
    except Exception as e:
        print(f"❌ Error al consultar API: {e}")
    
    print("\n" + "="*80)
    print("CONCLUSIÓN Y RECOMENDACIONES:")
    print("="*80)
    print("""
Si el código NO está en la BD pero SÍ en la API:
  → El producto debe cargarse primero en TipoComplemento
  → Usar un script de carga masiva desde la API
  
Si el código está en la BD:
  → Verificar que el campo 'serie' coincida exactamente
  → El JavaScript busca coincidencia exacta (case-insensitive)
  
Si el código NO está en ningún lado:
  → Verificar que el código sea correcto
  → Puede ser un producto de otro contrato
    """)

if __name__ == '__main__':
    buscar_codigo()
