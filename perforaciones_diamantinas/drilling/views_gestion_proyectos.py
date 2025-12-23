"""
Vista para Gestión de Proyectos - Stock y Turnos
Permite a usuarios con rol CONTROL_PROYECTOS y GERENCIA:
- Ver stock de PDD y ADITIVOS de los contratos
- Ver y editar turnos
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, OuterRef, Subquery, DecimalField
from .models import Contrato, Turno, TurnoAvance, Sondaje


@login_required
def gestion_proyectos_stock_turnos(request):
    """
    Vista integral para Control de Proyectos con:
    - Stock de PDD y Aditivos por contrato
    - Gestión y edición de turnos
    """
    user = request.user
    
    # Verificar permisos: solo CONTROL_PROYECTOS y GERENCIA
    if user.role not in ['CONTROL_PROYECTOS', 'GERENCIA']:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('dashboard')
    
    # Determinar contratos disponibles según permisos
    # CONTROL_PROYECTOS y GERENCIA tienen acceso a todos los contratos
    contratos_disponibles = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    
    if not contratos_disponibles.exists():
        messages.warning(request, "No hay contratos activos disponibles.")
        return redirect('dashboard')
    
    # Seleccionar contrato a visualizar
    contrato_id = request.GET.get('contrato')
    if contrato_id:
        try:
            contrato_seleccionado = Contrato.objects.get(id=contrato_id, estado='ACTIVO')
        except Contrato.DoesNotExist:
            contrato_seleccionado = contratos_disponibles.first()
    else:
        contrato_seleccionado = contratos_disponibles.first()
    
    if not contrato_seleccionado:
        messages.warning(request, "No hay contratos activos disponibles.")
        return redirect('dashboard')
    
    # ===== SECCIÓN TURNOS =====
    # Filtros de turnos
    filtros = {
        'sondaje': request.GET.get('sondaje', ''),
        'fecha_desde': request.GET.get('fecha_desde', ''),
        'fecha_hasta': request.GET.get('fecha_hasta', ''),
    }
    
    # Obtener turnos del contrato seleccionado
    turnos_query = Turno.objects.filter(contrato=contrato_seleccionado)
    
    # Aplicar filtros
    if filtros['sondaje']:
        turnos_query = turnos_query.filter(sondajes__id=filtros['sondaje'])
    
    if filtros['fecha_desde']:
        turnos_query = turnos_query.filter(fecha__gte=filtros['fecha_desde'])
    
    if filtros['fecha_hasta']:
        turnos_query = turnos_query.filter(fecha__lte=filtros['fecha_hasta'])
    
    # Optimizar queries con select_related y prefetch_related
    turnos = turnos_query.select_related(
        'maquina', 'tipo_turno'
    ).prefetch_related(
        'sondajes',
        'trabajadores_turno__trabajador',
    ).order_by('-fecha', '-id')
    
    # Anotar avance de metros
    avance_sq = TurnoAvance.objects.filter(turno=OuterRef('pk')).values('metros_perforados')[:1]
    turnos = turnos.annotate(avance_metros=Subquery(avance_sq, output_field=DecimalField()))
    
    # Estadísticas
    total_turnos = turnos.count()
    metros_result = TurnoAvance.objects.filter(turno__in=turnos).aggregate(total=Sum('metros_perforados'))
    metros_total = metros_result['total'] or 0
    
    # Sondajes para el filtro
    sondajes_filtro = Sondaje.objects.filter(contrato=contrato_seleccionado).only('id', 'nombre_sondaje')
    
    context = {
        'contratos_disponibles': contratos_disponibles,
        'contrato_seleccionado': contrato_seleccionado,
        'turnos': turnos[:100],  # Limitar a 100 registros para mejor performance
        'total_turnos': total_turnos,
        'metros_total': metros_total,
        'sondajes_filtro': sondajes_filtro,
        'filtros': filtros,
    }
    
    return render(request, 'drilling/gestion_proyectos/stock_turnos.html', context)
