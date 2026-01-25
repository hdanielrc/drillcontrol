"""
Script para generar data masiva de prueba para el contrato SISTEMA PRINCIPAL
Genera: trabajadores, máquinas, turnos y actividades de 3 meses
"""
import os
import sys
import django
from datetime import datetime, timedelta, time
from decimal import Decimal
import random

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import (
    Contrato, Trabajador, Maquina, Sondaje, Turno,
    TurnoActividad, TipoActividad, TipoTurno
)

# Datos realistas
NOMBRES = [
    "Juan Carlos", "Pedro Luis", "Miguel Angel", "José Antonio", "Carlos Eduardo",
    "Roberto Manuel", "Luis Fernando", "Francisco Javier", "Diego Alejandro", "Sergio Daniel",
    "Mario Alberto", "Raúl Enrique", "Jorge Luis", "Ricardo David", "Fernando José",
    "Andrés Felipe", "Martín Gonzalo", "Pablo César", "Héctor Raúl", "Oscar Iván"
]

APELLIDOS = [
    "García Pérez", "Rodríguez López", "Martínez Sánchez", "Fernández González", "López Díaz",
    "González Muñoz", "Pérez Hernández", "Sánchez Ramírez", "Ramírez Torres", "Torres Flores",
    "Flores Morales", "Morales Castro", "Castro Ortiz", "Ortiz Reyes", "Reyes Gutiérrez",
    "Gutiérrez Romero", "Romero Mendoza", "Mendoza Silva", "Silva Vargas", "Vargas Chávez"
]

CARGOS_OPERATIVOS = [
    ('PERFORISTA', 15),  # (cargo, cantidad)
    ('AYUDANTE PERFORISTA', 15),
    ('MECANICO', 5),
    ('GEÓLOGO', 3),
    ('TOPÓGRAFO', 2),
    ('SUPERVISOR', 4),
    ('WINCHERO', 6)
]

TIPOS_MAQUINA = [
    'DIAMANTINA', 'DIAMANTINA', 'DIAMANTINA', 'DIAMANTINA', 'DIAMANTINA',
    'DIAMANTINA', 'DIAMANTINA', 'RC', 'RC', 'MULTI-PROPOSITO'
]

TIPOS_TRABAJO = [
    'DDH SUPERFICIE', 'DDH SUBTERRANEO', 'EXPLORACIÓN', 'GEOTECNIA',
    'DDH SUPERFICIE', 'DDH SUBTERRANEO', 'EXPLORACIÓN', 'HIDROGEOLOGÍA',
    'DDH SUPERFICIE', 'CONTROL DE CALIDAD'
]

GUARDIAS = ['DIA', 'NOCHE']

ESTADOS_TURNO = ['PERFORANDO', 'PERFORANDO', 'PERFORANDO', 'MUESTREANDO', 'ENCAMISANDO', 'PERFORANDO']

ACTIVIDADES = [
    'Perforación DDH',
    'Recuperación de testigos',
    'Colocación de encamisado',
    'Retiro de barras',
    'Muestreo geológico',
    'Mantenimiento de equipo',
    'Instalación de bomba',
    'Cambio de broca',
    'Movimiento de equipo',
    'Preparación de plataforma'
]

