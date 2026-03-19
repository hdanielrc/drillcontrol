from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase

from drilling.utils.tareo_service import TareoEngine, TareoService


class TareoEngineProjectionTest(SimpleTestCase):
    def _trabajador(self, guardia, dia_cambio=3):
        contrato = SimpleNamespace(dia_cambio_guardia=dia_cambio)
        return SimpleNamespace(
            id=1,
            contrato=contrato,
            guardia_asignada=guardia,
            regimen_laboral='14x7',
            fecha_inicio_ciclo=None,
        )

    def test_rotacion_a_b_c_mantiene_dos_guardias_trabajando(self):
        fecha_ancla = date(2026, 2, 26)

        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('A'), fecha_ancla), 'TD')
        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('B'), fecha_ancla), 'TN')
        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('C'), fecha_ancla), 'DL')

        fecha_segundo_bloque = date(2026, 3, 5)
        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('A'), fecha_segundo_bloque), 'TN')
        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('B'), fecha_segundo_bloque), 'DL')
        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('C'), fecha_segundo_bloque), 'TD')

        fecha_tercer_bloque = date(2026, 3, 12)
        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('A'), fecha_tercer_bloque), 'DL')
        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('B'), fecha_tercer_bloque), 'TD')
        self.assertEqual(TareoEngine.estado_para_fecha(self._trabajador('C'), fecha_tercer_bloque), 'TN')

    def test_calcular_estado_dia_mapea_dl_a_descanso(self):
        trabajador_c = self._trabajador('C')
        trabajador_a = self._trabajador('A')

        self.assertEqual(TareoService.calcular_estado_dia(trabajador_a, date(2026, 2, 26)), 'TD')
        self.assertEqual(TareoService.calcular_estado_dia(trabajador_c, date(2026, 2, 26)), 'DESCANSO')
