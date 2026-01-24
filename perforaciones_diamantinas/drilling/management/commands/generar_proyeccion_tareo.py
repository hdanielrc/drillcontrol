"""
Comando de Django para generar proyección mensual de tareo automáticamente.

Uso:
    python manage.py generar_proyeccion_tareo
    python manage.py generar_proyeccion_tareo --mes 2 --anio 2026
    python manage.py generar_proyeccion_tareo --contrato 1 --sobrescribir
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from drilling.utils.tareo_service import generar_proyeccion_mensual
from drilling.models import Contrato
from datetime import date


class Command(BaseCommand):
    help = 'Genera la proyección mensual de asistencia (tareo) basada en regímenes laborales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mes',
            type=int,
            default=date.today().month,
            help='Mes para generar la proyección (1-12). Default: mes actual'
        )
        parser.add_argument(
            '--anio',
            type=int,
            default=date.today().year,
            help='Año para generar la proyección. Default: año actual'
        )
        parser.add_argument(
            '--contrato',
            type=int,
            default=None,
            help='ID del contrato específico. Default: todos los contratos activos'
        )
        parser.add_argument(
            '--sobrescribir',
            action='store_true',
            help='Eliminar proyecciones previas antes de generar nuevas'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular ejecución sin guardar cambios en BD'
        )

    def handle(self, *args, **options):
        mes = options['mes']
        anio = options['anio']
        contrato_id = options['contrato']
        sobrescribir = options['sobrescribir']
        dry_run = options['dry_run']
        
        # Validaciones
        if not (1 <= mes <= 12):
            raise CommandError(f'Mes inválido: {mes}. Debe estar entre 1 y 12.')
        
        # Obtener contrato si se especificó
        contrato = None
        if contrato_id:
            try:
                contrato = Contrato.objects.get(id=contrato_id, estado='ACTIVO')
                self.stdout.write(f'📋 Contrato: {contrato.nombre_contrato}')
            except Contrato.DoesNotExist:
                raise CommandError(f'Contrato con ID {contrato_id} no encontrado o no está activo')
        else:
            self.stdout.write('📋 Procesando todos los contratos activos')
        
        # Mostrar resumen
        self.stdout.write(
            self.style.WARNING(f'\n🗓️  Generando proyección para: {mes}/{anio}')
        )
        if sobrescribir:
            self.stdout.write(
                self.style.WARNING('⚠️  Modo SOBRESCRIBIR: Las proyecciones previas serán eliminadas')
            )
        if dry_run:
            self.stdout.write(
                self.style.NOTICE('🔍 Modo DRY-RUN: No se guardarán cambios')
            )
        
        # Confirmación (solo si no es dry-run)
        if not dry_run and not options.get('no_input', False):
            confirm = input('\n¿Desea continuar? (s/n): ')
            if confirm.lower() != 's':
                self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
                return
        
        self.stdout.write('\n⏳ Procesando...\n')
        
        try:
            if dry_run:
                # Modo simulación
                self.stdout.write(
                    self.style.NOTICE('🔍 Modo simulación - No se realizarán cambios en BD')
                )
                # Aquí podrías agregar lógica de simulación si es necesario
                resultado = {
                    'trabajadores_procesados': 0,
                    'registros_creados': 0,
                    'registros_existentes_respetados': 0,
                    'errores': []
                }
            else:
                # Ejecución real
                resultado = generar_proyeccion_mensual(
                    anio=anio,
                    mes=mes,
                    contrato=contrato,
                    sobrescribir=sobrescribir
                )
            
            # Mostrar resultados
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✅ PROYECCIÓN COMPLETADA'))
            self.stdout.write('='*60)
            self.stdout.write(f"👥 Trabajadores procesados: {resultado['trabajadores_procesados']}")
            self.stdout.write(f"📝 Registros creados: {resultado['registros_creados']}")
            self.stdout.write(f"🔒 Registros existentes respetados: {resultado['registros_existentes_respetados']}")
            
            if resultado['errores']:
                self.stdout.write(
                    self.style.ERROR(f"\n⚠️  Errores encontrados: {len(resultado['errores'])}")
                )
                for error in resultado['errores'][:5]:  # Mostrar max 5 errores
                    self.stdout.write(f"  - {error}")
                if len(resultado['errores']) > 5:
                    self.stdout.write(f"  ... y {len(resultado['errores']) - 5} errores más")
            else:
                self.stdout.write(self.style.SUCCESS('\n✨ Sin errores'))
            
            self.stdout.write('='*60 + '\n')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Error al generar proyección: {str(e)}')
            )
            raise CommandError(str(e))
