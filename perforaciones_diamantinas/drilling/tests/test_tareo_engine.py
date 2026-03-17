from django.test import TestCase
from datetime import date, timedelta
from ..utils.tareo_service import TareoEngine
from ..models import Cliente, Contrato, Trabajador


class TareoEngineTests(TestCase):
    def setUp(self):
        # Crear cliente y contrato con dia_cambio_guardia = Lunes (0)
        self.cliente = Cliente.objects.create(nombre='Cliente Test')
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            nombre_contrato='Contrato Test',
            dia_cambio_guardia=0
        )

        # Trabajadores para cada guardia
        self.trab_a = Trabajador.objects.create(dni='A001', nombres='A Test', apepat='One', contrato=self.contrato, guardia_asignada='A')
        self.trab_b = Trabajador.objects.create(dni='B001', nombres='B Test', apepat='Two', contrato=self.contrato, guardia_asignada='B')
        self.trab_c = Trabajador.objects.create(dni='C001', nombres='C Test', apepat='Three', contrato=self.contrato, guardia_asignada='C')

        # Forzar ancla conocida
        self.fecha_ancla = TareoEngine._fecha_ancla_contrato(self.contrato, referencia=date(2026, 3, 16))

    def test_offsets_and_states_on_anchor(self):
        # On fecha_ancla:
        self.assertEqual(TareoEngine.estado_para_fecha(self.trab_a, self.fecha_ancla), 'TD')
        self.assertEqual(TareoEngine.estado_para_fecha(self.trab_c, self.fecha_ancla), 'TN')
        self.assertEqual(TareoEngine.estado_para_fecha(self.trab_b, self.fecha_ancla), 'DL')

    def test_cycle_progression(self):
        # 7 days after anchor
        d7 = self.fecha_ancla + timedelta(days=7)
        self.assertEqual(TareoEngine.estado_para_fecha(self.trab_a, d7), 'TN')
        self.assertEqual(TareoEngine.estado_para_fecha(self.trab_c, d7), 'DL')
        self.assertEqual(TareoEngine.estado_para_fecha(self.trab_b, d7), 'TD')

    def test_proyectar_rango_length_and_determinism(self):
        inicio = self.fecha_ancla
        fin = inicio + timedelta(days=20)
        proy = TareoEngine.proyectar_rango(self.trab_a, inicio, fin)
        self.assertEqual(len(proy), 21)
        # determinismo: same call yields same sequence
        proy2 = TareoEngine.proyectar_rango(self.trab_a, inicio, fin)
        self.assertEqual(proy, proy2)

    def test_all_states_present_in_cycle(self):
        # Ensure within 21-day cycle we have TD, TN, DL at expected counts
        inicio = self.fecha_ancla
        fin = inicio + timedelta(days=20)
        proy = TareoEngine.proyectar_rango(self.trab_a, inicio, fin)
        estados = [p['estado'] for p in proy]
        self.assertEqual(estados.count('TD'), 7)
        self.assertEqual(estados.count('TN'), 7)
        self.assertEqual(estados.count('DL'), 7)
