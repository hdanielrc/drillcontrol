"""
Script para marcar/desmarcar trabajadores como personal STANDBY (reserva)

El personal STANDBY:
- NO se asigna a guardias fijas (A, B, C)
- Sirve para cubrir ausencias y emergencias
- Tiene mayor flexibilidad operativa

Uso:
    python manage.py shell < scripts/marcar_personal_standby.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador, Contrato


def marcar_standby_por_dni(dnis_list, es_standby=True):
    """
    Marca trabajadores como STANDBY por su DNI
    
    Args:
        dnis_list: Lista de DNIs
        es_standby: True para marcar como STANDBY, False para desmarcar
    """
    actualizados = 0
    no_encontrados = []
    
    for dni in dnis_list:
        try:
            trabajador = Trabajador.objects.get(dni=dni, estado='ACTIVO')
            trabajador.es_standby = es_standby
            # Si se marca como STANDBY, limpiar guardia asignada
            if es_standby:
                trabajador.guardia_asignada = None
            trabajador.save()
            
            estado = "STANDBY" if es_standby else "REGULAR"
            print(f"✓ {trabajador.apellidos}, {trabajador.nombres} ({dni}) → {estado}")
            actualizados += 1
            
        except Trabajador.DoesNotExist:
            print(f"✗ DNI {dni} no encontrado o no está activo")
            no_encontrados.append(dni)
    
    print(f"\n{'='*60}")
    print(f"Resumen:")
    print(f"  - Actualizados: {actualizados}")
    print(f"  - No encontrados: {len(no_encontrados)}")
    if no_encontrados:
        print(f"  - DNIs no encontrados: {', '.join(no_encontrados)}")
    print(f"{'='*60}\n")
    
    return actualizados


def listar_personal_standby(contrato_nombre=None):
    """
    Lista todo el personal marcado como STANDBY
    
    Args:
        contrato_nombre: Nombre del contrato (opcional, None = todos)
    """
    filtro = {'es_standby': True, 'estado': 'ACTIVO'}
    
    if contrato_nombre:
        filtro['contrato__nombre_contrato__icontains'] = contrato_nombre
    
    trabajadores = Trabajador.objects.filter(**filtro).select_related('cargo', 'contrato')
    
    if not trabajadores.exists():
        print("No hay personal STANDBY registrado")
        return
    
    print(f"\n{'='*80}")
    print(f"PERSONAL STANDBY (RESERVA)")
    print(f"{'='*80}")
    print(f"{'NOMBRE':<35} {'DNI':<12} {'CARGO':<25} {'CONTRATO':<20}")
    print(f"{'-'*80}")
    
    for t in trabajadores:
        nombre_completo = f"{t.apellidos}, {t.nombres}"[:34]
        cargo = t.cargo.nombre[:24]
        contrato = t.contrato.nombre_contrato[:19]
        print(f"{nombre_completo:<35} {t.dni:<12} {cargo:<25} {contrato:<20}")
    
    print(f"{'-'*80}")
    print(f"Total: {trabajadores.count()} trabajadores STANDBY")
    print(f"{'='*80}\n")


def sugerir_personal_standby(contrato_nombre):
    """
    Sugiere trabajadores que podrían ser STANDBY basándose en:
    - Exceso de personal del mismo cargo
    - Trabajadores sin máquina asignada
    """
    try:
        contrato = Contrato.objects.get(nombre_contrato__icontains=contrato_nombre)
    except Contrato.DoesNotExist:
        print(f"✗ Contrato '{contrato_nombre}' no encontrado")
        return
    
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO',
        es_standby=False
    ).select_related('cargo')
    
    # Contar por cargo
    from collections import Counter
    cargos_count = Counter([t.cargo.nombre for t in trabajadores])
    
    print(f"\n{'='*80}")
    print(f"ANÁLISIS DE PERSONAL - {contrato.nombre_contrato}")
    print(f"{'='*80}")
    print(f"\nDistribución por cargo:")
    for cargo, count in cargos_count.most_common():
        print(f"  {cargo}: {count}")
    
    # Sugerencias
    print(f"\n{'='*80}")
    print(f"SUGERENCIAS DE PERSONAL STANDBY")
    print(f"{'='*80}")
    
    # Trabajadores sin máquina asignada (candidatos a STANDBY)
    sin_maquina = trabajadores.filter(maquina_asignada__isnull=True)
    
    if sin_maquina.exists():
        print(f"\n🔄 Trabajadores SIN máquina asignada ({sin_maquina.count()}):")
        print(f"   (Buenos candidatos para STANDBY)")
        print(f"{'-'*80}")
        for t in sin_maquina[:10]:  # Mostrar primeros 10
            print(f"   DNI: {t.dni} - {t.apellidos}, {t.nombres} ({t.cargo.nombre})")
    else:
        print("\nTodos los trabajadores tienen máquina asignada")
    
    print(f"{'='*80}\n")


# ============================================================================
# EJEMPLOS DE USO
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("GESTIÓN DE PERSONAL STANDBY (RESERVA)")
    print("="*80 + "\n")
    
    # Opción 1: Listar todo el personal STANDBY actual
    print("1️⃣ Listando personal STANDBY actual...")
    listar_personal_standby()
    
    # Opción 2: Sugerir candidatos para STANDBY en un contrato
    # Descomentar y ajustar el nombre del contrato:
    # print("2️⃣ Analizando personal del contrato...")
    # sugerir_personal_standby("XRD12DST")
    
    # Opción 3: Marcar trabajadores específicos como STANDBY
    # Ejemplo: Descomentar y reemplazar con DNIs reales
    """
    print("3️⃣ Marcando trabajadores como STANDBY...")
    dnis_a_marcar = [
        '12345678',  # Trabajador 1
        '87654321',  # Trabajador 2
    ]
    marcar_standby_por_dni(dnis_a_marcar, es_standby=True)
    """
    
    # Opción 4: Desmarcar trabajadores (cambiar de STANDBY a regular)
    # Ejemplo: Descomentar y reemplazar con DNIs reales
    """
    print("4️⃣ Desmarcando trabajadores como STANDBY...")
    dnis_a_desmarcar = [
        '12345678',
    ]
    marcar_standby_por_dni(dnis_a_desmarcar, es_standby=False)
    """
    
    print("\n✅ Script finalizado\n")
