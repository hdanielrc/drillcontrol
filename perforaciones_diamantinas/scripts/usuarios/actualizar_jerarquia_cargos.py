"""
Script para asignar niveles jerárquicos a los cargos existentes en la base de datos.
Establece una jerarquía organizacional estándar de mina con RESIDENTE en nivel 1.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Cargo

def asignar_niveles_jerarquicos():
    """
    Asigna niveles jerárquicos a los cargos según su posición en la estructura organizacional.
    Nivel 1 = RESIDENTE (máxima autoridad)
    Nivel 2 = Personal administrativo (Administrador, Logística, Ing. Seguridad)
    Nivel 3 = Supervisor Operativo
    Nivel 4 = Personal de obra (Perforistas y Ayudantes por máquina)
    """
    
    # Definir jerarquía simplificada en 4 niveles
    jerarquia = {
        # Nivel 1: RESIDENTE - Máxima autoridad del contrato
        1: [
            'RESIDENTE', 'Residente', 'RESIDENTE CTR', 'Residente CTR',
            'RESIDENTE   ', 'RESIDENTE    '  # Con espacios extras
        ],
        
        # Nivel 2: Personal Administrativo (de izquierda a derecha: Admin, Logística, Ing.Seguridad)
        2: [
            # Administrador (primero - izquierda)
            'ADMINISTRADOR(A)', 'Administrador', 'Administradora', 'ADMINISTRADORA',
            'ADMINISTRADOR       ', 'ADMINISTRADOR        ',
            
            # Asistentes administrativos y logística
            'ASISTENTE DE RESIDENTE', 'Asistente de Residente', 'ASISTENTE RESIDENTE',
            'ASISTENTE ADMINISTRATIVO', 'Asistente Administrativo',
            'AUXILIAR ADMINISTRATIVO', 'Auxiliar Administrativo',
            'ASISTENTE LOGÍSTICO', 'Asistente Logístico', 'ASISTENTE LOG�STICO',
            'JEFE ZONAL', 'Jefe Zonal',
            
            # Ingenieros y supervisores de seguridad (derecha)
            'INGENIERO(A) SEGURIDAD', 'Ingeniero Seguridad', 'Ingeniero de Seguridad',
            'ING SEGURIDAD', 'ING SEGURIDAD        ',
            'ING. DE SEGURIDAD SENIOR', 'Ing. de Seguridad Senior',
            'SUPERVISOR(A) SEGURIDAD', 'Supervisor de Seguridad', 'Supervisor(a) Seguridad',
            'INSPECTOR DE SEGURIDAD', 'Inspector de Seguridad',
            
            # Otros técnicos administrativos
            'ANALISTA SSOMA', 'Analista SSOMA',
            'ASISTENTE SSOMA', 'Asistente SSOMA',
            'TECNICO QA QC', 'Técnico QA QC',
            'GEOLOGO JUNIOR', 'Geólogo Junior', 'GEOLOGO', 'Geólogo',
            'MAESTRO MUESTRERO LABORATORIO', 'Maestro Muestrero Laboratorio',
            'MAESTRO MUESTRERO', 'Maestro Muestrero',
        ],
        
        # Nivel 3: SUPERVISOR OPERATIVO - Supervisión de campo
        3: [
            'SUPERVISOR', 'Supervisor de Operaciones', 'SUPERVISOR DE OPERACIONES',
            'SUPERVISOR OPERATIVO-I', 'Supervisor Operativo-I',
            'ASISTENTE DE OPERACIONES', 'Asistente de Operaciones',
        ],
        
        # Nivel 4: Personal de OBRA (agrupados por máquina: Perforistas + Ayudantes)
        4: [
            # Perforistas
            'PERFORISTA', 'PERFORISTA DDH', 'Perforista DDH',
            'PERFORISTA DDH II - SB', 'Perforista DDH II',
            'PERFORISTA DDH I', 'Perforista DDH I',
            'PERFORISTA DDH-I', 'PERFORISTA DDH-II',
            
            # Ayudantes
            'AYUDANTE', 'AYUDANTE DDH', 'Ayudante DDH',
            'AYUDANTE PERFORISTA', 'Ayudante Perforista',
            'AYUDANTE DDH I', 'Ayudante DDH I',
            'AYUDANTE DDH II', 'Ayudante DDH II',
            'AYUDANTE DDH-I', 'AYUDANTE DDH-II',
            'AYUDANTE MUESTRERO', 'Ayudante Muestrero',
            'AYUDANTE GEOMECANICO', 'Ayudante Geomecánico',
            
            # Mecánicos de campo
            'TÉCNICO(A) MECÁCNICO', 'Técnico Mecánico', 'TECNICO MECANICO',
            'TÉCNICO MECÁNICO II', 'Técnico Mecánico II',
            'TECNICO MECANICO-I', 'TECNICO MECANICO-II',
            'Técnico Mecánico I', 'Técnico Mecánico II',
            
            # Conductores
            'CONDUCTOR', 'Conductor',
        ],
    }
    
    print("\n" + "="*70)
    print("ASIGNACIÓN DE NIVELES JERÁRQUICOS A CARGOS (4 NIVELES)")
    print("="*70)
    print("Nivel 1: RESIDENTE (Máxima autoridad)")
    print("Nivel 2: Personal Administrativo (Admin → Logística → Seguridad)")
    print("Nivel 3: Supervisor Operativo")
    print("Nivel 4: Personal de Obra (Perforistas + Ayudantes por máquina)")
    print("="*70 + "\n")
    
    actualizados = 0
    no_encontrados = 0
    
    # Obtener todos los cargos
    todos_los_cargos = Cargo.objects.all()
    total_cargos = todos_los_cargos.count()
    
    print(f"Total de cargos en base de datos: {total_cargos}\n")
    
    # Asignar niveles según la jerarquía definida
    for nivel, nombres_cargos in jerarquia.items():
        print(f"\n📊 NIVEL {nivel}:")
        print("-" * 70)
        
        for nombre in nombres_cargos:
            try:
                # Buscar cargo por nombre (case-insensitive)
                cargos = Cargo.objects.filter(nombre__iexact=nombre)
                
                if cargos.exists():
                    for cargo in cargos:
                        cargo.nivel_jerarquico = nivel
                        cargo.save(update_fields=['nivel_jerarquico'])
                        print(f"  ✅ {cargo.nombre} → Nivel {nivel}")
                        actualizados += 1
                        
            except Exception as e:
                print(f"  ❌ Error con '{nombre}': {str(e)}")
    
    # Listar cargos que quedaron con nivel 99 (no asignados)
    cargos_sin_nivel = Cargo.objects.filter(nivel_jerarquico=99)
    
    if cargos_sin_nivel.exists():
        print(f"\n\n⚠️  CARGOS SIN NIVEL ASIGNADO (Nivel 99 por defecto):")
        print("-" * 70)
        for cargo in cargos_sin_nivel:
            print(f"  • {cargo.nombre} (ID: {cargo.id_cargo})")
            no_encontrados += 1
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN:")
    print(f"  ✅ Cargos actualizados: {actualizados}")
    print(f"  ⚠️  Cargos sin nivel asignado: {no_encontrados}")
    print(f"  📊 Total cargos procesados: {total_cargos}")
    print("="*70 + "\n")
    
    if no_encontrados > 0:
        print("💡 TIP: Los cargos sin nivel asignado aparecerán al final del organigrama.")
        print("   Puedes asignarles un nivel manualmente desde el admin de Django.\n")

if __name__ == "__main__":
    asignar_niveles_jerarquicos()
