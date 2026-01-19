from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from datetime import datetime, timedelta
from decimal import Decimal
from .models import (
    Turno, TurnoSondaje, Maquina, Trabajador, Contrato,
    TurnoActividad, Sondaje
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
    fecha_actual = datetime.now().date()
    
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
    metraje_periodo = TurnoSondaje.objects.filter(
        filtro_base
    ).aggregate(
        total=Sum('metros_turno')
    )['total'] or Decimal('0')
    
    # Metraje por día para gráfica de tendencia - MES ACTUAL
    metraje_diario_actual = TurnoSondaje.objects.filter(
        filtro_base
    ).values(
        fecha=F('turno__fecha')
    ).annotate(
        metros=Sum('metros_turno')
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
    metraje_diario_anterior = TurnoSondaje.objects.filter(
        turno__fecha__range=[fecha_inicio_anterior, fecha_fin_anterior],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).values(
        fecha=F('turno__fecha')
    ).annotate(
        metros=Sum('metros_turno')
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
    metraje_por_contrato_raw = TurnoSondaje.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).values(
        contrato_nombre=F('turno__contrato__nombre_contrato')
    ).annotate(
        metros_total=Sum('metros_turno'),
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
    # KPI 3: DISPONIBILIDAD DE MÁQUINAS
    # ============================================
    total_maquinas = Maquina.objects.all().count()
    maquinas_operativas = Maquina.objects.filter(
        estado='OPERATIVO'
    ).count()
    
    disponibilidad_global = (maquinas_operativas / total_maquinas * 100) if total_maquinas > 0 else 0
    
    # Distribución de estados de máquinas
    estados_maquinas = Maquina.objects.all().values('estado').annotate(
        cantidad=Count('id')
    )
    
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
    top_maquinas_raw = TurnoSondaje.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).values(
        maquina_nombre=F('turno__maquina__nombre')
    ).annotate(
        metros_total=Sum('metros_turno'),
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
    metraje_periodo_anterior = TurnoSondaje.objects.filter(
        turno__fecha__range=[fecha_inicio_anterior, fecha_fin_anterior],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).aggregate(
        total=Sum('metros_turno')
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
    turnos_sin_filtro_estado = TurnoSondaje.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin]
    )
    if contrato_id:
        turnos_sin_filtro_estado = turnos_sin_filtro_estado.filter(turno__contrato_id=contrato_id)
    
    total_turnos_periodo = turnos_sin_filtro_estado.count()
    metraje_sin_filtro = turnos_sin_filtro_estado.aggregate(total=Sum('metros_turno'))['total'] or Decimal('0')
    
    # Estados de turnos en el período
    estados_turnos = turnos_sin_filtro_estado.values('turno__estado').annotate(
        cantidad=Count('id'),
        metraje=Sum('metros_turno')
    )
    
    estados_msg = ' | '.join([f"{e['turno__estado']}: {e['cantidad']} turnos ({float(e['metraje'] or 0):.2f}m)" for e in estados_turnos])
    
    alertas.append({
        'tipo': 'warning',
        'mensaje': f'Debug Estados: {total_turnos_periodo} TurnoSondaje en período | Total sin filtro: {float(metraje_sin_filtro):.2f}m | {estados_msg}'
    })
    
    # ============================================
    # OBTENER LISTA DE CONTRATOS
    # ============================================
    contratos = Contrato.objects.all().order_by('nombre_contrato')
    
    # ============================================
    # PREPARAR CONTEXTO
    # ============================================
    
    # Debug temporal - ver qué hay en la BD
    total_turno_sondaje = TurnoSondaje.objects.all().count()
    turnos_en_rango = TurnoSondaje.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin]
    ).count()
    turnos_completados_debug = TurnoSondaje.objects.filter(
        turno__fecha__range=[fecha_inicio, fecha_fin],
        turno__estado__in=['COMPLETADO', 'APROBADO']
    ).count()
    
    # Agregar alerta de debug
    if metraje_periodo == 0:
        alertas.append({
            'tipo': 'info',
            'mensaje': f'Debug: {total_turno_sondaje} TurnoSondaje total | {turnos_en_rango} en rango | {turnos_completados_debug} COMPLETADO/APROBADO'
        })
    
    context = {
        'periodo': periodo,
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
        'metraje_por_contrato': metraje_por_contrato,
        'estados_maquinas': list(estados_maquinas),
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
