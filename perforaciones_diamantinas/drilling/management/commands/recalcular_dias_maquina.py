from django.core.management.base import BaseCommand
from django.db.models import Count, Min, Max

from drilling.models import AsistenciaDiaria, ResumenDiasMaquina


class Command(BaseCommand):
    help = 'Regenera la tabla resumen_dias_maquina con los días de asignación por trabajador/máquina.'

    def handle(self, *args, **options):
        self.stdout.write('Calculando días por trabajador/máquina desde AsistenciaDiaria...')

        filas = (
            AsistenciaDiaria.objects
            .filter(maquina_snapshot__isnull=False)
            .values('trabajador_id', 'maquina_snapshot_id')
            .annotate(
                total_dias=Count('fecha'),
                primera_asignacion=Min('fecha'),
                ultima_asignacion=Max('fecha'),
            )
        )

        ResumenDiasMaquina.objects.all().delete()

        registros = [
            ResumenDiasMaquina(
                trabajador_id=f['trabajador_id'],
                maquina_id=f['maquina_snapshot_id'],
                total_dias=f['total_dias'],
                primera_asignacion=f['primera_asignacion'],
                ultima_asignacion=f['ultima_asignacion'],
            )
            for f in filas
        ]

        ResumenDiasMaquina.objects.bulk_create(registros)

        self.stdout.write(
            self.style.SUCCESS(f'Listo: {len(registros)} combinaciones trabajador/máquina procesadas.')
        )
