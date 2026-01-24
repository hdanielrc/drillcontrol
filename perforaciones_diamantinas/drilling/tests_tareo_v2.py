"""
=============================================================================
TESTS UNITARIOS PARA TAREO V2
=============================================================================

Ejecutar con: python manage.py test drilling.tests_tareo_v2
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date, timedelta
from drilling.models import (
    Cliente, Contrato, Cargo, Trabajador, AsistenciaDiaria
)
from drilling.utils.tareo_service import TareoService

User = get_user_model()


class AsistenciaDiariaModelTest(TestCase):
    """Tests para el modelo AsistenciaDiaria"""
    
    def setUp(self):
        # Crear datos de prueba
        self.cliente = Cliente.objects.create(nombre='Cliente Test')
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            nombre_contrato='Contrato Test',
            estado='ACTIVO'
        )
        self.cargo = Cargo.objects.create(
            nombre='Perforista',
            descripcion='Test'
        )
        self.trabajador = Trabajador.objects.create(
            contrato=self.contrato,
            nombres='Juan',
            apellidos='Pérez',
            dni='12345678',
            cargo=self.cargo,
            estado='ACTIVO',
            regimen_laboral='14x7',
            fecha_inicio_ciclo=date(2026, 1, 1),
            guardia_asignada='A'
        )
        self.user = User.objects.create_user(
            username='admin',
            password='test123',
            contrato=self.contrato
        )
    
    def test_crear_asistencia(self):
        """Test: Crear registro de asistencia"""
        asistencia = AsistenciaDiaria.objects.create(
            empleado=self.trabajador,
            fecha=date(2026, 1, 15),
            estado='TRABAJO',
            es_proyeccion=True,
            registrado_por=self.user
        )
        
        self.assertEqual(asistencia.empleado, self.trabajador)
        self.assertEqual(asistencia.estado, 'TRABAJO')
        self.assertTrue(asistencia.es_proyeccion)
        self.assertEqual(asistencia.guardia_snapshot, 'A')
    
    def test_constraint_unico(self):
        """Test: Constraint único empleado+fecha"""
        AsistenciaDiaria.objects.create(
            empleado=self.trabajador,
            fecha=date(2026, 1, 15),
            estado='TRABAJO'
        )
        
        # Intentar crear duplicado debe fallar
        with self.assertRaises(Exception):
            AsistenciaDiaria.objects.create(
                empleado=self.trabajador,
                fecha=date(2026, 1, 15),
                estado='DESCANSO'
            )
    
    def test_snapshot_guardia_automatico(self):
        """Test: Snapshot de guardia se captura automáticamente"""
        asistencia = AsistenciaDiaria.objects.create(
            empleado=self.trabajador,
            fecha=date(2026, 1, 15),
            estado='TRABAJO'
        )
        
        self.assertEqual(asistencia.guardia_snapshot, 'A')


class TareoServiceTest(TestCase):
    """Tests para el servicio de tareo"""
    
    def setUp(self):
        # Crear datos de prueba
        self.cliente = Cliente.objects.create(nombre='Cliente Test')
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            nombre_contrato='Contrato Test',
            estado='ACTIVO'
        )
        self.cargo = Cargo.objects.create(nombre='Perforista')
        
        # Crear trabajadores con diferentes regímenes
        self.trabajador_14x7 = Trabajador.objects.create(
            contrato=self.contrato,
            nombres='Juan',
            apellidos='Pérez',
            dni='12345678',
            cargo=self.cargo,
            estado='ACTIVO',
            regimen_laboral='14x7',
            fecha_inicio_ciclo=date(2026, 1, 1),
            guardia_asignada='A'
        )
        
        self.trabajador_20x10 = Trabajador.objects.create(
            contrato=self.contrato,
            nombres='María',
            apellidos='García',
            dni='87654321',
            cargo=self.cargo,
            estado='ACTIVO',
            regimen_laboral='20x10',
            fecha_inicio_ciclo=date(2026, 1, 1),
            guardia_asignada='B'
        )
        
        self.user = User.objects.create_user(
            username='admin',
            password='test123',
            contrato=self.contrato
        )
    
    def test_calcular_estado_dia_14x7(self):
        """Test: Cálculo de estado para régimen 14x7"""
        # Día 1 del ciclo = TRABAJO
        estado = TareoService.calcular_estado_dia(
            self.trabajador_14x7,
            date(2026, 1, 1)
        )
        self.assertEqual(estado, 'TRABAJO')
        
        # Día 14 del ciclo = TRABAJO
        estado = TareoService.calcular_estado_dia(
            self.trabajador_14x7,
            date(2026, 1, 14)
        )
        self.assertEqual(estado, 'TRABAJO')
        
        # Día 15 del ciclo = DESCANSO (primer día de descanso)
        estado = TareoService.calcular_estado_dia(
            self.trabajador_14x7,
            date(2026, 1, 15)
        )
        self.assertEqual(estado, 'DESCANSO')
        
        # Día 21 del ciclo = DESCANSO (último día de descanso)
        estado = TareoService.calcular_estado_dia(
            self.trabajador_14x7,
            date(2026, 1, 21)
        )
        self.assertEqual(estado, 'DESCANSO')
        
        # Día 22 del ciclo = TRABAJO (inicia nuevo ciclo)
        estado = TareoService.calcular_estado_dia(
            self.trabajador_14x7,
            date(2026, 1, 22)
        )
        self.assertEqual(estado, 'TRABAJO')
    
    def test_generar_proyeccion_mensual(self):
        """Test: Generación de proyección mensual"""
        resultado = TareoService.generar_proyeccion_mensual(
            anio=2026,
            mes=1,
            contrato=self.contrato,
            sobrescribir=False
        )
        
        # Verificar estadísticas
        self.assertEqual(resultado['trabajadores_procesados'], 2)
        self.assertGreater(resultado['registros_creados'], 0)
        self.assertEqual(len(resultado['errores']), 0)
        
        # Verificar registros en BD
        registros = AsistenciaDiaria.objects.filter(
            fecha__year=2026,
            fecha__month=1
        )
        self.assertGreater(registros.count(), 0)
        
        # Verificar que todos son proyecciones
        self.assertTrue(all(r.es_proyeccion for r in registros))
    
    def test_corregir_asistencia(self):
        """Test: Corrección de asistencia"""
        # Crear proyección primero
        AsistenciaDiaria.objects.create(
            empleado=self.trabajador_14x7,
            fecha=date(2026, 1, 15),
            estado='TRABAJO',
            es_proyeccion=True
        )
        
        # Corregir
        asistencia = TareoService.corregir_asistencia(
            empleado_id=self.trabajador_14x7.id,
            fecha=date(2026, 1, 15),
            nuevo_estado='FALTA',
            usuario=self.user,
            observaciones='Test de corrección'
        )
        
        # Verificar corrección
        self.assertEqual(asistencia.estado, 'FALTA')
        self.assertFalse(asistencia.es_proyeccion)
        self.assertEqual(asistencia.observaciones, 'Test de corrección')
        self.assertEqual(asistencia.registrado_por, self.user)
    
    def test_obtener_matriz_tareo(self):
        """Test: Obtención de matriz pivoteada"""
        # Crear asistencias de prueba
        for dia in range(1, 8):
            AsistenciaDiaria.objects.create(
                empleado=self.trabajador_14x7,
                fecha=date(2026, 1, dia),
                estado='TRABAJO',
                es_proyeccion=True
            )
        
        # Obtener matriz
        matriz = TareoService.obtener_matriz_tareo(
            contrato=self.contrato,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 31)
        )
        
        # Verificar estructura
        self.assertEqual(len(matriz), 2)  # 2 trabajadores
        self.assertIn('trabajador', matriz[0])
        self.assertIn('guardia', matriz[0])
        self.assertIn('asistencias', matriz[0])
        
        # Verificar datos
        self.assertEqual(matriz[0]['guardia'], 'A')
        self.assertGreater(len(matriz[0]['asistencias']), 0)


class TareoViewsTest(TestCase):
    """Tests para las vistas del tareo"""
    
    def setUp(self):
        # Crear datos de prueba
        self.cliente = Cliente.objects.create(nombre='Cliente Test')
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            nombre_contrato='Contrato Test',
            estado='ACTIVO'
        )
        self.cargo = Cargo.objects.create(nombre='Perforista')
        self.trabajador = Trabajador.objects.create(
            contrato=self.contrato,
            nombres='Juan',
            apellidos='Pérez',
            dni='12345678',
            cargo=self.cargo,
            estado='ACTIVO',
            regimen_laboral='14x7',
            fecha_inicio_ciclo=date(2026, 1, 1),
            guardia_asignada='A'
        )
        
        # Crear usuario con permisos
        self.user = User.objects.create_user(
            username='admin',
            password='test123',
            contrato=self.contrato,
            rol='MANAGER_CONTRATO'
        )
        
        self.client = Client()
        self.client.login(username='admin', password='test123')
    
    def test_tareo_v2_mensual_view_get(self):
        """Test: GET de vista principal"""
        response = self.client.get(reverse('tareo_v2_mensual'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('matriz_tareo', response.context)
        self.assertIn('dias_rango', response.context)
        self.assertIn('estados_choices', response.context)
    
    def test_api_generar_proyeccion(self):
        """Test: API de generación de proyección"""
        response = self.client.post(
            reverse('api_generar_proyeccion'),
            {
                'contrato_id': self.contrato.id,
                'anio': 2026,
                'mes': 1,
                'sobrescribir': 'false'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)


class PerformanceTest(TestCase):
    """Tests de rendimiento"""
    
    def setUp(self):
        # Crear datos de prueba a escala
        self.cliente = Cliente.objects.create(nombre='Cliente Test')
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            nombre_contrato='Contrato Test',
            estado='ACTIVO'
        )
        self.cargo = Cargo.objects.create(nombre='Perforista')
        
        # Crear 100 trabajadores
        trabajadores = []
        for i in range(100):
            trabajadores.append(
                Trabajador(
                    contrato=self.contrato,
                    nombres=f'Trabajador{i}',
                    apellidos=f'Test{i}',
                    dni=f'{10000000 + i}',
                    cargo=self.cargo,
                    estado='ACTIVO',
                    regimen_laboral='14x7',
                    fecha_inicio_ciclo=date(2026, 1, 1),
                    guardia_asignada='A'
                )
            )
        Trabajador.objects.bulk_create(trabajadores)
    
    def test_proyeccion_masiva_performance(self):
        """Test: Rendimiento de proyección masiva (100 trabajadores x 30 días)"""
        import time
        
        start = time.time()
        resultado = TareoService.generar_proyeccion_mensual(
            anio=2026,
            mes=1,
            contrato=self.contrato
        )
        end = time.time()
        
        tiempo_transcurrido = end - start
        
        # Verificar que se completó en menos de 5 segundos
        self.assertLess(tiempo_transcurrido, 5.0)
        
        # Verificar cantidad de registros
        self.assertEqual(resultado['trabajadores_procesados'], 100)
        self.assertGreater(resultado['registros_creados'], 2500)  # ~100 * 30
        
        print(f"\n⏱️  Tiempo: {tiempo_transcurrido:.2f}s")
        print(f"📝 Registros: {resultado['registros_creados']}")
        print(f"🚀 Throughput: {resultado['registros_creados'] / tiempo_transcurrido:.0f} reg/s")
