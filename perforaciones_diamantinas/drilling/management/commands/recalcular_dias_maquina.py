from django.core.management.base import BaseCommand
from django.db import connection

from drilling.models import ResumenDiasMaquina


_SQL_RESUMEN = """
    SELECT
        trabajador_id,
        maquina_id,
        COUNT(*)          AS total_dias,
        MIN(fecha)        AS primera_asignacion,
        MAX(fecha)        AS ultima_asignacion
    FROM public.vw_tareo_trabajador_maquina
    GROUP BY trabajador_id, maquina_id
"""


class Command(BaseCommand):
    help = (
        'Regenera resumen_dias_maquina desde la vista vw_tareo_trabajador_maquina '
        '(tareo V2). Fuente: tareo_entry con maquina_snapshot asignada y estado de trabajo.'
    )

    def handle(self, *args, **options):
        self.stdout.write('Leyendo vw_tareo_trabajador_maquina...')

        with connection.cursor() as cursor:
            cursor.execute(_SQL_RESUMEN)
            filas = cursor.fetchall()

        registros = [
            ResumenDiasMaquina(
                trabajador_id=trabajador_id,
                maquina_id=maquina_id,
                total_dias=total_dias,
                primera_asignacion=primera_asignacion,
                ultima_asignacion=ultima_asignacion,
            )
            for trabajador_id, maquina_id, total_dias, primera_asignacion, ultima_asignacion in filas
        ]

        ResumenDiasMaquina.objects.all().delete()
        ResumenDiasMaquina.objects.bulk_create(registros)

        self.stdout.write(
            self.style.SUCCESS(
                f'Listo: {len(registros)} combinaciones trabajador/máquina procesadas.'
            )
        )
