from datetime import date
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from drilling.models import AsistenciaDiaria, AsistenciaTrabajador, Cliente, Contrato, FechaCerrada, Trabajador
from drilling.tareo_compat import CierreMensualTareo
from drilling.utils.tareo_service import TareoService, TareoEngine
from drilling.utils.attendance_projector import AttendanceProjector

User = get_user_model()


class TareoBaseTestCase(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente Test')
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            nombre_contrato='Contrato Test',
            estado='ACTIVO',
        )
        self.otro_contrato = Contrato.objects.create(
            cliente=self.cliente,
            nombre_contrato='Contrato Externo',
            estado='ACTIVO',
        )
        self.trabajador = Trabajador.objects.create(
            contrato=self.contrato,
            nombres='Juan',
            apepat='Perez',
            apemat='Quispe',
            dni='12345678',
            cargo='Perforista',
            estado='ACTIVO',
            regimen_laboral='14x7',
            fecha_inicio_ciclo=date(2026, 3, 1),
            guardia_asignada='A',
        )
        self.trabajador_externo = Trabajador.objects.create(
            contrato=self.otro_contrato,
            nombres='Mario',
            apepat='Soto',
            apemat='Diaz',
            dni='87654321',
            cargo='Ayudante',
            estado='ACTIVO',
            regimen_laboral='14x7',
            fecha_inicio_ciclo=date(2026, 3, 1),
            guardia_asignada='B',
        )


class AsistenciaDiariaModelTest(TareoBaseTestCase):
    def test_crear_asistencia_captura_snapshot(self):
        user = User.objects.create_user(
            username='admin-model',
            password='test123',
            contrato=self.contrato,
            role='ADMINISTRADOR',
        )

        asistencia = AsistenciaDiaria.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 3, 15),
            estado='TRABAJO',
            es_proyeccion=True,
            registrado_por=user,
        )

        self.assertEqual(asistencia.trabajador, self.trabajador)
        self.assertEqual(asistencia.guardia_snapshot, 'A')
        self.assertTrue(asistencia.es_proyeccion)


class TareoServiceTest(TareoBaseTestCase):
    def test_corregir_asistencia_vuelve_real_el_registro(self):
        user = User.objects.create_user(
            username='admin-service',
            password='test123',
            contrato=self.contrato,
            role='ADMINISTRADOR',
        )
        AsistenciaDiaria.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 3, 15),
            estado='TRABAJO',
            es_proyeccion=True,
        )

        asistencia = TareoService.corregir_asistencia(
            trabajador_id=self.trabajador.id,
            fecha=date(2026, 3, 15),
            nuevo_estado='FALTA',
            usuario=user,
            observaciones='Correccion manual',
        )

        self.assertEqual(asistencia.estado, 'FALTA')
        self.assertFalse(asistencia.es_proyeccion)
        self.assertEqual(asistencia.observaciones, 'Correccion manual')
        self.assertEqual(asistencia.registrado_por, user)


