"""
Comando Django para re-clasificar TipoComplemento:
  - categoria  (BROCA, ZAPATA, REAMING_SHELL, CORE_LIFTER)
  - marca      (Boart Longyear, Boyles Bros, Diamantec, etc.)
  - calibre    (HQ, NQ, BQ, PQ, HWL, NWL, etc.)
  - altura     (12mm, 16mm, 20mm)
  - serie_bit  (X8, X10, NG-9, UP 7-10)

Usa la función inferir_tipo_desde_descripcion() del modelo para detectar
automáticamente estos datos a partir del campo nombre/descripcion.
"""
from django.core.management.base import BaseCommand
from drilling.models import TipoComplemento, inferir_tipo_desde_descripcion


class Command(BaseCommand):
    help = 'Re-clasifica productos PDD: detecta categoria, marca, calibre, altura y serie_bit desde la descripcion'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin guardar cambios',
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Sobreescribe marca/calibre aunque ya tengan valor',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        forzar = options['forzar']

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("RE-CLASIFICACIÓN DE PRODUCTOS DIAMANTADOS"))
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: No se guardarán cambios"))
        if forzar:
            self.stdout.write(self.style.WARNING("--forzar: Se sobreescribirán marca/calibre existentes"))
        self.stdout.write("=" * 80)

        productos = TipoComplemento.objects.all()
        total = productos.count()
        actualizados = 0
        sin_cambios = 0

        self.stdout.write(f"\nTotal de productos a revisar: {total}\n")

        for producto in productos:
            # Usar nombre o descripcion para inferir
            texto_base = producto.descripcion or producto.nombre or ''
            cat_nueva, marca_nueva, calibre_nuevo, altura_nueva, serie_bit_nuevo = inferir_tipo_desde_descripcion(texto_base)

            cambios = {}

            # Categoria: actualizar si está vacía o si cambió
            if not producto.categoria or producto.categoria != cat_nueva:
                cambios['categoria'] = (producto.categoria, cat_nueva)

            # Marca: actualizar solo si está vacía (o --forzar)
            if marca_nueva and (not producto.marca or forzar):
                if producto.marca != marca_nueva:
                    cambios['marca'] = (producto.marca, marca_nueva)

            # Calibre: actualizar solo si está vacío (o --forzar)
            if calibre_nuevo and (not producto.calibre or forzar):
                if producto.calibre != calibre_nuevo:
                    cambios['calibre'] = (producto.calibre, calibre_nuevo)

            # Altura: actualizar solo si está vacía (o --forzar)
            if altura_nueva and (not producto.altura or forzar):
                if producto.altura != altura_nueva:
                    cambios['altura'] = (producto.altura, altura_nueva)

            # Serie bit: actualizar solo si está vacía (o --forzar)
            if serie_bit_nuevo and (not producto.serie_bit or forzar):
                if producto.serie_bit != serie_bit_nuevo:
                    cambios['serie_bit'] = (producto.serie_bit, serie_bit_nuevo)

            if cambios:
                if not dry_run:
                    if 'categoria' in cambios:
                        producto.categoria = cambios['categoria'][1]
                    if 'marca' in cambios:
                        producto.marca = cambios['marca'][1]
                    if 'calibre' in cambios:
                        producto.calibre = cambios['calibre'][1]
                    if 'altura' in cambios:
                        producto.altura = cambios['altura'][1]
                    if 'serie_bit' in cambios:
                        producto.serie_bit = cambios['serie_bit'][1]
                    producto.save(update_fields=list(cambios.keys()))

                actualizados += 1
                self.stdout.write(
                    self.style.SUCCESS(f"[OK] {producto.serie or 'SIN-SERIE'} | {producto.nombre[:50]}")
                )
                for campo, (antes, despues) in cambios.items():
                    self.stdout.write(f"   {campo}: '{antes or '(vacio)'}' -> '{despues}'")
            else:
                sin_cambios += 1

        # Resumen por categoria
        from django.db.models import Count
        resumen = (
            TipoComplemento.objects.values('categoria')
            .annotate(total=Count('id'))
            .order_by('categoria')
        )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("RESUMEN"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total productos revisados : {total}")
        self.stdout.write(self.style.SUCCESS(f"Actualizados             : {actualizados}"))
        self.stdout.write(f"Sin cambios              : {sin_cambios}")

        if not dry_run:
            self.stdout.write("\nDistribución actual por tipo:")
            for r in resumen:
                cat = r['categoria'] or 'Sin categoria'
                self.stdout.write(f"  {cat:<20} {r['total']:>4} productos")

        if dry_run and actualizados > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nEjecuta sin --dry-run para aplicar {actualizados} cambios"
                )
            )