def generar_data():
    print("=" * 80)
    print("GENERADOR DE DATA MASIVA - SISTEMA PRINCIPAL")
    print("=" * 80)
    
    # 1. Buscar o crear contrato
    print("\n[1/4] Buscando contrato SISTEMA PRINCIPAL...")
    contrato, created = Contrato.objects.get_or_create(
        nombre_contrato="SISTEMA PRINCIPAL",
        defaults={
            'cliente': "Cliente Demo",
            'activo': True,
            'fecha_inicio': datetime.now().date() - timedelta(days=180),
            'fecha_fin': datetime.now().date() + timedelta(days=180)
        }
    )
    if created:
        print(f"✓ Contrato creado: {contrato.nombre_contrato}")
    else:
        print(f"✓ Contrato encontrado: {contrato.nombre_contrato}")
    
    # 2. Crear trabajadores
    print("\n[2/4] Generando trabajadores...")
    trabajadores_creados = 0
    trabajadores = []
    
    for cargo, cantidad in CARGOS_OPERATIVOS:
        for i in range(cantidad):
            nombre = random.choice(NOMBRES)
            apellido = random.choice(APELLIDOS)
            dni = f"7{random.randint(0, 9)}{random.randint(100000, 999999)}"
            
            # Verificar si existe
            if Trabajador.objects.filter(dni=dni).exists():
                dni = f"7{random.randint(0, 9)}{random.randint(100000, 999999)}"
            
            # Régimen laboral aleatorio
            regimenes = ['14x7', '20x10', '28x14', '40x20']
            regimen = random.choice(regimenes)
            
            trabajador = Trabajador.objects.create(
                contrato=contrato,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                cargo=cargo,
                regimen_laboral=regimen,
                estado_laboral='ACTIVO',
                fecha_ingreso=datetime.now().date() - timedelta(days=random.randint(90, 365))
            )
            trabajadores.append(trabajador)
            trabajadores_creados += 1
    
    print(f"✓ {trabajadores_creados} trabajadores creados")
    
    # 3. Crear máquinas
    print("\n[3/4] Generando máquinas...")
    maquinas_creadas = 0
    maquinas = []
    
    for i, (tipo, tipo_trabajo) in enumerate(zip(TIPOS_MAQUINA, TIPOS_TRABAJO), 1):
        codigo = f"MQ-{i:03d}"
        nombre = f"MÁQUINA {i:02d}"
        
        maquina = Maquina.objects.create(
            contrato=contrato,
            codigo=codigo,
            nombre=nombre,
            tipo=tipo,
            tipo_trabajo=tipo_trabajo,
            estado='OPERATIVO',
            horometro=Decimal(str(random.randint(5000, 15000)))
        )
        maquinas.append(maquina)
        maquinas_creadas += 1
    
    print(f"✓ {maquinas_creadas} máquinas creadas")
    
    # Asignar máquinas a perforistas
    perforistas = [t for t in trabajadores if t.cargo == 'PERFORISTA']
    for perforista, maquina in zip(perforistas[:len(maquinas)], maquinas):
        perforista.maquina_asignada = maquina
        perforista.save()
    
    # 4. Crear sondajes
    print("\n[4/4] Generando sondajes y turnos (3 meses)...")
    sondajes = []
    for i in range(30):  # 30 sondajes
        codigo = f"DDH-{2025}-{i+1:04d}"
        sondaje = Sondaje.objects.create(
            contrato=contrato,
            codigo_sondaje=codigo,
            proyecto=f"PROYECTO {random.choice(['A', 'B', 'C', 'D'])}",
            tipo='DDH',
            profundidad_programada=Decimal(str(random.randint(200, 800))),
            estado='EN_PROCESO'
        )
        sondajes.append(sondaje)
    
    print(f"✓ {len(sondajes)} sondajes creados")
    
    # 5. Generar turnos de 3 meses
    print("\nGenerando turnos con actividades completas...")
    fecha_inicio = datetime.now().date() - timedelta(days=90)
    fecha_fin = datetime.now().date()
    
    # Obtener o crear tipos de turno
    tipo_dia, _ = TipoTurno.objects.get_or_create(nombre='DIA')
    tipo_noche, _ = TipoTurno.objects.get_or_create(nombre='NOCHE')
    
    # Obtener o crear tipos de actividad
    tipos_actividad = {}
    for nombre_act in ACTIVIDADES:
        tipo_act, _ = TipoActividad.objects.get_or_create(
            nombre=nombre_act,
            defaults={'descripcion': f'Actividad: {nombre_act}'}
        )
        tipos_actividad[nombre_act] = tipo_act
    
    turnos_creados = 0
    actividades_creadas = 0
    
    current_date = fecha_inicio
    while current_date <= fecha_fin:
        # Crear turnos para día y noche
        for tipo_turno, guardia_nombre in [(tipo_dia, 'DIA'), (tipo_noche, 'NOCHE')]:
            # Seleccionar 8-12 turnos por guardia
            num_turnos = random.randint(8, 12)
            
            for _ in range(num_turnos):
                sondaje = random.choice(sondajes)
                maquina = random.choice(maquinas)
                
                # Seleccionar perforista y ayudante
                perforista = random.choice([t for t in trabajadores if t.cargo == 'PERFORISTA'])
                ayudante = random.choice([t for t in trabajadores if t.cargo == 'AYUDANTE PERFORISTA'])
                
                try:
                    turno = Turno.objects.create(
                        contrato=contrato,
                        maquina=maquina,
                        tipo_turno=tipo_turno,
                        fecha=current_date,
                        estado=random.choice(['COMPLETADO', 'APROBADO', 'COMPLETADO', 'COMPLETADO']),
                        comentarios_perforistas=f"Turno generado - {guardia_nombre}",
                        litologia_general="Andesita con vetas de cuarzo"
                    )
                    
                    # Agregar sondaje al turno (M2M)
                    turno.sondajes.add(sondaje)
                    
                    # Crear trabajadores del turno
                    from drilling.models import TurnoTrabajador
                    TurnoTrabajador.objects.create(
                        turno=turno,
                        trabajador=perforista,
                        funcion='PERFORISTA'
                    )
                    TurnoTrabajador.objects.create(
                        turno=turno,
                        trabajador=ayudante,
                        funcion='AYUDANTE'
                    )
                    
                    turnos_creados += 1
                    
                    # Crear 3-5 actividades por turno
                    num_actividades = random.randint(3, 5)
                    hora_actual = time(7, 0) if guardia_nombre == 'DIA' else time(19, 0)
                    
                    for j in range(num_actividades):
                        actividad_nombre = random.choice(ACTIVIDADES)
                        tipo_actividad = tipos_actividad[actividad_nombre]
                        duracion = random.randint(30, 180)  # 30 a 180 minutos
                        
                        hora_fin_actividad = (
                            datetime.combine(current_date, hora_actual) + 
                            timedelta(minutes=duracion)
                        ).time()
                        
                        # Crear TurnoActividad
                        TurnoActividad.objects.create(
                            turno=turno,
                            actividad=tipo_actividad,
                            hora_inicio=hora_actual,
                            hora_fin=hora_fin_actividad,
                            observaciones=f"Actividad {j+1} del turno"
                        )
                        
                        actividades_creadas += 1
                        hora_actual = hora_fin_actividad
                
                except Exception as e:
                    # Si hay error (turno duplicado), continuar
                    pass
        
        current_date += timedelta(days=1)
        
        # Progreso cada 10 días
        if (current_date - fecha_inicio).days % 10 == 0:
            print(f"  Progreso: {(current_date - fecha_inicio).days}/90 días - {turnos_creados} turnos - {actividades_creadas} actividades")
    
    print(f"\n✓ {turnos_creados} turnos creados")
    print(f"✓ {actividades_creadas} actividades creadas")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    print(f"Contrato: {contrato.nombre_contrato}")
    print(f"Trabajadores: {trabajadores_creados}")
    print(f"Máquinas: {maquinas_creadas}")
    print(f"Sondajes: {len(sondajes)}")
    print(f"Turnos: {turnos_creados} (últimos 3 meses)")
    print(f"Actividades: {actividades_creadas}")
    print(f"Fecha inicio: {fecha_inicio}")
    print(f"Fecha fin: {fecha_fin}")
    print("=" * 80)
    print("✓ DATA GENERADA EXITOSAMENTE")
    print("=" * 80)

if __name__ == '__main__':
    generar_data()
