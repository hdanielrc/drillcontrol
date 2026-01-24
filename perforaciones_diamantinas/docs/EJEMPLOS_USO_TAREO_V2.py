"""
=============================================================================
EJEMPLOS DE USO - TAREO V2
=============================================================================

Este archivo contiene ejemplos prácticos de cómo utilizar el nuevo sistema
de Tareo V2 desde diferentes contextos: shell de Django, comandos personalizados,
scripts de automatización, etc.
"""

# =============================================================================
# EJEMPLO 1: Generar Proyección desde Django Shell
# =============================================================================

"""
$ python manage.py shell

>>> from drilling.utils.tareo_service import TareoService
>>> from drilling.models import Contrato
>>> from datetime import date
>>> 
>>> # Obtener contrato
>>> contrato = Contrato.objects.get(nombre_contrato='Colquisirir')
>>> 
>>> # Generar proyección para enero 2026
>>> resultado = TareoService.generar_proyeccion_mensual(2026, 1, contrato)
>>> print(f"Registros creados: {resultado['registros_creados']}")
>>> print(f"Trabajadores procesados: {resultado['trabajadores_procesados']}")
"""

# =============================================================================
# EJEMPLO 2: Corregir Asistencia Individual
# =============================================================================

"""
>>> from drilling.utils.tareo_service import TareoService
>>> from drilling.models import CustomUser
>>> from datetime import date
>>> 
>>> # Obtener usuario que registra
>>> usuario = CustomUser.objects.get(username='admin')
>>> 
>>> # Corregir asistencia (cambiar de TRABAJO a FALTA)
>>> asistencia = TareoService.corregir_asistencia(
...     empleado_id=123,
...     fecha=date(2026, 1, 15),
...     nuevo_estado='FALTA',
...     usuario=usuario,
...     observaciones='Falta injustificada'
... )
>>> 
>>> print(f"Estado: {asistencia.estado}")
>>> print(f"Es proyección: {asistencia.es_proyeccion}")  # False (ahora es corrección)
"""

# =============================================================================
# EJEMPLO 3: Obtener Matriz de Tareo para Exportación
# =============================================================================

"""
>>> from drilling.utils.tareo_service import TareoService
>>> from drilling.models import Contrato
>>> from datetime import date
>>> 
>>> contrato = Contrato.objects.first()
>>> 
>>> # Obtener matriz de todo el mes
>>> matriz = TareoService.obtener_matriz_tareo(
...     contrato=contrato,
...     fecha_inicio=date(2026, 1, 1),
...     fecha_fin=date(2026, 1, 31)
... )
>>> 
>>> # Iterar sobre trabajadores
>>> for fila in matriz:
...     trabajador = fila['trabajador']
...     asistencias = fila['asistencias']
...     print(f"{trabajador.apellidos}, {trabajador.nombres} - Guardia {fila['guardia']}")
...     
...     # Contar días trabajados
...     dias_trabajo = sum(1 for a in asistencias.values() if a['estado'] == 'TRABAJO')
...     print(f"  Días trabajados: {dias_trabajo}")
"""

# =============================================================================
# EJEMPLO 4: Calcular Demanda de Refrigerios (Caso de Uso Real)
# =============================================================================

"""
>>> from drilling.models import AsistenciaDiaria
>>> from datetime import date
>>> 
>>> # Fecha específica
>>> fecha_consulta = date(2026, 1, 15)
>>> 
>>> # Contar trabajadores que requieren refrigerio (estado = TRABAJO)
>>> trabajadores_con_refrigerio = AsistenciaDiaria.objects.filter(
...     fecha=fecha_consulta,
...     estado='TRABAJO'
... ).count()
>>> 
>>> print(f"Refrigerios a solicitar para {fecha_consulta}: {trabajadores_con_refrigerio}")
>>> 
>>> # Agrupar por contrato
>>> from django.db.models import Count
>>> por_contrato = AsistenciaDiaria.objects.filter(
...     fecha=fecha_consulta,
...     estado='TRABAJO'
... ).values('empleado__contrato__nombre_contrato').annotate(
...     total=Count('id')
... )
>>> 
>>> for item in por_contrato:
...     print(f"{item['empleado__contrato__nombre_contrato']}: {item['total']} refrigerios")
"""

# =============================================================================
# EJEMPLO 5: Reporte de Ausentismo Mensual
# =============================================================================

"""
>>> from drilling.models import AsistenciaDiaria
>>> from django.db.models import Count, Q
>>> from datetime import date
>>> 
>>> # Filtros por mes
>>> mes = 1
>>> anio = 2026
>>> 
>>> # Ausentismo por tipo
>>> reporte_ausentismo = AsistenciaDiaria.objects.filter(
...     fecha__year=anio,
...     fecha__month=mes,
... ).exclude(
...     estado__in=['TRABAJO', 'DESCANSO']
... ).values('estado').annotate(
...     total=Count('id')
... ).order_by('-total')
>>> 
>>> print("📊 Reporte de Ausentismo:")
>>> for item in reporte_ausentismo:
...     print(f"  {item['estado']}: {item['total']} casos")
>>> 
>>> # Top 5 trabajadores con más faltas
>>> top_faltas = AsistenciaDiaria.objects.filter(
...     fecha__year=anio,
...     fecha__month=mes,
...     estado='FALTA'
... ).values(
...     'empleado__apellidos',
...     'empleado__nombres'
... ).annotate(
...     total_faltas=Count('id')
... ).order_by('-total_faltas')[:5]
>>> 
>>> print("\n⚠️  Top 5 trabajadores con más faltas:")
>>> for item in top_faltas:
...     print(f"  {item['empleado__apellidos']}, {item['empleado__nombres']}: {item['total_faltas']} faltas")
"""

