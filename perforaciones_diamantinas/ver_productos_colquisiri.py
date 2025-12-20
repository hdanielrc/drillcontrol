#!/usr/bin/env python
"""
Script para consultar y mostrar los productos diamantados (PDD) disponibles en Colquisiri
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

from drilling.models import Contrato
from drilling.api_client import VilbragroupAPIClient

def obtener_productos_colquisiri():
    """Obtiene y muestra los productos diamantados de Colquisiri"""
    
    # Buscar el contrato de Colquisiri
    try:
        contrato = Contrato.objects.get(nombre_contrato__icontains='COLQUISIRI')
    except Contrato.DoesNotExist:
        print("❌ Error: No se encontró el contrato COLQUISIRI")
        return
    except Contrato.MultipleObjectsReturned:
        print("⚠️ Se encontraron múltiples contratos con 'COLQUISIRI', usando el primero...")
        contrato = Contrato.objects.filter(nombre_contrato__icontains='COLQUISIRI').first()
    
    print("\n" + "="*80)
    print(f"PRODUCTOS DIAMANTADOS (PDD) - {contrato.nombre_contrato}")
    print("="*80)
    print(f"Cliente: {contrato.cliente.nombre}")
    print(f"Centro de Costo: {contrato.codigo_centro_costo}")
    print("="*80)
    
    if not contrato.codigo_centro_costo:
        print("\n❌ Error: El contrato no tiene código de centro de costo configurado")
        return
    
    # Crear cliente API
    api_client = VilbragroupAPIClient()
    
    # Obtener productos diamantados
    print(f"\n📦 Consultando productos diamantados (PDD) para CC: {contrato.codigo_centro_costo}...")
    
    productos = api_client.obtener_productos_diamantados(contrato.codigo_centro_costo)
    
    if not productos:
        print("\n⚠️ No se encontraron productos diamantados o hubo un error en la consulta")
        return
    
    print(f"\n✅ Se encontraron {len(productos)} productos\n")
    
    # Agrupar por familia
    productos_por_familia = {}
    for prod in productos:
        familia = prod.get('familia', 'SIN FAMILIA')
        if familia not in productos_por_familia:
            productos_por_familia[familia] = []
        productos_por_familia[familia].append(prod)
    
    # Mostrar productos agrupados por familia
    for familia, items in sorted(productos_por_familia.items()):
        print(f"\n{'='*80}")
        print(f"📋 FAMILIA: {familia} ({len(items)} productos)")
        print(f"{'='*80}")
        
        for i, prod in enumerate(items, 1):
            print(f"\n{i}. {prod.get('descripcion', 'Sin descripción')}")
            print(f"   Código: {prod.get('codigo_producto', 'N/A')}")
            print(f"   Serie: {prod.get('serie', 'N/A')}")
            print(f"   Stock: {prod.get('cantidad', 0)} {prod.get('unidad_medida', '')}")
            
            if prod.get('precio_unitario'):
                print(f"   Precio Unit: ${prod.get('precio_unitario', 0):,.2f}")
                total = float(prod.get('cantidad', 0)) * float(prod.get('precio_unitario', 0))
                print(f"   Total: ${total:,.2f}")
    
    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    for familia, items in sorted(productos_por_familia.items()):
        print(f"  {familia}: {len(items)} productos")
    print(f"\n  TOTAL: {len(productos)} productos")
    print("="*80)
    
    # Guardar en archivo CSV
    guardar = input("\n¿Desea guardar los resultados en un archivo CSV? (S/N): ").strip().upper()
    if guardar == 'S':
        import csv
        from datetime import datetime
        
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stock_pdd_colquisiri_{fecha_hora}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'familia', 'codigo_producto', 'descripcion', 'serie', 
                'cantidad', 'unidad_medida', 'precio_unitario', 'total'
            ], delimiter=';')
            
            writer.writeheader()
            
            for prod in productos:
                cantidad = float(prod.get('cantidad', 0))
                precio = float(prod.get('precio_unitario', 0))
                total = cantidad * precio
                
                writer.writerow({
                    'familia': prod.get('familia', ''),
                    'codigo_producto': prod.get('codigo_producto', ''),
                    'descripcion': prod.get('descripcion', ''),
                    'serie': prod.get('serie', ''),
                    'cantidad': cantidad,
                    'unidad_medida': prod.get('unidad_medida', ''),
                    'precio_unitario': precio,
                    'total': total
                })
        
        print(f"\n✅ Archivo guardado: {filename}")

if __name__ == '__main__':
    print("🚀 Consultando productos diamantados de Colquisiri...")
    obtener_productos_colquisiri()
