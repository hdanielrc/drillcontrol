"""
Comando para sincronizar brocas que fueron guardadas sin datos del API.

Busca TurnoComplemento sin tipo_complemento (porque la broca no estaba en el API)
y los actualiza si ahora ya existe el producto en TipoComplemento.

Uso:
    python manage.py sincronizar_brocas_pendientes
    python manage.py sincronizar_brocas_pendientes --dry-run  # Ver qué se actualizaría sin hacer cambios
    python manage.py sincronizar_brocas_pendientes --serie=409381  # Sincronizar una serie específica
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from drilling.models import TurnoComplemento, TipoComplemento, HistorialBroca
from decimal import Decimal


class Command(BaseCommand):
    help = 'Sincroniza brocas que fueron guardadas sin datos del API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se actualizaría sin hacer cambios',
        )
        parser.add_argument(
            '--serie',
            type=str,
            help='Sincronizar solo una serie específica',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        serie_especifica = options.get('serie')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('SINCRONIZACIÓN DE BROCAS PENDIENTES'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN: No se harán cambios reales\n'))
        
        # Buscar TurnoComplemento sin tipo_complemento (guardadas sin API)
        query = TurnoComplemento.objects.filter(tipo_complemento__isnull=True)
        
        if serie_especifica:
            query = query.filter(codigo_serie=serie_especifica)
            self.stdout.write(f'\n🔍 Buscando serie específica: {serie_especifica}')
        
        pendientes = query.select_related('turno').order_by('codigo_serie', 'turno__fecha')
        
        if not pendientes.exists():
            self.stdout.write(self.style.SUCCESS('\n✓ No hay brocas pendientes de sincronizar'))
            return
        
        self.stdout.write(f'\n📊 Total de registros pendientes: {pendientes.count()}\n')
        
        # Agrupar por serie para mostrar resumen
        series_pendientes = {}
        for tc in pendientes:
            serie = tc.codigo_serie
            if serie not in series_pendientes:
                series_pendientes[serie] = []
            series_pendientes[serie].append(tc)
        
        self.stdout.write(f'📦 Series únicas pendientes: {len(series_pendientes)}\n')
        
        # Procesar cada serie
        sincronizadas = 0
        no_encontradas = 0
        errores = 0
        
        for serie, turnos_complementos in series_pendientes.items():
            self.stdout.write(f'\n{"─" * 70}')
            self.stdout.write(f'Serie: {serie} ({len(turnos_complementos)} usos)')
            
            # Buscar el producto en TipoComplemento por serie
            producto = TipoComplemento.objects.filter(serie=serie).first()
            
            if not producto:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Producto no encontrado en API (aún pendiente)'))
                no_encontradas += 1
                
                # Mostrar detalles de los turnos
                for tc in turnos_complementos[:3]:  # Solo primeros 3
                    self.stdout.write(f'    - Turno {tc.turno_id} ({tc.turno.fecha}): {tc.metros_turno_calc}m')
                if len(turnos_complementos) > 3:
                    self.stdout.write(f'    ... y {len(turnos_complementos) - 3} usos más')
                continue
            
            # Producto encontrado
            self.stdout.write(self.style.SUCCESS(f'  ✓ Producto encontrado: {producto.nombre}'))
            self.stdout.write(f'    Categoría: {producto.categoria}')
            self.stdout.write(f'    Código: {producto.codigo or "N/A"}')
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'    [DRY-RUN] Se actualizarían {len(turnos_complementos)} registros'))
                sincronizadas += 1
            else:
                try:
                    with transaction.atomic():
                        # Actualizar todos los TurnoComplemento de esta serie
                        actualizados = TurnoComplemento.objects.filter(
                            id__in=[tc.id for tc in turnos_complementos]
                        ).update(tipo_complemento=producto)
                        
                        # Actualizar o crear HistorialBroca
                        historial, created = HistorialBroca.objects.get_or_create(
                            serie=serie,
                            defaults={
                                'tipo_complemento': producto,
                                'contrato_actual': turnos_complementos[0].turno.contrato,
                                'fecha_primer_uso': min(tc.turno.fecha for tc in turnos_complementos),
                                'estado': 'EN_USO'
                            }
                        )
                        
                        if not created:
                            # Si ya existía, solo actualizar el tipo_complemento
                            historial.tipo_complemento = producto
                            historial.save(update_fields=['tipo_complemento'])
                        
                        self.stdout.write(self.style.SUCCESS(f'    ✓ {actualizados} registros actualizados'))
                        if created:
                            self.stdout.write(self.style.SUCCESS(f'    ✓ HistorialBroca creado'))
                        else:
                            self.stdout.write(self.style.SUCCESS(f'    ✓ HistorialBroca actualizado'))
                        
                        sincronizadas += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ✗ Error: {str(e)}'))
                    errores += 1
        
        # Resumen final
        self.stdout.write(f'\n{"=" * 70}')
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write(f'{"=" * 70}')
        self.stdout.write(f'✓ Series sincronizadas:     {sincronizadas}')
        self.stdout.write(f'⚠️  Series no encontradas:    {no_encontradas}')
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errores:                  {errores}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  Esto fue un DRY-RUN. Ejecuta sin --dry-run para aplicar cambios.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Sincronización completada'))
        
        self.stdout.write('')