# =============================================================================
# EJEMPLO 6: Actualización Masiva con Formset (Backend)
# =============================================================================

"""
>>> from drilling.utils.tareo_service import TareoService
>>> from drilling.models import CustomUser
>>> from datetime import date
>>> 
>>> # Datos del formset (simulado)
>>> formset_data = [
...     {
...         'empleado_id': 10,
...         'fecha': date(2026, 1, 15),
...         'estado': 'FALTA',
...         'observaciones': 'No presentó justificación'
...     },
...     {
...         'empleado_id': 11,
...         'fecha': date(2026, 1, 15),
...         'estado': 'TRABAJO',
...         'observaciones': ''
...     },
...     {
...         'empleado_id': 12,
...         'fecha': date(2026, 1, 15),
...         'estado': 'DM',
...         'observaciones': 'Descanso médico por 3 días'
...     },
... ]
>>> 
>>> usuario = CustomUser.objects.get(username='admin')
>>> 
>>> # Actualizar masivamente
>>> resultado = TareoService.actualizar_masivo_desde_formset(formset_data, usuario)
>>> 
>>> print(f"Actualizados: {resultado['actualizados']}")
>>> print(f"Creados: {resultado['creados']}")
>>> print(f"Errores: {len(resultado['errores'])}")
"""

# =============================================================================
# EJEMPLO 7: Script de Automatización - Proyección Mensual Automática
# =============================================================================

"""
Script para ejecutar como cronjob el día 1 de cada mes

Archivo: scripts/proyeccion_mensual_auto.py
"""

import os
import django
import sys
from datetime import date

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.utils.tareo_service import generar_proyeccion_mensual
from drilling.models import Contrato

def ejecutar_proyeccion_automatica():
    """
    Genera la proyección mensual para todos los contratos activos
    """
    hoy = date.today()
    
    # Determinar mes a proyectar (mes actual)
    mes = hoy.month
    anio = hoy.year
    
    print(f"📅 Iniciando proyección automática para {mes}/{anio}")
    
    # Obtener contratos activos
    contratos = Contrato.objects.filter(estado='ACTIVO')
    
    for contrato in contratos:
        print(f"\n🔄 Procesando: {contrato.nombre_contrato}")
        
        try:
            resultado = generar_proyeccion_mensual(
                anio=anio,
                mes=mes,
                contrato=contrato,
                sobrescribir=False
            )
            
            print(f"  ✅ Completado:")
            print(f"     - Trabajadores: {resultado['trabajadores_procesados']}")
            print(f"     - Registros: {resultado['registros_creados']}")
            
            if resultado['errores']:
                print(f"  ⚠️  Errores: {len(resultado['errores'])}")
                for error in resultado['errores'][:3]:
                    print(f"     - {error}")
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    print("\n✨ Proyección automática completada")

if __name__ == '__main__':
    ejecutar_proyeccion_automatica()

"""
Configurar en crontab (Linux):
0 1 1 * * /usr/bin/python /path/to/scripts/proyeccion_mensual_auto.py

Configurar en Task Scheduler (Windows):
- Trigger: Monthly, día 1, 01:00 AM
- Action: python C:\\path\\to\\scripts\\proyeccion_mensual_auto.py
"""

# =============================================================================
# EJEMPLO 8: Consulta Optimizada - Trabajadores en Operación Hoy
# =============================================================================

"""
>>> from drilling.models import AsistenciaDiaria, Trabajador
>>> from datetime import date
>>> 
>>> hoy = date.today()
>>> 
>>> # Trabajadores activos en operación hoy (con prefetch)
>>> trabajadores_activos = Trabajador.objects.filter(
...     estado='ACTIVO',
...     asistencias_diarias__fecha=hoy,
...     asistencias_diarias__estado='TRABAJO'
... ).select_related('cargo', 'contrato').prefetch_related('asistencias_diarias')
>>> 
>>> print(f"👷 Trabajadores activos hoy: {trabajadores_activos.count()}")
>>> 
>>> # Agrupar por guardia
>>> por_guardia = {}
>>> for trabajador in trabajadores_activos:
...     guardia = trabajador.guardia_asignada or 'SIN_GUARDIA'
...     por_guardia[guardia] = por_guardia.get(guardia, 0) + 1
>>> 
>>> print("\n📊 Por guardia:")
>>> for guardia, count in por_guardia.items():
...     print(f"  Guardia {guardia}: {count} trabajadores")
"""

# =============================================================================
# EJEMPLO 9: Migración de Datos Legacy a Nuevo Modelo
# =============================================================================

