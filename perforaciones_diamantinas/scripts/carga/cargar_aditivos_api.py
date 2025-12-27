#!/usr/bin/env python
"""
Script para cargar aditivos (ADIT) desde la API de Vilbragroup a la base de datos.
Sincroniza los aditivos disponibles en la API con la tabla TipoAditivo.
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

from drilling.models import Contrato, TipoAditivo, UnidadMedida
from drilling.api_client import VilbragroupAPIClient

def cargar_aditivos_desde_api():
    """
    Carga todos los aditivos desde la API de Vilbragroup a TipoAditivo.
    """
    
    print("\n" + "="*80)
    print("CARGA DE ADITIVOS DESDE API VILBRAGROUP")
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
    
    # Crear cliente API
    api_client = VilbragroupAPIClient()
    
    # Obtener aditivos de la API
    print(f"\n📡 Consultando API para CC: {contrato.codigo_centro_costo}...")
    aditivos = api_client.obtener_aditivos(contrato.codigo_centro_costo)
    
    if not aditivos:
        print("\n⚠️ No se encontraron aditivos en la API o hubo un error")
        return
    
    print(f"✅ Se encontraron {len(aditivos)} aditivos en la API\n")
    
    # Procesar aditivos en memoria para eliminar duplicados
    print("Procesando aditivos y eliminando duplicados...")
    print("-" * 80)
    
    aditivos_unicos = {}
    duplicados = 0
    sin_codigo = 0
    
    # Mapeo de palabras clave a categorías
    categorias_map = {
        'BENTONITA': 'BENTONITA',
        'POLIMERO': 'POLIMEROS',
        'CMC': 'CMC',
        'SODA': 'SODA_ASH',
        'DISPERSANTE': 'DISPERSANTE',
        'LUBRICANTE': 'LUBRICANTE',
        'ESPUMANTE': 'ESPUMANTE',
    }
    
    for prod in aditivos:
        codigo = (prod.get('codigo') or '').strip()
        serie = (prod.get('serie') or '').strip()
        descripcion = (prod.get('descripcion') or 'Sin descripción').strip()
        
        # Usar codigo como clave principal para aditivos
        clave = codigo if codigo else serie
        
        if not clave:
            sin_codigo += 1
            continue
        
        # Si ya existe este codigo, es un duplicado
        if clave in aditivos_unicos:
            duplicados += 1
            continue
        
        # Intentar detectar la categoría por el nombre
        categoria = None
        descripcion_upper = descripcion.upper()
        for keyword, cat in categorias_map.items():
            if keyword in descripcion_upper:
                categoria = cat
                break
        
        aditivos_unicos[clave] = {
            'codigo': codigo if codigo else None,
            'serie': serie if serie else None,
            'descripcion': descripcion,
            'nombre': descripcion[:100],
            'categoria': categoria
        }
    
    print(f"✓ Aditivos únicos: {len(aditivos_unicos)}")
    print(f"⚠️  Duplicados eliminados: {duplicados}")
    print(f"⚠️  Sin código: {sin_codigo}")
    print()
    
    # Obtener códigos ya existentes en BD
    codigos_existentes = set(
        TipoAditivo.objects.filter(
            codigo__in=[k for k in aditivos_unicos.keys() if k]
        ).values_list('codigo', flat=True)
    )
    
    print(f"📊 Aditivos ya en BD: {len(codigos_existentes)}")
    print(f"📊 Aditivos nuevos a crear: {len(aditivos_unicos) - len(codigos_existentes)}")
    print()
    
    # Preparar objetos para bulk_create
    objetos_crear = []
    objetos_actualizar = []
    
    for codigo, datos in aditivos_unicos.items():
        if codigo in codigos_existentes:
            # Actualizar existentes
            objetos_actualizar.append(codigo)
        else:
            # Crear nuevos
            objetos_crear.append(
                TipoAditivo(
                    codigo=datos['codigo'],
                    nombre=datos['nombre'],
                    descripcion=datos['descripcion'],
                    categoria=datos['categoria'],
                    contrato=contrato
                )
            )
    
    # Crear nuevos aditivos en lote
    creados = 0
    if objetos_crear:
        print(f"Creando {len(objetos_crear)} aditivos nuevos...")
        try:
            TipoAditivo.objects.bulk_create(objetos_crear, batch_size=100)
            creados = len(objetos_crear)
            print(f"✅ {creados} aditivos creados exitosamente")
        except Exception as e:
            print(f"❌ Error al crear aditivos: {e}")
    
    # Actualizar aditivos existentes
    actualizados = 0
    errores = 0
    if objetos_actualizar:
        print(f"\nActualizando {len(objetos_actualizar)} aditivos existentes...")
        for codigo in objetos_actualizar:
            try:
                datos = aditivos_unicos[codigo]
                TipoAditivo.objects.filter(codigo=codigo).update(
                    nombre=datos['nombre'],
                    descripcion=datos['descripcion'],
                    categoria=datos['categoria'],
                    contrato=contrato
                )
                actualizados += 1
            except Exception as e:
                errores += 1
                print(f"❌ Error al actualizar {codigo}: {e}")
        print(f"✅ {actualizados} aditivos actualizados")
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE LA CARGA")
    print("="*80)
    print(f"Total aditivos en API:     {len(aditivos)}")
    print(f"Aditivos únicos:           {len(aditivos_unicos)}")
    print(f"✓ Aditivos creados:        {creados}")
    print(f"↻ Aditivos actualizados:   {actualizados}")
    print(f"❌ Errores:                 {errores}")
    print(f"⚠️  Duplicados ignorados:   {duplicados}")
    print(f"⚠️  Sin código:             {sin_codigo}")
    print("="*80)
    
    # Verificar total en BD
    total_bd = TipoAditivo.objects.filter(contrato=contrato).count()
    print(f"\nTotal de aditivos en BD para {contrato.nombre_contrato}: {total_bd}")
    
    print("\n✅ Proceso completado!")
    print("\nAhora el formulario de turnos mostrará los aditivos disponibles")
    print("en el combobox de la sección de aditivos.")

if __name__ == '__main__':
    cargar_aditivos_desde_api()
