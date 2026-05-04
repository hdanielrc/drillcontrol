"""
Sincroniza trabajadores desde la API de Vilbragroup.

Uso:
    python manage.py sync_trabajadores
    python manage.py sync_trabajadores --dry-run
    python manage.py sync_trabajadores --marcar-ausentes
    python manage.py sync_trabajadores --marcar-ausentes --dias-umbral 5
    python manage.py sync_trabajadores --filtro-cc CC01
"""

import sys
import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sincroniza trabajadores desde la API de Vilbragroup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la sincronización sin hacer cambios en la base de datos',
        )
        parser.add_argument(
            '--marcar-ausentes',
            action='store_true',
            help=(
                'Marca como cesados los trabajadores que no aparecen en la API '
                'y llevan más del umbral de días sin sincronizar'
            ),
        )
        parser.add_argument(
            '--dias-umbral',
            type=int,
            default=3,
            help='Días sin aparecer en la API antes de marcar como cesado (default: 3)',
        )
        parser.add_argument(
            '--filtro-cc',
            default=None,
            help='Filtrar sincronización por código de centro de costo',
        )

    def handle(self, *args, **options):
        # Agregar el directorio de scripts al path para importar sync_trabajadores
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        scripts_sync_dir = os.path.join(project_root, 'scripts', 'sync')
        if scripts_sync_dir not in sys.path:
            sys.path.insert(0, scripts_sync_dir)

        # Importar la función principal del script existente
        # (evita duplicar la lógica de sincronización)
        from sync_trabajadores import sync_trabajadores

        dry_run = options['dry_run']
        marcar_ausentes = options['marcar_ausentes']
        dias_umbral = options['dias_umbral']
        filtro_cc = options['filtro_cc']

        if dry_run:
            self.stdout.write(self.style.WARNING('Modo DRY-RUN activo — no se harán cambios.'))

        if marcar_ausentes:
            self.stdout.write(
                self.style.WARNING(
                    f'Opción --marcar-ausentes activa: se cesarán trabajadores ausentes '
                    f'por más de {dias_umbral} días.'
                )
            )

        sync_trabajadores(
            dry_run=dry_run,
            filter_centro=filtro_cc,
            marcar_ausentes=marcar_ausentes,
            dias_ausente_umbral=dias_umbral,
        )

        self.stdout.write(self.style.SUCCESS('Sincronización de trabajadores completada.'))
