from django.core.management.base import BaseCommand
from drilling.models import *
from datetime import date

class Command(BaseCommand):
    help = 'Carga datos iniciales del sistema'

    def handle(self, *args, **options):
        # Crear tipos de turno
        tipos_turno = [
            {'nombre': 'Mañana', 'descripcion': 'Turno de mañana 7:00 - 15:00'},
            {'nombre': 'Tarde', 'descripcion': 'Turno de tarde 15:00 - 23:00'},
            {'nombre': 'Noche', 'descripcion': 'Turno de noche 23:00 - 7:00'},
        ]
        
        for tipo_data in tipos_turno:
            TipoTurno.objects.get_or_create(**tipo_data)
        
        self.stdout.write(self.style.SUCCESS('Tipos de turno creados'))
        
        # Crear estados de turno
        estados = [
            {'nombre': 'Borrador', 'descripcion': 'Turno en proceso de creación'},
            {'nombre': 'Completado', 'descripcion': 'Turno completado'},
        ]
        
        for estado_data in estados:
            EstadoTurno.objects.get_or_create(**estado_data)
        
        # Crear actividades típicas
        actividades = [
            {'nombre': 'Perforación', 'descripcion': 'Actividad de perforación normal'},
            {'nombre': 'Entubado', 'descripcion': 'Instalación de tubería'},
            {'nombre': 'Recuperación de herramientas', 'descripcion': 'Recuperación de herramientas atascadas'},
            {'nombre': 'Mantenimiento preventivo', 'descripcion': 'Mantenimiento de equipos'},
            {'nombre': 'Cambio de broca', 'descripcion': 'Cambio de herramientas de perforación'},
            {'nombre': 'Lavado de pozo', 'descripcion': 'Limpieza y acondicionamiento del pozo'},
        ]
        
        for actividad_data in actividades:
            TipoActividad.objects.get_or_create(**actividad_data)
        
        self.stdout.write(self.style.SUCCESS('Actividades creadas'))
        
        # Crear unidades de medida
        unidades = [
            {'nombre': 'Kilogramos', 'simbolo': 'kg'},
            {'nombre': 'Litros', 'simbolo': 'L'},
            {'nombre': 'Metros', 'simbolo': 'm'},
            {'nombre': 'Unidades', 'simbolo': 'und'},
            {'nombre': 'Cajas', 'simbolo': 'cja'},
            {'nombre': 'Sacos', 'simbolo': 'sco'},
        ]
        
        for unidad_data in unidades:
            UnidadMedida.objects.get_or_create(**unidad_data)
        
        # Crear tipos de complemento - CORREGIDO
        complementos = [
            {'nombre': 'Broca Diamantada HQ', 'categoria': 'BROCA', 'descripcion': 'Broca diamantada calibre HQ'},
            {'nombre': 'Broca Diamantada NQ', 'categoria': 'BROCA', 'descripcion': 'Broca diamantada calibre NQ'},
            {'nombre': 'Reaming Shell HQ', 'categoria': 'REAMING_SHELL', 'descripcion': 'Reaming Shell calibre HQ'},
            {'nombre': 'Zapata HQ', 'categoria': 'ZAPATA', 'descripcion': 'Zapata calibre HQ'},
            {'nombre': 'Core Lifter HQ', 'categoria': 'CORE_LIFTER', 'descripcion': 'Core Lifter calibre HQ'},  # CORREGIDO: sin tilde
        ]
        
        for comp_data in complementos:
            TipoComplemento.objects.get_or_create(**comp_data)
        
        # Crear tipos de aditivo
        unidad_kg = UnidadMedida.objects.get(simbolo='kg')
        unidad_l = UnidadMedida.objects.get(simbolo='L')
        
        aditivos = [
            {'nombre': 'Bentonita', 'categoria': 'BENTONITA', 'unidad_medida_default': unidad_kg},
            {'nombre': 'Polímero PAC', 'categoria': 'POLIMEROS', 'unidad_medida_default': unidad_kg},
            {'nombre': 'CMC HV', 'categoria': 'CMC', 'unidad_medida_default': unidad_kg},
            {'nombre': 'Soda Ash', 'categoria': 'SODA_ASH', 'unidad_medida_default': unidad_kg},
            {'nombre': 'Dispersante', 'categoria': 'DISPERSANTE', 'unidad_medida_default': unidad_l},
        ]
        
        for adit_data in aditivos:
            TipoAditivo.objects.get_or_create(**adit_data)
        
        self.stdout.write(self.style.SUCCESS('Complementos y aditivos creados'))
        
        # Resto del código...
        try:
            contrato = Contrato.objects.get(nombre_contrato='Sistema Principal')
            
            # Crear trabajadores de ejemplo
            trabajadores = [
                {'nombre': 'Juan Pérez', 'cargo': 'OPERADOR_SENIOR', 'rut': '12345678-9'},
                {'nombre': 'María González', 'cargo': 'OPERADOR', 'rut': '98765432-1'},
                {'nombre': 'Carlos Rodríguez', 'cargo': 'AYUDANTE', 'rut': '11111111-1'},
                {'nombre': 'Ana Martínez', 'cargo': 'SUPERVISOR', 'rut': '22222222-2'},
                {'nombre': 'Pedro Silva', 'cargo': 'MECANICO', 'rut': '33333333-3'},
            ]
            
            for trab_data in trabajadores:
                Trabajador.objects.get_or_create(
                    contrato=contrato,
                    rut=trab_data['rut'],
                    defaults={
                        'nombre': trab_data['nombre'],
                        'cargo': trab_data['cargo'],
                        'fecha_ingreso': date.today(),
                        'is_active': True
                    }
                )
            
            # Crear máquinas de ejemplo
            maquinas = [
                {'nombre': 'Perforadora Atlas Copco CS14', 'tipo': 'Atlas Copco CS14', 'estado': 'OPERATIVO'},
                {'nombre': 'Perforadora Longyear LF90D', 'tipo': 'Longyear LF90D', 'estado': 'OPERATIVO'},
                {'nombre': 'Perforadora Boart Longyear LF230', 'tipo': 'Boart Longyear LF230', 'estado': 'MANTENIMIENTO'},
            ]
            
            for maq_data in maquinas:
                Maquina.objects.get_or_create(
                    contrato=contrato,
                    nombre=maq_data['nombre'],
                    defaults={
                        'tipo': maq_data['tipo'],
                        'estado': maq_data['estado']
                    }
                )
            
            # Crear sondajes de ejemplo
            sondajes = [
                {
                    'nombre_sondaje': 'DDH-001',
                    'fecha_inicio': date.today(),
                    'profundidad': 150.0,
                    'inclinacion': -60.0,
                    'cota_collar': 1200.0,
                    'estado': 'ACTIVO'
                },
                {
                    'nombre_sondaje': 'DDH-002', 
                    'fecha_inicio': date.today(),
                    'profundidad': 200.0,
                    'inclinacion': -75.0,
                    'cota_collar': 1180.0,
                    'estado': 'ACTIVO'
                }
            ]
            
            for sond_data in sondajes:
                Sondaje.objects.get_or_create(
                    contrato=contrato,
                    nombre_sondaje=sond_data['nombre_sondaje'],
                    defaults=sond_data
                )
            
            self.stdout.write(self.style.SUCCESS('Datos de ejemplo creados para el contrato'))
            
        except Contrato.DoesNotExist:
            self.stdout.write(self.style.WARNING('Contrato Sistema Principal no encontrado'))
        
        self.stdout.write(self.style.SUCCESS('Carga de datos iniciales completada'))
