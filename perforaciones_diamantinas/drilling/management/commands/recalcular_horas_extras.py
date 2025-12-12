"""
Comando para recalcular las horas extras de turnos existentes.

Uso:
    python manage.py recalcular_horas_extras
    python manage.py recalcular_horas_extras --contrato=1
    python manage.py recalcular_horas_extras --desde=2024-01-01 --hasta=2024-12-31
    python manage.py recalcular_horas_extras --turno=123
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from drilling.models import Turno, TurnoAvance, ConfiguracionHoraExtra, TurnoHoraExtra
from datetime import datetime


class Command(BaseCommand):
    help = 'Recalcula las horas extras de los turnos existentes basándose en la configuración actual'

    def add_arguments(self, parser):
        parser.add_argument(
            '--contrato',
            type=int,
            help='ID del contrato a recalcular',
        )
        parser.add_argument(
            '--desde',
            type=str,
            help='Fecha desde (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--hasta',
            type=str,
            help='Fecha hasta (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--turno',
            type=int,
            help='ID de un turno específico',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Construir query de turnos
        turnos_query = Turno.objects.select_related('contrato', 'maquina').prefetch_related(
            'trabajadores_turno__trabajador',
            'avance'
        )
        
        # Aplicar filtros
        if options['turno']:
            turnos_query = turnos_query.filter(id=options['turno'])
            self.stdout.write(f"Filtrando por turno ID: {options['turno']}")
        
        if options['contrato']:
            turnos_query = turnos_query.filter(contrato_id=options['contrato'])
            self.stdout.write(f"Filtrando por contrato ID: {options['contrato']}")
        
        if options['desde']:
            try:
                fecha_desde = datetime.strptime(options['desde'], '%Y-%m-%d').date()
                turnos_query = turnos_query.filter(fecha__gte=fecha_desde)
                self.stdout.write(f"Filtrando desde: {fecha_desde}")
            except ValueError:
                raise CommandError('Formato de fecha inválido. Use YYYY-MM-DD')
        
        if options['hasta']:
            try:
                fecha_hasta = datetime.strptime(options['hasta'], '%Y-%m-%d').date()
                turnos_query = turnos_query.filter(fecha__lte=fecha_hasta)
                self.stdout.write(f"Filtrando hasta: {fecha_hasta}")
            except ValueError:
                raise CommandError('Formato de fecha inválido. Use YYYY-MM-DD')
        
        # Obtener turnos con avance
        turnos = turnos_query.filter(avance__isnull=False).order_by('fecha', 'id')
        total_turnos = turnos.count()
        
        if total_turnos == 0:
            self.stdout.write(self.style.WARNING('No se encontraron turnos con avance para procesar'))
            return
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Total de turnos a procesar: {total_turnos}")
        self.stdout.write(f"{'='*60}\n")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios reales\n'))
        
        # Contadores
        turnos_procesados = 0
        turnos_con_horas_extras = 0
        trabajadores_beneficiados = 0
        total_horas_otorgadas = 0
        errores = 0
        
        # Procesar cada turno
        for turno in turnos:
            try:
                avance = turno.avance
                
                # Mostrar información del turno
                self.stdout.write(f"\nProcesando Turno #{turno.id}:")
                self.stdout.write(f"  Fecha: {turno.fecha}")
                self.stdout.write(f"  Contrato: {turno.contrato.nombre_contrato}")
                self.stdout.write(f"  Máquina: {turno.maquina.nombre}")
                self.stdout.write(f"  Metros: {avance.metros_perforados}m")
                
                # Obtener trabajadores del turno
                trabajadores_count = turno.trabajadores_turno.count()
                self.stdout.write(f"  Trabajadores: {trabajadores_count}")
                
                if trabajadores_count == 0:
                    self.stdout.write(self.style.WARNING('  ⚠️  Sin trabajadores asignados, omitiendo...'))
                    continue
                
                # Buscar configuración aplicable usando las reglas hardcoded por contrato
                from decimal import Decimal
                
                REGLAS_HORAS_EXTRAS = {
                    'AMERICANA': {'metros_minimos': Decimal('25.00'), 'horas_extra': Decimal('1.00')},
                    'COLQUISIRI': {'metros_minimos': Decimal('15.00'), 'horas_extra': Decimal('1.00')},
                }
                
                nombre_contrato = turno.contrato.nombre_contrato.upper().strip()
                
                # Buscar regla específica por nombre de contrato
                regla = None
                for contrato_key, config in REGLAS_HORAS_EXTRAS.items():
                    if contrato_key in nombre_contrato:
                        regla = config
                        break
                
                # Si no hay regla hardcoded, buscar en configuración de BD
                if not regla:
                    configuraciones = ConfiguracionHoraExtra.objects.filter(
                        contrato=turno.contrato,
                        activo=True
                    )
                    
                    config_aplicable = None
                    
                    # Buscar configuración específica de la máquina
                    for config in configuraciones:
                        if config.maquina and config.maquina_id == turno.maquina_id:
                            if config.aplica_para_turno(turno, avance.metros_perforados):
                                config_aplicable = config
                                break
                    
                    # Si no hay configuración específica, buscar general
                    if not config_aplicable:
                        for config in configuraciones:
                            if not config.maquina:
                                if config.aplica_para_turno(turno, avance.metros_perforados):
                                    config_aplicable = config
                                    break
                    
                    if config_aplicable:
                        regla = {
                            'metros_minimos': config_aplicable.metros_minimos,
                            'horas_extra': config_aplicable.horas_extra,
                            'config_obj': config_aplicable
                        }
                
                # Verificar si aplica horas extras (metraje > mínimo, no >=)
                if regla and avance.metros_perforados > regla['metros_minimos']:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Aplica regla: >{regla['metros_minimos']}m → {regla['horas_extra']}h"))
                    
                    if not dry_run:
                        with transaction.atomic():
                            # Eliminar horas extras previas
                            TurnoHoraExtra.objects.filter(turno=turno).delete()
                            
                            # Crear nuevas horas extras
                            horas_extras_list = []
                            for tt in turno.trabajadores_turno.select_related('trabajador'):
                                horas_extras_list.append(
                                    TurnoHoraExtra(
                                        turno=turno,
                                        trabajador=tt.trabajador,
                                        horas_extra=regla['horas_extra'],
                                        metros_turno=avance.metros_perforados,
                                        configuracion_aplicada=regla.get('config_obj'),
                                        observaciones=f'Recalculado automáticamente. Metraje: {avance.metros_perforados}m > {regla["metros_minimos"]}m'
                                    )
                                )
                            
                            if horas_extras_list:
                                TurnoHoraExtra.objects.bulk_create(horas_extras_list)
                                trabajadores_beneficiados += len(horas_extras_list)
                                total_horas_otorgadas += float(regla['horas_extra']) * len(horas_extras_list)
                    else:
                        # En dry-run solo contar
                        trabajadores_beneficiados += trabajadores_count
                        total_horas_otorgadas += float(regla['horas_extra']) * trabajadores_count
                    
                    turnos_con_horas_extras += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {trabajadores_count} trabajadores recibirán {regla['horas_extra']}h extra"))
                else:
                    self.stdout.write(self.style.WARNING(f"  - No aplica (metraje: {avance.metros_perforados}m, se requiere >{regla['metros_minimos'] if regla else '?'}m)"))
                    
                    if not dry_run:
                        # Eliminar horas extras si existían
                        deleted = TurnoHoraExtra.objects.filter(turno=turno).delete()
                        if deleted[0] > 0:
                            self.stdout.write(f"  - Eliminadas {deleted[0]} horas extras previas")
                
                turnos_procesados += 1
                
            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(f"  ✗ Error procesando turno #{turno.id}: {str(e)}"))
        
        # Resumen final
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Turnos procesados: {turnos_procesados}")
        self.stdout.write(f"Turnos con horas extras: {turnos_con_horas_extras}")
        self.stdout.write(f"Trabajadores beneficiados: {trabajadores_beneficiados}")
        self.stdout.write(f"Total horas extras otorgadas: {total_horas_otorgadas:.2f}h")
        
        if errores > 0:
            self.stdout.write(self.style.ERROR(f"Errores encontrados: {errores}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN: No se realizaron cambios reales'))
            self.stdout.write('Ejecute sin --dry-run para aplicar los cambios')
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Recálculo completado exitosamente'))
