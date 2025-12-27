#!/usr/bin/env python
"""
Script para cargar productos diamantados (PDD) desde la API de Vilbragroup a la base de datos.
Sincroniza los productos disponibles en la API con la tabla TipoComplemento.
"""
import os
import sys
import django
from pathlib import Path
from decimal import Decimal

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato, TipoComplemento, UnidadMedida
from drilling.api_client import VilbragroupAPIClient
from django.db import transaction
from collections import defaultdict

def cargar_productos_desde_api():
    """
    Carga todos los productos diamantados desde la API de Vilbragroup a TipoComplemento.
    Utiliza update_or_create para evitar duplicados basándose en la serie.
    """
    
    print("\n" + "="*80)
    print("CARGA DE PRODUCTOS DIAMANTADOS DESDE API VILBRAGROUP")
    print("="*80)
    
    # Buscar contrato de Colquisiri
    try:
        contrato = Contrato.objects.get(nombre_contrato__icontains='COLQUISIRI')
    except Contrato.DoesNotExist:
        print("❌ Error: No se encontró el contrato COLQUISIRI")
        return
    except Contrato.MultipleObjectsReturned:
        print("⚠️ Se encontraron múltiples contratos con 'COLQUISIRI', usando el primero...")
        contrato = Contrato.objects.filter(nombre_contrato__icontains='COLQUISIRI').first()
    
    print(f"\nContrato: {contrato.nombre_contrato}")
    print(f"Cliente: {contrato.cliente.nombre}")
    print(f"Centro de Costo: {contrato.codigo_centro_costo}")
    
    if not contrato.codigo_centro_costo:
        print("\n❌ Error: El contrato no tiene código de centro de costo configurado")
        return
    
    # Obtener unidad de medida por defecto (UND)
    unidad_und, created = UnidadMedida.objects.get_or_create(
        simbolo='UND',
        defaults={'nombre': 'Unidad'}
    )
    if created:
        print(f"✓ Creada unidad de medida: {unidad_und.nombre}")
    
    # Crear cliente API
    api_client = VilbragroupAPIClient()
    
    # Obtener productos de la API
    print(f"\n📡 Consultando API para CC: {contrato.codigo_centro_costo}...")
    productos = api_client.obtener_productos_diamantados(contrato.codigo_centro_costo)
    
    if not productos:
        print("\n⚠️ No se encontraron productos en la API o hubo un error")
        return
    
    print(f"✅ Se encontraron {len(productos)} productos en la API\n")
    
    # Procesar productos en memoria primero para eliminar duplicados
    print("Procesando productos y eliminando duplicados...")
    print("-" * 80)
    
    productos_unicos = {}
    duplicados = 0
    sin_serie = 0
    
    for prod in productos:
        codigo = prod.get('codigo', '').strip()
        serie = prod.get('serie', '').strip()
        descripcion = prod.get('descripcion', 'Sin descripción').strip()
        
        if not serie:
            sin_serie += 1
            continue
        
        # Si ya existe esta serie, es un duplicado
        if serie in productos_unicos:
            duplicados += 1
            continue
        
        productos_unicos[serie] = {
            'codigo': codigo if codigo else None,
            'serie': serie,
            'descripcion': descripcion,
            'nombre': descripcion[:100]
        }
    
    print(f"✓ Productos únicos: {len(productos_unicos)}")
    print(f"⚠️  Duplicados eliminados: {duplicados}")
    print(f"⚠️  Sin serie: {sin_serie}")
    print()
    
    # Obtener series ya existentes en BD
    series_existentes = set(
        TipoComplemento.objects.filter(
            serie__in=productos_unicos.keys()
        ).values_list('serie', flat=True)
    )
    
    print(f"📊 Productos ya en BD: {len(series_existentes)}")
    print(f"📊 Productos nuevos a crear: {len(productos_unicos) - len(series_existentes)}")
    print()
    
    # Preparar objetos para bulk_create
    objetos_crear = []
    objetos_actualizar = []
    
    for serie, datos in productos_unicos.items():
        if serie in series_existentes:
            # Actualizar existentes
            objetos_actualizar.append(serie)
        else:
            # Crear nuevos
            objetos_crear.append(
                TipoComplemento(
                    serie=datos['serie'],
                    codigo=datos['codigo'],
                    nombre=datos['nombre'],
                    descripcion=datos['descripcion'],
                    categoria='BROCA',
                    estado='NUEVO',
                    contrato=contrato
                )
            )
    
    # Crear nuevos productos en lote
    creados = 0
    if objetos_crear:
        print(f"Creando {len(objetos_crear)} productos nuevos...")
        try:
            TipoComplemento.objects.bulk_create(objetos_crear, batch_size=100)
            creados = len(objetos_crear)
            print(f"✅ {creados} productos creados exitosamente")
        except Exception as e:
            print(f"❌ Error al crear productos: {e}")
    
    # Actualizar productos existentes
    actualizados = 0
    errores = 0
    if objetos_actualizar:
        print(f"\nActualizando {len(objetos_actualizar)} productos existentes...")
        for serie in objetos_actualizar:
            try:
                datos = productos_unicos[serie]
                TipoComplemento.objects.filter(serie=serie).update(
                    codigo=datos['codigo'],
                    nombre=datos['nombre'],
                    descripcion=datos['descripcion'],
                    contrato=contrato
                )
                actualizados += 1
            except Exception as e:
                errores += 1
                print(f"❌ Error al actualizar {serie}: {e}")
        print(f"✅ {actualizados} productos actualizados")
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE LA CARGA")
    print("="*80)
    print(f"Total productos en API:    {len(productos)}")
    print(f"Productos únicos:          {len(productos_unicos)}")
    print(f"✓ Productos creados:       {creados}")
    print(f"↻ Productos actualizados:  {actualizados}")
    print(f"❌ Errores:                 {errores}")
    print(f"⚠️  Duplicados ignorados:   {duplicados}")
    print(f"⚠️  Sin serie:              {sin_serie}")
    print("="*80)
    
    # Verificar total en BD
    total_bd = TipoComplemento.objects.count()
    print(f"\nTotal de productos en BD:  {total_bd}")
    
    print("\n✅ Proceso completado!")
    print("\nAhora el formulario de turnos podrá autocompletar las descripciones")
    print("al ingresar los códigos/series de los productos diamantados.")

def verificar_codigo_especifico(codigo):
    """Verifica que un código específico esté cargado"""
    print(f"\n{'='*80}")
    print(f"VERIFICACIÓN DEL CÓDIGO: {codigo}")
    print(f"{'='*80}")
    
    try:
        producto = TipoComplemento.objects.get(serie=codigo)
        print(f"✅ Producto encontrado en la BD:")
        print(f"   ID: {producto.id}")
        print(f"   Serie: {producto.serie}")
        print(f"   Código: {producto.codigo}")
        print(f"   Nombre: {producto.nombre}")
        print(f"   Descripción: {producto.descripcion}")
        print(f"   Estado: {producto.estado}")
        print(f"   Categoría: {producto.categoria}")
    except TipoComplemento.DoesNotExist:
        print(f"❌ El código {codigo} NO está en la base de datos")
    except TipoComplemento.MultipleObjectsReturned:
        print(f"⚠️  Se encontraron múltiples productos con la serie {codigo}")
        productos = TipoComplemento.objects.filter(serie=codigo)
        for p in productos:
            print(f"   - ID {p.id}: {p.nombre}")

if __name__ == '__main__':
    # Cargar productos desde API
    cargar_productos_desde_api()
    
    # Verificar el código específico que reportó el usuario
    verificar_codigo_especifico('409381')
