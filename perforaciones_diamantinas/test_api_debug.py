"""
Script de debug para probar la conexión con la API de Vilbragroup
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.conf import settings
from drilling.api_client import get_api_client
from drilling.models import Contrato

print("\n" + "="*70)
print("DEBUG - CONFIGURACIÓN DE API")
print("="*70 + "\n")

# Verificar configuración
print("1. CONFIGURACIÓN EN SETTINGS:")
print(f"   VILBRAGROUP_API_TOKEN: {'Configurado' if hasattr(settings, 'VILBRAGROUP_API_TOKEN') and settings.VILBRAGROUP_API_TOKEN else 'NO CONFIGURADO'}")
if hasattr(settings, 'VILBRAGROUP_API_TOKEN') and settings.VILBRAGROUP_API_TOKEN:
    token = settings.VILBRAGROUP_API_TOKEN
    print(f"   Token (primeros 10 chars): {token[:10]}...")
print(f"   CENTRO_COSTO_DEFAULT: {getattr(settings, 'CENTRO_COSTO_DEFAULT', 'NO CONFIGURADO')}")

# Verificar contrato CONDESTABLE
print("\n2. CONTRATO CONDESTABLE:")
try:
    contrato = Contrato.objects.get(nombre_contrato__icontains='CONDESTABLE')
    print(f"   ✓ Encontrado: {contrato.nombre_contrato}")
    print(f"   ID: {contrato.id}")
    print(f"   Cliente: {contrato.cliente.nombre}")
    print(f"   Código Centro Costo: {contrato.codigo_centro_costo or 'NO CONFIGURADO'}")
except Contrato.DoesNotExist:
    print("   ✗ No se encontró el contrato")
    contrato = None
except Contrato.MultipleObjectsReturned:
    print("   ✗ Múltiples contratos encontrados")
    contrato = None

if contrato and contrato.codigo_centro_costo:
    print("\n3. PROBANDO CONEXIÓN CON API:")
    print(f"   URL Base: https://tic.vilbragroup.net/API/DrillControl")
    print(f"   Centro Costo: {contrato.codigo_centro_costo}")
    
    # Probar API
    api_client = get_api_client()
    
    print("\n   a) Probando endpoint de PDD...")
    try:
        productos = api_client.obtener_productos_diamantados(contrato.codigo_centro_costo)
        print(f"      Respuesta: {len(productos)} productos")
        if productos:
            print(f"\n      Primeros 3 productos:")
            for i, p in enumerate(productos[:3], 1):
                print(f"      {i}. Código: {p.get('codigo', 'N/A')}")
                print(f"         Serie: {p.get('serie', 'N/A')}")
                print(f"         Descripción: {p.get('descripcion', 'N/A')[:60]}")
                print()
        else:
            print("      ⚠ No se obtuvieron productos (lista vacía)")
    except Exception as e:
        print(f"      ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n   b) Probando endpoint de ADIT...")
    try:
        aditivos = api_client.obtener_aditivos(contrato.codigo_centro_costo)
        print(f"      Respuesta: {len(aditivos)} aditivos")
        if aditivos:
            print(f"\n      Primeros 3 aditivos:")
            for i, a in enumerate(aditivos[:3], 1):
                print(f"      {i}. Código: {a.get('codigo', 'N/A')}")
                print(f"         Descripción: {a.get('descripcion', 'N/A')[:60]}")
                print()
        else:
            print("      ⚠ No se obtuvieron aditivos (lista vacía)")
    except Exception as e:
        print(f"      ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n4. DIAGNÓSTICO:")
    if not hasattr(settings, 'VILBRAGROUP_API_TOKEN') or not settings.VILBRAGROUP_API_TOKEN:
        print("   ✗ Falta configurar VILBRAGROUP_API_TOKEN en settings.py")
        print("   Agrega en settings.py:")
        print("   VILBRAGROUP_API_TOKEN = 'tu_token_aqui'")
    
    if not contrato.codigo_centro_costo:
        print("   ✗ El contrato no tiene código de centro de costo")
        print(f"   Edita el contrato {contrato.nombre_contrato} y agrega el código")

print("\n" + "="*70 + "\n")
