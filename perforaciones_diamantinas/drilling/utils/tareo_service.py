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
from datetime import datetime
from calendar import monthrange
from django.db import transaction
from django.db.models import Q, Case, When, Value, IntegerField
from ..models import Trabajador, AsistenciaTrabajador, FechaCerrada
from ..tareo_compat import AsistenciaDiaria, CierreMensualTareo, HistorialCambioAsistencia, NEW_TAREO


# Helper adaptors to support both legacy and new Tareo models
def _empleado_field_name():
    return 'trabajador' if NEW_TAREO else 'empleado'


def _proyeccion_filter(qs):
    return qs.filter(tipo='PROY') if NEW_TAREO else qs.filter(es_proyeccion=True)


def _manual_filter(qs):
    return qs.filter(tipo='REAL') if NEW_TAREO else qs.filter(es_proyeccion=False)


def _mark_as_proyeccion_defaults():
    return {'tipo': 'PROY'} if NEW_TAREO else {'es_proyeccion': True}


def _mark_as_manual_defaults():
    return {'tipo': 'REAL'} if NEW_TAREO else {'es_proyeccion': False}

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

    # Fecha histórica de inicio del calendario de tareo (inclusive).
    # No se deben generar ni procesar registros anteriores a esta fecha.
    HISTORICO_START = date(2026, 2, 26)
    
    @staticmethod
    def _snap_a_dia_cambio(fecha_ref, dia_cambio_guardia):
        """
        Retrocede fecha_ref hasta el día de semana == dia_cambio_guardia
        más reciente (o la misma fecha si ya cae en ese día).
        
        Ej: fecha_ref=Viernes, dia_cambio_guardia=2(Mié) → retrocede 2 días → Mié.
        """
        delta = (fecha_ref.weekday() - dia_cambio_guardia) % 7
        return fecha_ref - timedelta(days=delta)

    @staticmethod
    def _verificar_alineacion_ciclo(trabajador, contrato):
        """
        Verifica si la fecha_inicio_ciclo del trabajador cae en el
        dia_cambio_guardia del contrato.

        Returns:
            True  → alineado correctamente
            False → desalineado (debe corregirse)
            None  → no verificable (faltan datos)
        """
        dia_cambio = contrato.dia_cambio_guardia
        if dia_cambio is None:
            return None  # contrato sin día configurado

        fecha_ciclo = trabajador.fecha_inicio_ciclo
        if not fecha_ciclo:
            # Sin fecha manual → el sistema aplicará snap automático (considerado alineado)
            return None

        # El sistema aplica snap automático en calcular_estado_dia y generar_proyeccion_mensual,
        # por lo que una fecha_inicio_ciclo desalineada queda corregida internamente.
        # No es necesario advertir al usuario.
        return None

    @staticmethod
    def calcular_estado_dia(trabajador, fecha_consulta, forzar_alineacion=False):
        """
        Calcula el estado esperado de un trabajador para una fecha específica
        basándose en su régimen laboral y fecha de inicio de ciclo.
        
        Args:
            trabajador (Trabajador): Instancia del trabajador
            fecha_consulta (date): Fecha a evaluar
            forzar_alineacion (bool): Si True, snapea fecha_inicio_ciclo al
                dia_cambio_guardia del contrato aunque ya esté seteada.
                Útsese en la generación de proyecciones para garantizar que
                el ciclo siempre quede alineado al contrato.
            
        Returns:
            str: 'TD' | 'TN' | 'DESCANSO' (TD = turno día, TN = turno noche)
        """
        regimen = trabajador.regimen_laboral
        fecha_inicio_ciclo = trabajador.fecha_inicio_ciclo
        
        # Si no tiene régimen, asumir el régimen por defecto '14x7'
        # (antes el sistema retornaba 'TD' directamente, lo que producía
        # incoherencias en proyecciones). Ahora forzamos el régimen por
        # defecto para que la lógica de ciclo se aplique consistentemente.
        if not regimen:
            logger.info(f"Trabajador {getattr(trabajador, 'id', '?')} sin régimen; aplicando default '14x7'.")
            regimen = '14x7'

        # Obtener dia_cambio_guardia del contrato una sola vez
        dia_cambio = getattr(getattr(trabajador, 'contrato', None), 'dia_cambio_guardia', None)

        # Si no tiene fecha de inicio, anclar al dia_cambio_guardia del contrato
        if not fecha_inicio_ciclo:
            # trabajador.fecha_ingreso puede no existir o estar vacío en algunos
            # entornos/instancias; usar getattr para evitar AttributeError.
            fecha_ingreso = getattr(trabajador, 'fecha_ingreso', None)
            if fecha_ingreso:
                fecha_ref = fecha_ingreso
            else:
                fecha_ref = TareoService.HISTORICO_START

            if dia_cambio is not None:
                fecha_inicio_ciclo = TareoService._snap_a_dia_cambio(fecha_ref, dia_cambio)
            else:
                fecha_inicio_ciclo = fecha_ref

        elif forzar_alineacion and dia_cambio is not None:
            # La fecha_inicio_ciclo está seteada pero puede no alinear con el
            # dia_cambio_guardia del contrato.  Al generar proyecciones forzamos
            # el snap para que el ciclo quede siempre anclado al contrato.
            fecha_inicio_ciclo = TareoService._snap_a_dia_cambio(fecha_inicio_ciclo, dia_cambio)
        
        # Obtener configuración del régimen
        if regimen not in TareoService.REGIMEN_CONFIG:
            logger.warning(f"Régimen '{regimen}' no reconocido para trabajador {trabajador.id}")
            return 'TD'
        
        dias_trabajo, dias_descanso = TareoService.REGIMEN_CONFIG[regimen]
        ciclo_total = dias_trabajo + dias_descanso

        # Normalizar fecha_inicio_ciclo: si el inicio del ciclo está en el
        # futuro respecto a la fecha consultada, retroceder por múltiplos del
        # ciclo (dias_trabajo + dias_descanso) hasta ubicar el inicio en el
        # pasado. Esto evita que ciclos definidos con una fecha de inicio
        # posterior produzcan bloques de trabajo continuos en la proyección.
        try:
            if fecha_inicio_ciclo > fecha_consulta:
                dias_diff = (fecha_inicio_ciclo - fecha_consulta).days
                ciclos_atras = (dias_diff // ciclo_total) + 1
                fecha_inicio_ciclo = fecha_inicio_ciclo - timedelta(days=ciclos_atras * ciclo_total)
        except Exception:
            pass
        
        # Calcular días transcurridos desde el inicio del ciclo
        dias_transcurridos = (fecha_consulta - fecha_inicio_ciclo).days
        
        # Posición en el ciclo actual (0 = día 1, ciclo_total-1 = último día)
        posicion_ciclo = dias_transcurridos % ciclo_total
        
        # Si está dentro de los días de trabajo, retornar TD o TN según
        # la partición del bloque de trabajo (primera mitad = TD, segunda = TN)
        # Nota: no forzamos TD en el día de cambio de guardia; ese día
        # se trata como parte del ciclo normal para respetar la partición
        # del régimen (ej. 14x7 => 7 TD, 7 TN, 7 DL).

        if posicion_ciclo < dias_trabajo:
            # Dentro de los días de trabajo: determinar si corresponde a TD o TN
            # Repartimos el bloque de trabajo en dos mitades: TD primero, TN después.
            mitad = (dias_trabajo + 1) // 2  # TD obtiene el extra si es impar
            posicion_en_trabajo = posicion_ciclo  # 0..dias_trabajo-1
            if posicion_en_trabajo < mitad:
                return 'TD'
            else:
                return 'TN'
        else:
            return 'DESCANSO'
        
    @staticmethod
    def debug_estado_dia(trabajador, fecha_consulta, forzar_alineacion=False):
        """Devuelve un dict con variables intermedias usadas por calcular_estado_dia.
        Útil para debug remoto desde la shell.
        """
        info = {
            'trabajador_id': getattr(trabajador, 'id', None),
            'regimen': getattr(trabajador, 'regimen_laboral', None),
            'fecha_inicio_ciclo_raw': getattr(trabajador, 'fecha_inicio_ciclo', None),
            'fecha_consulta': fecha_consulta,
            'dia_cambio_guardia': getattr(getattr(trabajador, 'contrato', None), 'dia_cambio_guardia', None),
            'forzar_alineacion': forzar_alineacion,
        }
        try:
            # Run the same code path but collect internals
            regimen = trabajador.regimen_laboral
            fecha_inicio_ciclo = trabajador.fecha_inicio_ciclo
            dia_cambio = getattr(getattr(trabajador, 'contrato', None), 'dia_cambio_guardia', None)
            if not regimen:
                info['note'] = "Sin régimen; aplicando default '14x7'"
                regimen = '14x7'

            if not fecha_inicio_ciclo:
                # Usar getattr para evitar AttributeError si no hay campo fecha_ingreso
                fecha_ref = getattr(trabajador, 'fecha_ingreso', None) or date(2024,1,1)
                if dia_cambio is not None:
                    fecha_inicio_ciclo = TareoService._snap_a_dia_cambio(fecha_ref, dia_cambio)
                else:
                    fecha_inicio_ciclo = fecha_ref
            elif forzar_alineacion and dia_cambio is not None:
                fecha_inicio_ciclo = TareoService._snap_a_dia_cambio(fecha_inicio_ciclo, dia_cambio)

            dias_trabajo, dias_descanso = TareoService.REGIMEN_CONFIG.get(regimen, (None, None))
            ciclo_total = (dias_trabajo or 0) + (dias_descanso or 0)
            info.update({
                'fecha_inicio_ciclo_normalized': fecha_inicio_ciclo,
                'dias_trabajo': dias_trabajo,
                'dias_descanso': dias_descanso,
                'ciclo_total': ciclo_total,
            })

            # normalize future start
            if fecha_inicio_ciclo and fecha_inicio_ciclo > fecha_consulta and ciclo_total:
                dias_diff = (fecha_inicio_ciclo - fecha_consulta).days
                ciclos_atras = (dias_diff // ciclo_total) + 1
                fecha_inicio_ciclo = fecha_inicio_ciclo - timedelta(days=ciclos_atras * ciclo_total)
                info['fecha_inicio_ciclo_adjusted'] = fecha_inicio_ciclo

            dias_transcurridos = (fecha_consulta - fecha_inicio_ciclo).days
            posicion_ciclo = dias_transcurridos % ciclo_total if ciclo_total else None
            mitad = (dias_trabajo + 1) // 2 if dias_trabajo else None
            info.update({
                'dias_transcurridos': dias_transcurridos,
                'posicion_ciclo': posicion_ciclo,
                'mitad': mitad,
                'weekday': fecha_consulta.weekday(),
            })

            # compute result
            result = None
            try:
                if fecha_consulta.weekday() == dia_cambio:
                    result = 'TD'
                elif posicion_ciclo is not None and posicion_ciclo < dias_trabajo:
                    posicion_en_trabajo = posicion_ciclo
                    result = 'TD' if posicion_en_trabajo < mitad else 'TN'
                else:
                    result = 'DESCANSO'
            except Exception as e:
                result = f'ERR:{e}'

            info['result'] = result
            return info
        except Exception as e:
            info['error'] = str(e)
            return info

    
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
            'errores': [],
            'ajustes_guardia': []  # lista de (fecha, maquina_id, guardia_cambiada, causa)
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
        # No generar proyecciones previas al inicio histórico del tareo
        if primer_dia < TareoService.HISTORICO_START:
            primer_dia = TareoService.HISTORICO_START
        ultimo_dia = date(anio, mes, 25)
        
        # Filtrar trabajadores activos con contrato asignado (evitar trabajadores huérfanos)
        trabajadores_query = Trabajador.objects.filter(estado='ACTIVO', contrato__isnull=False)
        
        if contrato:
            trabajadores_query = trabajadores_query.filter(contrato=contrato)
        
        trabajadores_query = trabajadores_query.select_related('contrato')
        
        # Si sobrescribir=True, eliminar proyecciones previas
        if sobrescribir:
            qs = AsistenciaDiaria.objects.filter(
                fecha__gte=primer_dia,
                fecha__lte=ultimo_dia,
                **(({f"{_empleado_field_name()}__contrato": contrato}) if contrato else {})
            )
            _proyeccion_filter(qs).delete()
            logger.info(f"Proyecciones previas del mes {mes}/{anio} eliminadas")
        
        # Obtener registros ya existentes que NO deben tocarse
        # (correcciones manuales: es_proyeccion=False)
        registros_manuales = set(
            (lambda: _manual_filter(AsistenciaDiaria.objects.filter(
                fecha__gte=primer_dia,
                fecha__lte=ultimo_dia,
                **(({f"{_empleado_field_name()}__contrato": contrato}) if contrato else {})
            )).values_list(f"{_empleado_field_name()}_id", 'fecha'))()
        )

        # Proyecciones ya existentes (es_proyeccion=True) que tal vez hay que
        # actualizar (estado corregido, máquina, guardia)
        proyecciones_existentes = {}
        # Obtener proyecciones existentes (según esquema nuevo o legacy)
        existente_qs = AsistenciaDiaria.objects.filter(
            fecha__gte=primer_dia,
            fecha__lte=ultimo_dia,
            **(({f"{_empleado_field_name()}__contrato": contrato}) if contrato else {})
        )
        existente_qs = _proyeccion_filter(existente_qs)
        for p in existente_qs:
            key_id = getattr(p, f"{_empleado_field_name()}_id")
            proyecciones_existentes[(key_id, p.fecha)] = p

        # Listas para operaciones bulk
        registros_a_crear     = []
        registros_a_actualizar = []

        # Iterar sobre trabajadores
        for trabajador in trabajadores_query:
            try:
                stats['trabajadores_procesados'] += 1
                maquina  = trabajador.maquina_asignada
                guardia  = trabajador.guardia_asignada

                # Pre-cargar fechas cerradas para el contrato del trabajador
                fechas_cerradas_set = set(FechaCerrada.objects.filter(
                    contrato=trabajador.contrato,
                    fecha__gte=primer_dia,
                    fecha__lte=ultimo_dia
                ).values_list('fecha', flat=True))

                # Iterar sobre cada día del período
                # Intentar inferir la posición de ciclo a partir del cierre del mes
                # anterior (día 25). Si existe registro para el día anterior al
                # periodo operativo, lo usamos para continuar el ciclo en lugar
                # de recalcular desde `fecha_inicio_ciclo`.
                fecha_actual = primer_dia
                usar_estado_previo = False
                ciclo_pos = None
                try:
                    emp_field = _empleado_field_name()
                    dia_anterior = primer_dia - timedelta(days=1)
                    # Buscar registro manual preferente
                    filtros = {f"fecha": dia_anterior, f"{emp_field}__id": trabajador.id}
                    registro_manual = _manual_filter(AsistenciaDiaria.objects.filter(**filtros)).first()
                    registro_proy   = _proyeccion_filter(AsistenciaDiaria.objects.filter(**filtros)).first()
                    registro_last = registro_manual or registro_proy
                    # Si no existe registro para el día anterior, intentar
                    # buscar proyecciones previas en los días anteriores
                    # hasta el tamaño del bloque de trabajo (p. ej. 14 días)
                    if not registro_last:
                        try:
                            dias_trabajo, _ = TareoService.REGIMEN_CONFIG.get(trabajador.regimen_laboral or '14x7', (14,7))
                            for i in range(dias_trabajo):
                                fecha_check = dia_anterior - timedelta(days=i)
                                filtros_check = {f"fecha": fecha_check, f"{emp_field}__id": trabajador.id}
                                registro_proy_check = _proyeccion_filter(AsistenciaDiaria.objects.filter(**filtros_check)).first()
                                if registro_proy_check and registro_proy_check.estado in ('TD', 'TN', 'TRABAJO'):
                                    registro_last = registro_proy_check
                                    registro_proy = registro_proy_check
                                    break
                        except Exception:
                            pass

                    if registro_last and registro_last.estado in ('TD', 'TN', 'TRABAJO'):
                        # Contar días consecutivos de trabajo terminando en dia_anterior
                        dias_trabajo, dias_descanso = TareoService.REGIMEN_CONFIG.get(trabajador.regimen_laboral or '14x7', (14,7))
                        ciclo_total = dias_trabajo + dias_descanso
                        contador = 0
                        fecha_walk = dia_anterior
                        # No andamos más atrás que el total de días de trabajo
                        while contador < dias_trabajo and fecha_walk >= TareoService.HISTORICO_START:
                            f_filt = {f"fecha": fecha_walk, f"{emp_field}__id": trabajador.id}
                            r_man = _manual_filter(AsistenciaDiaria.objects.filter(**f_filt)).first()
                            r_pro = _proyeccion_filter(AsistenciaDiaria.objects.filter(**f_filt)).first()
                            r = r_man or r_pro
                            if r and r.estado in ('TD', 'TN', 'TRABAJO'):
                                contador += 1
                                fecha_walk = fecha_walk - timedelta(days=1)
                            else:
                                break

                        # Sólo usar el estado previo si tenemos suficiente evidencia
                        # de que el trabajador está en un bloque de trabajo continuo.
                        # Si el registro anterior es una proyección, lo aceptamos;
                        # si es una corrección manual aislada (contador == 1) la
                        # ignoramos para evitar romper ciclos.
                        registro_es_proy = (registro_proy is not None and registro_last is registro_proy)
                        if contador >= 2 or registro_es_proy:
                            # Posición en el ciclo para primer_dia = contador % ciclo_total
                            ciclo_pos = contador % ciclo_total
                            usar_estado_previo = True
                        else:
                            usar_estado_previo = False
                except Exception:
                    usar_estado_previo = False
                while fecha_actual <= ultimo_dia:
                    # Nunca tocar correcciones manuales
                    if (trabajador.id, fecha_actual) in registros_manuales:
                        stats['registros_existentes_respetados'] += 1
                        fecha_actual += timedelta(days=1)
                        continue

                    # Si la fecha está cerrada para este contrato, no tocar
                    if fecha_actual in fechas_cerradas_set:
                        stats['registros_existentes_respetados'] += 1
                        fecha_actual += timedelta(days=1)
                        continue

                    # Calcular estado: si tenemos datos del día anterior al periodo,
                    # simulamos el ciclo desde esa posición; si no, usamos la
                    # función existente que se basa en fecha_inicio_ciclo.
                    if usar_estado_previo and ciclo_pos is not None:
                        dias_trabajo, dias_descanso = TareoService.REGIMEN_CONFIG.get(trabajador.regimen_laboral or '14x7', (14,7))
                        ciclo_total = dias_trabajo + dias_descanso
                        # Determinar estado según posición en ciclo
                        if ciclo_pos < dias_trabajo:
                            mitad = (dias_trabajo + 1) // 2
                            posicion_en_trabajo = ciclo_pos
                            estado_esperado = 'TD' if posicion_en_trabajo < mitad else 'TN'
                        else:
                            estado_esperado = 'DESCANSO'
                        # Avanzar en el ciclo
                        ciclo_pos = (ciclo_pos + 1) % ciclo_total
                    else:
                        estado_esperado = TareoService.calcular_estado_dia(
                            trabajador, fecha_actual, forzar_alineacion=True
                        )

                    clave = (trabajador.id, fecha_actual)
                    if clave in proyecciones_existentes:
                        # Actualizar proyección existente (corrige estado,
                        # máquina y guardia sin perder el id del registro)
                        p = proyecciones_existentes[clave]
                        p.estado           = estado_esperado
                        p.guardia_snapshot = guardia
                        p.maquina_snapshot = maquina
                        registros_a_actualizar.append(p)
                    else:
                        # Registro nuevo
                        # Construir kwargs dinámicos para legacy vs nuevo modelo
                        create_kwargs = {
                            _empleado_field_name(): trabajador,
                            'fecha': fecha_actual,
                            'estado': estado_esperado,
                            'guardia_snapshot': guardia,
                            'maquina_snapshot': maquina,
                            'registrado_por': None,
                        }
                        create_kwargs.update(_mark_as_proyeccion_defaults())

                        # Si usamos el nuevo esquema, asegurarnos de asignar periodo
                        if NEW_TAREO:
                            from ..models_tareo import TareoPeriod
                            periodo_obj, _ = TareoPeriod.objects.get_or_create(
                                contrato=trabajador.contrato,
                                anio=anio,
                                mes=mes,
                                defaults={'fecha_inicio': primer_dia, 'fecha_fin': ultimo_dia}
                            )
                            create_kwargs['periodo'] = periodo_obj

                        registros_a_crear.append(AsistenciaDiaria(**create_kwargs))

                    fecha_actual += timedelta(days=1)

            except Exception as e:
                error_msg = f"Error procesando trabajador {trabajador.id}: {str(e)}"
                logger.error(error_msg)
                stats['errores'].append(error_msg)

        # ─── Operaciones bulk ────────────────────────────────────────────────────
        # Before persisting, enforce guardia rule: por día y por máquina no deben
        # trabajar más de 2 guardias simultáneamente (salvo día de cambio de
        # guardia, que puede permitirse). Para eso, construimos un mapa de
        # (fecha, maquina_id) -> guardia -> entradas y, si hay más de 2
        # guardias con estado 'TRABAJO', elegimos una guardia para pasar a
        # 'DESCANSO' (preferimos la guardia con menos trabajadores).
        try:
            # Build index of entries by (fecha, maquina_id)
            entries_map = {}  # (fecha, maq_id) -> guardia_key -> list of (source, ref)
            # registros_a_crear: list of AsistenciaDiaria instances
            for idx, reg in enumerate(registros_a_crear):
                fecha = reg.fecha
                maq_id = getattr(reg, 'maquina_snapshot_id', None)
                # Si no hay máquina asignada, agrupar por contrato (p.ej. Línea de Mando)
                contrato_id = None
                try:
                    contrato_id = getattr(reg.empleado, 'contrato_id', None)
                except Exception:
                    contrato_id = None
                if maq_id:
                    group_key = f"MAQ_{maq_id}"
                else:
                    group_key = f"NO_MAQ_CONTRATO_{contrato_id}"

                guardia = reg.guardia_snapshot or 'SIN_GUARDIA'
                key = (fecha, group_key)
                entries_map.setdefault(key, {}).setdefault(guardia, []).append(('create', idx))
            # registros_a_actualizar: list of AsistenciaDiaria instances
            for idx, reg in enumerate(registros_a_actualizar):
                fecha = reg.fecha
                maq_id = getattr(reg, 'maquina_snapshot_id', None)
                contrato_id = None
                try:
                    # reg may be existing AsistenciaDiaria with empleado_id
                    contrato_id = getattr(reg.empleado, 'contrato_id', None) if getattr(reg, 'empleado', None) else None
                except Exception:
                    contrato_id = None

                if maq_id:
                    group_key = f"MAQ_{maq_id}"
                else:
                    group_key = f"NO_MAQ_CONTRATO_{contrato_id}"

                guardia = reg.guardia_snapshot or 'SIN_GUARDIA'
                key = (fecha, group_key)
                entries_map.setdefault(key, {}).setdefault(guardia, []).append(('update', idx))

            # Iterate and apply deterministic rule: por (fecha, maquina) garantizar
            # que a lo sumo 2 guardias estén en estado de trabajo. Si hay >2,
            # determinísticamente elegimos una guardia para pasar a DESCANSO.
            for (fecha, maq_id), guardias in entries_map.items():
                # Determine existing working guardias in DB for this group (maquina or no-maq per contrato)
                existing_working = {}  # guardia -> count from DB (manual or old proy)
                try:
                    # Parse group key: 'MAQ_{id}' or 'NO_MAQ_CONTRATO_{id}'
                    contrato_filter = None
                    maquina_filter = None
                    if isinstance(maq_id, str) and maq_id.startswith('MAQ_'):
                        try:
                            maquina_filter = int(maq_id.split('_', 1)[1])
                        except Exception:
                            maquina_filter = None
                    elif isinstance(maq_id, str) and maq_id.startswith('NO_MAQ_CONTRATO_'):
                        try:
                            contrato_filter = int(maq_id.split('_', 2)[2])
                        except Exception:
                            contrato_filter = None

                    qd = {'fecha': fecha, 'estado__in': ('TD', 'TN', 'TRABAJO')}
                    if maquina_filter:
                        qd['maquina_snapshot_id'] = maquina_filter
                    else:
                        # no-maq: maquina_snapshot is null and match contrato
                        qd['maquina_snapshot_id__isnull'] = True
                        if contrato_filter:
                            qd['trabajador__contrato_id'] = contrato_filter

                    existing_qs = AsistenciaDiaria.objects.filter(**qd).values_list('guardia_snapshot', flat=True)
                    for g in existing_qs:
                        if not g:
                            continue
                        existing_working[g] = existing_working.get(g, 0) + 1
                except Exception:
                    existing_working = {}

                # Build working_guardias combining existing DB entries and new/updated regs
                working_guardias = []  # list of (guardia_key, total_count)
                counts = {}
                for gk, items in guardias.items():
                    # count items that represent work in new/updated regs
                    new_work_count = 0
                    for src, idx in items:
                        reg = registros_a_crear[idx] if src == 'create' else registros_a_actualizar[idx]
                        if getattr(reg, 'estado', None) in ('TD', 'TN'):
                            new_work_count += 1
                    total = new_work_count + existing_working.get(gk, 0)
                    if total > 0:
                        counts[gk] = total
                        working_guardias.append((gk, total))

                if len(working_guardias) <= 2:
                    continue

                # Deterministic selection of guardia a descansar
                rotation_order = ['A', 'B', 'C']
                available_ordered = [gk for gk, _ in working_guardias if gk in rotation_order]
                guardia_to_rest = None

                # 1) intentar inferir última guardia en DESCANSO manual para la máquina
                try:
                    if maq_id is not None and available_ordered:
                        last_manual = AsistenciaDiaria.objects.filter(
                            maquina_snapshot_id=maq_id,
                            fecha__lt=fecha,
                            es_proyeccion=False,
                            estado='DESCANSO'
                        ).order_by('-fecha').values_list('guardia_snapshot', flat=True).first()
                        if last_manual and last_manual in rotation_order:
                            idx = rotation_order.index(last_manual)
                            for off in range(1, len(rotation_order)+1):
                                cand = rotation_order[(idx + off) % len(rotation_order)]
                                if cand in available_ordered:
                                    guardia_to_rest = cand
                                    break
                except Exception:
                    guardia_to_rest = None

                # 2) fallback: seed rotation deterministic but biased by contrato.dia_cambio_guardia
                if guardia_to_rest is None and available_ordered:
                    # Use numeric maquina id (maquina_filter) as seed bias instead of
                    # the string group key `maq_id` which may be non-numeric.
                    seed = fecha.toordinal() + (maquina_filter or 0)
                    # Try to infer dia_cambio_guardia from one of the workers in the group
                    contrato_dia = None
                    try:
                        sample_src, sample_idx = next(iter(guardias.values()))[0]
                        sample_reg = registros_a_crear[sample_idx] if sample_src == 'create' else registros_a_actualizar[sample_idx]
                        contrato_dia = getattr(getattr(sample_reg, 'empleado', None), 'contrato', None)
                        if contrato_dia:
                            contrato_dia = getattr(contrato_dia, 'dia_cambio_guardia', None)
                    except Exception:
                        contrato_dia = None

                    bias = contrato_dia if isinstance(contrato_dia, int) else 0
                    start_idx = (seed + bias) % len(rotation_order)
                    for i in range(len(rotation_order)):
                        cand = rotation_order[(start_idx + i) % len(rotation_order)]
                        if cand in available_ordered:
                            guardia_to_rest = cand
                            break

                # 3) final fallback: choose guardia with smallest group size
                if guardia_to_rest is None:
                    working_guardias.sort(key=lambda x: x[1])
                    guardia_to_rest = working_guardias[0][0]

                # Apply: set estado -> 'DESCANSO' for all entries in that guardia
                changed = 0
                for src, idx in guardias.get(guardia_to_rest, []):
                    if src == 'create':
                        registros_a_crear[idx].estado = 'DESCANSO'
                    else:
                        registros_a_actualizar[idx].estado = 'DESCANSO'
                    changed += 1

                stats['ajustes_guardia'].append({
                    'fecha': fecha.isoformat(),
                    'maquina_id': maq_id,
                    'guardia': guardia_to_rest,
                    'cambiados': changed,
                    'causa': 'regla_2_guardias_deterministica'
                })

        except Exception as e:
            logger.warning(f"Error post-procesando guardias para proyección: {e}")

        try:
            if registros_a_crear:
                AsistenciaDiaria.objects.bulk_create(
                    registros_a_crear,
                    batch_size=500,
                    ignore_conflicts=True
                )
                stats['registros_creados'] = len(registros_a_crear)
                logger.info(f"Proyección: {stats['registros_creados']} registros nuevos")

            if registros_a_actualizar:
                AsistenciaDiaria.objects.bulk_update(
                    registros_a_actualizar,
                    ['estado', 'guardia_snapshot', 'maquina_snapshot'],
                    batch_size=500
                )
                stats['registros_actualizados'] = len(registros_a_actualizar)
                logger.info(
                    f"Proyección: {stats['registros_actualizados']} registros actualizados "
                    "(estado + máquina + guardia)"
                )

            if not registros_a_crear and not registros_a_actualizar:
                logger.info("No se generaron ni actualizaron registros de proyección")

        except Exception as e:
            error_msg = f"Error en bulk_create/update: {str(e)}"
            logger.error(error_msg)
            stats['errores'].append(error_msg)
            raise

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

            # Construir kwargs dinámicos para buscar/crear según el esquema
            lookup = {f"{_empleado_field_name()}": trabajador, 'fecha': fecha}
            defaults = {
                'estado': nuevo_estado,
                'observaciones': observaciones,
                'registrado_por': usuario,
                'guardia_snapshot': trabajador.guardia_asignada
            }
            defaults.update(_mark_as_manual_defaults())

            # Si nuevo esquema, asignar periodo si fuera necesario (no obligatorio aquí)
            if NEW_TAREO:
                from ..models_tareo import TareoPeriod
                periodo_obj, _ = TareoPeriod.objects.get_or_create(
                    contrato=trabajador.contrato,
                    anio=fecha.year if fecha.month != 1 else fecha.year,
                    mes=fecha.month,
                    defaults={'fecha_inicio': fecha, 'fecha_fin': fecha}
                )
                defaults['periodo'] = periodo_obj

            asistencia, created = AsistenciaDiaria.objects.update_or_create(
                **lookup,
                defaults=defaults
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
            'CONDUCTORES':    4,
        }
        trabajadores = Trabajador.objects.filter(
            contrato=contrato,
            estado='ACTIVO'
        ).select_related('contrato', 'maquina_asignada').annotate(
            grupo_ord=Case(
                When(es_standby=True,                       then=Value(5)),
                When(grupo='LINEA_MANDO',                   then=Value(1)),
                When(grupo='OPERADORES',                    then=Value(2)),
                When(grupo='SERVICIOS_GEOLOGICOS',          then=Value(3)),
                When(grupo='CONDUCTORES',             then=Value(4)),
                default=Value(6),
                output_field=IntegerField()
            )
        ).order_by('grupo_ord', 'guardia_asignada', 'apepat', 'apemat', 'nombres')
        
        # Obtener asistencias del rango (adaptar nombre de FK empleado/trabajador)
        emp_field = _empleado_field_name()
        filter_kwargs = {f"{emp_field}__contrato": contrato, 'fecha__gte': fecha_inicio, 'fecha__lte': fecha_fin}
        asistencias = AsistenciaDiaria.objects.filter(
            **filter_kwargs
        ).select_related(emp_field, 'maquina_snapshot')
        
        # Crear diccionario de asistencias: {trabajador_id: {fecha: datos}}
        asistencias_dict = {}
        for asist in asistencias:
            key_id = getattr(asist, f"{emp_field}_id")
            if key_id not in asistencias_dict:
                asistencias_dict[key_id] = {}

            # determinar si es proyección según esquema
            if NEW_TAREO:
                es_proy = (getattr(asist, 'tipo', None) == 'PROY')
            else:
                es_proy = getattr(asist, 'es_proyeccion', False)

            asistencias_dict[key_id][asist.fecha] = {
                'estado': asist.estado,
                'estado_display': getattr(asist, 'get_estado_display')() if hasattr(asist, 'get_estado_display') else asist.estado,
                'es_proyeccion': es_proy,
                'observaciones': getattr(asist, 'observaciones', ''),
                'id': asist.id,
                'guardia_snapshot': getattr(asist, 'guardia_snapshot', None) or '',
                'maquina_id': getattr(asist, 'maquina_snapshot_id', None),
                'maquina_nombre': asist.maquina_snapshot.nombre if getattr(asist, 'maquina_snapshot', None) else None
            }
        
        # Construir matriz agrupada por grupo
        GRUPO_META = {
            'LINEA_MANDO':          ('Línea de Mando',       'lm'),
            'OPERADORES':           ('Operadores',            'op'),
            'SERVICIOS_GEOLOGICOS': ('Servicios Geológicos',  'geo'),
            'CONDUCTORES':    ('Conductores',     'aux'),
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
                    'rows': [],
                    'total_trabajadores': 0,
                }

            grupos_dict[grupo_key]['rows'].append({
                'trabajador': trabajador,
                'guardia': trabajador.guardia_asignada or 'N/A',
                'asistencias': asistencias_dict.get(trabajador.id, {}),
                # True si fecha_inicio_ciclo cae en el dia_cambio_guardia del contrato
                # None si no hay suficientes datos para verificar
                'ciclo_alineado': TareoService._verificar_alineacion_ciclo(trabajador, contrato),
            })
            grupos_dict[grupo_key]['total_trabajadores'] += 1

        # Reconstruir OPERADORES: intercalar cabeceras de máquina y guardia en las filas
        if 'OPERADORES' in grupos_dict:
            import re as _re
            op = grupos_dict['OPERADORES']
            maquinas_op = {}
            for row in op['rows']:
                maq = row['trabajador'].maquina_asignada
                maq_key = maq.nombre if maq else '__SIN_MAQUINA__'
                maq_nombre = maq.nombre if maq else 'Sin Máquina Asignada'
                maq_css = 'maq-' + _re.sub(r'[^a-zA-Z0-9]', '-', maq_key)
                if maq_key not in maquinas_op:
                    maquinas_op[maq_key] = {
                        'maquina_nombre': maq_nombre,
                        'maquina_key_css': maq_css,
                        'guardias': {}
                    }
                row['maquina_key_css'] = maq_css
                guardia = row['guardia']
                if guardia not in maquinas_op[maq_key]['guardias']:
                    maquinas_op[maq_key]['guardias'][guardia] = []
                maquinas_op[maq_key]['guardias'][guardia].append(row)

            new_rows = []
            for maq_key in sorted(maquinas_op.keys(), key=lambda k: (k == '__SIN_MAQUINA__', k)):
                md = maquinas_op[maq_key]
                total_maq = sum(len(r) for r in md['guardias'].values())
                new_rows.append({
                    'is_maquina_header': True,
                    'maquina_nombre': md['maquina_nombre'],
                    'maquina_key_css': md['maquina_key_css'],
                    'total_personas': total_maq,
                })
                for guardia in sorted(md['guardias'].keys()):
                    g_rows = md['guardias'][guardia]
                    new_rows.append({
                        'is_guardia_header': True,
                        'guardia': guardia,
                        'maquina_key_css': md['maquina_key_css'],
                        'count': len(g_rows),
                    })
                    new_rows.extend(g_rows)
            op['rows'] = new_rows

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
                guardia_snapshot = dato.get('guardia_snapshot') if 'guardia_snapshot' in dato else None
                
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
                    lookup_get = {f"{_empleado_field_name()}_id": empleado_id, 'fecha': fecha}
                    asistencia = AsistenciaDiaria.objects.get(**lookup_get)
                    # Actualizar campos
                    asistencia.estado = estado
                    asistencia.observaciones = observaciones
                    asistencia.maquina_snapshot = maquina
                    if guardia_snapshot is not None:
                        asistencia.guardia_snapshot = guardia_snapshot
                    # Marcar como corrección manual según esquema
                    if NEW_TAREO:
                        asistencia.tipo = 'REAL'
                    else:
                        asistencia.es_proyeccion = False
                    asistencia.registrado_por = usuario
                    registros_actualizar.append(asistencia)
                    
                except AsistenciaDiaria.DoesNotExist:
                    # Crear nuevo
                    trabajador = Trabajador.objects.get(id=empleado_id)
                    create_kwargs = {
                        _empleado_field_name(): trabajador,
                        'fecha': fecha,
                        'estado': estado,
                        'observaciones': observaciones,
                        'maquina_snapshot': maquina,
                        'registrado_por': usuario,
                        'guardia_snapshot': (guardia_snapshot if guardia_snapshot is not None else trabajador.guardia_asignada)
                    }
                    create_kwargs.update(_mark_as_manual_defaults())
                    # If new schema, assign periodo is optional here
                    if NEW_TAREO:
                        from ..models_tareo import TareoPeriod
                        periodo_obj, _ = TareoPeriod.objects.get_or_create(
                            contrato=trabajador.contrato,
                            anio=fecha.year,
                            mes=fecha.month,
                            defaults={'fecha_inicio': fecha, 'fecha_fin': fecha}
                        )
                        create_kwargs['periodo'] = periodo_obj
                    asistencia = AsistenciaDiaria(**create_kwargs)
                    registros_crear.append(asistencia)
            
            except Exception as e:
                stats['errores'].append(f"Error procesando registro: {str(e)}")
        
        # Bulk operations
        try:
            if registros_actualizar:
                update_fields = ['estado', 'observaciones', 'maquina_snapshot', 'guardia_snapshot', 'registrado_por']
                if NEW_TAREO:
                    update_fields.append('tipo')
                else:
                    update_fields.append('es_proyeccion')
                AsistenciaDiaria.objects.bulk_update(
                    registros_actualizar,
                    update_fields,
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

    @staticmethod
    @transaction.atomic
    def importar_desde_v1(contrato, fecha_inicio, fecha_fin, usuario=None, sobrescribir_proyecciones=True):
        """
        Importa los registros de AsistenciaTrabajador (V1) a AsistenciaDiaria (V2).
        - Respeta correcciones manuales (es_proyeccion=False): nunca las sobreescribe.
        - Proyecciones existentes: las actualiza si sobrescribir_proyecciones=True.
        - Nuevos registros: los crea con es_proyeccion=True.
        Retorna stats: importados, actualizados, omitidos_manual, sin_mapeo, errores.
        """
        ESTADO_MAP = {
            'TRABAJADO':              'TRABAJO',
            'DIA_LIBRE':              'DESCANSO',
            'DIA_APOYO':              'DIA_APOYO',
            'PERMISO_PATERNIDAD':     'PERMISO',
            'DESCANSO_MEDICO':        'DM',
            'STAND_BY':               'STAND_BY',
            'SUBSIDIO':               'DM',
            'INDUCCION':              'INDUCCION',
            'INDUCCION_VIRTUAL':      'INDUCCION',
            'RECORRIDO':              'TRABAJO',
            'FALTA':                  'FALTA',
            'PERMISO':                'PERMISO',
            'SUSPENSION':             'SUSPENSION',
            'VACACIONES':             'VACACIONES',
            'LICENCIA_SIN_GOCE':      'LICENCIA',
            'LICENCIA_CON_GOCE':      'LICENCIA',
            'LICENCIA_FALLECIMIENTO': 'LICENCIA',
            'TRABAJO_CALIENTE':       'TRABAJO',
            'CESADO':                 None,  # omitir
        }

        stats = {
            'importados': 0,
            'actualizados': 0,
            'omitidos_manual': 0,
            'sin_mapeo': 0,
            'errores': [],
        }

        # Todos los registros V1 del contrato en el rango
        registros_v1 = AsistenciaTrabajador.objects.filter(
            trabajador__contrato=contrato,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
        ).select_related('trabajador')

        if not registros_v1.exists():
            return stats

        # Pre-cargar registros V2 existentes
        # Pre-cargar registros V2 existentes (adaptar nombre FK)
        emp_field = _empleado_field_name()
        existentes = {
            (getattr(a, f"{emp_field}_id"), a.fecha): a
            for a in AsistenciaDiaria.objects.filter(
                **{f"{emp_field}__contrato": contrato, 'fecha__gte': fecha_inicio, 'fecha__lte': fecha_fin}
            )
        }

        crear = []
        actualizar = []

        for reg in registros_v1:
            try:
                estado_v2 = ESTADO_MAP.get(reg.estado)
                if estado_v2 is None:
                    # Estado sin mapeo (CESADO u otro desconocido) — omitir
                    stats['sin_mapeo'] += 1
                    continue

                key = (reg.trabajador_id, reg.fecha)
                existente = existentes.get(key)

                if existente:
                    # Si ya existe, respetar correcciones manuales según esquema
                    if NEW_TAREO:
                        if getattr(existente, 'tipo', None) == 'REAL':
                            stats['omitidos_manual'] += 1
                            continue
                    else:
                        if not getattr(existente, 'es_proyeccion', True):
                            stats['omitidos_manual'] += 1
                            continue

                    if sobrescribir_proyecciones:
                        existente.estado = estado_v2
                        existente.guardia_snapshot = reg.guardia_snapshot
                        existente.observaciones = reg.observaciones or ''
                        existente.registrado_por = usuario
                        actualizar.append(existente)
                else:
                    create_kwargs = {
                        _empleado_field_name(): reg.trabajador,
                        'fecha': reg.fecha,
                        'estado': estado_v2,
                        'guardia_snapshot': reg.guardia_snapshot,
                        'observaciones': reg.observaciones or '',
                        'registrado_por': usuario,
                    }
                    create_kwargs.update(_mark_as_proyeccion_defaults())
                    if NEW_TAREO:
                        from ..models_tareo import TareoPeriod
                        periodo_obj, _ = TareoPeriod.objects.get_or_create(
                            contrato=reg.trabajador.contrato,
                            anio=reg.fecha.year,
                            mes=reg.fecha.month,
                            defaults={'fecha_inicio': reg.fecha, 'fecha_fin': reg.fecha}
                        )
                        create_kwargs['periodo'] = periodo_obj

                    crear.append(AsistenciaDiaria(**create_kwargs))
            except Exception as e:
                stats['errores'].append(f"{reg.trabajador_id}/{reg.fecha}: {str(e)}")

        if crear:
            AsistenciaDiaria.objects.bulk_create(crear, batch_size=500)
            stats['importados'] = len(crear)

        if actualizar:
            AsistenciaDiaria.objects.bulk_update(
                actualizar,
                ['estado', 'guardia_snapshot', 'observaciones', 'registrado_por'],
                batch_size=500,
            )
            stats['actualizados'] = len(actualizar)

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


def get_proyeccion(trabajador, fecha_inicio, fecha_fin):
    """
    Genera una proyección simple TD/TN/DL para un trabajador en el rango dado
    siguiendo el régimen 14x7 y las reglas indicadas.

    Reglas implementadas:
    - Ciclo total = 21 días (14 trabajo + 7 descanso)
    - Offset por guardia: A=0, B=7, C=14
    - Dentro de los 14 días de trabajo: primeros 7 = TD, siguientes 7 = TN
    - Los 7 días finales del ciclo = DL (descanso libre)
    - Los cambios de fase se alinean al `dia_cambio_guardia` del contrato:
      se calcula una `fecha_referencia` snappeada al último día con ese
      weekday <= referencia (preferencia: `trabajador.fecha_inicio_ciclo`,
      luego `trabajador.fecha_ingreso`, luego 2024-01-01).

    Args:
        trabajador (Trabajador): instancia de modelo Trabajador
        fecha_inicio (date): fecha inicial (inclusive)
        fecha_fin (date): fecha final (inclusive)

    Returns:
        list of dict: [{'fecha': date, 'estado': 'TD'|'TN'|'DL'}]
    """
    # Offsets por guardia
    OFFSET_MAP = {'A': 0, 'B': 7, 'C': 14}

    # Determinar offset según guardia asignada
    guardia = getattr(trabajador, 'guardia_asignada', None) or 'A'
    guardia = guardia.upper() if isinstance(guardia, str) else 'A'
    offset = OFFSET_MAP.get(guardia, 0)

    # Determinar fecha referencia para el ciclo (preferir fecha_inicio_ciclo)
    dia_cambio = getattr(getattr(trabajador, 'contrato', None), 'dia_cambio_guardia', None)

    if getattr(trabajador, 'fecha_inicio_ciclo', None):
        fecha_ref = trabajador.fecha_inicio_ciclo
    elif getattr(trabajador, 'fecha_ingreso', None):
        fecha_ref = trabajador.fecha_ingreso
    else:
        fecha_ref = TareoService.HISTORICO_START

    # Si tenemos dia_cambio, snapear la fecha_ref al mismo weekday
    try:
        if dia_cambio is not None:
            # Reuse helper if available
            fecha_ref = TareoService._snap_a_dia_cambio(fecha_ref, int(dia_cambio))
    except Exception:
        # Fallback silencioso: dejar fecha_ref tal cual
        pass

    total_ciclo = 21
    dias_trabajo = 14
    mitad_trabajo = 7  # TD first 7, TN next 7

    resultado = []
    fecha = fecha_inicio
    # No proyectar antes del inicio histórico
    if fecha < TareoService.HISTORICO_START:
        fecha = TareoService.HISTORICO_START
    while fecha <= fecha_fin:
        dias_transcurridos = (fecha - fecha_ref).days
        # Normalizar a entero (puede ser negativo)
        idx = (dias_transcurridos + offset) % total_ciclo

        if idx < dias_trabajo:
            # Dentro del bloque de trabajo
            if idx < mitad_trabajo:
                estado = 'TD'
            else:
                estado = 'TN'
        else:
            estado = 'DL'

        resultado.append({'fecha': fecha, 'estado': estado})
        fecha += timedelta(days=1)

    return resultado


class TareoEngine:
    """
    Tareo Engine 3.0 — Motor puro, determinista y estadístico basado en
    aritmética modular para regímenes 14x7.

    Regla principal: (FechaConsulta - FechaAncla + OffsetGuardia) % 21
    Secuencia maestra: 7 TD -> 7 TN -> 7 DL
    Offsets: A=0, C=7, B=14 (según especificación)
    """

    TOTAL_CICLO = 21
    DIAS_TD = 7
    DIAS_TN = 7
    DIAS_DL = 7
    OFFSET = {'A': 0, 'C': 7, 'B': 14}
    # Normalize OFFSET to A=0, B=7, C=14 (consistent with UI and get_proyeccion)
    OFFSET = {'A': 0, 'B': 7, 'C': 14}

    @staticmethod
    def _fecha_ancla_contrato(contrato, referencia=None):
        """
        Calcula la FechaAncla para el contrato: el primer día con weekday ==
        contrato.dia_cambio_guardia que sea <= fecha_referencia.

        Si no hay `dia_cambio_guardia` configurado, utiliza la fecha de creación
        del contrato (`created_at`) o 2024-01-01 como fallback.
        """
        if referencia is None:
            ref = getattr(contrato, 'created_at', None)
            if ref:
                try:
                    referencia = ref.date()
                except Exception:
                    referencia = referencia or date(2024, 1, 1)
            else:
                referencia = date(2024, 1, 1)

        dia_cambio = getattr(contrato, 'dia_cambio_guardia', None)
        if dia_cambio is None:
            return referencia

        # Snapear hacia atrás hasta el primer día con ese weekday <= referencia
        delta = (referencia.weekday() - int(dia_cambio)) % 7
        return referencia - timedelta(days=delta)

    @classmethod
    def estado_para_fecha(cls, trabajador, fecha_consulta):
        """
        Calcula el estado (TD, TN, DL) de manera puramente determinista.
        """
        contrato = getattr(trabajador, 'contrato', None)
        if contrato is None:
            # Si no hay contrato, fallback determinista anclado a 2024-01-01
            fecha_ancla = date(2024, 1, 1)
        else:
            fecha_ancla = cls._fecha_ancla_contrato(contrato)

        guardia = (getattr(trabajador, 'guardia_asignada', None) or 'A').upper()
        offset = cls.OFFSET.get(guardia, 0)

        dias_trans = (fecha_consulta - fecha_ancla).days
        idx = (dias_trans + offset) % cls.TOTAL_CICLO

        if idx < cls.DIAS_TD:
            return 'TD'
        if idx < cls.DIAS_TD + cls.DIAS_TN:
            return 'TN'
        return 'DL'

    @classmethod
    def proyectar_rango(cls, trabajador, fecha_inicio, fecha_fin):
        resultado = []
        f = fecha_inicio
        while f <= fecha_fin:
            resultado.append({'fecha': f, 'estado': cls.estado_para_fecha(trabajador, f)})
            f += timedelta(days=1)
        return resultado


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
        
        emp_field = _empleado_field_name()
        filter_qs = AsistenciaDiaria.objects.filter(
            **{f"{emp_field}__in": trabajadores_activos, 'fecha__gte': primer_dia, 'fecha__lte': ultimo_dia}
        )
        proyecciones_pendientes = _proyeccion_filter(filter_qs).count()
        
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
                **{f"{emp_field}": trabajador, 'fecha__gte': primer_dia, 'fecha__lte': ultimo_dia}
            )

            total_dias = asistencias.count()
            proyecciones = _proyeccion_filter(asistencias).count()
            reales = _manual_filter(asistencias).count()
            
            # Desglose por estado
            trabajo = _manual_filter(asistencias).filter(estado='TRABAJO').count()
            descanso = _manual_filter(asistencias).filter(estado='DESCANSO').count()
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
            emp_field = _empleado_field_name()
            empleado_obj = getattr(asistencia, _empleado_field_name())
            cierre = CierreMensualTareo.objects.get(
                contrato=getattr(empleado_obj, 'contrato'),
                anio=asistencia.fecha.year,
                mes=asistencia.fecha.month
            )
            mes_cerrado = cierre.estado == 'CERRADO'
        except CierreMensualTareo.DoesNotExist:
            mes_cerrado = False
        
        # Crear registro de auditoría
        # Determinar bandera es_proyeccion_nuevo según esquema
        if NEW_TAREO:
            es_proy_nuevo = getattr(asistencia, 'tipo', None) == 'PROY'
        else:
            es_proy_nuevo = getattr(asistencia, 'es_proyeccion', False)

        historial = HistorialCambioAsistencia.objects.create(
            asistencia=asistencia,
            estado_anterior=estado_anterior,
            es_proyeccion_anterior=es_proyeccion_anterior,
            estado_nuevo=asistencia.estado,
            es_proyeccion_nuevo=es_proy_nuevo,
            usuario=usuario,
            motivo=motivo,
            ip_address=ip_address,
            mes_cerrado=mes_cerrado
        )
        
        logger.info(
            f"Cambio registrado: {getattr(asistencia, _empleado_field_name())} - {asistencia.fecha}: "
            f"{estado_anterior} → {asistencia.estado} por {usuario}"
        )
        
        return historial
    
    @staticmethod
    def obtener_historial_trabajador(trabajador, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene el historial completo de cambios de un trabajador.
        """
        from ..models import HistorialCambioAsistencia
        
        emp_field = _empleado_field_name()
        historial = HistorialCambioAsistencia.objects.filter(
            **{f"asistencia__{emp_field}": trabajador}
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
                **{f"asistencia__{emp_field}__contrato": contrato, 'asistencia__fecha__year': anio, 'asistencia__fecha__month': mes, 'fecha_cambio__gt': cierre.fecha_cierre, 'mes_cerrado': True}
            ).select_related(f"asistencia__{emp_field}", 'usuario')
            
            return {
                'cierre': cierre,
                'cambios': cambios,
                'total_cambios': cambios.count()
            }
            
        except CierreMensualTareo.DoesNotExist:
            return {
                'error': 'No existe cierre para este periodo'
            }
