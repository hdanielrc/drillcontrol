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

        qs = Trabajador.objects.all()
        total = qs.count()
        changed = 0
        overwritten = 0
        for t in qs.iterator():
            if t.fecha_inicio_ciclo is None:
                t.fecha_inicio_ciclo = fecha
                t.save(update_fields=['fecha_inicio_ciclo'])
                changed += 1
            elif force:
                t.fecha_inicio_ciclo = fecha
                t.save(update_fields=['fecha_inicio_ciclo'])
                overwritten += 1

        self.stdout.write(self.style.SUCCESS(f'Total trabajadores scanned: {total}'))
        self.stdout.write(self.style.SUCCESS(f'Assigned fecha_inicio_ciclo to {changed} workers'))
        if force:
            self.stdout.write(self.style.SUCCESS(f'Overwrote fecha_inicio_ciclo for {overwritten} workers'))
