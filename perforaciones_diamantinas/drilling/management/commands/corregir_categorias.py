"""
Comando Django para corregir las categorías de TipoComplemento
basándose en palabras clave en el nombre del producto
"""
from django.core.management.base import BaseCommand
from drilling.models import TipoComplemento


class Command(BaseCommand):
    help = 'Corrige las categorías de productos basándose en su nombre'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin guardar cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("CORRIGIENDO CATEGORÍAS DE PRODUCTOS"))
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: No se guardarán cambios"))
        self.stdout.write("=" * 80)
        
        # Definir reglas de categorización basadas en palabras clave
        reglas = [
            {
                'keywords': ['REAMER', 'REAMING'],
                'categoria': 'REAMING_SHELL',
                'descripcion': 'Reaming Shells'
            },
            {
                'keywords': ['ZAPATA', 'SHOE'],
                'categoria': 'ZAPATA',
                'descripcion': 'Zapatas'
            },
            {
                'keywords': ['CORE LIFTER', 'LIFTER'],
                'categoria': 'CORE_LIFTER',
                'descripcion': 'Core Lifters'
            },
            {
                'keywords': ['DRILL BIT', 'BIT', 'BROCA'],
                'categoria': 'BROCA',
                'descripcion': 'Brocas',
                'exclude': ['REAMER', 'REAMING', 'ZAPATA', 'SHOE', 'LIFTER']
            }
        ]
        
        productos = TipoComplemento.objects.all()
        total = productos.count()
        corregidos = 0
        sin_cambios = 0
        
        self.stdout.write(f"\nTotal de productos a revisar: {total}\n")
        
        for producto in productos:
            nombre_upper = producto.nombre.upper()
            categoria_anterior = producto.categoria
            categoria_nueva = None
            
            # Buscar coincidencia con las reglas
            for regla in reglas:
                # Verificar palabras de exclusión
                if 'exclude' in regla:
                    if any(excl in nombre_upper for excl in regla['exclude']):
                        continue
                
                # Verificar palabras clave
                if any(kw in nombre_upper for kw in regla['keywords']):
                    categoria_nueva = regla['categoria']
                    break
            
            # Si no se encontró categoría, marcar como desconocido
            if categoria_nueva is None:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Serie {producto.serie}: '{producto.nombre}' - Sin categoría detectada")
                )
                continue
            
            # Solo actualizar si cambió
            if categoria_anterior != categoria_nueva:
                if not dry_run:
                    producto.categoria = categoria_nueva
                    producto.save()
                
                corregidos += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Serie {producto.serie}")
                )
                self.stdout.write(f"  Nombre: {producto.nombre}")
                self.stdout.write(f"  Anterior: '{categoria_anterior}' → Nuevo: '{categoria_nueva}'")
                self.stdout.write("")
            else:
                sin_cambios += 1
        
        # Resumen
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("RESUMEN"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total productos revisados: {total}")
        self.stdout.write(self.style.SUCCESS(f"Productos corregidos: {corregidos}"))
        self.stdout.write(f"Sin cambios: {sin_cambios}")
        
        if dry_run and corregidos > 0:
            self.stdout.write(
                self.style.WARNING(f"\nEjecuta sin --dry-run para aplicar {corregidos} cambios")
            )
