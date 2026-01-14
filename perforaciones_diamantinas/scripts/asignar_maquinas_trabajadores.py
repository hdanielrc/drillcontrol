"""
Script para asignar máquinas automáticamente a trabajadores perforistas y ayudantes
que actualmente no tienen máquina asignada.
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador
from django.db.models import Count


def asignar_maquinas_faltantes():
    """
    Asigna máquinas a trabajadores que deberían tenerla pero no la tienen.
    """
    # Buscar trabajadores activos sin máquina asignada
    trabajadores_sin_maquina = Trabajador.objects.filter(
        estado='ACTIVO',
        maquina_asignada__isnull=True,
        cargo__isnull=False
    ).select_related('cargo', 'contrato')
    
    print(f"📋 Encontrados {trabajadores_sin_maquina.count()} trabajadores sin máquina asignada")
    print("=" * 80)
    
    asignados = 0
    no_aplica = 0
    sin_maquinas = 0
    
    for trabajador in trabajadores_sin_maquina:
        cargo_nombre = trabajador.cargo.nombre.upper()
        
        # Verificar si debería tener máquina (perforistas/ayudantes)
        if any(keyword in cargo_nombre for keyword in ['PERFORISTA', 'AYUDANTE']):
            # Intentar asignar máquina
            maquina = trabajador.asignar_maquina_por_defecto()
            
            if maquina:
                trabajador.maquina_asignada = maquina
                trabajador.save()
                asignados += 1
                print(f"✅ {trabajador.apellidos}, {trabajador.nombres}")
                print(f"   Cargo: {trabajador.cargo.nombre}")
                print(f"   Máquina asignada: {maquina.nombre} ({maquina.codigo})")
                print(f"   Contrato: {trabajador.contrato.nombre_contrato}")
                print()
            else:
                sin_maquinas += 1
                print(f"⚠️  {trabajador.apellidos}, {trabajador.nombres}")
                print(f"   Cargo: {trabajador.cargo.nombre}")
                print(f"   ❌ No hay máquinas disponibles en el contrato {trabajador.contrato.nombre_contrato}")
                print()
        else:
            no_aplica += 1
    
    print("=" * 80)
    print(f"📊 RESUMEN:")
    print(f"   ✅ Máquinas asignadas: {asignados}")
    print(f"   ⚠️  Sin máquinas disponibles: {sin_maquinas}")
    print(f"   ℹ️  No aplica (otros cargos): {no_aplica}")
    print(f"   📋 Total procesados: {trabajadores_sin_maquina.count()}")
    
    return asignados


def mostrar_estadisticas():
    """
    Muestra estadísticas de asignación de máquinas
    """
    from drilling.models import Maquina
    
    print("\n" + "=" * 80)
    print("📊 ESTADÍSTICAS DE MÁQUINAS")
    print("=" * 80)
    
    total_trabajadores = Trabajador.objects.filter(estado='ACTIVO').count()
    con_maquina = Trabajador.objects.filter(estado='ACTIVO', maquina_asignada__isnull=False).count()
    sin_maquina = total_trabajadores - con_maquina
    
    print(f"\n👷 TRABAJADORES ACTIVOS:")
    print(f"   Total: {total_trabajadores}")
    print(f"   Con máquina asignada: {con_maquina}")
    print(f"   Sin máquina: {sin_maquina}")
    
    # Perforistas y ayudantes
    perforistas_ayudantes = Trabajador.objects.filter(
        estado='ACTIVO',
        cargo__nombre__iregex=r'(perforist|ayudante)'
    )
    total_operadores = perforistas_ayudantes.count()
    operadores_con_maquina = perforistas_ayudantes.filter(maquina_asignada__isnull=False).count()
    
    print(f"\n🔧 PERFORISTAS Y AYUDANTES:")
    print(f"   Total: {total_operadores}")
    print(f"   Con máquina: {operadores_con_maquina}")
    print(f"   Sin máquina: {total_operadores - operadores_con_maquina}")
    
    # Máquinas por contrato
    print(f"\n🏭 MÁQUINAS POR CONTRATO:")
    maquinas = Maquina.objects.filter(estado='OPERATIVO').select_related('contrato').annotate(
        num_trabajadores=Count('trabajadores_asignados')
    )
    
    for maquina in maquinas:
        print(f"   {maquina.nombre} ({maquina.codigo}) - {maquina.contrato.nombre_contrato}")
        print(f"      Trabajadores asignados: {maquina.num_trabajadores}")


if __name__ == '__main__':
    print("🚀 INICIANDO ASIGNACIÓN DE MÁQUINAS A TRABAJADORES")
    print("=" * 80)
    print()
    
    # Mostrar estadísticas antes
    mostrar_estadisticas()
    
    print("\n" + "=" * 80)
    input("Presione ENTER para continuar con la asignación...")
    print()
    
    # Realizar asignación
    asignados = asignar_maquinas_faltantes()
    
    # Mostrar estadísticas después
    if asignados > 0:
        mostrar_estadisticas()
    
    print("\n✅ Proceso completado")
