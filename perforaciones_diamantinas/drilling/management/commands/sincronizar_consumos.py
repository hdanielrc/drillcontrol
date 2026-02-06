"""
Management command para sincronizar consumos desde API externa
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
import sys

from drilling.utils.consumo_service import consumo_service

class Command(BaseCommand):
    help = 'Sincroniza consumos de artículos desde API externa por periodo'

    def add_arguments(self, parser):
        parser.add_argument(
            'periodo',
            type=str,
            help='Periodo en formato YYYYMM (ej: 202501)'
        )
        
        parser.add_argument(
            '--centro-costo',
            type=str,
            help='Centro de costo específico (opcional)',
            default=None
        )

    def handle(self, *args, **options):
        periodo = options['periodo']
        centro_costo = options['centro_costo']
        
        # Validar formato del periodo
        if not (periodo.isdigit() and len(periodo) == 6):
            self.stdout.write(self.style.ERROR(f'Formato inválido: {periodo}. Use YYYYMM.'))
            sys.exit(1)
        
        year = int(periodo[:4])
        month = int(periodo[4:])
        
        # Calcular último día del mes
        last_day = calendar.monthrange(year, month)[1]
        
        # Formatos para API DD-MM-YYYY (con guiones, según ejemplo funcional)
        fecha_inicio = f"01-{month:02d}-{year}"
        fecha_fin = f"{last_day:02d}-{month:02d}-{year}"
        
        self.stdout.write(f"Sincronizando consumos: {periodo} ({fecha_inicio} - {fecha_fin})")
        if centro_costo:
            self.stdout.write(f"Centro Costo: {centro_costo}")

        resultado = consumo_service.sincronizar_periodo(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            centro_costo=centro_costo
        )
        
        self.stdout.write(self.style.SUCCESS('Sincronización completada:'))
        self.stdout.write(f"- Importados: {resultado['importados']}")
        self.stdout.write(f"- Actualizados: {resultado['actualizados']}")
        self.stdout.write(f"- Errores: {resultado['errores']}")
        
        if resultado['detalles_errores']:
            self.stdout.write(self.style.WARNING("Detalles de errores:"))
            for err in resultado['detalles_errores'][:10]:
                self.stdout.write(f"  * {err}")
