"""
Management command para sincronizar abastecimientos desde API externa
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import sys

from drilling.utils.abastecimiento_service import abastecimiento_service


class Command(BaseCommand):
    help = 'Sincroniza abastecimientos de artículos desde API externa por periodo'

    def add_arguments(self, parser):
        parser.add_argument(
            'periodo',
            type=str,
            help='Periodo en formato YYYYMM (ej: 202601 para Enero 2026)'
        )
        
        parser.add_argument(
            '--centro-costo',
            type=str,
            help='Centro de costo específico (opcional)',
            default=None
        )
        
        parser.add_argument(
            '--familia',
            type=str,
            choices=['PDD', 'ADIT'],
            help='Filtrar solo por familia específica (PDD o ADIT)',
            default=None
        )
        
        parser.add_argument(
            '--todos-ddh',
            action='store_true',
            help='Sincronizar todos los centros de costo DDH automáticamente'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada del proceso'
        )

    def handle(self, *args, **options):
        periodo = options['periodo']
        centro_costo = options['centro_costo']
        familia = options['familia']
        todos_ddh = options['todos_ddh']
        verbose = options['verbose']
        
        # Validar formato del periodo
        if not (periodo.isdigit() and len(periodo) == 6):
            self.stdout.write(
                self.style.ERROR(
                    f'Formato de periodo inválido: {periodo}. '
                    'Debe ser YYYYMM (ej: 202601)'
                )
            )
            sys.exit(1)
        
        # Si se especifica --todos-ddh, ejecutar sincronización masiva
        if todos_ddh:
            self._sincronizar_todos_ddh(periodo, familia, verbose)
            return
        
        # Sincronización normal (un solo centro de costo)
        self._sincronizar_individual(periodo, centro_costo, familia, verbose)
    
    def _sincronizar_todos_ddh(self, periodo, familia, verbose):
        """Sincroniza todos los centros de costo DDH"""
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('SINCRONIZACIÓN MASIVA DDH - TODOS LOS CENTROS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Periodo: {periodo} ({self._format_periodo(periodo)})')
        
        if familia:
            self.stdout.write(f'Familia: {familia}')
        else:
            self.stdout.write('Familia: Todas')
        
        self.stdout.write('')
        self.stdout.write('Iniciando sincronización masiva de todos los centros DDH...')
        self.stdout.write('')
        
        try:
            inicio = timezone.now()
            
            resultado = abastecimiento_service.sincronizar_todos_ddh(
                periodo=periodo,
                solo_familia=familia
            )
            
            fin = timezone.now()
            duracion = (fin - inicio).total_seconds()
            
            # Mostrar resultados consolidados
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('RESULTADOS CONSOLIDADOS'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            self.stdout.write(f'✓ Centros de costo DDH configurados: {resultado["total_centros"]}')
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Centros procesados exitosamente: {resultado["centros_procesados"]}'
                )
            )
            
            if resultado['centros_con_error'] > 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ Centros con error: {resultado["centros_con_error"]}')
                )
            
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(f'✓ Total registros importados: {resultado["total_importados"]}')
            )
            self.stdout.write(
                self.style.WARNING(f'✓ Total registros actualizados: {resultado["total_actualizados"]}')
            )
            
            if resultado['total_brocas_creadas'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Total brocas creadas: {resultado["total_brocas_creadas"]}'
                    )
                )
            
            if resultado['total_errores'] > 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ Total errores: {resultado["total_errores"]}')
                )
            
            # Mostrar detalle por centro si verbose
            if verbose:
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('DETALLE POR CENTRO DE COSTO:'))
                self.stdout.write(self.style.SUCCESS('-' * 70))
                
                for centro, datos in resultado['resultados_por_centro'].items():
                    if 'error' in datos:
                        self.stdout.write(
                            self.style.ERROR(f'Centro {centro}: ERROR - {datos["error"]}')
                        )
                    else:
                        self.stdout.write(
                            f'Centro {centro}: '
                            f'API={datos["total_api"]}, '
                            f'Importados={datos["importados"]}, '
                            f'Actualizados={datos["actualizados"]}, '
                            f'Brocas={datos["brocas_creadas"]}'
                        )
            
            # Mostrar errores generales
            if resultado['errores'] and verbose:
                self.stdout.write('')
                self.stdout.write(self.style.ERROR('ERRORES GENERALES:'))
                for error in resultado['errores']:
                    self.stdout.write(self.style.ERROR(f'  - {error}'))
            
            self.stdout.write('')
            self.stdout.write(f'Tiempo de ejecución total: {duracion:.2f} segundos')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            # Mensaje final
            if resultado['centros_con_error'] == 0 and resultado['total_errores'] == 0:
                self.stdout.write(
                    self.style.SUCCESS('✓ Sincronización masiva completada exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠ Sincronización masiva completada con algunos errores. '
                        'Use --verbose para ver detalles.'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error crítico durante sincronización masiva: {str(e)}')
            )
            
            if verbose:
                import traceback
                self.stdout.write(self.style.ERROR('\nTraceback:'))
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
            
            sys.exit(1)
    
    def _sincronizar_individual(self, periodo, centro_costo, familia, verbose):
        """Sincroniza un solo centro de costo"""
        # Mostrar resumen de parámetros
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('SINCRONIZACIÓN DE ABASTECIMIENTOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Periodo: {periodo} ({self._format_periodo(periodo)})')
        
        if centro_costo:
            self.stdout.write(f'Centro de costo: {centro_costo}')
        else:
            self.stdout.write('Centro de costo: Todos (por defecto en settings)')
        
        if familia:
            self.stdout.write(f'Familia: {familia}')
        else:
            self.stdout.write('Familia: Todas')
        
        self.stdout.write('')
        self.stdout.write('Iniciando sincronización...')
        self.stdout.write('')
        
        # Ejecutar sincronización
        try:
            inicio = timezone.now()
            
            resultado = abastecimiento_service.sincronizar_periodo(
                periodo=periodo,
                centro_costo=centro_costo,
                solo_familia=familia
            )
            
            fin = timezone.now()
            duracion = (fin - inicio).total_seconds()
            
            # Mostrar resultados
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('RESULTADOS DE SINCRONIZACIÓN'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            self.stdout.write(f'✓ Total de registros en API: {resultado["total_api"]}')
            self.stdout.write(
                self.style.SUCCESS(f'✓ Registros importados: {resultado["importados"]}')
            )
            self.stdout.write(
                self.style.WARNING(f'✓ Registros actualizados: {resultado["actualizados"]}')
            )
            
            if resultado['brocas_creadas'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Nuevas brocas registradas en historial: {resultado["brocas_creadas"]}'
                    )
                )
            
            if resultado['errores'] > 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ Errores: {resultado["errores"]}')
                )
                
                if verbose and resultado['detalles_errores']:
                    self.stdout.write('')
                    self.stdout.write(self.style.ERROR('Detalles de errores:'))
                    for error in resultado['detalles_errores']:
                        self.stdout.write(self.style.ERROR(f'  - {error}'))
            else:
                self.stdout.write(self.style.SUCCESS('✓ Sin errores'))
            
            self.stdout.write('')
            self.stdout.write(f'Tiempo de ejecución: {duracion:.2f} segundos')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            # Mensaje final
            if resultado['errores'] == 0:
                self.stdout.write(
                    self.style.SUCCESS('✓ Sincronización completada exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠ Sincronización completada con errores. '
                        'Use --verbose para ver detalles.'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error crítico durante sincronización: {str(e)}')
            )
            
            if verbose:
                import traceback
                self.stdout.write(self.style.ERROR('\nTraceback:'))
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
            
            sys.exit(1)
    
    def _format_periodo(self, periodo: str) -> str:
        """Formatea el periodo YYYYMM a texto legible"""
        try:
            year = periodo[:4]
            month = periodo[4:]
            
            meses = {
                '01': 'Enero', '02': 'Febrero', '03': 'Marzo',
                '04': 'Abril', '05': 'Mayo', '06': 'Junio',
                '07': 'Julio', '08': 'Agosto', '09': 'Septiembre',
                '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
            }
            
            return f'{meses.get(month, month)} {year}'
        except:
            return periodo