class TareoViewsTest(TareoBaseTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='manager',
            password='test123',
            contrato=self.contrato,
            role='MANAGER_CONTRATO',
        )
        self.client = Client()
        self.client.login(username='manager', password='test123')

    def test_manager_contrato_puede_ver_tareo_v2(self):
        response = self.client.get(reverse('tareo-v2-mensual'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('matriz_tareo', response.context)
        self.assertIn('dias_rango', response.context)
        self.assertIn('estados_choices', response.context)

    def test_api_corregir_asistencia_bloquea_otro_contrato(self):
        response = self.client.post(
            reverse('api-corregir-asistencia'),
            data=json.dumps({
                'trabajador_id': self.trabajador_externo.id,
                'fecha': '2026-03-15',
                'estado': 'FALTA',
                'observaciones': 'Intento invalido',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(AsistenciaDiaria.objects.count(), 0)

    def test_api_guardar_dia_bloquea_otro_contrato(self):
        response = self.client.post(
            reverse('api-guardar-dia-tareo'),
            data=json.dumps({
                'fecha': '2026-03-15',
                'contrato_id': self.otro_contrato.id,
                'asistencias': [
                    {
                        'trabajador_id': self.trabajador_externo.id,
                        'estado': 'TRABAJO',
                    }
                ],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(AsistenciaDiaria.objects.count(), 0)


# =============================================================================
# NUEVOS TESTS: turno_inicio, AttendanceProjector, limpiar_mes
# =============================================================================

class TurnoInicioEngineTest(TareoBaseTestCase):
    """Verifica que TareoEngine respeta contrato.turno_inicio."""

    def _make_trabajador_guardia_b(self, turno_inicio='TD'):
        """Crea un trabajador con guardia B (offset=0, en epoch = índice 0 en ciclo)."""
        self.contrato.turno_inicio = turno_inicio
        self.contrato.save(update_fields=['turno_inicio', 'updated_at'])
        trabajador = Trabajador.objects.create(
            contrato=self.contrato,
            nombres='Carlos',
            apepat='Mamani',
            apemat=f'Q_{turno_inicio}',
            dni=f'9999{turno_inicio}',
            cargo='Operador',
            estado='ACTIVO',
            regimen_laboral='14x7',
            guardia_asignada='B',
        )
        return trabajador

    def test_turno_inicio_td_proyecta_td_primero(self):
        """Con turno_inicio='TD', guardia B en epoch (idx=0) debe ser TD."""
        t = self._make_trabajador_guardia_b(turno_inicio='TD')
        estado = TareoEngine.estado_para_fecha(t, TareoService.HISTORICO_START)
        self.assertEqual(estado, 'TD')

    def test_turno_inicio_tn_proyecta_tn_primero(self):
        """Con turno_inicio='TN', guardia B en epoch (idx=0) debe ser TN."""
        t = self._make_trabajador_guardia_b(turno_inicio='TN')
        estado = TareoEngine.estado_para_fecha(t, TareoService.HISTORICO_START)
        self.assertEqual(estado, 'TN')

    def test_turno_inicio_td_ciclo_completo_21_dias(self):
        """Ciclo 21 días con turno_inicio='TD': primeros 7=TD, siguientes 7=TN, últimos 7=DL."""
        from datetime import timedelta
        t = self._make_trabajador_guardia_b(turno_inicio='TD')
        fecha_base = TareoService.HISTORICO_START
        estados = [TareoEngine.estado_para_fecha(t, fecha_base + timedelta(days=i)) for i in range(21)]
        self.assertEqual(estados.count('TD'), 7)
        self.assertEqual(estados.count('TN'), 7)
        self.assertEqual(estados.count('DL'), 7)
        self.assertTrue(all(e == 'TD' for e in estados[:7]))

    def test_turno_inicio_tn_ciclo_completo_21_dias(self):
        """Ciclo 21 días con turno_inicio='TN': primeros 7=TN, siguientes 7=TD, últimos 7=DL."""
        from datetime import timedelta
        t = self._make_trabajador_guardia_b(turno_inicio='TN')
        fecha_base = TareoService.HISTORICO_START
        estados = [TareoEngine.estado_para_fecha(t, fecha_base + timedelta(days=i)) for i in range(21)]
        self.assertTrue(all(e == 'TN' for e in estados[:7]))
        self.assertTrue(all(e == 'TD' for e in estados[7:14]))
        self.assertTrue(all(e == 'DL' for e in estados[14:]))


class DefaultEstadoValidoTest(TareoBaseTestCase):
    """Verifica que el campo default de AsistenciaDiaria sea una clave válida."""

    def test_default_estado_es_valido(self):
        claves_validas = {k for k, _ in AsistenciaDiaria.ESTADO_CHOICES}
        campo = AsistenciaDiaria._meta.get_field('estado')
        self.assertIn(
            campo.default,
            claves_validas,
            f"AsistenciaDiaria.estado default='{campo.default}' no está en ESTADO_CHOICES",
        )


class LimpiarMesV1V2Test(TareoBaseTestCase):
    """Verifica que limpiar_asistencias_mes elimina registros de V1 y V2."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='manager-limpiar',
            password='test123',
            contrato=self.contrato,
            role='MANAGER_CONTRATO',
        )
        self.client = Client()
        self.client.login(username='manager-limpiar', password='test123')

    def test_limpiar_mes_borra_v1_y_v2(self):
        """Limpiar mes debe eliminar registros de AsistenciaTrabajador Y AsistenciaDiaria."""
        fecha = date(2026, 3, 10)
        AsistenciaTrabajador.objects.create(
            trabajador=self.trabajador,
            fecha=fecha,
            estado='TD',
            registrado_por=self.user,
        )
        AsistenciaDiaria.objects.create(
            trabajador=self.trabajador,
            fecha=fecha,
            estado='TD',
            es_proyeccion=True,
        )

        response = self.client.post(
            reverse('tareo-limpiar-mes'),
            data=json.dumps({
                'contrato_id': self.contrato.id,
                'fecha_inicio': '2026-03-01',
                'fecha_fin': '2026-03-25',
                'mantener_protegidos': False,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(AsistenciaTrabajador.objects.filter(trabajador=self.trabajador).count(), 0)
        self.assertEqual(AsistenciaDiaria.objects.filter(trabajador=self.trabajador).count(), 0)


class AttendanceProjectorTest(TareoBaseTestCase):
    """Tests para la clase AttendanceProjector."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='admin-proj',
            password='test123',
            contrato=self.contrato,
            role='ADMINISTRADOR',
        )
        self.trabajador.fecha_inicio_labores = TareoService.HISTORICO_START
        self.trabajador.save(update_fields=['fecha_inicio_labores'])

    def test_proyector_continua_desde_ultimo_real(self):
        """AttendanceProjector comienza desde el día siguiente al último registro real."""
        from datetime import timedelta
        ultimo_real = TareoService.HISTORICO_START + timedelta(days=5)
        AsistenciaDiaria.objects.create(
            trabajador=self.trabajador,
            fecha=ultimo_real,
            estado='TD',
            es_proyeccion=False,
        )
        fecha_objetivo = TareoService.HISTORICO_START + timedelta(days=10)
        proj = AttendanceProjector(self.trabajador.id, fecha_objetivo)
        resultado = proj.project()
        self.assertEqual(resultado[0].fecha, ultimo_real + timedelta(days=1))

    def test_proyector_trunca_en_fecha_cese(self):
        """La proyección se detiene el día después de fecha_cese."""
        from datetime import timedelta
        fecha_cese = TareoService.HISTORICO_START + timedelta(days=3)
        self.trabajador.fecha_cese = fecha_cese
        self.trabajador.save(update_fields=['fecha_cese'])
        fecha_objetivo = TareoService.HISTORICO_START + timedelta(days=10)
        proj = AttendanceProjector(self.trabajador.id, fecha_objetivo)
        resultado = proj.project()
        ultimo = resultado[-1]
        self.assertEqual(ultimo.fuente, 'FIN_CONTRATO')

    def test_proyector_respeta_correcciones_manuales(self):
        """Un día con es_proyeccion=False no debe sobreescribirse."""
        from datetime import timedelta
        fecha_manual = TareoService.HISTORICO_START + timedelta(days=1)
        AsistenciaDiaria.objects.create(
            trabajador=self.trabajador,
            fecha=fecha_manual,
            estado='V',
            es_proyeccion=False,
        )
        fecha_objetivo = TareoService.HISTORICO_START + timedelta(days=5)
        proj = AttendanceProjector(self.trabajador.id, fecha_objetivo)
        resultado = proj.project()
        dias_manuales = [d for d in resultado if d.fecha == fecha_manual]
        self.assertEqual(len(dias_manuales), 1)
        self.assertEqual(dias_manuales[0].estado, 'V')
        self.assertEqual(dias_manuales[0].fuente, 'MANUAL')

    def test_proyector_respeta_fecha_cerrada(self):
        """Una FechaCerrada existente debe devolver fuente='CERRADO'."""
        from datetime import timedelta
        fecha_cerrada = TareoService.HISTORICO_START + timedelta(days=2)
        AsistenciaDiaria.objects.create(
            trabajador=self.trabajador,
            fecha=fecha_cerrada,
            estado='TD',
            es_proyeccion=True,
        )
        FechaCerrada.objects.create(
            contrato=self.contrato,
            fecha=fecha_cerrada,
            cerrado_por=self.user,
            motivo='Cierre de auditoría',
        )
        fecha_objetivo = TareoService.HISTORICO_START + timedelta(days=5)
        proj = AttendanceProjector(self.trabajador.id, fecha_objetivo)
        resultado = proj.project()
        dias_cerrados = [d for d in resultado if d.fecha == fecha_cerrada]
        self.assertEqual(len(dias_cerrados), 1)
        self.assertEqual(dias_cerrados[0].fuente, 'CERRADO')

