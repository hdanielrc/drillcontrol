"""
=============================================================================
SERVICIO DE PROYECCIÓN DE ASISTENCIA (TAREO)
=============================================================================

Módulo para la generación automática de proyecciones mensuales de asistencia
basadas en los regímenes laborales de los trabajadores (14x7, 20x10, etc.)

Autor: Sistema DrillControl
Fecha: Enero 2026
=============================================================================
"""

from datetime import date, timedelta
from calendar import monthrange
from django.db import transaction
from django.db.models import Q
from ..models import Trabajador, AsistenciaDiaria
import logging

logger = logging.getLogger(__name__)


class TareoService:
    """
    Servicio centralizado para la gestión de asistencias diarias
    """
    
    # Mapeo de regímenes laborales: (días_trabajo, días_descanso)
    REGIMEN_CONFIG = {
        '14x7': (14, 7),
        '20x10': (20, 10),
        '28x14': (28, 14),
        '5x2': (5, 2),
        '6x1': (6, 1),
    }
    
    @staticmethod
    def calcular_estado_dia(trabajador, fecha_consulta):
        """
        Calcula el estado esperado de un trabajador para una fecha específica
        basándose en su régimen laboral y fecha de inicio de ciclo.
        
        Args:
            trabajador (Trabajador): Instancia del trabajador
            fecha_consulta (date): Fecha a evaluar
            
        Returns:
            str: 'TRABAJO' o 'DESCANSO'
        """
        regimen = trabajador.regimen_laboral
        fecha_inicio_ciclo = trabajador.fecha_inicio_ciclo
        
        # Si no tiene régimen o fecha de inicio, asumir trabajo
        if not regimen or not fecha_inicio_ciclo:
            return 'TRABAJO'
        
        # Si la fecha de consulta es anterior al inicio del ciclo, no aplica
        if fecha_consulta < fecha_inicio_ciclo:
            return 'DESCANSO'
        
        # Obtener configuración del régimen
        if regimen not in TareoService.REGIMEN_CONFIG:
            logger.warning(f"Régimen '{regimen}' no reconocido para trabajador {trabajador.id}")
            return 'TRABAJO'
        
        dias_trabajo, dias_descanso = TareoService.REGIMEN_CONFIG[regimen]
        ciclo_total = dias_trabajo + dias_descanso
        
        # Calcular días transcurridos desde el inicio del ciclo
        dias_transcurridos = (fecha_consulta - fecha_inicio_ciclo).days
        
        # Posición en el ciclo actual (0 = día 1, ciclo_total-1 = último día)
        posicion_ciclo = dias_transcurridos % ciclo_total
        
        # Si está dentro de los días de trabajo, retornar TRABAJO
        if posicion_ciclo < dias_trabajo:
            return 'TRABAJO'
        else:
            return 'DESCANSO'
    
    @staticmethod
    @transaction.atomic
    def generar_proyeccion_mensual(anio, mes, contrato=None, sobrescribir=False):
        """
        Genera la proyección mensual de asistencias para todos los trabajadores activos.
        
        Este método:
        1. Itera sobre todos los empleados activos del contrato especificado
        2. Calcula matemáticamente si les toca TRABAJO o DESCANSO según su régimen
        3. Inserta masivamente (bulk_create) los registros como proyección
        4. Respeta excepciones ya registradas (vacaciones, permisos, etc.)
        
        Args:
            anio (int): Año de la proyección (ej: 2026)
            mes (int): Mes de la proyección (1-12)
            contrato (Contrato, optional): Contrato específico. Si es None, procesa todos.
            sobrescribir (bool): Si True, elimina proyecciones previas del mes
            
        Returns:
            dict: Estadísticas de la operación
                {
                    'trabajadores_procesados': int,
                    'registros_creados': int,
                    'registros_existentes_respetados': int,
                    'errores': list
                }
        """
        logger.info(f"Iniciando proyección mensual para {mes}/{anio}")
        
        stats = {
            'trabajadores_procesados': 0,
            'registros_creados': 0,
            'registros_existentes_respetados': 0,
            'errores': []
        }
        
        # Validación de parámetros
        if not (1 <= mes <= 12):
            error_msg = f"Mes inválido: {mes}. Debe estar entre 1 y 12."
            logger.error(error_msg)
            stats['errores'].append(error_msg)
            return stats
        
        # Calcular primer y último día del mes
        primer_dia = date(anio, mes, 1)
        num_dias = monthrange(anio, mes)[1]
        ultimo_dia = date(anio, mes, num_dias)
        
        # Filtrar trabajadores activos
        trabajadores_query = Trabajador.objects.filter(estado='ACTIVO')
        
        if contrato:
            trabajadores_query = trabajadores_query.filter(contrato=contrato)
        
        trabajadores_query = trabajadores_query.select_related('contrato')
        
        # Si sobrescribir=True, eliminar proyecciones previas
        if sobrescribir:
            AsistenciaDiaria.objects.filter(
                fecha__gte=primer_dia,
                fecha__lte=ultimo_dia,
                es_proyeccion=True
            ).delete()
            logger.info(f"Proyecciones previas del mes {mes}/{anio} eliminadas")
        
        # Obtener registros ya existentes (correcciones manuales o excepciones)
        registros_existentes = set(
            AsistenciaDiaria.objects.filter(
                fecha__gte=primer_dia,
                fecha__lte=ultimo_dia,
                es_proyeccion=False
            ).values_list('empleado_id', 'fecha')
        )
        
        # Lista para bulk_create
        registros_a_crear = []
        
        # Iterar sobre trabajadores
        for trabajador in trabajadores_query:
            try:
                stats['trabajadores_procesados'] += 1
                
                # Iterar sobre cada día del mes
                fecha_actual = primer_dia
                while fecha_actual <= ultimo_dia:
                    # Verificar si ya existe un registro manual/corrección
                    if (trabajador.id, fecha_actual) in registros_existentes:
                        stats['registros_existentes_respetados'] += 1
                        fecha_actual += timedelta(days=1)
                        continue
                    
                    # Calcular estado esperado según régimen laboral
                    estado_esperado = TareoService.calcular_estado_dia(trabajador, fecha_actual)
                    
                    # Crear registro de proyección
                    registro = AsistenciaDiaria(
                        empleado=trabajador,
                        fecha=fecha_actual,
                        estado=estado_esperado,
                        guardia_snapshot=trabajador.guardia_asignada,
                        es_proyeccion=True,
                        registrado_por=None  # Sistema automático
                    )
                    registros_a_crear.append(registro)
                    
                    fecha_actual += timedelta(days=1)
                
            except Exception as e:
                error_msg = f"Error procesando trabajador {trabajador.id}: {str(e)}"
                logger.error(error_msg)
                stats['errores'].append(error_msg)
        
        # Inserción masiva (bulk_create)
        try:
            if registros_a_crear:
                AsistenciaDiaria.objects.bulk_create(
                    registros_a_crear,
                    batch_size=500,  # Insertar en lotes de 500
                    ignore_conflicts=True  # Ignorar duplicados por constraint único
                )
                stats['registros_creados'] = len(registros_a_crear)
                logger.info(f"Proyección completada: {stats['registros_creados']} registros creados")
            else:
                logger.info("No se generaron nuevos registros de proyección")
        
        except Exception as e:
            error_msg = f"Error en bulk_create: {str(e)}"
            logger.error(error_msg)
            stats['errores'].append(error_msg)
            raise  # Re-lanzar para rollback de transacción
        
        return stats
    
    @staticmethod
    def corregir_asistencia(empleado_id, fecha, nuevo_estado, usuario, observaciones=''):
        """
        Actualiza o crea una corrección manual de asistencia.
        
        Args:
            empleado_id (int): ID del trabajador
            fecha (date): Fecha de la asistencia
            nuevo_estado (str): Nuevo estado (debe estar en ESTADO_CHOICES)
            usuario (CustomUser): Usuario que realiza la corrección
            observaciones (str): Observaciones opcionales
            
        Returns:
            AsistenciaDiaria: Registro actualizado o creado
        """
        try:
            trabajador = Trabajador.objects.get(id=empleado_id)
            
            # Buscar registro existente
            asistencia, created = AsistenciaDiaria.objects.update_or_create(
                empleado=trabajador,
                fecha=fecha,
                defaults={
                    'estado': nuevo_estado,
                    'es_proyeccion': False,  # Marcar como corrección manual
                    'observaciones': observaciones,
                    'registrado_por': usuario,
                    'guardia_snapshot': trabajador.guardia_asignada
                }
            )
            
            accion = "creada" if created else "actualizada"
            logger.info(f"Asistencia {accion}: Trabajador {empleado_id}, Fecha {fecha}, Estado {nuevo_estado}")
            
            return asistencia
            
        except Trabajador.DoesNotExist:
            logger.error(f"Trabajador con ID {empleado_id} no encontrado")
            raise ValueError(f"Trabajador con ID {empleado_id} no encontrado")
        
        except Exception as e:
            logger.error(f"Error corrigiendo asistencia: {str(e)}")
            raise
    
    @staticmethod
    def obtener_matriz_tareo(contrato, fecha_inicio, fecha_fin):
        """
        Obtiene los datos de asistencia en formato pivoteado para el frontend.
        
        Transforma datos verticales (empleado, fecha, estado) en matriz horizontal
        para facilitar la visualización tipo Excel.
        
        Args:
            contrato (Contrato): Contrato a consultar
            fecha_inicio (date): Primer día del rango
            fecha_fin (date): Último día del rango
            
        Returns:
            list: Lista de diccionarios con estructura:
                [
                    {
                        'trabajador': Trabajador,
                        'guardia': 'A',
                        'asistencias': {
                            date(2026,1,1): {'estado': 'TRABAJO', 'es_proyeccion': True},
                            date(2026,1,2): {'estado': 'DESCANSO', 'es_proyeccion': True},
                            ...
                        }
                    },
                    ...
                ]
        """
        # Obtener trabajadores activos del contrato
        trabajadores = Trabajador.objects.filter(
            contrato=contrato,
            estado='ACTIVO'
        ).select_related('cargo', 'maquina_asignada').order_by(
            'guardia_asignada', 'apellidos', 'nombres'
        )
        
        # Obtener asistencias del rango
        asistencias = AsistenciaDiaria.objects.filter(
            empleado__contrato=contrato,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('empleado')
        
        # Crear diccionario de asistencias: {trabajador_id: {fecha: datos}}
        asistencias_dict = {}
        for asist in asistencias:
            if asist.empleado_id not in asistencias_dict:
                asistencias_dict[asist.empleado_id] = {}
            
            asistencias_dict[asist.empleado_id][asist.fecha] = {
                'estado': asist.estado,
                'estado_display': asist.get_estado_display(),
                'es_proyeccion': asist.es_proyeccion,
                'observaciones': asist.observaciones,
                'id': asist.id
            }
        
        # Construir matriz
        matriz = []
        for trabajador in trabajadores:
            matriz.append({
                'trabajador': trabajador,
                'guardia': trabajador.guardia_asignada or 'N/A',
                'asistencias': asistencias_dict.get(trabajador.id, {})
            })
        
        return matriz
    
    @staticmethod
    def actualizar_masivo_desde_formset(formset_data, usuario):
        """
        Procesa un formset y actualiza masivamente las asistencias.
        
        Optimizado para operaciones batch usando bulk_update.
        
        Args:
            formset_data (list): Lista de diccionarios con datos del formset
            usuario (CustomUser): Usuario que realiza la actualización
            
        Returns:
            dict: Estadísticas de la operación
        """
        stats = {
            'actualizados': 0,
            'creados': 0,
            'errores': []
        }
        
        registros_actualizar = []
        registros_crear = []
        
        for dato in formset_data:
            try:
                empleado_id = dato.get('empleado_id')
                fecha = dato.get('fecha')
                estado = dato.get('estado')
                observaciones = dato.get('observaciones', '')
                
                if not all([empleado_id, fecha, estado]):
                    continue
                
                # Buscar si existe
                try:
                    asistencia = AsistenciaDiaria.objects.get(
                        empleado_id=empleado_id,
                        fecha=fecha
                    )
                    # Actualizar campos
                    asistencia.estado = estado
                    asistencia.observaciones = observaciones
                    asistencia.es_proyeccion = False
                    asistencia.registrado_por = usuario
                    registros_actualizar.append(asistencia)
                    
                except AsistenciaDiaria.DoesNotExist:
                    # Crear nuevo
                    trabajador = Trabajador.objects.get(id=empleado_id)
                    asistencia = AsistenciaDiaria(
                        empleado=trabajador,
                        fecha=fecha,
                        estado=estado,
                        observaciones=observaciones,
                        es_proyeccion=False,
                        registrado_por=usuario,
                        guardia_snapshot=trabajador.guardia_asignada
                    )
                    registros_crear.append(asistencia)
            
            except Exception as e:
                stats['errores'].append(f"Error procesando registro: {str(e)}")
        
        # Bulk operations
        try:
            if registros_actualizar:
                AsistenciaDiaria.objects.bulk_update(
                    registros_actualizar,
                    ['estado', 'observaciones', 'es_proyeccion', 'registrado_por'],
                    batch_size=500
                )
                stats['actualizados'] = len(registros_actualizar)
            
            if registros_crear:
                AsistenciaDiaria.objects.bulk_create(
                    registros_crear,
                    batch_size=500
                )
                stats['creados'] = len(registros_crear)
                
        except Exception as e:
            stats['errores'].append(f"Error en operación masiva: {str(e)}")
        
        return stats


def generar_proyeccion_mensual(anio, mes, contrato=None, sobrescribir=False):
    """
    Función wrapper para facilitar el uso desde comandos de Django o vistas.
    
    Ejemplo de uso:
        from drilling.utils.tareo_service import generar_proyeccion_mensual
        
        # Generar proyección para enero 2026
        resultado = generar_proyeccion_mensual(2026, 1)
        print(f"Registros creados: {resultado['registros_creados']}")
    """
    return TareoService.generar_proyeccion_mensual(anio, mes, contrato, sobrescribir)
