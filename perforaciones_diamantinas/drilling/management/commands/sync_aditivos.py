"""
Comando para sincronizar aditivos de perforación (ADIT) desde la API de Vilbragroup.

Este comando obtiene todos los aditivos del centro de costo especificado
y los sincroniza con el modelo TipoAditivo en la base de datos local.

Uso:
    python manage.py sync_aditivos --contrato-id=1
    python manage.py sync_aditivos --centro-costo=000003 --contrato-id=1
    python manage.py sync_aditivos --contrato-id=1 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from drilling.api_client import get_api_client
from drilling.models import TipoAditivo, Contrato
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza aditivos de perforación (ADIT) desde la API de Vilbragroup al modelo TipoAditivo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--contrato-id',
            type=int,
            required=True,
            help='ID del contrato al que pertenecen los aditivos'
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
            help='Muestra información detallada de cada aditivo sincronizado'
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
        self.stdout.write(self.style.SUCCESS(f'SINCRONIZACIÓN DE ADITIVOS DE PERFORACIÓN (ADIT)'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))
        self.stdout.write(f'Contrato: {contrato.nombre_contrato} (ID: {contrato.id})')
        self.stdout.write(f'Centro de Costo: {centro_costo}')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios en la base de datos\n'))

        # Obtener aditivos desde la API
        self.stdout.write('\nObteniendo aditivos desde la API...')
        api_client = get_api_client()
        
        try:
            aditivos = api_client.obtener_aditivos(centro_costo)
        except Exception as e:
            raise CommandError(f'Error al obtener aditivos de la API: {str(e)}')

        if not aditivos:
            self.stdout.write(self.style.WARNING('No se encontraron aditivos en la API'))
            return

        self.stdout.write(self.style.SUCCESS(f'Se obtuvieron {len(aditivos)} aditivos de la API\n'))

        # Contadores
        creados = 0
        actualizados = 0
        sin_cambios = 0
        errores = 0
        procesados = 0
        total = len(aditivos)

        # Pre-cargar códigos existentes para optimizar
        self.stdout.write('Cargando aditivos existentes...')
        codigos_existentes = set(
            TipoAditivo.objects.filter(
                contrato=contrato,
                codigo__isnull=False
            ).values_list('codigo', flat=True)
        )
        self.stdout.write(f'  {len(codigos_existentes)} aditivos encontrados en BD\n')

        # Procesar cada aditivo
        self.stdout.write(f'{"─"*70}')
        self.stdout.write('Procesando aditivos...\n')

        # Listas para bulk operations
        aditivos_a_crear = []
        aditivos_a_actualizar = []

        for aditivo in aditivos:
            procesados += 1
            codigo = aditivo.get('codigo', '') or ''
            descripcion = aditivo.get('descripcion', '') or ''
            
            # Strip solo si es string
            if isinstance(codigo, str):
                codigo = codigo.strip()
            if isinstance(descripcion, str):
                descripcion = descripcion.strip()
            
            # Mostrar progreso cada 5 aditivos
            if procesados % 5 == 0 or procesados == total:
                self.stdout.write(f'  Progreso: {procesados}/{total} aditivos procesados...')

            # Validar descripción es requerida, código es opcional
            if not descripcion:
                if verbose:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Aditivo sin descripción omitido'))
                errores += 1
                continue
            
            # Si no hay código, generar uno basado en descripción
            if not codigo:
                # Generar código único basado en descripción (primeros 20 caracteres + hash)
                import hashlib
                codigo = f"ADIT_{hashlib.md5(descripcion.encode()).hexdigest()[:8].upper()}"

            try:
                if dry_run:
                    # En modo dry-run, solo verificar si existe
                    if codigo in codigos_existentes:
                        sin_cambios += 1
                    else:
                        creados += 1
                else:
                    # Preparar para bulk operation
                    if codigo in codigos_existentes:
                        # Aditivo existe, agregar a lista de actualización
                        aditivos_a_actualizar.append({
                            'codigo': codigo,
                            'nombre': descripcion,
                            'contrato': contrato
                        })
                    else:
                        # Aditivo nuevo, agregar a lista de creación
                        aditivos_a_crear.append(TipoAditivo(
                            codigo=codigo,
                            nombre=descripcion,
                            contrato=contrato
                        ))

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error en código {codigo}: {str(e)}')
                )
                errores += 1
                logger.exception(f'Error sincronizando aditivo con código {codigo}')

        # Ejecutar bulk operations
        if not dry_run:
            with transaction.atomic():
                # Bulk create
                if aditivos_a_crear:
                    self.stdout.write(f'\n  Creando {len(aditivos_a_crear)} aditivos nuevos...')
                    TipoAditivo.objects.bulk_create(aditivos_a_crear, ignore_conflicts=True)
                    creados = len(aditivos_a_crear)
                    if verbose:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ {creados} aditivos creados'))

                # Bulk update
                if aditivos_a_actualizar:
                    self.stdout.write(f'\n  Actualizando {len(aditivos_a_actualizar)} aditivos existentes...')
                    for adit_data in aditivos_a_actualizar:
                        try:
                            TipoAditivo.objects.filter(
                                codigo=adit_data['codigo'],
                                contrato=adit_data['contrato']
                            ).update(nombre=adit_data['nombre'])
                            actualizados += 1
                        except Exception as e:
                            errores += 1
                            if verbose:
                                self.stdout.write(self.style.ERROR(f'  ✗ Error actualizando {adit_data["codigo"]}: {e}'))
                    
                    if verbose:
                        self.stdout.write(self.style.WARNING(f'  ↻ {actualizados} aditivos actualizados'))
                
                sin_cambios = total - creados - actualizados - errores

        # Resumen final
        self.stdout.write(f'\n{"─"*70}')
        self.stdout.write(self.style.SUCCESS('\nRESUMEN DE SINCRONIZACIÓN:'))
        self.stdout.write(f'  Total aditivos en API: {len(aditivos)}')
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
