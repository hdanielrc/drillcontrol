from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta, date as date_class
from decimal import Decimal
from collections import defaultdict
from .models import (
    Turno, TurnoAvance, Maquina, Trabajador, Contrato,
    TurnoActividad, Sondaje, ProgramacionMes, TipoTurno, MetaTurno,
    ResumenDiasMaquina,
)


def gerente_required(view_func):
    """Decorador para restringir acceso solo a Gerente General"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'GERENTE_GENERAL':
            return view_func(request, *args, **kwargs)
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Acceso denegado. Solo para Gerente General.")
    return wrapper


@login_required
@gerente_required
def gerencia_dashboard(request):
    """Dashboard principal para Gerente General con KPIs y gráficas"""
    
    # Obtener parámetros de filtro
    periodo = request.GET.get('periodo', 'mes')  # semana, quincena, mes
    contrato_id = request.GET.get('contrato', None)  # Filtro por contrato
    mes_offset = int(request.GET.get('mes_offset', 0))  # Offset de meses para navegación
    fecha_actual = datetime.now().date()
    
    # Ajustar fecha_actual según el offset de meses para navegación histórica
    if mes_offset != 0:
        # Calcular mes de referencia
        mes_referencia = fecha_actual.month + mes_offset
        anio_referencia = fecha_actual.year
        
        # Ajustar año si el mes se sale del rango 1-12
        while mes_referencia < 1:
            mes_referencia += 12
            anio_referencia -= 1
        while mes_referencia > 12:
            mes_referencia -= 12
            anio_referencia += 1
        
        # Usar el día actual o el último día del mes si no existe
        try:
            fecha_actual = fecha_actual.replace(year=anio_referencia, month=mes_referencia)
        except ValueError:
            # Si el día no existe en ese mes (ej: 31 en febrero), usar último día del mes
            import calendar
            ultimo_dia = calendar.monthrange(anio_referencia, mes_referencia)[1]
            fecha_actual = fecha_actual.replace(year=anio_referencia, month=mes_referencia, day=ultimo_dia)
    
    # Calcular fecha de inicio y fin según período
    # NOTA: Los meses operativos van del 26 de un mes al 25 del siguiente
    if periodo == 'semana':
        fecha_fin = fecha_actual
        fecha_inicio = fecha_fin - timedelta(days=7)
    elif periodo == 'quincena':
        fecha_fin = fecha_actual
        fecha_inicio = fecha_fin - timedelta(days=15)
    else:  # mes operativo (26 al 25)
        if fecha_actual.day >= 26:
            # Estamos en el mes operativo actual (del 26 de este mes al 25 del siguiente)
            fecha_inicio = fecha_actual.replace(day=26)
            # Calcular el 25 del mes siguiente
            if fecha_actual.month == 12:
                fecha_fin = fecha_actual.replace(year=fecha_actual.year + 1, month=1, day=25)
            else:
                fecha_fin = fecha_actual.replace(month=fecha_actual.month + 1, day=25)
        else:
            # Estamos antes del 26, por lo que pertenecemos al mes operativo anterior
            # Del 26 del mes pasado al 25 de este mes
            if fecha_actual.month == 1:
                fecha_inicio = fecha_actual.replace(year=fecha_actual.year - 1, month=12, day=26)
            else:
                fecha_inicio = fecha_actual.replace(month=fecha_actual.month - 1, day=26)
            fecha_fin = fecha_actual.replace(day=25)
    
    # Construir filtro base para queries
    filtro_base = Q(
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    )
    if contrato_id:
        filtro_base &= Q(turno__contrato_id=contrato_id)
    
    # ============================================
    # KPI 1: METRAJE TOTAL AVANZADO
    # ============================================
    metraje_periodo = TurnoAvance.objects.filter(
        filtro_base
    ).aggregate(
        total=Sum('metros_perforados')
    )['total'] or Decimal('0')
    
    # Metraje por día para gráfica de tendencia - MES ACTUAL
    metraje_diario_actual = TurnoAvance.objects.filter(
        filtro_base
    ).values(
        fecha=F('turno__fecha')
    ).annotate(
        metros=Sum('metros_perforados')
    ).order_by('fecha')
    
    # Calcular período anterior para comparación histórica
    if periodo == 'mes':
        # Mes operativo anterior (26 a 25)
        if fecha_inicio.month == 1:
            # Actual: 26 dic - 25 ene | Anterior: 26 nov - 25 dic
            fecha_inicio_anterior = fecha_inicio.replace(year=fecha_inicio.year - 1, month=12, day=26)
            fecha_fin_anterior = fecha_inicio.replace(year=fecha_inicio.year - 1, month=12, day=25)
        elif fecha_inicio.month == 2:
            # Actual: 26 ene - 25 feb | Anterior: 26 dic - 25 ene
            fecha_inicio_anterior = fecha_inicio.replace(year=fecha_inicio.year - 1, month=12, day=26)
            fecha_fin_anterior = fecha_inicio.replace(month=1, day=25)
        else:
            # Meses normales
            fecha_inicio_anterior = fecha_inicio.replace(month=fecha_inicio.month - 1, day=26)
            fecha_fin_anterior = fecha_inicio.replace(month=fecha_inicio.month, day=25)
    else:
        # Para semana y quincena, usar la misma duración hacia atrás
        dias_periodo = (fecha_fin - fecha_inicio).days
        fecha_fin_anterior = fecha_inicio - timedelta(days=1)
        fecha_inicio_anterior = fecha_fin_anterior - timedelta(days=dias_periodo)
    
    # Metraje por día para gráfica de tendencia - MES ANTERIOR
    metraje_diario_anterior = TurnoAvance.objects.filter(
        turno__fecha__range=[fecha_inicio_anterior, fecha_fin_anterior],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).values(
        fecha=F('turno__fecha')
    ).annotate(
        metros=Sum('metros_perforados')
    ).order_by('fecha')
    
    # Convertir a formato día relativo (día 1, 2, 3... del período)
    # Para facilitar comparación en la gráfica
    metraje_diario_actual_dict = {}
    for item in metraje_diario_actual:
        dia_relativo = (item['fecha'] - fecha_inicio).days + 1
        metraje_diario_actual_dict[dia_relativo] = float(item['metros'])
    
    metraje_diario_anterior_dict = {}
    for item in metraje_diario_anterior:
        dia_relativo = (item['fecha'] - fecha_inicio_anterior).days + 1
        metraje_diario_anterior_dict[dia_relativo] = float(item['metros'])
    
    # ============================================
    # KPI 2: METRAJE POR CONTRATO
    # ============================================
    metraje_por_contrato_raw = TurnoAvance.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).values(
        contrato_nombre=F('turno__contrato__nombre_contrato')
    ).annotate(
        metros_total=Sum('metros_perforados'),
        turnos_count=Count('turno', distinct=True)
    ).order_by('-metros_total')[:10]
    
    # Convertir Decimals a float para JSON
    metraje_por_contrato = []
    for item in metraje_por_contrato_raw:
        metraje_por_contrato.append({
            'contrato_nombre': item['contrato_nombre'],
            'metros_total': float(item['metros_total']) if item['metros_total'] else 0.0,
            'turnos_count': item['turnos_count']
        })
    
    # ============================================
    # KPI 3: DISPONIBILIDAD GLOBAL (Basada en Actividades)
    # ============================================
    # Calcular horas por tipo de actividad
    from django.db.models import Sum as DbSum
    
    actividades_periodo = TurnoActividad.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    )
    
    if contrato_id:
        actividades_periodo = actividades_periodo.filter(turno__contrato_id=contrato_id)
    
    # Agrupar por tipo de actividad
    horas_por_tipo = actividades_periodo.values(
        tipo=F('actividad__tipo_actividad')
    ).annotate(
        total_horas=DbSum('tiempo_calc')
    )
    
    # Convertir a diccionario
    horas_dict = {}
    total_horas = Decimal('0')
    for item in horas_por_tipo:
        tipo = item['tipo']
        horas = item['total_horas'] or Decimal('0')
        horas_dict[tipo] = float(horas)
        total_horas += horas
    
    # Calcular disponibilidad: horas OPERATIVO / total de horas
    horas_operativo = horas_dict.get('OPERATIVO', 0.0)
    disponibilidad_global = (horas_operativo / float(total_horas) * 100) if total_horas > 0 else 0
    
    # Preparar datos para gráfica de distribución de actividades
    distribucion_actividades = [
        {'tipo': 'Operativo', 'horas': horas_dict.get('OPERATIVO', 0.0), 'porcentaje': (horas_dict.get('OPERATIVO', 0.0) / float(total_horas) * 100) if total_horas > 0 else 0},
        {'tipo': 'Inoperativo', 'horas': horas_dict.get('INOPERATIVO', 0.0), 'porcentaje': (horas_dict.get('INOPERATIVO', 0.0) / float(total_horas) * 100) if total_horas > 0 else 0},
        {'tipo': 'Stand By Cliente', 'horas': horas_dict.get('STAND_BY_CLIENTE', 0.0), 'porcentaje': (horas_dict.get('STAND_BY_CLIENTE', 0.0) / float(total_horas) * 100) if total_horas > 0 else 0},
        {'tipo': 'Stand By RockDrill', 'horas': horas_dict.get('STAND_BY_ROCKDRILL', 0.0), 'porcentaje': (horas_dict.get('STAND_BY_ROCKDRILL', 0.0) / float(total_horas) * 100) if total_horas > 0 else 0},
        {'tipo': 'Otros', 'horas': horas_dict.get('OTROS', 0.0), 'porcentaje': (horas_dict.get('OTROS', 0.0) / float(total_horas) * 100) if total_horas > 0 else 0},
    ]
    
    # Total de máquinas para otras métricas
    total_maquinas = Maquina.objects.all().count()
    maquinas_operativas = Maquina.objects.filter(estado='OPERATIVO').count()
    
    # ============================================
    # KPI 4: EFICIENCIA OPERATIVA
    # ============================================
    # Turnos completados vs programados
    turnos_periodo = Turno.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin]
    )
    
    turnos_completados = turnos_periodo.filter(
        Q(estado='COMPLETADO') | Q(estado='APROBADO')
    ).count()
    
    turnos_total = turnos_periodo.count()
    eficiencia_turnos = (turnos_completados / turnos_total * 100) if turnos_total > 0 else 0
    
    # ============================================
    # KPI 5: RECURSOS HUMANOS
    # ============================================
    trabajadores_activos = Trabajador.objects.filter(estado='ACTIVO').count()
    
    # Trabajadores que trabajaron en el período
    trabajadores_periodo = Trabajador.objects.filter(
        turnotrabajador__turno__fecha__range=[fecha_inicio, fecha_fin]
    ).distinct().count()
    
    # ============================================
    # KPI 6: TOP MÁQUINAS POR RENDIMIENTO
    # ============================================
    top_maquinas_raw = TurnoAvance.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).values(
        maquina_nombre=F('turno__maquina__nombre')
    ).annotate(
        metros_total=Sum('metros_perforados'),
        dias_trabajados=Count('turno__fecha', distinct=True)
    ).annotate(
        promedio_diario=F('metros_total') / F('dias_trabajados')
    ).order_by('-metros_total')[:10]
    
    # Convertir Decimals a float para JSON
    top_maquinas = []
    for item in top_maquinas_raw:
        top_maquinas.append({
            'maquina_nombre': item['maquina_nombre'],
            'metros_total': float(item['metros_total']) if item['metros_total'] else 0.0,
            'dias_trabajados': item['dias_trabajados'],
            'promedio_diario': float(item['promedio_diario']) if item['promedio_diario'] else 0.0
        })
    
    # ============================================
    # KPI 7: SONDAJES ACTIVOS
    # ============================================
    sondajes_activos = Sondaje.objects.filter(estado='ACTIVO').count()
    sondajes_completados = Sondaje.objects.filter(estado='FINALIZADO').count()

    # ============================================
    # METAS DIARIAS: calculadas desde ProgramacionMes
    # ============================================
    # Obtener máquinas del filtro actual
    if contrato_id:
        maquinas_filtro = Maquina.objects.filter(contrato_id=contrato_id)
    else:
        maquinas_filtro = Maquina.objects.all()

    año_op, mes_op = _mes_operativo_de_fecha(fecha_inicio + timedelta(days=15))
    progs_periodo = ProgramacionMes.objects.filter(
        maquina__in=maquinas_filtro,
        año=año_op,
        mes=mes_op,
    ).select_related('maquina')

    # Para cada día del período calcular la suma de metas
    metraje_diario_meta_dict = {}
    dias_periodo_total = (fecha_fin - fecha_inicio).days + 1
    for dia_num in range(1, dias_periodo_total + 1):
        fecha_dia = fecha_inicio + timedelta(days=dia_num - 1)
        total_meta_dia = 0.0
        for prog in progs_periodo:
            if prog.dia_inicio and fecha_dia >= prog.dia_inicio and prog.meta_metros:
                meta_dia = float(prog.meta_metros) / 30
                total_meta_dia += meta_dia
        if total_meta_dia > 0:
            metraje_diario_meta_dict[dia_num] = round(total_meta_dia, 2)
    
    # ============================================
    # ALERTAS Y PROBLEMAS
    # ============================================
    alertas = []
    
    # Máquinas en mantenimiento
    maquinas_mantenimiento = Maquina.objects.filter(
        estado='MANTENIMIENTO'
    ).count()
    if maquinas_mantenimiento > 0:
        alertas.append({
            'tipo': 'warning',
            'mensaje': f'{maquinas_mantenimiento} máquina(s) en mantenimiento'
        })
    
    # Disponibilidad baja
    if disponibilidad_global < 70:
        alertas.append({
            'tipo': 'danger',
            'mensaje': f'Disponibilidad crítica: {disponibilidad_global:.1f}%'
        })
    
    # ============================================
    # ALERTAS AUTOMÁTICAS
    # ============================================
    alertas = []
    
    # Comparar metraje con período anterior
    metraje_periodo_anterior = TurnoAvance.objects.filter(
        turno__fecha__range=[fecha_inicio_anterior, fecha_fin_anterior],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).aggregate(
        total=Sum('metros_perforados')
    )['total'] or Decimal('0')
    
    if metraje_periodo < metraje_periodo_anterior * Decimal('0.8'):
        alertas.append({
            'tipo': 'warning',
            'mensaje': f'Metraje 20% menor al período anterior'
        })
    
    # Agregar alerta de debug con fechas del período anterior
    alertas.append({
        'tipo': 'info',
        'mensaje': f'Debug Período Anterior: {fecha_inicio_anterior.strftime("%d/%m/%Y")} - {fecha_fin_anterior.strftime("%d/%m/%Y")} | Metraje: {float(metraje_periodo_anterior):.2f} m'
    })
    
    # Debug adicional para verificar datos
    if contrato_id:
        contrato_nombre = Contrato.objects.filter(id=contrato_id).first()
        if contrato_nombre:
            alertas.append({
                'tipo': 'info',
                'mensaje': f'Debug Filtro: Contrato "{contrato_nombre.nombre_contrato}" (ID: {contrato_id})'
            })
    
    # Contar turnos sin filtro de estado para debug
    turnos_sin_filtro_estado = TurnoAvance.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin]
    )
    if contrato_id:
        turnos_sin_filtro_estado = turnos_sin_filtro_estado.filter(turno__contrato_id=contrato_id)
    
    total_turnos_periodo = turnos_sin_filtro_estado.count()
    metraje_sin_filtro = turnos_sin_filtro_estado.aggregate(total=Sum('metros_perforados'))['total'] or Decimal('0')
    
    # Estados de turnos en el período
    estados_turnos = turnos_sin_filtro_estado.values('turno__estado').annotate(
        cantidad=Count('id'),
        metraje=Sum('metros_perforados')
    )
    
    estados_msg = ' | '.join([f"{e['turno__estado']}: {e['cantidad']} turnos ({float(e['metraje'] or 0):.2f}m)" for e in estados_turnos])
    
    alertas.append({
        'tipo': 'warning',
        'mensaje': f'Debug Estados: {total_turnos_periodo} TurnoAvance en período | Total sin filtro: {float(metraje_sin_filtro):.2f}m | {estados_msg}'
    })
    
    # ============================================
    # OBTENER LISTA DE CONTRATOS
    # ============================================
    contratos = Contrato.objects.all().order_by('nombre_contrato')
    
    # ============================================
    # PREPARAR CONTEXTO
    # ============================================
    
    # Debug temporal - ver qué hay en la BD
    total_turno_avance = TurnoAvance.objects.all().count()
    turnos_en_rango = TurnoAvance.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin]
    ).count()
    turnos_completados_debug = TurnoAvance.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).count()
    
    # Agregar alerta de debug
    if metraje_periodo == 0:
        alertas.append({
            'tipo': 'info',
            'mensaje': f'Debug: {total_turno_avance} TurnoAvance total | {turnos_en_rango} en rango | {turnos_completados_debug} COMPLETADO/APROBADO'
        })
    
    context = {
        'periodo': periodo,
        'mes_offset': mes_offset,
        'contrato_seleccionado': contrato_id,
        'contratos': contratos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'fecha_inicio_anterior': fecha_inicio_anterior,
        'fecha_fin_anterior': fecha_fin_anterior,
        
        # KPIs principales
        'metraje_total': float(metraje_periodo),
        'metraje_periodo_anterior': float(metraje_periodo_anterior),
        'diferencia_metraje': float(metraje_periodo - metraje_periodo_anterior),
        'disponibilidad_global': float(disponibilidad_global),
        'eficiencia_turnos': float(eficiencia_turnos),
        'trabajadores_activos': trabajadores_activos,
        'trabajadores_periodo': trabajadores_periodo,
        'sondajes_activos': sondajes_activos,
        'sondajes_completados': sondajes_completados,
        
        # Datos para gráficas comparativas
        'metraje_diario_actual': metraje_diario_actual_dict,
        'metraje_diario_anterior': metraje_diario_anterior_dict,
        'metraje_diario_meta': metraje_diario_meta_dict,
        'metraje_por_contrato': metraje_por_contrato,
        'distribucion_actividades': distribucion_actividades,
        'total_horas_periodo': float(total_horas),
        'top_maquinas': top_maquinas,
        
        # Máquinas
        'total_maquinas': total_maquinas,
        'maquinas_operativas': maquinas_operativas,
        'maquinas_mantenimiento': maquinas_mantenimiento,
        
        # Turnos
        'turnos_total': turnos_total,
        'turnos_completados': turnos_completados,
        
        # Alertas
        'alertas': alertas,
    }
    
    return render(request, 'drilling/gerencia/dashboard.html', context)


# =============================================================================
# PROGRAMACIÓN MENSUAL
# =============================================================================

def _calcular_periodo_operativo(fecha):
    """Calcula fecha_inicio y fecha_fin del período operativo (26-25) para una fecha dada."""
    from .utils.periodo_operativo import mes_operativo_de_fecha, get_rango_mes_operativo
    anio, mes = mes_operativo_de_fecha(fecha)
    return get_rango_mes_operativo(anio, mes)


def _mes_operativo_de_fecha(fecha):
    """Devuelve (año, mes) del período operativo donde cae la fecha (mes = mes del día 25)."""
    from .utils.periodo_operativo import mes_operativo_de_fecha
    return mes_operativo_de_fecha(fecha)


@login_required
@gerente_required
def gerencia_programacion(request):
    """Vista de programación mensual de máquinas — tabla estilo Excel."""

    # Navegación de meses
    mes_offset = int(request.GET.get('mes_offset', 0))
    fecha_ref = date_class.today()
    if mes_offset != 0:
        import calendar
        mes_ref = fecha_ref.month + mes_offset
        anio_ref = fecha_ref.year
        while mes_ref < 1:
            mes_ref += 12
            anio_ref -= 1
        while mes_ref > 12:
            mes_ref -= 12
            anio_ref += 1
        ultimo_dia = calendar.monthrange(anio_ref, mes_ref)[1]
        dia = min(fecha_ref.day, ultimo_dia)
        fecha_ref = fecha_ref.replace(year=anio_ref, month=mes_ref, day=dia)

    fecha_inicio, fecha_fin = _calcular_periodo_operativo(fecha_ref)
    año_op, mes_op = _mes_operativo_de_fecha(fecha_ref)
    cantidad_dias = (fecha_fin - fecha_inicio).days + 1

    MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    nombre_mes = MESES[mes_op]

    # Obtener todos los contratos activos con sus máquinas operativas
    # Excluir "SISTEMA PRINCIPAL" (contrato ficticio del sistema)
    contratos = Contrato.objects.filter(estado='ACTIVO').exclude(
        nombre_contrato__icontains='sistema principal'
    ).prefetch_related('maquinas').order_by('nombre_contrato')

    # Programaciones existentes para el período: {maquina_id: ProgramacionMes}
    progs = ProgramacionMes.objects.filter(
        año=año_op, mes=mes_op
    ).select_related('maquina')
    prog_dict = {p.maquina_id: p for p in progs}

    # Turnos del período para el calendario: {maquina_id: {fecha: [tipo_turno_nombre, ...]}}
    turnos_qs = Turno.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin]
    ).select_related('maquina', 'tipo_turno').values(
        'maquina_id', 'fecha', 'tipo_turno__nombre', 'estado'
    )
    cal_dict = defaultdict(lambda: defaultdict(list))
    for t in turnos_qs:
        cal_dict[t['maquina_id']][t['fecha']].append({
            'tipo': t['tipo_turno__nombre'],
            'estado': t['estado'],
        })

    # Categorizar TipoTurno en TD (día) y TN (noche) por nombre
    tipos_turno_all = list(TipoTurno.objects.values('id', 'nombre').order_by('nombre'))
    td_ids   = {t['id'] for t in tipos_turno_all
                if any(kw in t['nombre'].lower() for kw in ['día', 'dia', 'diurno', ' td', 'td '])}
    tn_ids   = {t['id'] for t in tipos_turno_all
                if any(kw in t['nombre'].lower() for kw in ['noche', 'nocturno', ' tn', 'tn '])}
    td_nombres = {t['nombre'] for t in tipos_turno_all if t['id'] in td_ids}
    tn_nombres = {t['nombre'] for t in tipos_turno_all if t['id'] in tn_ids}
    # Fallback: primer tipo → TD, resto → TN
    if not td_ids and not tn_ids and tipos_turno_all:
        td_ids   = {tipos_turno_all[0]['id']}
        tn_ids   = {t['id'] for t in tipos_turno_all[1:]}
        td_nombres = {tipos_turno_all[0]['nombre']}
        tn_nombres = {t['nombre'] for t in tipos_turno_all[1:]}

    tipo_td_id = next(iter(td_ids), None)
    tipo_tn_id = next(iter(tn_ids), None)

    # Overrides de MetaTurno para el período: {maquina_id: {fecha: {tipo_turno_id: {valor, id}}}}
    meta_turno_qs = MetaTurno.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin]
    ).values('id', 'maquina_id', 'fecha', 'tipo_turno_id', 'meta_metros')

    mt_dict = defaultdict(lambda: defaultdict(dict))
    for mt in meta_turno_qs:
        mt_dict[mt['maquina_id']][mt['fecha']][mt['tipo_turno_id']] = {
            'id': mt['id'],
            'valor': float(mt['meta_metros']),
        }

    # Construir estructura de datos para el template
    grupos = []
    for contrato in contratos:
        maquinas = contrato.maquinas.filter(estado='OPERATIVO').order_by('nombre')
        if not maquinas.exists():
            continue

        filas = []
        for m in maquinas:
            prog = prog_dict.get(m.id)
            meta = float(prog.meta_metros) if prog else None
            dia_ini = prog.dia_inicio if prog else None

            if prog and meta:
                meta_dia   = meta / 30
                meta_turno = meta_dia / 2
                dias_trab  = max(0, (fecha_fin - dia_ini).days + 1) if dia_ini else cantidad_dias
                dias_trab  = min(dias_trab, cantidad_dias)
                programa   = meta_dia * cantidad_dias
            else:
                meta_dia = meta_turno = dias_trab = programa = None

            # Calendario como lista ordenada: un dict por día con celdas TD y TN
            cal_maquina = []
            prog_final_calculado = 0.0

            for offset in range(cantidad_dias):
                fecha_dia = fecha_inicio + timedelta(days=offset)
                activo    = (dia_ini is None) or (fecha_dia >= dia_ini)

                turnos_dia   = cal_dict[m.id].get(fecha_dia, [])
                overrides_dia = mt_dict[m.id].get(fecha_dia, {})

                def _celda(tipo_id, nombres_set):
                    ov       = overrides_dia.get(tipo_id)
                    default  = round(meta_turno or 0, 2)
                    valor    = ov['valor'] if ov else default
                    estado_t = next(
                        (t['estado'] for t in turnos_dia if t['tipo'] in nombres_set),
                        None
                    )
                    return {
                        'valor':      valor,
                        'es_override': bool(ov),
                        'override_id': ov['id'] if ov else None,
                        'estado':      estado_t,
                        'tipo_id':     tipo_id,
                    }

                cel_td = _celda(tipo_td_id, td_nombres)
                cel_tn = _celda(tipo_tn_id, tn_nombres)

                if activo:
                    prog_final_calculado += cel_td['valor'] + cel_tn['valor']

                cal_maquina.append({
                    'fecha':  fecha_dia.strftime('%Y-%m-%d'),
                    'activo': activo,
                    'td':     cel_td,
                    'tn':     cel_tn,
                })

            filas.append({
                'maquina_id':     m.id,
                'maquina_nombre': m.nombre,
                'prog_id':        prog.id if prog else None,
                'meta':           meta,
                'dia_inicio':     dia_ini.strftime('%Y-%m-%d') if dia_ini else '',
                'dias_trabajados': dias_trab,
                'programa':       round(programa, 2) if programa else None,
                'meta_dia':       round(meta_dia, 2) if meta_dia else None,
                'meta_turno':     round(meta_turno, 2) if meta_turno else None,
                'programa_final': round(prog_final_calculado, 2) if meta else None,
                'calendario':     cal_maquina,
            })

        grupos.append({
            'contrato_id': contrato.id,
            'contrato_nombre': contrato.nombre_contrato,
            'filas': filas,
        })

    # Máquinas disponibles para agregar (para el modal "Agregar máquina")
    # Todas las máquinas excepto las que ya están en grupos y las del contrato SISTEMA PRINCIPAL
    maquinas_en_grupos = {
        fila['maquina_id']
        for grupo in grupos
        for fila in grupo['filas']
    }
    todas_maquinas = list(
        Maquina.objects.exclude(id__in=maquinas_en_grupos)
        .exclude(contrato__nombre_contrato__icontains='sistema principal')
        .select_related('contrato')
        .order_by('contrato__nombre_contrato', 'nombre')
        .values('id', 'nombre', 'estado', 'contrato__nombre_contrato', 'contrato_id')
    )

    # Lista de fechas del período para encabezado del calendario
    fechas_periodo = [
        (fecha_inicio + timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(cantidad_dias)
    ]
    dias_calendario = [
        {
            'fecha': fecha_inicio + timedelta(days=i),
            'label': str((fecha_inicio + timedelta(days=i)).day),
        }
        for i in range(cantidad_dias)
    ]

    context = {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'año_op': año_op,
        'mes_op': mes_op,
        'nombre_mes': nombre_mes,
        'cantidad_dias': cantidad_dias,
        'mes_offset': mes_offset,
        'grupos': grupos,
        'todas_maquinas_json': json.dumps(todas_maquinas),
        'tipos_turno': [t['nombre'] for t in tipos_turno_all],
        'tipo_td_id': tipo_td_id,
        'tipo_tn_id': tipo_tn_id,
        'dias_calendario': dias_calendario,
        'fechas_periodo_json': json.dumps(fechas_periodo),
    }
    return render(request, 'drilling/gerencia/programacion.html', context)


@login_required
@gerente_required
@require_http_methods(["POST"])
def programacion_save(request):
    """Guarda o actualiza la programación de una máquina para el período operativo."""
    try:
        body = json.loads(request.body)
        maquina_id = int(body['maquina_id'])
        año = int(body['año'])
        mes = int(body['mes'])
        meta_metros = Decimal(str(body['meta_metros']))
        dia_inicio = date_class.fromisoformat(body['dia_inicio'])
    except (KeyError, ValueError, TypeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)

    maquina = get_object_or_404(Maquina, pk=maquina_id)

    obj, created = ProgramacionMes.objects.update_or_create(
        maquina=maquina,
        año=año,
        mes=mes,
        defaults={
            'meta_metros': meta_metros,
            'dia_inicio': dia_inicio,
            'created_by': request.user,
        }
    )

    # Devolver valores calculados
    meta = float(obj.meta_metros)
    meta_dia = meta / 30
    fi, ff = _calcular_periodo_operativo(date_class(año, mes, 1))
    cantidad_dias = (ff - fi).days + 1
    dias_trab = max(0, min((ff - obj.dia_inicio).days + 1, cantidad_dias)) if obj.dia_inicio >= fi else cantidad_dias
    return JsonResponse({
        'id': obj.id,
        'created': created,
        'meta_dia': round(meta_dia, 2),
        'meta_turno': round(meta_dia / 2, 2),
        'programa': round(meta_dia * cantidad_dias, 2),
        'programa_final': round(meta_dia * dias_trab, 2),
        'dias_trabajados': dias_trab,
    })


# =============================================================================
# META TURNO: override individual de celda del calendario
# =============================================================================

@login_required
@gerente_required
@require_http_methods(["POST"])
def meta_turno_save(request):
    """Guarda o actualiza el override de meta para un turno específico."""
    try:
        body           = json.loads(request.body)
        maquina_id     = int(body['maquina_id'])
        fecha          = date_class.fromisoformat(body['fecha'])
        tipo_turno_id  = int(body['tipo_turno_id'])
        meta_metros    = Decimal(str(body['meta_metros']))
    except (KeyError, ValueError, TypeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)

    maquina    = get_object_or_404(Maquina, pk=maquina_id)
    tipo_turno = get_object_or_404(TipoTurno, pk=tipo_turno_id)

    obj, created = MetaTurno.objects.update_or_create(
        maquina=maquina,
        fecha=fecha,
        tipo_turno=tipo_turno,
        defaults={'meta_metros': meta_metros, 'created_by': request.user}
    )
    return JsonResponse({'id': obj.id, 'created': created, 'valor': float(obj.meta_metros)})


@login_required
@gerente_required
@require_http_methods(["DELETE"])
def meta_turno_delete(request, pk):
    """Elimina un override de MetaTurno (restaura al valor por defecto)."""
    mt = get_object_or_404(MetaTurno, pk=pk)
    mt.delete()
    return JsonResponse({'deleted': True})


@login_required
@gerente_required
def dias_maquina(request):
    """Tabla de días asignados por trabajador/máquina según el tareo."""
    contrato_id = request.GET.get('contrato')
    maquina_id  = request.GET.get('maquina')
    busqueda    = request.GET.get('q', '').strip()

    qs = (
        ResumenDiasMaquina.objects
        .select_related('trabajador', 'maquina', 'maquina__contrato')
        .order_by('-total_dias')
    )

    if contrato_id:
        qs = qs.filter(maquina__contrato_id=contrato_id)
    if maquina_id:
        qs = qs.filter(maquina_id=maquina_id)
    if busqueda:
        qs = qs.filter(
            Q(trabajador__nombres__icontains=busqueda) |
            Q(trabajador__apepat__icontains=busqueda)  |
            Q(trabajador__dni__icontains=busqueda)     |
            Q(maquina__nombre__icontains=busqueda)
        )

    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    maquinas  = Maquina.objects.filter(estado='OPERATIVO').order_by('nombre')

    return render(request, 'drilling/gerencia/dias_maquina.html', {
        'registros':    qs,
        'contratos':    contratos,
        'maquinas':     maquinas,
        'contrato_id':  contrato_id,
        'maquina_id':   maquina_id,
        'busqueda':     busqueda,
        'total':        qs.count(),
        'tabla_vacia':  not ResumenDiasMaquina.objects.exists(),
    })
