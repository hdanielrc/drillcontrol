"""
Comando Django para recalcular el metraje de todos los turnos
considerando SOLO las brocas (categoria='BROCA')
"""
from django.core.management.base import BaseCommand
from drilling.models import Turno, TurnoAvance, TurnoComplemento
from django.db.models import Sum
from decimal import Decimal


class Command(BaseCommand):
    help = 'Recalcula el metraje de todos los turnos basándose solo en brocas (categoria=BROCA)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin guardar cambios',
        )
        parser.add_argument(
            '--turno-id',
            type=int,
            help='Recalcular solo un turno específico por ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        turno_id = options.get('turno_id')
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("RECALCULANDO METRAJE DE TURNOS - SOLO BROCAS"))
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: No se guardarán cambios"))
        self.stdout.write("=" * 80)
        
        # Filtrar turnos
        if turno_id:
            turnos_con_avance = TurnoAvance.objects.filter(turno_id=turno_id).select_related('turno')
            if not turnos_con_avance.exists():
                self.stdout.write(self.style.ERROR(f"No se encontró el turno #{turno_id} o no tiene avance"))
                return
        else:
            turnos_con_avance = TurnoAvance.objects.select_related('turno').all()
        
        total_turnos = turnos_con_avance.count()
        actualizados = 0
        sin_cambios = 0
        errores = 0
        
        self.stdout.write(f"\nTotal de turnos a procesar: {total_turnos}\n")
        
        for avance in turnos_con_avance:
            turno = avance.turno
            metros_anterior = avance.metros_perforados
            
            try:
                # Calcular metros solo de BROCAS
                total_brocas = TurnoComplemento.objects.filter(
                    turno=turno,
                    tipo_complemento__categoria='BROCA'
                ).aggregate(total=Sum('metros_turno_calc'))['total']
                
                metros_nuevo = Decimal(str(total_brocas)) if total_brocas is not None else Decimal('0.00')
                
                # Solo actualizar si hay diferencia
                if metros_anterior != metros_nuevo:
                    if not dry_run:
                        avance.metros_perforados = metros_nuevo
                        avance.save()
                    
                    actualizados += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Turno #{turno.id} ({turno.fecha})")
                    )
                    self.stdout.write(f"  Anterior: {metros_anterior}m → Nuevo: {metros_nuevo}m")
                    self.stdout.write(f"  Diferencia: {metros_anterior - metros_nuevo}m")
                    
                    # Mostrar detalle de complementos
                    total_brocas_count = TurnoComplemento.objects.filter(
                        turno=turno, 
                        tipo_complemento__categoria='BROCA'
                    ).count()
                    total_complementos = TurnoComplemento.objects.filter(
                        turno=turno
                    ).exclude(
                        tipo_complemento__categoria='BROCA'
                    ).count()
                    self.stdout.write(
                        f"  Items: {total_brocas_count} brocas, {total_complementos} complementos\n"
                    )
                else:
                    sin_cambios += 1
                    
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f"✗ Error en Turno #{turno.id}: {e}\n")
                )
        
        # Resumen
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("RESUMEN"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total procesados: {total_turnos}")
        self.stdout.write(self.style.SUCCESS(f"Actualizados:     {actualizados}"))
        self.stdout.write(f"Sin cambios:      {sin_cambios}")
        if errores > 0:
            self.stdout.write(self.style.ERROR(f"Errores:          {errores}"))
        self.stdout.write("=" * 80)
        
        if dry_run and actualizados > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠ Modo dry-run: {actualizados} turnos serían actualizados. "
                    "Ejecuta sin --dry-run para aplicar los cambios."
                )
            )
