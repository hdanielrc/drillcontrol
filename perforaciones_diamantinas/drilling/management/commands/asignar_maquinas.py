"""
Comando de Django para asignar máquinas automáticamente a trabajadores perforistas y ayudantes
que actualmente no tienen máquina asignada.

Uso: python manage.py asignar_maquinas
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from drilling.models import Trabajador, Maquina


class Command(BaseCommand):
    help = 'Asigna máquinas automáticamente a trabajadores perforistas y ayudantes sin máquina asignada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular la asignación sin guardar cambios',
        )
        parser.add_argument(
            '--contrato',
            type=int,
            help='ID del contrato para filtrar trabajadores (opcional)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        contrato_id = options.get('contrato')
        
        self.stdout.write(self.style.SUCCESS('🚀 INICIANDO ASIGNACIÓN DE MÁQUINAS A TRABAJADORES'))
        self.stdout.write('=' * 80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  MODO SIMULACIÓN - No se guardarán cambios'))
        
        # Mostrar estadísticas antes
        self.mostrar_estadisticas(contrato_id)
        
        # Realizar asignación
        asignados = self.asignar_maquinas_faltantes(dry_run, contrato_id)
        
        # Mostrar estadísticas después
        if asignados > 0 and not dry_run:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.SUCCESS('📊 ESTADÍSTICAS DESPUÉS DE LA ASIGNACIÓN'))
            self.mostrar_estadisticas(contrato_id)
        
        self.stdout.write('\n' + self.style.SUCCESS('✅ Proceso completado'))

    def asignar_maquinas_faltantes(self, dry_run, contrato_id=None):
        """
        Asigna máquinas a trabajadores que deberían tenerla pero no la tienen.
        """
        # Filtro base
        filtro = {
            'estado': 'ACTIVO',
            'maquina_asignada__isnull': True,
            'cargo__isnull': False
        }
        
        if contrato_id:
            filtro['contrato_id'] = contrato_id
        
        trabajadores_sin_maquina = Trabajador.objects.filter(**filtro).select_related('cargo', 'contrato')
        
        self.stdout.write(f"\n📋 Encontrados {trabajadores_sin_maquina.count()} trabajadores sin máquina asignada")
        self.stdout.write('=' * 80 + '\n')
        
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
                    if not dry_run:
                        trabajador.maquina_asignada = maquina
                        trabajador.save()
                    
                    asignados += 1
                    self.stdout.write(self.style.SUCCESS(f"✅ {trabajador.apellidos}, {trabajador.nombres}"))
                    self.stdout.write(f"   Cargo: {trabajador.cargo.nombre}")
                    self.stdout.write(f"   Máquina asignada: {maquina.nombre}")
                    self.stdout.write(f"   Contrato: {trabajador.contrato.nombre_contrato}")
                    if dry_run:
                        self.stdout.write(self.style.WARNING("   [SIMULACIÓN - No guardado]"))
                    self.stdout.write('')
                else:
                    sin_maquinas += 1
                    self.stdout.write(self.style.WARNING(f"⚠️  {trabajador.apellidos}, {trabajador.nombres}"))
                    self.stdout.write(f"   Cargo: {trabajador.cargo.nombre}")
                    self.stdout.write(self.style.ERROR(f"   ❌ No hay máquinas disponibles en el contrato {trabajador.contrato.nombre_contrato}"))
                    self.stdout.write('')
            else:
                no_aplica += 1
        
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN:'))
        self.stdout.write(f"   ✅ Máquinas asignadas: {asignados}")
        self.stdout.write(f"   ⚠️  Sin máquinas disponibles: {sin_maquinas}")
        self.stdout.write(f"   ℹ️  No aplica (otros cargos): {no_aplica}")
        self.stdout.write(f"   📋 Total procesados: {trabajadores_sin_maquina.count()}")
        
        return asignados

    def mostrar_estadisticas(self, contrato_id=None):
        """
        Muestra estadísticas de asignación de máquinas
        """
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('📊 ESTADÍSTICAS DE MÁQUINAS'))
        self.stdout.write('=' * 80)
        
        # Filtro base
        filtro_base = {'estado': 'ACTIVO'}
        if contrato_id:
            filtro_base['contrato_id'] = contrato_id
        
        total_trabajadores = Trabajador.objects.filter(**filtro_base).count()
        con_maquina = Trabajador.objects.filter(**filtro_base, maquina_asignada__isnull=False).count()
        sin_maquina = total_trabajadores - con_maquina
        
        self.stdout.write(f"\n👷 TRABAJADORES ACTIVOS:")
        self.stdout.write(f"   Total: {total_trabajadores}")
        self.stdout.write(f"   Con máquina asignada: {con_maquina}")
        self.stdout.write(f"   Sin máquina: {sin_maquina}")
        
        # Perforistas y ayudantes
        filtro_operadores = filtro_base.copy()
        filtro_operadores['cargo__nombre__iregex'] = r'(perforist|ayudante)'
        
        perforistas_ayudantes = Trabajador.objects.filter(**filtro_operadores)
        total_operadores = perforistas_ayudantes.count()
        operadores_con_maquina = perforistas_ayudantes.filter(maquina_asignada__isnull=False).count()
        
        self.stdout.write(f"\n🔧 PERFORISTAS Y AYUDANTES:")
        self.stdout.write(f"   Total: {total_operadores}")
        self.stdout.write(f"   Con máquina: {operadores_con_maquina}")
        self.stdout.write(f"   Sin máquina: {total_operadores - operadores_con_maquina}")
        
        # Máquinas por contrato
        self.stdout.write(f"\n🏭 MÁQUINAS DISPONIBLES:")
        
        filtro_maquinas = {'estado': 'OPERATIVO'}
        if contrato_id:
            filtro_maquinas['contrato_id'] = contrato_id
        
        maquinas = Maquina.objects.filter(**filtro_maquinas).select_related('contrato').annotate(
            num_trabajadores=Count('trabajadores_asignados')
        ).order_by('contrato__nombre_contrato', 'nombre')
        
        if maquinas.exists():
            contrato_actual = None
            for maquina in maquinas:
                if contrato_actual != maquina.contrato.nombre_contrato:
                    contrato_actual = maquina.contrato.nombre_contrato
                    self.stdout.write(f"\n   📍 {contrato_actual}:")
                self.stdout.write(f"      • {maquina.nombre} - {maquina.num_trabajadores} trabajadores")
        else:
            self.stdout.write(self.style.WARNING("   ⚠️  No hay máquinas operativas"))
