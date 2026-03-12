from django.core.management.base import BaseCommand
from datetime import datetime

from drilling.models import Trabajador


class Command(BaseCommand):
    help = 'Set fecha_inicio_ciclo for all Trabajador records (optionally force overwrite)'

    def add_arguments(self, parser):
        parser.add_argument('--date', required=True, help='Fecha inicio ciclo YYYY-MM-DD')
        parser.add_argument('--force', action='store_true', help='Overwrite existing fecha_inicio_ciclo')

    def handle(self, *args, **options):
        date_str = options['date']
        force = options['force']
        try:
            fecha = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Fecha inválida: {e}'))
            return

        # Use bulk update to avoid loading full model rows (prevents issues with
        # mismatched DB schema/selecting missing columns in some environments).
        qs = Trabajador.objects.all()
        total = qs.count()
        if force:
            updated = qs.update(fecha_inicio_ciclo=fecha)
            self.stdout.write(self.style.SUCCESS(f'Total trabajadores scanned: {total}'))
            self.stdout.write(self.style.SUCCESS(f'Overwrote fecha_inicio_ciclo for {updated} workers'))
        else:
            updated = qs.filter(fecha_inicio_ciclo__isnull=True).update(fecha_inicio_ciclo=fecha)
            self.stdout.write(self.style.SUCCESS(f'Total trabajadores scanned: {total}'))
            self.stdout.write(self.style.SUCCESS(f'Assigned fecha_inicio_ciclo to {updated} workers (only nulls)'))
