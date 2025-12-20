#!/usr/bin/env python
"""
Script para asignar actividades a contratos.
Permite asignar todas las actividades o un conjunto específico a uno o varios contratos.
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

from drilling.models import Contrato, TipoActividad, ContratoActividad

def listar_contratos():
    """Lista todos los contratos disponibles"""
    print("\n" + "="*80)
    print("CONTRATOS DISPONIBLES")
    print("="*80)
    
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    
    if not contratos.exists():
        print("❌ No hay contratos activos en el sistema")
        return []
    
    for contrato in contratos:
        actividades_count = contrato.actividades.count()
        print(f"\n📋 ID: {contrato.id} - {contrato.nombre_contrato}")
        print(f"   Cliente: {contrato.cliente.nombre}")
        print(f"   Actividades asignadas: {actividades_count}")
    
    print("\n" + "="*80)
    return list(contratos)

def listar_actividades():
    """Lista todas las actividades disponibles"""
    print("\n" + "="*80)
    print("ACTIVIDADES DISPONIBLES")
    print("="*80)
    
    actividades = TipoActividad.objects.all().order_by('tipo_actividad', 'nombre')
    
    print(f"\n📊 Total actividades: {actividades.count()}\n")
    
    tipos = {
        'OPERATIVO': [],
        'INOPERATIVO': [],
        'STAND_BY_CLIENTE': [],
        'STAND_BY_ROCKDRILL': [],
        'OTROS': []
    }
    
    for act in actividades:
        tipos[act.tipo_actividad].append(act)
    
    for tipo, acts in tipos.items():
        if acts:
            print(f"\n🔹 {tipo} ({len(acts)} actividades):")
            for act in acts:
                cobrable = "💰" if act.es_cobrable else "🔹"
                print(f"   {cobrable} {act.id}: {act.nombre}")
    
    print("\n" + "="*80)
    return list(actividades)

def asignar_todas_actividades_a_contrato(contrato_id):
    """Asigna todas las actividades disponibles a un contrato específico"""
    try:
        contrato = Contrato.objects.get(id=contrato_id)
    except Contrato.DoesNotExist:
        print(f"❌ Error: No existe contrato con ID {contrato_id}")
        return False
    
    print(f"\n🔄 Asignando todas las actividades a: {contrato.nombre_contrato}")
    
    actividades = TipoActividad.objects.all()
    asignadas = 0
    ya_existentes = 0
    
    for actividad in actividades:
        # Usar get_or_create para evitar duplicados
        _, created = ContratoActividad.objects.get_or_create(
            contrato=contrato,
            tipoactividad=actividad
        )
        
        if created:
            asignadas += 1
            print(f"   ✅ Asignada: {actividad.nombre}")
        else:
            ya_existentes += 1
    
    print(f"\n✅ Proceso completado:")
    print(f"   - Nuevas asignaciones: {asignadas}")
    print(f"   - Ya existentes: {ya_existentes}")
    print(f"   - Total actividades del contrato: {contrato.actividades.count()}")
    
    return True

def asignar_todas_actividades_a_todos_contratos():
    """Asigna todas las actividades a todos los contratos activos"""
    contratos = Contrato.objects.filter(estado='ACTIVO')
    actividades = TipoActividad.objects.all()
    
    if not contratos.exists():
        print("❌ No hay contratos activos")
        return
    
    if not actividades.exists():
        print("❌ No hay actividades en el sistema")
        return
    
    print("\n" + "="*80)
    print(f"🚀 Asignando {actividades.count()} actividades a {contratos.count()} contratos")
    print("="*80)
    
    total_asignadas = 0
    total_ya_existentes = 0
    
    for contrato in contratos:
        print(f"\n📋 Procesando: {contrato.nombre_contrato}")
        
        for actividad in actividades:
            _, created = ContratoActividad.objects.get_or_create(
                contrato=contrato,
                tipoactividad=actividad
            )
            
            if created:
                total_asignadas += 1
            else:
                total_ya_existentes += 1
        
        print(f"   ✅ Actividades del contrato: {contrato.actividades.count()}")
    
    print("\n" + "="*80)
    print("✅ RESUMEN GLOBAL")
    print("="*80)
    print(f"   - Contratos procesados: {contratos.count()}")
    print(f"   - Nuevas asignaciones: {total_asignadas}")
    print(f"   - Ya existentes: {total_ya_existentes}")
    print("="*80)

def asignar_actividades_por_tipo(contrato_id, tipo_actividad):
    """Asigna todas las actividades de un tipo específico a un contrato"""
    try:
        contrato = Contrato.objects.get(id=contrato_id)
    except Contrato.DoesNotExist:
        print(f"❌ Error: No existe contrato con ID {contrato_id}")
        return False
    
    tipos_validos = ['OPERATIVO', 'INOPERATIVO', 'STAND_BY_CLIENTE', 'STAND_BY_ROCKDRILL', 'OTROS']
    if tipo_actividad not in tipos_validos:
        print(f"❌ Error: Tipo de actividad inválido. Debe ser uno de: {', '.join(tipos_validos)}")
        return False
    
    print(f"\n🔄 Asignando actividades tipo '{tipo_actividad}' a: {contrato.nombre_contrato}")
    
    actividades = TipoActividad.objects.filter(tipo_actividad=tipo_actividad)
    asignadas = 0
    ya_existentes = 0
    
    for actividad in actividades:
        _, created = ContratoActividad.objects.get_or_create(
            contrato=contrato,
            tipoactividad=actividad
        )
        
        if created:
            asignadas += 1
            print(f"   ✅ Asignada: {actividad.nombre}")
        else:
            ya_existentes += 1
    
    print(f"\n✅ Proceso completado:")
    print(f"   - Nuevas asignaciones: {asignadas}")
    print(f"   - Ya existentes: {ya_existentes}")
    
    return True

def ver_actividades_contrato(contrato_id):
    """Muestra las actividades asignadas a un contrato"""
    try:
        contrato = Contrato.objects.get(id=contrato_id)
    except Contrato.DoesNotExist:
        print(f"❌ Error: No existe contrato con ID {contrato_id}")
        return
    
    print("\n" + "="*80)
    print(f"ACTIVIDADES ASIGNADAS A: {contrato.nombre_contrato}")
    print("="*80)
    
    actividades = contrato.actividades.all().order_by('tipo_actividad', 'nombre')
    
    if not actividades.exists():
        print("\n⚠️ Este contrato no tiene actividades asignadas")
        return
    
    print(f"\n📊 Total: {actividades.count()} actividades\n")
    
    tipos = {}
    for act in actividades:
        if act.tipo_actividad not in tipos:
            tipos[act.tipo_actividad] = []
        tipos[act.tipo_actividad].append(act)
    
    for tipo, acts in tipos.items():
        print(f"\n🔹 {tipo} ({len(acts)}):")
        for act in acts:
            cobrable = "💰 COBRABLE" if act.es_cobrable else "🔹 NO COBRABLE"
            print(f"   • {act.nombre} - {cobrable}")
    
    print("\n" + "="*80)

def menu_principal():
    """Menú interactivo para gestionar asignaciones"""
    while True:
        print("\n" + "="*80)
        print("GESTIÓN DE ACTIVIDADES POR CONTRATO")
        print("="*80)
        print("\n1. Ver contratos disponibles")
        print("2. Ver actividades disponibles")
        print("3. Asignar TODAS las actividades a UN contrato específico")
        print("4. Asignar TODAS las actividades a TODOS los contratos")
        print("5. Asignar actividades por TIPO a un contrato")
        print("6. Ver actividades de un contrato")
        print("7. Salir")
        
        opcion = input("\n👉 Seleccione una opción: ").strip()
        
        if opcion == '1':
            listar_contratos()
        
        elif opcion == '2':
            listar_actividades()
        
        elif opcion == '3':
            listar_contratos()
            contrato_id = input("\n👉 Ingrese ID del contrato: ").strip()
            try:
                asignar_todas_actividades_a_contrato(int(contrato_id))
            except ValueError:
                print("❌ Error: Debe ingresar un número válido")
        
        elif opcion == '4':
            confirmacion = input("\n⚠️ ¿Está seguro de asignar TODAS las actividades a TODOS los contratos? (S/N): ").strip().upper()
            if confirmacion == 'S':
                asignar_todas_actividades_a_todos_contratos()
            else:
                print("❌ Operación cancelada")
        
        elif opcion == '5':
            listar_contratos()
            contrato_id = input("\n👉 Ingrese ID del contrato: ").strip()
            print("\nTipos disponibles:")
            print("  1. OPERATIVO")
            print("  2. INOPERATIVO")
            print("  3. STAND_BY_CLIENTE")
            print("  4. STAND_BY_ROCKDRILL")
            print("  5. OTROS")
            tipo_opcion = input("\n👉 Seleccione tipo (1-5): ").strip()
            
            tipos_map = {
                '1': 'OPERATIVO',
                '2': 'INOPERATIVO',
                '3': 'STAND_BY_CLIENTE',
                '4': 'STAND_BY_ROCKDRILL',
                '5': 'OTROS'
            }
            
            if tipo_opcion in tipos_map:
                try:
                    asignar_actividades_por_tipo(int(contrato_id), tipos_map[tipo_opcion])
                except ValueError:
                    print("❌ Error: Debe ingresar un número válido")
            else:
                print("❌ Opción inválida")
        
        elif opcion == '6':
            listar_contratos()
            contrato_id = input("\n👉 Ingrese ID del contrato: ").strip()
            try:
                ver_actividades_contrato(int(contrato_id))
            except ValueError:
                print("❌ Error: Debe ingresar un número válido")
        
        elif opcion == '7':
            print("\n👋 ¡Hasta luego!")
            break
        
        else:
            print("❌ Opción inválida")

if __name__ == '__main__':
    print("🚀 Iniciando gestor de actividades por contrato...")
    
    # Si se pasa un argumento, asignar a todos los contratos directamente
    if len(sys.argv) > 1 and sys.argv[1] == '--todos':
        asignar_todas_actividades_a_todos_contratos()
    else:
        menu_principal()
