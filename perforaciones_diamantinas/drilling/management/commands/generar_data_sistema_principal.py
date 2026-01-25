"""
Management command para generar data masiva de prueba para el contrato SISTEMA PRINCIPAL
Genera: trabajadores, máquinas, turnos y actividades de 3 meses
"""
from django.core.management.base import BaseCommand
from django.db import models
from datetime import datetime, timedelta, time
from decimal import Decimal
import random

from drilling.models import (
    Contrato, Trabajador, Maquina, Sondaje, Turno,
    TurnoActividad, TipoActividad, TipoTurno, TurnoTrabajador, Cliente, Cargo, TurnoAvance,
    TurnoSondaje, TurnoMaquina, TurnoComplemento, TurnoAditivo, TurnoCorrida,
    TipoComplemento, TipoAditivo, UnidadMedida, HistorialBroca
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
    ('PERFORISTA', 15),
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
    'SUPERFICIAL', 'SUBTERRANEA', 'SUPERFICIAL', 'SUPERFICIAL',
    'SUPERFICIAL', 'SUBTERRANEA', 'SUPERFICIAL', 'SUBTERRANEA',
    'SUPERFICIAL', 'SUPERFICIAL'
]

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


class Command(BaseCommand):
    help = 'Genera data masiva para el contrato SISTEMA PRINCIPAL'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("GENERADOR DE DATA MASIVA - SISTEMA PRINCIPAL"))
        self.stdout.write("=" * 80)
        
        # 1. Buscar o crear contrato
        self.stdout.write("\n[1/4] Buscando contrato SISTEMA PRINCIPAL...")
        
        # Obtener o crear cliente
        cliente, _ = Cliente.objects.get_or_create(
            nombre="CLIENTE DEMO",
            defaults={
                'is_active': True
            }
        )
        
        contrato, created = Contrato.objects.get_or_create(
            nombre_contrato="SISTEMA PRINCIPAL",
            defaults={
                'cliente': cliente,
                'estado': 'ACTIVO',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Contrato creado: {contrato.nombre_contrato}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Contrato encontrado: {contrato.nombre_contrato}"))
        
        # 2. Crear/obtener cargos necesarios
        self.stdout.write("\n[2/5] Creando cargos necesarios...")
        cargos_map = {}
        
        try:
            for cargo_nombre, _ in CARGOS_OPERATIVOS:
                # Obtener ID único para el cargo
                max_id = Cargo.objects.aggregate(models.Max('id_cargo'))['id_cargo__max'] or 0
                
                cargo_obj, created = Cargo.objects.get_or_create(
                    nombre=cargo_nombre,
                    defaults={
                        'id_cargo': max_id + 1,
                        'descripcion': f'Cargo operativo: {cargo_nombre}',
                        'is_active': True,
                        'nivel_jerarquico': 50  # Nivel medio en la jerarquía
                    }
                )
                cargos_map[cargo_nombre] = cargo_obj
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Cargo creado: {cargo_nombre}"))
            
            self.stdout.write(self.style.SUCCESS(f"✓ {len(cargos_map)} cargos listos"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error al crear cargos: {e}"))
            return
        
        # 3. Crear trabajadores
        self.stdout.write("\n[3/5] Generando trabajadores...")
        trabajadores_creados = 0
        trabajadores = []
        
        for cargo_nombre, cantidad in CARGOS_OPERATIVOS:
            cargo_obj = cargos_map[cargo_nombre]
            
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
                    nombres=nombre,
                    apellidos=apellido,
                    dni=dni,
                    cargo=cargo_obj,  # Usar el objeto Cargo, no el string
                    regimen_laboral=regimen,
                    estado='ACTIVO',
                    fecha_ingreso=datetime.now().date() - timedelta(days=random.randint(90, 365))
                )
                trabajadores.append(trabajador)
                trabajadores_creados += 1
        
        self.stdout.write(self.style.SUCCESS(f"✓ {trabajadores_creados} trabajadores creados"))
        
        # 4. Crear máquinas
        self.stdout.write("\n[4/5] Generando máquinas...")
        maquinas_creadas = 0
        maquinas = []
        
        for i, (tipo, tipo_trabajo) in enumerate(zip(TIPOS_MAQUINA, TIPOS_TRABAJO), 1):
            nombre = f"MÁQUINA-{i:02d}"
            
            maquina = Maquina.objects.create(
                contrato=contrato,
                nombre=nombre,
                tipo=tipo,
                tipo_trabajo=tipo_trabajo,
                estado='OPERATIVO',
                horometro=Decimal(str(random.randint(5000, 15000)))
            )
            maquinas.append(maquina)
            maquinas_creadas += 1
        
        self.stdout.write(self.style.SUCCESS(f"✓ {maquinas_creadas} máquinas creadas"))
        
        # Asignar máquinas a perforistas
        perforistas = [t for t in trabajadores if t.cargo.nombre == 'PERFORISTA']
        for perforista, maquina in zip(perforistas[:len(maquinas)], maquinas):
            perforista.maquina_asignada = maquina
            perforista.save()
        
        # 5. Crear sondajes y turnos
        self.stdout.write("\n[5/5] Generando sondajes y turnos (3 meses)...")
        sondajes = []
        fecha_base = datetime.now().date() - timedelta(days=90)
        
        for i in range(30):
            codigo = f"DDH-2026-{i+1:04d}"
            sondaje = Sondaje.objects.create(
                contrato=contrato,
                nombre_sondaje=codigo,
                fecha_inicio=fecha_base + timedelta(days=random.randint(0, 30)),
                profundidad=Decimal(str(random.randint(200, 800))),
                inclinacion=Decimal(str(random.randint(-45, 45))),
                cota_collar=Decimal(str(random.randint(2000, 4500))),
                estado='ACTIVO'
            )
            sondajes.append(sondaje)
        
        self.stdout.write(self.style.SUCCESS(f"✓ {len(sondajes)} sondajes creados"))
        
        # 5. Generar turnos de 3 meses
        self.stdout.write("\nGenerando turnos con actividades completas...")
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
                    perforista = random.choice([t for t in trabajadores if t.cargo.nombre == 'PERFORISTA'])
                    ayudante = random.choice([t for t in trabajadores if t.cargo.nombre == 'AYUDANTE PERFORISTA'])
                    
                    try:
                        # Usar get_or_create para evitar duplicados (unique_together en contrato+maquina+fecha+tipo_turno)
                        turno, created = Turno.objects.get_or_create(
                            contrato=contrato,
                            maquina=maquina,
                            tipo_turno=tipo_turno,
                            fecha=current_date,
                            defaults={
                                'estado': random.choice(['COMPLETADO', 'APROBADO', 'COMPLETADO', 'COMPLETADO']),
                                'comentarios_perforistas': f"Turno generado - {guardia_nombre}",
                                'litologia_general': "Andesita con vetas de cuarzo"
                            }
                        )
                        
                        if not created:
                            continue  # Ya existe, saltar a siguiente iteración
                        
                        # Agregar sondaje al turno (M2M)
                        turno.sondajes.add(sondaje)
                        
                        # ===== 1. TurnoSondaje (M2M con metros) =====
                        metros_perforados = Decimal(str(round(random.uniform(5.0, 25.0), 2)))  # Redondear a 2 decimales
                        TurnoSondaje.objects.update_or_create(
                            turno=turno,
                            sondaje=sondaje,
                            defaults={'metros_turno': metros_perforados}
                        )
                        
                        # ===== 2. TurnoMaquina (estado de máquina y horas) =====
                        hora_inicio_maq = time(7, 0) if guardia_nombre == 'DIA' else time(19, 0)
                        hora_fin_maq = time(19, 0) if guardia_nombre == 'DIA' else time(7, 0)
                        
                        TurnoMaquina.objects.create(
                            turno=turno,
                            hora_inicio=hora_inicio_maq,
                            hora_fin=hora_fin_maq,
                            estado_bomba=random.choice(['OPERATIVO', 'OPERATIVO', 'OPERATIVO', 'CON_FALLA']),
                            estado_unidad=random.choice(['OPERATIVO', 'OPERATIVO', 'OPERATIVO', 'CON_FALLA']),
                            estado_rotacion=random.choice(['OPERATIVO', 'OPERATIVO', 'OPERATIVO', 'CON_FALLA']),
                            comentarios_mantenimiento='Turno generado automáticamente'
                        )
                        
                        # ===== 3. TurnoTrabajador (personal asignado) =====
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
                        
                        # ===== 4. TurnoComplemento (brocas con series) =====
                        try:
                            tipos_broca = TipoComplemento.objects.filter(categoria='BROCA')[:5]
                            if tipos_broca.exists():
                                tipo_broca = random.choice(list(tipos_broca))
                                serie_broca = f"BROCA-{random.randint(1000, 9999)}"
                                metros_inicio_broca = Decimal(str(round(random.randint(0, 200), 2)))
                                metros_fin_broca = metros_inicio_broca + metros_perforados
                                
                                complemento = TurnoComplemento.objects.create(
                                    turno=turno,
                                    sondaje=sondaje,
                                    tipo_complemento=tipo_broca,
                                    codigo_serie=serie_broca,
                                    metros_inicio=metros_inicio_broca,
                                    metros_fin=metros_fin_broca,
                                    metros_turno_calc=metros_perforados
                                )
                                
                                # Actualizar HistorialBroca
                                historial, created_hist = HistorialBroca.objects.get_or_create(
                                    serie=serie_broca,
                                    defaults={
                                        'tipo_complemento': tipo_broca,
                                        'contrato_actual': contrato,
                                        'fecha_primer_uso': current_date,
                                        'estado': 'EN_USO'
                                    }
                                )
                                if not created_hist:
                                    historial.metraje_acumulado += metros_perforados
                                    historial.numero_usos += 1
                                    historial.fecha_ultimo_uso = current_date
                                    historial.save()
                        except Exception:
                            pass  # Si no hay tipos de complemento, continuar
                        
                        # ===== 5. TurnoAditivo (aditivos usados) =====
                        try:
                            tipos_aditivo = TipoAditivo.objects.all()[:5]
                            unidades = UnidadMedida.objects.all()[:3]
                            if tipos_aditivo.exists() and unidades.exists():
                                tipo_adit = random.choice(list(tipos_aditivo))
                                unidad = random.choice(list(unidades))
                                cantidad = random.uniform(10.0, 50.0)
                                
                                TurnoAditivo.objects.create(
                                    turno=turno,
                                    sondaje=sondaje,
                                    tipo_aditivo=tipo_adit,
                                    cantidad_usada=cantidad,
                                    unidad_medida=unidad
                                )
                        except Exception:
                            pass  # Si no hay aditivos, continuar
                        
                        # ===== 6. TurnoCorrida (corridas de testigos) =====
                        num_corridas = random.randint(2, 4)
                        desde_metros = Decimal('0')
                        for corrida_num in range(1, num_corridas + 1):
                            longitud = Decimal(str(round(random.uniform(3.0, 10.0), 2)))
                            hasta_metros = desde_metros + longitud
                            testigo = Decimal(str(round(random.uniform(float(longitud) * 0.7, float(longitud) * 0.95), 2)))
                            recuperacion = round((testigo / longitud * 100) if longitud > 0 else Decimal('0'), 2)
                            
                            TurnoCorrida.objects.create(
                                turno=turno,
                                corrida_numero=corrida_num,
                                desde=desde_metros,
                                hasta=hasta_metros,
                                longitud_testigo=testigo,
                                pct_recuperacion=Decimal(str(recuperacion)),
                                pct_retorno_agua=Decimal(str(round(random.uniform(70.0, 95.0), 2))),
                                litologia=random.choice([
                                    'Andesita', 'Diorita', 'Granito', 'Caliza', 'Arenisca',
                                    'Cuarcita', 'Pizarra', 'Lutita', 'Basalto'
                                ])
                            )
                            desde_metros = hasta_metros
                        
                        # ===== 7. TurnoAvance (metros totales) =====
                        TurnoAvance.objects.create(
                            turno=turno,
                            metros_perforados=metros_perforados
                        )
                        
                        # ===== 8. TurnoActividad (actividades con horas) =====
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
                        
                        turnos_creados += 1
                    
                    except Exception as e:
                        # Mostrar error para debugging
                        self.stdout.write(self.style.ERROR(f"✗ Error creando turno: {e}"))
                        import traceback
                        traceback.print_exc()
                        pass
            
            current_date += timedelta(days=1)
            
            # Progreso cada 10 días
            if (current_date - fecha_inicio).days % 10 == 0:
                self.stdout.write(f"  Progreso: {(current_date - fecha_inicio).days}/90 días - {turnos_creados} turnos - {actividades_creadas} actividades")
        
        self.stdout.write(self.style.SUCCESS(f"\n✓ {turnos_creados} turnos creados"))
        self.stdout.write(self.style.SUCCESS(f"✓ {actividades_creadas} actividades creadas"))
        
        # Resumen final
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("RESUMEN FINAL"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Contrato: {contrato.nombre_contrato}")
        self.stdout.write(f"Trabajadores: {trabajadores_creados}")
        self.stdout.write(f"Máquinas: {maquinas_creadas}")
        self.stdout.write(f"Sondajes: {len(sondajes)}")
        self.stdout.write(f"Turnos: {turnos_creados} (últimos 3 meses)")
        self.stdout.write(f"Actividades: {actividades_creadas}")
        self.stdout.write(f"Fecha inicio: {fecha_inicio}")
        self.stdout.write(f"Fecha fin: {fecha_fin}")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("✓ DATA GENERADA EXITOSAMENTE"))
        self.stdout.write("=" * 80)
