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
from django.db.models import Q, Case, When, Value, IntegerField
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
        
        # Si no tiene régimen, asumir trabajo
        if not regimen:
            return 'TRABAJO'
            
        # Si no tiene fecha de inicio, intentar usar un default razonable 
        # para permitir que patrones como 14x7 funcionen
        if not fecha_inicio_ciclo:
            if trabajador.fecha_ingreso:
                fecha_inicio_ciclo = trabajador.fecha_ingreso
            else:
                # Fallback: 1 de Enero de 2024 como ancla
                fecha_inicio_ciclo = date(2024, 1, 1)
        
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
        
        # Calcular mes operativo: del 26 del mes anterior al 25 del mes actual
        # Enero 2026 operativo = 26/12/2025 al 25/01/2026
        mes_anterior = mes - 1 if mes > 1 else 12
        anio_anterior = anio if mes > 1 else anio - 1
        
        primer_dia = date(anio_anterior, mes_anterior, 26)
        ultimo_dia = date(anio, mes, 25)
        
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
                    
                    # Crear registro de proyección con máquina asignada
                    registro = AsistenciaDiaria(
                        empleado=trabajador,
                        fecha=fecha_actual,
                        estado=estado_esperado,
                        guardia_snapshot=trabajador.guardia_asignada,
                        maquina_snapshot=trabajador.maquina_asignada,  # Copiar máquina asignada
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
        # Anotamos orden por grupo para agrupar igual que V1
        GRUPO_ORDER = {
            'LINEA_MANDO':          1,
            'OPERADORES':           2,
            'SERVICIOS_GEOLOGICOS': 3,
            'PERSONAL_AUXILIAR':    4,
        }
        trabajadores = Trabajador.objects.filter(
            contrato=contrato,
            estado='ACTIVO'
        ).select_related('maquina_asignada').annotate(
            grupo_ord=Case(
                When(es_standby=True,                       then=Value(5)),
                When(grupo='LINEA_MANDO',                   then=Value(1)),
                When(grupo='OPERADORES',                    then=Value(2)),
                When(grupo='SERVICIOS_GEOLOGICOS',          then=Value(3)),
                When(grupo='PERSONAL_AUXILIAR',             then=Value(4)),
                default=Value(6),
                output_field=IntegerField()
            )
        ).order_by('grupo_ord', 'guardia_asignada', 'apepat', 'apemat', 'nombres')
        
        # Obtener asistencias del rango
        asistencias = AsistenciaDiaria.objects.filter(
            empleado__contrato=contrato,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('empleado', 'maquina_snapshot')
        
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
                'id': asist.id,
                'maquina_id': asist.maquina_snapshot_id,
                'maquina_nombre': asist.maquina_snapshot.nombre if asist.maquina_snapshot else None
            }
        
        # Construir matriz agrupada por grupo
        GRUPO_META = {
            'LINEA_MANDO':          ('Línea de Mando',       'lm'),
            'OPERADORES':           ('Operadores',            'op'),
            'SERVICIOS_GEOLOGICOS': ('Servicios Geológicos',  'geo'),
            'PERSONAL_AUXILIAR':    ('Personal Auxiliar',     'aux'),
            '__STAND_BY__':         ('Personal Stand By',     'sb'),
            '__SIN_GRUPO__':        ('Sin Grupo Asignado',    'sin'),
        }

        grupos_dict = {}  # grupo_key -> {'grupo_nombre': str, 'order': int, 'rows': []}
        for trabajador in trabajadores:
            if trabajador.es_standby:
                grupo_key = '__STAND_BY__'
                orden = 5
            elif trabajador.grupo:
                grupo_key = trabajador.grupo
                orden = trabajador.grupo_ord
            else:
                grupo_key = '__SIN_GRUPO__'
                orden = 6

            if grupo_key not in grupos_dict:
                meta_nombre, meta_css = GRUPO_META.get(grupo_key, (grupo_key, 'sin'))
                grupos_dict[grupo_key] = {
                    'grupo': grupo_key,
                    'grupo_nombre': meta_nombre,
                    'grupo_css': meta_css,
                    'order': orden,
                    'rows': []
                }

            grupos_dict[grupo_key]['rows'].append({
                'trabajador': trabajador,
                'guardia': trabajador.guardia_asignada or 'N/A',
                'asistencias': asistencias_dict.get(trabajador.id, {})
            })

        # Devolver lista ordenada por grupo
        matriz = sorted(grupos_dict.values(), key=lambda g: g['order'])
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
                maquina_id = dato.get('maquina_id')
                
                if not all([empleado_id, fecha, estado]):
                    continue
                
                # Obtener máquina si existe
                from ..models import Maquina
                maquina = None
                if maquina_id:
                    try:
                        maquina = Maquina.objects.get(id=maquina_id)
                    except Maquina.DoesNotExist:
                        pass
                
                # Buscar si existe
                try:
                    asistencia = AsistenciaDiaria.objects.get(
                        empleado_id=empleado_id,
                        fecha=fecha
                    )
                    # Actualizar campos
                    asistencia.estado = estado
                    asistencia.observaciones = observaciones
                    asistencia.maquina_snapshot = maquina
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
                        maquina_snapshot=maquina,
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
                    ['estado', 'observaciones', 'maquina_snapshot', 'es_proyeccion', 'registrado_por'],
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


# =============================================================================
# SERVICIO DE CIERRE MENSUAL Y AUDITORÍA
# =============================================================================

class CierreMensualService:
    """
    Servicio para gestionar cierres contables mensuales del tareo.
    Asegura integridad de datos para nómina y pagos.
    """
    
    @staticmethod
    def obtener_o_crear_cierre(contrato, anio, mes):
        """
        Obtiene o crea el registro de cierre mensual para un contrato/periodo.
        """
        from ..models import CierreMensualTareo
        
        cierre, created = CierreMensualTareo.objects.get_or_create(
            contrato=contrato,
            anio=anio,
            mes=mes,
            defaults={
                'estado': 'ABIERTO',
                'total_trabajadores': 0,
            }
        )
        
        if created:
            logger.info(f"Cierre mensual creado: {contrato} - {mes}/{anio}")
        
        return cierre
    
    @staticmethod
    def puede_editar_mes(contrato, anio, mes):
        """
        Verifica si un mes puede ser editado (no está cerrado).
        """
        from ..models import CierreMensualTareo
        
        try:
            cierre = CierreMensualTareo.objects.get(
                contrato=contrato,
                anio=anio,
                mes=mes
            )
            return cierre.puede_editarse()
        except CierreMensualTareo.DoesNotExist:
            # Si no existe cierre, se puede editar
            return True
    
    @staticmethod
    @transaction.atomic
    def cerrar_mes(contrato, anio, mes, usuario, observaciones=''):
        """
        Cierra contablemente un mes, congelando los datos para nómina.
        
        Proceso:
        1. Valida que todos los días tengan registro real (no proyección)
        2. Calcula estadísticas finales
        3. Cambia estado a CERRADO
        4. Registra auditoría
        
        Returns:
            dict: Resultado de la operación
        """
        from datetime import date
        from calendar import monthrange
        from ..models import CierreMensualTareo, AsistenciaDiaria, Trabajador
        
        # Obtener o crear cierre
        cierre = CierreMensualService.obtener_o_crear_cierre(contrato, anio, mes)
        
        if cierre.estado == 'CERRADO':
            return {
                'success': False,
                'error': 'El mes ya está cerrado',
                'cierre': cierre
            }
        
        # Validar que no haya proyecciones sin confirmar
        # Mes operativo: del 26 del mes anterior al 25 del mes actual
        mes_anterior = mes - 1 if mes > 1 else 12
        anio_anterior = anio if mes > 1 else anio - 1
        
        primer_dia = date(anio_anterior, mes_anterior, 26)
        ultimo_dia = date(anio, mes, 25)
        
        trabajadores_activos = Trabajador.objects.filter(
            contrato=contrato,
            estado='ACTIVO'
        )
        
        proyecciones_pendientes = AsistenciaDiaria.objects.filter(
            empleado__in=trabajadores_activos,
            fecha__gte=primer_dia,
            fecha__lte=ultimo_dia,
            es_proyeccion=True
        ).count()
        
        if proyecciones_pendientes > 0:
            return {
                'success': False,
                'error': f'Hay {proyecciones_pendientes} proyecciones sin confirmar. Deben convertirse a registros reales antes de cerrar.',
                'proyecciones_pendientes': proyecciones_pendientes,
                'cierre': cierre
            }
        
        # Calcular estadísticas finales
        cierre.calcular_estadisticas()
        
        # Cerrar mes
        cierre.estado = 'CERRADO'
        cierre.fecha_cierre = date.today()
        cierre.cerrado_por = usuario
        cierre.observaciones = observaciones
        cierre.save()
        
        logger.info(
            f"Mes cerrado: {contrato} - {mes}/{anio} por {usuario}. "
            f"Trabajadores: {cierre.total_trabajadores}, "
            f"Días trabajo: {cierre.total_dias_trabajo}"
        )
        
        return {
            'success': True,
            'cierre': cierre,
            'mensaje': f'Mes {mes}/{anio} cerrado exitosamente'
        }
    
    @staticmethod
    @transaction.atomic
    def reabrir_mes(contrato, anio, mes, usuario, motivo):
        """
        Reabre un mes cerrado (caso excepcional, requiere justificación).
        """
        from ..models import CierreMensualTareo
        
        try:
            cierre = CierreMensualTareo.objects.get(
                contrato=contrato,
                anio=anio,
                mes=mes
            )
        except CierreMensualTareo.DoesNotExist:
            return {
                'success': False,
                'error': 'No existe cierre para este periodo'
            }
        
        if cierre.estado != 'CERRADO':
            return {
                'success': False,
                'error': 'El mes no está cerrado'
            }
        
        # Reapertura requiere motivo obligatorio
        if not motivo or len(motivo.strip()) < 10:
            return {
                'success': False,
                'error': 'Debe proporcionar un motivo detallado (mínimo 10 caracteres)'
            }
        
        # Reabrir
        cierre.estado = 'REABIERTO'
        cierre.fecha_reapertura = date.today()
        cierre.reabierto_por = usuario
        cierre.motivo_reapertura = motivo
        cierre.save()
        
        logger.warning(
            f"Mes REABIERTO: {contrato} - {mes}/{anio} por {usuario}. "
            f"Motivo: {motivo}"
        )
        
        return {
            'success': True,
            'cierre': cierre,
            'mensaje': f'Mes {mes}/{anio} reabierto'
        }
    
    @staticmethod
    def obtener_resumen_mes(contrato, anio, mes):
        """
        Obtiene un resumen completo del mes para revisión antes de cerrar.
        """
        from datetime import date
        from calendar import monthrange
        from ..models import AsistenciaDiaria, Trabajador
        from django.db.models import Count, Q
        
        # Mes operativo: del 26 del mes anterior al 25 del mes actual
        mes_anterior = mes - 1 if mes > 1 else 12
        anio_anterior = anio if mes > 1 else anio - 1
        
        primer_dia = date(anio_anterior, mes_anterior, 26)
        ultimo_dia = date(anio, mes, 25)
        num_dias = (ultimo_dia - primer_dia).days + 1  # Total días en el mes operativo
        
        trabajadores_activos = Trabajador.objects.filter(
            contrato=contrato,
            estado='ACTIVO'
        )
        
        # Resumen por trabajador
        resumen_trabajadores = []
        
        for trabajador in trabajadores_activos:
            asistencias = AsistenciaDiaria.objects.filter(
                empleado=trabajador,
                fecha__gte=primer_dia,
                fecha__lte=ultimo_dia
            )
            
            total_dias = asistencias.count()
            proyecciones = asistencias.filter(es_proyeccion=True).count()
            reales = asistencias.filter(es_proyeccion=False).count()
            
            # Desglose por estado
            trabajo = asistencias.filter(estado='TRABAJO', es_proyeccion=False).count()
            descanso = asistencias.filter(estado='DESCANSO', es_proyeccion=False).count()
            faltas = asistencias.filter(estado='FALTA').count()
            vacaciones = asistencias.filter(estado='VACACIONES').count()
            permisos = asistencias.filter(estado='PERMISO').count()
            
            resumen_trabajadores.append({
                'trabajador': trabajador,
                'total_dias': total_dias,
                'proyecciones': proyecciones,
                'reales': reales,
                'trabajo': trabajo,
                'descanso': descanso,
                'faltas': faltas,
                'vacaciones': vacaciones,
                'permisos': permisos,
                'completo': proyecciones == 0 and total_dias == num_dias
            })
        
        # Totales generales
        totales = {
            'trabajadores': trabajadores_activos.count(),
            'dias_esperados': num_dias * trabajadores_activos.count(),
            'proyecciones_pendientes': sum(r['proyecciones'] for r in resumen_trabajadores),
            'registros_reales': sum(r['reales'] for r in resumen_trabajadores),
            'total_trabajo': sum(r['trabajo'] for r in resumen_trabajadores),
            'total_descanso': sum(r['descanso'] for r in resumen_trabajadores),
            'total_faltas': sum(r['faltas'] for r in resumen_trabajadores),
            'total_vacaciones': sum(r['vacaciones'] for r in resumen_trabajadores),
            'total_permisos': sum(r['permisos'] for r in resumen_trabajadores),
        }
        
        # Verificar si está listo para cerrar
        listo_para_cerrar = totales['proyecciones_pendientes'] == 0
        
        return {
            'resumen_trabajadores': resumen_trabajadores,
            'totales': totales,
            'listo_para_cerrar': listo_para_cerrar,
            'anio': anio,
            'mes': mes,
            'contrato': contrato
        }


class AuditoriaAsistenciaService:
    """
    Servicio para gestionar auditoría de cambios en asistencias.
    """
    
    @staticmethod
    def registrar_cambio(asistencia, estado_anterior, es_proyeccion_anterior, usuario, motivo='', ip_address=None):
        """
        Registra un cambio en el historial de auditoría.
        """
        from ..models import HistorialCambioAsistencia, CierreMensualTareo
        
        # Verificar si el mes está cerrado
        try:
            cierre = CierreMensualTareo.objects.get(
                contrato=asistencia.empleado.contrato,
                anio=asistencia.fecha.year,
                mes=asistencia.fecha.month
            )
            mes_cerrado = cierre.estado == 'CERRADO'
        except CierreMensualTareo.DoesNotExist:
            mes_cerrado = False
        
        # Crear registro de auditoría
        historial = HistorialCambioAsistencia.objects.create(
            asistencia=asistencia,
            estado_anterior=estado_anterior,
            es_proyeccion_anterior=es_proyeccion_anterior,
            estado_nuevo=asistencia.estado,
            es_proyeccion_nuevo=asistencia.es_proyeccion,
            usuario=usuario,
            motivo=motivo,
            ip_address=ip_address,
            mes_cerrado=mes_cerrado
        )
        
        logger.info(
            f"Cambio registrado: {asistencia.empleado} - {asistencia.fecha}: "
            f"{estado_anterior} → {asistencia.estado} por {usuario}"
        )
        
        return historial
    
    @staticmethod
    def obtener_historial_trabajador(trabajador, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene el historial completo de cambios de un trabajador.
        """
        from ..models import HistorialCambioAsistencia
        
        historial = HistorialCambioAsistencia.objects.filter(
            asistencia__empleado=trabajador
        ).select_related('asistencia', 'usuario')
        
        if fecha_inicio:
            historial = historial.filter(asistencia__fecha__gte=fecha_inicio)
        
        if fecha_fin:
            historial = historial.filter(asistencia__fecha__lte=fecha_fin)
        
        return historial.order_by('-fecha_cambio')
    
    @staticmethod
    def obtener_cambios_post_cierre(contrato, anio, mes):
        """
        Obtiene todos los cambios realizados después del cierre del mes.
        Útil para auditorías y control.
        """
        from datetime import date
        from ..models import HistorialCambioAsistencia, CierreMensualTareo
        
        try:
            cierre = CierreMensualTareo.objects.get(
                contrato=contrato,
                anio=anio,
                mes=mes,
                estado='CERRADO'
            )
            
            cambios = HistorialCambioAsistencia.objects.filter(
                asistencia__empleado__contrato=contrato,
                asistencia__fecha__year=anio,
                asistencia__fecha__month=mes,
                fecha_cambio__gt=cierre.fecha_cierre,
                mes_cerrado=True
            ).select_related('asistencia__empleado', 'usuario')
            
            return {
                'cierre': cierre,
                'cambios': cambios,
                'total_cambios': cambios.count()
            }
            
        except CierreMensualTareo.DoesNotExist:
            return {
                'error': 'No existe cierre para este periodo'
            }