"""
Script para migrar datos del modelo AsistenciaTrabajador (legacy) al nuevo AsistenciaDiaria

>>> from drilling.models import AsistenciaTrabajador, AsistenciaDiaria
>>> from django.db import transaction
>>> from datetime import date
>>> 
>>> @transaction.atomic
... def migrar_rango_fechas(fecha_inicio, fecha_fin):
...     '''Migra registros de un rango de fechas'''
...     
...     # Obtener registros legacy
...     registros_legacy = AsistenciaTrabajador.objects.filter(
...         fecha__gte=fecha_inicio,
...         fecha__lte=fecha_fin
...     ).select_related('trabajador', 'registrado_por')
...     
...     registros_nuevos = []
...     errores = []
...     
...     for reg in registros_legacy:
...         try:
...             # Mapear estado (ajustar según nomenclatura)
...             estado_mapeado = reg.estado
...             
...             # Crear registro nuevo
...             nuevo = AsistenciaDiaria(
...                 empleado=reg.trabajador,
...                 fecha=reg.fecha,
...                 estado=estado_mapeado,
...                 guardia_snapshot=reg.guardia_snapshot,
...                 es_proyeccion=False,  # Datos históricos son correcciones
...                 observaciones=reg.observaciones,
...                 registrado_por=reg.registrado_por
...             )
...             registros_nuevos.append(nuevo)
...         
...         except Exception as e:
...             errores.append(f"Error en registro {reg.id}: {str(e)}")
...     
...     # Inserción masiva
...     if registros_nuevos:
...         AsistenciaDiaria.objects.bulk_create(
...             registros_nuevos,
...             batch_size=1000,
...             ignore_conflicts=True  # Ignorar duplicados
...         )
...     
...     print(f"✅ Migrados: {len(registros_nuevos)} registros")
...     print(f"⚠️  Errores: {len(errores)}")
...     
...     return len(registros_nuevos), errores
>>> 
>>> # Ejecutar migración
>>> migrados, errores = migrar_rango_fechas(
...     fecha_inicio=date(2025, 1, 1),
...     fecha_fin=date(2025, 12, 31)
... )
"""

# =============================================================================
# EJEMPLO 10: Integración con API Externa (Envío de Demanda de Servicios)
# =============================================================================

"""
Script para enviar proyección de servicios a sistema externo

>>> from drilling.models import AsistenciaDiaria
>>> from datetime import date, timedelta
>>> import requests
>>> 
>>> def enviar_proyeccion_servicios(fecha_inicio, fecha_fin, contrato_id):
...     '''Envía proyección de refrigerios/campamento a API externa'''
...     
...     # Obtener demanda diaria
...     demanda_diaria = []
...     
...     fecha_actual = fecha_inicio
...     while fecha_actual <= fecha_fin:
...         # Contar trabajadores que requieren servicio
...         count_refrigerios = AsistenciaDiaria.objects.filter(
...             empleado__contrato_id=contrato_id,
...             fecha=fecha_actual,
...             estado='TRABAJO'
...         ).count()
...         
...         demanda_diaria.append({
...             'fecha': fecha_actual.strftime('%Y-%m-%d'),
...             'cantidad_refrigerios': count_refrigerios,
...             'cantidad_campamento': count_refrigerios  # Asumiendo 1:1
...         })
...         
...         fecha_actual += timedelta(days=1)
...     
...     # Enviar a API externa
...     payload = {
...         'contrato_id': contrato_id,
...         'periodo': f"{fecha_inicio.strftime('%Y-%m')}",
...         'demanda': demanda_diaria
...     }
...     
...     response = requests.post(
...         'https://api.externa.com/servicios/proyeccion',
...         json=payload,
...         headers={'Authorization': 'Bearer TOKEN'}
...     )
...     
...     if response.status_code == 200:
...         print("✅ Proyección enviada exitosamente")
...     else:
...         print(f"❌ Error: {response.status_code}")
...     
...     return response
>>> 
>>> # Ejecutar
>>> enviar_proyeccion_servicios(
...     fecha_inicio=date(2026, 2, 1),
...     fecha_fin=date(2026, 2, 29),
...     contrato_id=1
... )
"""

# =============================================================================
# NOTAS FINALES
# =============================================================================

"""
📝 TIPS DE OPTIMIZACIÓN:

1. Usar select_related() y prefetch_related() en queries complejas
2. Batch operations (bulk_create, bulk_update) para operaciones masivas
3. Índices de BD correctamente configurados (ya implementados)
4. Cachear resultados frecuentes si es necesario

🔧 DEBUGGING:

1. Activar logging en tareo_service.py:
   import logging
   logger = logging.getLogger(__name__)
   logger.setLevel(logging.DEBUG)

2. Inspeccionar queries ejecutadas:
   from django.db import connection
   print(connection.queries)

3. Usar Django Debug Toolbar en desarrollo

📚 REFERENCIAS:

- Documentación completa: docs/MIGRACION_TAREO_V2.md
- Tests: drilling/tests_tareo_v2.py
- Comando CLI: python manage.py generar_proyeccion_tareo --help
"""
