"""
Comando para sincronizar productos diamantados (PDD) desde la API de Vilbragroup.

Este comando obtiene todos los productos diamantados del centro de costo especificado
y los sincroniza con el modelo TipoComplemento en la base de datos local.

Uso:
    python manage.py sync_productos_diamantados --contrato-id=1
    python manage.py sync_productos_diamantados --centro-costo=000003 --contrato-id=1
    python manage.py sync_productos_diamantados --contrato-id=1 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from drilling.api_client import get_api_client
from drilling.models import TipoComplemento, Contrato
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza productos diamantados (PDD) desde la API de Vilbragroup al modelo TipoComplemento'

    def add_arguments(self, parser):
        parser.add_argument(
            '--contrato-id',
            type=int,
            required=True,
            help='ID del contrato al que pertenecen los productos'
        )
        parser.add_argument(
            '--centro-costo',
            type=str,
            help='Código del centro de costo (ej: 000003). Si no se proporciona, se usa el del contrato'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la sincronización sin hacer cambios en la base de datos'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Muestra información detallada de cada producto sincronizado'
        )

    def handle(self, *args, **options):
        contrato_id = options['contrato_id']
        centro_costo = options.get('centro_costo')
        dry_run = options['dry_run']
        verbose = options['verbose']

        # Obtener el contrato
        try:
            contrato = Contrato.objects.get(id=contrato_id)
        except Contrato.DoesNotExist:
            raise CommandError(f'No existe un contrato con ID {contrato_id}')

        # Si no se proporcionó centro de costo, usar el del contrato
        if not centro_costo:
            centro_costo = contrato.codigo_centro_costo
            if not centro_costo:
                raise CommandError(
                    f'El contrato {contrato.nombre_contrato} no tiene código de centro de costo configurado. '
                    'Proporciona uno con --centro-costo'
                )

        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS(f'SINCRONIZACIÓN DE PRODUCTOS DIAMANTADOS (PDD)'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))
        self.stdout.write(f'Contrato: {contrato.nombre_contrato} (ID: {contrato.id})')
        self.stdout.write(f'Centro de Costo: {centro_costo}')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios en la base de datos\n'))

        # Obtener productos desde la API
        self.stdout.write('\nObteniendo productos diamantados desde la API...')
        api_client = get_api_client()
        
        try:
            productos = api_client.obtener_productos_diamantados(centro_costo)
        except Exception as e:
            raise CommandError(f'Error al obtener productos de la API: {str(e)}')

        if not productos:
            self.stdout.write(self.style.WARNING('No se encontraron productos diamantados en la API'))
            return

        self.stdout.write(self.style.SUCCESS(f'Se obtuvieron {len(productos)} productos de la API\n'))

        # Contadores
        creados = 0
        actualizados = 0
        sin_cambios = 0
        errores = 0
        procesados = 0
        total = len(productos)

        # Pre-cargar series existentes para optimizar
        self.stdout.write('Cargando productos existentes...')
        series_existentes = set(
            TipoComplemento.objects.filter(serie__isnull=False)
            .values_list('serie', flat=True)
        )
        self.stdout.write(f'  {len(series_existentes)} productos encontrados en BD\n')

        # Procesar cada producto
        self.stdout.write(f'{"─"*70}')
        self.stdout.write('Procesando productos...\n')

        # Listas para bulk operations
        productos_a_crear = []
        productos_a_actualizar = []

        for producto in productos:
            procesados += 1
            codigo = producto.get('codigo', '') or ''
            serie = producto.get('serie', '') or ''
            descripcion = producto.get('descripcion', '') or ''
            
            # Strip solo si es string
            if isinstance(codigo, str):
                codigo = codigo.strip()
            if isinstance(serie, str):
                serie = serie.strip()
            if isinstance(descripcion, str):
                descripcion = descripcion.strip()
            
            # Mostrar progreso cada 50 productos
            if procesados % 50 == 0 or procesados == total:
                self.stdout.write(f'  Progreso: {procesados}/{total} productos procesados...')

            # Validar datos mínimos requeridos
            if not serie:
                errores += 1
                continue

            if not codigo:
                errores += 1
                continue

            try:
                if dry_run:
                    # En modo dry-run, solo verificar si existe
                    if serie in series_existentes:
                        sin_cambios += 1
                    else:
                        creados += 1
                else:
                    # Preparar para bulk operation
                    if serie in series_existentes:
                        # Producto existe, agregar a lista de actualización
                        productos_a_actualizar.append({
                            'serie': serie,
                            'nombre': descripcion or f'Producto {codigo}',
                            'codigo': codigo,
                            'contrato': contrato
                        })
                    else:
                        # Producto nuevo, agregar a lista de creación
                        productos_a_crear.append(TipoComplemento(
                            serie=serie,
                            nombre=descripcion or f'Producto {codigo}',
                            codigo=codigo,
                            contrato=contrato,
                            estado='NUEVO'
                        ))

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error en serie {serie}: {str(e)}')
                )
                errores += 1
                logger.exception(f'Error sincronizando producto con serie {serie}')

        # Ejecutar bulk operations
        if not dry_run:
            with transaction.atomic():
                # Bulk create
                if productos_a_crear:
                    self.stdout.write(f'\n  Creando {len(productos_a_crear)} productos nuevos...')
                    TipoComplemento.objects.bulk_create(productos_a_crear, ignore_conflicts=True)
                    creados = len(productos_a_crear)
                    if verbose:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ {creados} productos creados'))

                # Bulk update
                if productos_a_actualizar:
                    self.stdout.write(f'\n  Actualizando {len(productos_a_actualizar)} productos existentes...')
                    for prod_data in productos_a_actualizar:
                        try:
                            TipoComplemento.objects.filter(serie=prod_data['serie']).update(
                                nombre=prod_data['nombre'],
                                codigo=prod_data['codigo']
                            )
                            actualizados += 1
                        except Exception as e:
                            errores += 1
                            if verbose:
                                self.stdout.write(self.style.ERROR(f'  ✗ Error actualizando {prod_data["serie"]}: {e}'))
                    
                    if verbose:
                        self.stdout.write(self.style.WARNING(f'  ↻ {actualizados} productos actualizados'))
                
                sin_cambios = total - creados - actualizados - errores

        # Resumen final
        self.stdout.write(f'\n{"─"*70}')
        self.stdout.write(self.style.SUCCESS('\nRESUMEN DE SINCRONIZACIÓN:'))
        self.stdout.write(f'  Total productos en API: {len(productos)}')
        self.stdout.write(self.style.SUCCESS(f'  ✓ Creados: {creados}'))
        self.stdout.write(self.style.WARNING(f'  ↻ Actualizados: {actualizados}'))
        self.stdout.write(f'  • Sin cambios: {sin_cambios}')
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'  ✗ Errores: {errores}'))
        
        self.stdout.write(f'\n{"="*70}\n')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('Modo DRY-RUN completado. Ejecuta sin --dry-run para aplicar los cambios.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Sincronización completada exitosamente.')
            )
