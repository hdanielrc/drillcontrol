from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import *
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import *
import json
from datetime import timedelta


class TurnoStateTests(TestCase):
    def setUp(self):
        # Create contract with duration 8 hours
        self.contrato = Contrato.objects.create(
            nombre_contrato='CT-TEST',
            cliente=Cliente.objects.create(nombre='C1'),
            duracion_turno=8,
        )
        # Tipo turno and actividad
        self.tipo_turno = TipoTurno.objects.create(nombre='Mañana')
        self.tipo_actividad = TipoActividad.objects.create(nombre='Perforación')
        # Maquina and sondaje
        self.maquina = Maquina.objects.create(contrato=self.contrato, nombre='Maq-1', tipo='T1')
        self.sondaje = Sondaje.objects.create(
            contrato=self.contrato,
            nombre_sondaje='S1',
            fecha_inicio=timezone.now().date(),
            profundidad=100,
            inclinacion=0,
            cota_collar=1000,
            estado='ACTIVO',
        )
        # base date used in tests to avoid collisions with existing test DB state
        self.base_date = timezone.now().date()
        # Users: supervisor and admin
        self.supervisor = CustomUser.objects.create_user(
            username='sup', password='pass', role='SUPERVISOR', contrato=self.contrato
        )
        self.admin = CustomUser.objects.create_user(
            username='admin', password='pass', role='ADMIN_SISTEMA', is_system_admin=True
        )

    def test_auto_mark_completado_when_activities_sum_duration(self):
        c = Client()
        c.force_login(self.supervisor)

        fecha = self.base_date.isoformat()
        actividades = [
            {
                'actividad_id': self.tipo_actividad.id,
                'hora_inicio': '08:00',
                'hora_fin': '12:00',
                'observaciones': '',
            },
            {
                'actividad_id': self.tipo_actividad.id,
                'hora_inicio': '12:00',
                'hora_fin': '16:00',
                'observaciones': '',
            },
        ]

        post_data = {
            'sondaje': str(self.sondaje.id),
            'maquina': str(self.maquina.id),
            'tipo_turno': str(self.tipo_turno.id),
            'fecha': fecha,
            'actividades': json.dumps(actividades),
        }

        response = c.post(reverse('crear-turno-completo'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # Check that a turno was created and is COMPLETADO
        turno = Turno.objects.first()
        self.assertIsNotNone(turno)
        self.assertEqual(turno.estado, 'COMPLETADO')

    def test_approve_only_admin_or_supervisor(self):
        # Create a turno in BORRADOR using a different date to avoid collisions
        fecha_nueva = self.base_date + timedelta(days=1)
        turno = Turno.objects.create(
            sondaje=self.sondaje,
            maquina=self.maquina,
            tipo_turno=self.tipo_turno,
            fecha=fecha_nueva,
        )

        c = Client()
        # normal user (operator) cannot approve
        op = CustomUser.objects.create_user(username='op', password='p', role='OPERADOR', contrato=self.contrato)
        c.force_login(op)
        r = c.post(reverse('turno-approve', args=[turno.id]), follow=True)
        turno.refresh_from_db()
        self.assertEqual(turno.estado, 'BORRADOR')

        # supervisor can approve
        c.force_login(self.supervisor)
        r = c.get(reverse('turno-approve', args=[turno.id]))
        self.assertEqual(r.status_code, 200)
        r = c.post(reverse('turno-approve', args=[turno.id]), follow=True)
        turno.refresh_from_db()
        self.assertEqual(turno.estado, 'APROBADO')

        # admin can approve (create another turno)
        turno2 = Turno.objects.create(
            sondaje=self.sondaje,
            maquina=self.maquina,
            tipo_turno=self.tipo_turno,
            fecha=fecha_nueva + timedelta(days=1),
        )
        c.force_login(self.admin)
        r = c.post(reverse('turno-approve', args=[turno2.id]), follow=True)
        turno2.refresh_from_db()
        self.assertEqual(turno2.estado, 'APROBADO')

    def test_block_save_when_insufficient_activity_hours(self):
        """Posting a turno with total activity hours less than contrato.duracion_turno should be blocked."""
        c = Client()
        c.force_login(self.supervisor)

        fecha = self.base_date.isoformat()
        # Only 2 hours of activity while contrato.duracion_turno is 8
        actividades = [
            {
                'actividad_id': self.tipo_actividad.id,
                'hora_inicio': '08:00',
                'hora_fin': '10:00',
                'observaciones': '',
            }
        ]

        post_data = {
            'sondaje': str(self.sondaje.id),
            'maquina': str(self.maquina.id),
            'tipo_turno': str(self.tipo_turno.id),
            'fecha': fecha,
            'actividades': json.dumps(actividades),
        }

        response = c.post(reverse('crear-turno-completo'), post_data, follow=True)
        # The view should re-render the form (status 200) and no Turno should be created
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Turno.objects.count(), 0)
        # Ensure the error message about missing hours is present
        msgs = []
        if response.context and 'messages' in response.context:
            msgs = [str(m) for m in response.context['messages']]
        self.assertTrue(any('Faltan horas al turno' in m for m in msgs), f"Messages did not contain expected text. Got: {msgs}")

