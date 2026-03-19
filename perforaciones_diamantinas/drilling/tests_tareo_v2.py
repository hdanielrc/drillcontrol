from datetime import date
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from drilling.models import AsistenciaDiaria, Cliente, Contrato, Trabajador
from drilling.utils.tareo_service import TareoService

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
