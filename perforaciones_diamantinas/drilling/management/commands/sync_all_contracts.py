"""
Comando para sincronizar todos los contratos activos desde la API de Vilbragroup.

Este comando sincroniza automáticamente productos diamantados (PDD) y aditivos (ADIT)
para todos los contratos que tengan código de centro de costo configurado.

Uso:
    python manage.py sync_all_contracts
    python manage.py sync_all_contracts --dry-run
    python manage.py sync_all_contracts --verbose
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from drilling.models import Contrato
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza productos diamantados y aditivos para todos los contratos activos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la sincronización sin hacer cambios en la base de datos'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Muestra información detallada de cada producto/aditivo sincronizado'
        )
        parser.add_argument(
            '--skip-pdd',
            action='store_true',
            help='Omitir sincronización de productos diamantados (solo ADIT)'
        )
        parser.add_argument(
            '--skip-adit',
            action='store_true',
            help='Omitir sincronización de aditivos (solo PDD)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        skip_pdd = options['skip_pdd']
        skip_adit = options['skip_adit']

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('SINCRONIZACIÓN AUTOMÁTICA - TODOS LOS CONTRATOS'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios en la base de datos\n'))

        # Obtener contratos activos con centro de costo configurado
        contratos = Contrato.objects.filter(
            estado='ACTIVO',
            codigo_centro_costo__isnull=False
        ).exclude(codigo_centro_costo='').select_related('cliente')

        total_contratos = contratos.count()

        if total_contratos == 0:
            self.stdout.write(self.style.WARNING('No se encontraron contratos activos con centro de costo configurado'))
            return

        self.stdout.write(f'Contratos a sincronizar: {total_contratos}\n')

        # Contadores globales
        total_success = 0
        total_errors = 0
        contratos_sincronizados = []
        contratos_con_error = []

        # Procesar cada contrato
        for idx, contrato in enumerate(contratos, 1):
            self.stdout.write('\n' + '─'*70)
            self.stdout.write(f'[{idx}/{total_contratos}] Procesando: {contrato.nombre_contrato}')
            self.stdout.write(f'Cliente: {contrato.cliente.nombre}')
            self.stdout.write(f'Centro de Costo: {contrato.codigo_centro_costo}')
            self.stdout.write('─'*70 + '\n')

            contrato_ok = True

            # Sincronizar Productos Diamantados (PDD)
            if not skip_pdd:
                self.stdout.write(self.style.HTTP_INFO('\n▶ Sincronizando Productos Diamantados (PDD)...\n'))
                try:
                    call_command(
                        'sync_productos_diamantados',
                        contrato_id=contrato.id,
                        dry_run=dry_run,
                        verbose=verbose,
                        stdout=self.stdout,
                        stderr=self.stderr
                    )
                    self.stdout.write(self.style.SUCCESS('✓ PDD sincronizado correctamente\n'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Error sincronizando PDD: {str(e)}\n'))
                    logger.exception(f'Error en sync_productos_diamantados para contrato {contrato.id}')
                    contrato_ok = False
                    total_errors += 1

            # Sincronizar Aditivos (ADIT)
            if not skip_adit:
                self.stdout.write(self.style.HTTP_INFO('\n▶ Sincronizando Aditivos (ADIT)...\n'))
                try:
                    call_command(
                        'sync_aditivos',
                        contrato_id=contrato.id,
                        dry_run=dry_run,
                        verbose=verbose,
                        stdout=self.stdout,
                        stderr=self.stderr
                    )
                    self.stdout.write(self.style.SUCCESS('✓ ADIT sincronizado correctamente\n'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Error sincronizando ADIT: {str(e)}\n'))
                    logger.exception(f'Error en sync_aditivos para contrato {contrato.id}')
                    contrato_ok = False
                    total_errors += 1

            # Registrar resultado
            if contrato_ok:
                total_success += 1
                contratos_sincronizados.append(contrato.nombre_contrato)
            else:
                contratos_con_error.append(contrato.nombre_contrato)

        # Resumen final
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('RESUMEN FINAL'))
        self.stdout.write('='*70 + '\n')

        self.stdout.write(f'Total contratos procesados: {total_contratos}')
        self.stdout.write(self.style.SUCCESS(f'✓ Sincronizados correctamente: {total_success}'))
        
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'✗ Con errores: {len(contratos_con_error)}'))

        if contratos_sincronizados:
            self.stdout.write('\nContratos sincronizados:')
            for nombre in contratos_sincronizados:
                self.stdout.write(f'  ✓ {nombre}')

        if contratos_con_error:
            self.stdout.write('\nContratos con errores:')
            for nombre in contratos_con_error:
                self.stdout.write(f'  ✗ {nombre}')

        # Mostrar estadísticas generales
        from drilling.models import TipoComplemento, TipoAditivo
        
        self.stdout.write('\n' + '-'*70)
        self.stdout.write('ESTADÍSTICAS GENERALES:')
        self.stdout.write('-'*70)
        
        for contrato in contratos:
            pdd_count = TipoComplemento.objects.filter(contrato=contrato).count()
            pdd_nuevo = TipoComplemento.objects.filter(contrato=contrato, estado='NUEVO').count()
            adit_count = TipoAditivo.objects.filter(contrato=contrato).count()
            
            self.stdout.write(f'\n{contrato.nombre_contrato}:')
            self.stdout.write(f'  PDD: {pdd_count} total ({pdd_nuevo} NUEVOS)')
            self.stdout.write(f'  ADIT: {adit_count} total')

        self.stdout.write('\n' + '='*70 + '\n')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('Modo DRY-RUN completado. Ejecuta sin --dry-run para aplicar los cambios.')
            )
        else:
            if total_errors == 0:
                self.stdout.write(
                    self.style.SUCCESS('Sincronización completada exitosamente.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Sincronización completada con {total_errors} errores. Revisa los logs.')
                )
