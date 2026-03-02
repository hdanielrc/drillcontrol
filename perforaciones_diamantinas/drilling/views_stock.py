"""
Vistas para el Dashboard de Stock con Histórico y Alertas

Proporciona:
- Dashboard de stock con métricas y proyecciones
- Vista detallada por artículo con tendencia
- Gestión de alertas
- API endpoints para gráficas

Autor: DrillControl
Fecha: Diciembre 2024
"""

import json
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import ListView
from django.utils import timezone
from django.db.models import Count, Sum, Q

from .models import (
    Contrato, StockSnapshot, AlertaStock, ConfiguracionAlertaStock
)
from .utils.stock_service import StockService


@login_required
def dashboard_stock(request):
    """
    Dashboard principal de stock con métricas, proyecciones y alertas.
    """
    user = request.user
    
    # Determinar contratos accesibles
    if user.is_superuser or user.role in ['GERENCIA', 'CONTROL_PROYECTOS']:
        contratos = Contrato.objects.filter(estado='ACTIVO')
    elif hasattr(user, 'contrato') and user.contrato:
        contratos = Contrato.objects.filter(id=user.contrato.id)
    else:
        messages.error(request, "No tienes acceso a ningún contrato.")
        return redirect('dashboard')
    
    # Contrato seleccionado
    contrato_id = request.GET.get('contrato')
    if contrato_id:
        contrato = get_object_or_404(Contrato, id=contrato_id, estado='ACTIVO')
    else:
        contrato = contratos.first()
    
    if not contrato:
        messages.warning(request, "No hay contratos activos.")
        return redirect('dashboard')
    
    # Obtener datos del servicio
    service = StockService(contrato)
    resumen = service.obtener_resumen_stock()
    proyecciones = service.obtener_proyeccion_stock()
    
    # Obtener alertas activas
    alertas = AlertaStock.get_alertas_activas(contrato=contrato)[:10]
    
    # Separar por familia para las tabs
    pdd_proyecciones = [p for p in proyecciones if p['familia'] == 'PDD']
    adit_proyecciones = [p for p in proyecciones if p['familia'] == 'ADIT']
    
    # Artículos críticos para destacar
    articulos_criticos = [p for p in proyecciones if p['estado'] in ['AGOTADO', 'CRITICO']]
    
    context = {
        'contratos': contratos,
        'contrato_seleccionado': contrato,
        'resumen': resumen,
        'proyecciones': proyecciones,
        'pdd_proyecciones': pdd_proyecciones,
        'adit_proyecciones': adit_proyecciones,
        'articulos_criticos': articulos_criticos,
        'alertas': alertas,
    }
    
    return render(request, 'drilling/stock/dashboard_stock.html', context)


@login_required
def detalle_articulo_stock(request, contrato_id, codigo_articulo):
    """
    Vista detallada de un artículo con histórico y tendencia.
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    service = StockService(contrato)
    
    # Obtener datos del artículo
    stock_actual = StockSnapshot.get_stock_actual(contrato).filter(
        codigo_articulo=codigo_articulo
    ).first()
    
    if not stock_actual:
        messages.error(request, f"Artículo {codigo_articulo} no encontrado.")
        return redirect('dashboard-stock')
    
    # Calcular métricas
    consumo_diario = service.calcular_consumo_diario(codigo_articulo)
    dias_restantes = service.calcular_dias_restantes(stock_actual.stock_cantidad, consumo_diario)
    
    # Historial para gráfica
    tendencia = service.obtener_tendencia_articulo(codigo_articulo, dias=30)
    
    # Alertas del artículo
    alertas = AlertaStock.objects.filter(
        contrato=contrato,
        codigo_articulo=codigo_articulo,
        resuelta=False
    )
    
    context = {
        'contrato': contrato,
        'articulo': stock_actual,
        'consumo_diario': consumo_diario,
        'dias_restantes': dias_restantes,
        'tendencia_json': json.dumps(tendencia),
        'alertas': alertas,
    }
    
    return render(request, 'drilling/stock/detalle_articulo.html', context)


# =============================================================================
# GESTIÓN DE ALERTAS
# =============================================================================

class AlertaStockListView(LoginRequiredMixin, ListView):
    """Lista de alertas de stock"""
    model = AlertaStock
    template_name = 'drilling/stock/alertas_list.html'
    context_object_name = 'alertas'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = AlertaStock.objects.all()
        user = self.request.user
        
        # Filtrar por contrato según permisos
        if not user.is_superuser and user.role not in ['GERENCIA', 'CONTROL_PROYECTOS']:
            if hasattr(user, 'contrato') and user.contrato:
                queryset = queryset.filter(contrato=user.contrato)
            else:
                queryset = queryset.none()
        
        # Filtros
        contrato = self.request.GET.get('contrato')
        tipo = self.request.GET.get('tipo')
        prioridad = self.request.GET.get('prioridad')
        estado = self.request.GET.get('estado')
        
        if contrato:
            queryset = queryset.filter(contrato_id=contrato)
        if tipo:
            queryset = queryset.filter(tipo_alerta=tipo)
        if prioridad:
            queryset = queryset.filter(prioridad=prioridad)
        if estado == 'activas':
            queryset = queryset.filter(resuelta=False)
        elif estado == 'resueltas':
            queryset = queryset.filter(resuelta=True)
        elif estado == 'no_leidas':
            queryset = queryset.filter(leida=False)
        
        return queryset.select_related('contrato').order_by('prioridad', '-fecha_creacion')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Contratos para filtro
        if user.is_superuser or user.role in ['GERENCIA', 'CONTROL_PROYECTOS']:
            context['contratos'] = Contrato.objects.filter(estado='ACTIVO')
        elif hasattr(user, 'contrato') and user.contrato:
            context['contratos'] = Contrato.objects.filter(id=user.contrato.id)
        
        context['tipos_alerta'] = AlertaStock.TIPO_CHOICES
        context['prioridades'] = AlertaStock.PRIORIDAD_CHOICES
        context['filtros'] = {
            'contrato': self.request.GET.get('contrato', ''),
            'tipo': self.request.GET.get('tipo', ''),
            'prioridad': self.request.GET.get('prioridad', ''),
            'estado': self.request.GET.get('estado', 'activas'),
        }
        
        # Contador de alertas activas
        context['total_activas'] = AlertaStock.objects.filter(resuelta=False).count()
        context['total_criticas'] = AlertaStock.objects.filter(resuelta=False, prioridad=1).count()
        
        return context


@login_required
@require_POST
def marcar_alerta_leida(request, alerta_id):
    """Marca una alerta como leída"""
    alerta = get_object_or_404(AlertaStock, id=alerta_id)
    alerta.marcar_leida(request.user)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Alerta marcada como leída.')
    return redirect(request.META.get('HTTP_REFERER', 'alertas-stock-list'))


@login_required
@require_POST
def resolver_alerta(request, alerta_id):
    """Resuelve una alerta"""
    alerta = get_object_or_404(AlertaStock, id=alerta_id)
    nota = request.POST.get('nota', '')
    alerta.resolver(request.user, nota)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Alerta marcada como resuelta.')
    return redirect(request.META.get('HTTP_REFERER', 'alertas-stock-list'))


# =============================================================================
# API ENDPOINTS PARA GRÁFICAS Y FRONTEND
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_tendencia_articulo(request, contrato_id, codigo_articulo):
    """
    API: Obtiene datos de tendencia para gráfica de un artículo.
    """
    dias = int(request.GET.get('dias', 30))
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    service = StockService(contrato)
    tendencia = service.obtener_tendencia_articulo(codigo_articulo, dias=dias)
    
    return JsonResponse({
        'success': True,
        'codigo': codigo_articulo,
        'contrato': contrato.nombre_contrato,
        'dias': dias,
        'data': tendencia
    })


@login_required
@require_http_methods(["GET"])
def api_resumen_stock(request, contrato_id):
    """
    API: Obtiene resumen de stock para un contrato.
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    service = StockService(contrato)
    resumen = service.obtener_resumen_stock()
    
    # Convertir Decimals a float para JSON
    for key, value in resumen.items():
        if isinstance(value, Decimal):
            resumen[key] = float(value)
    
    return JsonResponse({
        'success': True,
        'data': resumen
    })


@login_required
@require_http_methods(["GET"])
def api_proyecciones_stock(request, contrato_id):
    """
    API: Obtiene proyecciones de stock para un contrato.
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    familia = request.GET.get('familia')  # PDD o ADIT
    
    service = StockService(contrato)
    proyecciones = service.obtener_proyeccion_stock()
    
    if familia:
        proyecciones = [p for p in proyecciones if p['familia'] == familia]
    
    # Convertir para JSON
    for p in proyecciones:
        for key, value in p.items():
            if isinstance(value, Decimal):
                p[key] = float(value)
            elif hasattr(value, 'isoformat'):
                p[key] = value.isoformat()
    
    return JsonResponse({
        'success': True,
        'contrato': contrato.nombre_contrato,
        'familia': familia,
        'count': len(proyecciones),
        'data': proyecciones
    })


@login_required
@require_http_methods(["GET"])
def api_alertas_activas(request):
    """
    API: Obtiene alertas activas para el badge del header.
    """
    user = request.user
    alertas = AlertaStock.get_alertas_activas(usuario=user)
    
    return JsonResponse({
        'success': True,
        'total': alertas.count(),
        'criticas': alertas.filter(prioridad=1).count(),
        'no_leidas': alertas.filter(leida=False).count(),
        'ultimas': list(alertas[:5].values(
            'id', 'tipo_alerta', 'descripcion_articulo', 
            'prioridad', 'mensaje', 'fecha_creacion'
        ))
    })


@login_required
@require_http_methods(["GET"])
def api_stock_actual(request, contrato_id):
    """
    API: Obtiene stock actual completo de un contrato.
    Útil para tablas y Power BI.
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    familia = request.GET.get('familia')
    
    stock = StockSnapshot.get_stock_actual(contrato, familia=familia)
    
    data = []
    for item in stock:
        data.append({
            'codigo': item.codigo_articulo,
            'descripcion': item.descripcion,
            'familia': item.familia,
            'stock': float(item.stock_cantidad),
            'unidad': item.unidad_medida,
            'lote': item.lote,
            'ubicacion': item.ubicacion,
            'precio_unitario': float(item.precio_unitario) if item.precio_unitario else None,
            'valor_total': float(item.valor_total) if item.valor_total else None,
            'fecha_sync': item.fecha_sync.isoformat()
        })
    
    return JsonResponse({
        'success': True,
        'contrato': contrato.nombre_contrato,
        'contrato_id': contrato.id,
        'familia': familia,
        'count': len(data),
        'data': data
    })


# =============================================================================
# SINCRONIZACIÓN MANUAL
# =============================================================================

@login_required
@require_POST
def sincronizar_stock_contrato(request, contrato_id):
    """
    Trigger sincronización manual de un contrato.
    Solo para usuarios con permisos.
    """
    user = request.user
    
    # Verificar permisos
    if not user.is_superuser and user.role not in ['GERENCIA', 'CONTROL_PROYECTOS', 'ADMINISTRADOR']:
        return JsonResponse({
            'success': False,
            'error': 'No tienes permisos para sincronizar stock.'
        }, status=403)
    
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if not contrato.codigo_centro_costo:
        return JsonResponse({
            'success': False,
            'error': 'El contrato no tiene código de centro de costo configurado.'
        }, status=400)
    
    try:
        service = StockService(contrato)
        resultado = service.sincronizar_stock_completo()
        
        return JsonResponse({
            'success': True,
            'contrato': contrato.nombre_contrato,
            'pdd_count': resultado['pdd']['count'],
            'adit_count': resultado['adit']['count'],
            'alertas_generadas': resultado['alertas_generadas'],
            'message': f'Sincronización completada: {resultado["pdd"]["count"]} PDD, {resultado["adit"]["count"]} ADIT'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def historial_sincronizaciones(request):
    """
    Vista para mostrar el historial de sincronizaciones de stock por contrato.
    Muestra las últimas sincronizaciones, cantidad de artículos y tiempos.
    """
    user = request.user
    
    # Verificar permisos
    if not user.is_superuser and user.role not in ['GERENCIA', 'CONTROL_PROYECTOS', 'ADMINISTRADOR']:
        messages.error(request, "No tienes permisos para ver este historial.")
        return redirect('dashboard')
    
    # Obtener contratos accesibles
    if user.is_superuser or user.role in ['GERENCIA', 'CONTROL_PROYECTOS']:
        contratos = Contrato.objects.filter(estado='ACTIVO')
    else:
        contratos = Contrato.objects.filter(id=user.contrato.id) if hasattr(user, 'contrato') else Contrato.objects.none()
    
    # Contrato seleccionado
    contrato_id = request.GET.get('contrato')
    if contrato_id:
        contrato = get_object_or_404(Contrato, id=contrato_id, estado='ACTIVO')
    else:
        contrato = contratos.first()
    
    historial = []
    
    if contrato:
        # Debug: Verificar si hay snapshots
        total_snapshots = StockSnapshot.objects.filter(contrato=contrato).count()
        print(f"[DEBUG] Total snapshots para {contrato.nombre_contrato}: {total_snapshots}")
        
        # Obtener fechas únicas de sincronización (últimas 50)
        fechas_sync = StockSnapshot.objects.filter(
            contrato=contrato
        ).values('fecha_sync').distinct().order_by('-fecha_sync')[:50]
        
        print(f"[DEBUG] Fechas únicas encontradas: {fechas_sync.count()}")
        
        for fecha_obj in fechas_sync:
            fecha = fecha_obj['fecha_sync']
            
            # Contar artículos por familia en esa fecha
            pdd_count = StockSnapshot.objects.filter(
                contrato=contrato,
                fecha_sync=fecha,
                familia='PDD'
            ).count()
            
            adit_count = StockSnapshot.objects.filter(
                contrato=contrato,
                fecha_sync=fecha,
                familia='ADIT'
            ).count()
            
            historial.append({
                'fecha': fecha,
                'pdd_count': pdd_count,
                'adit_count': adit_count,
                'total': pdd_count + adit_count
            })
            
        print(f"[DEBUG] Historial generado con {len(historial)} entradas")
    
    context = {
        'contratos': contratos,
        'contrato_seleccionado': contrato,
        'historial': historial,
        'tiene_centro_costo': contrato.codigo_centro_costo if contrato else None,
    }
    
    return render(request, 'drilling/stock/historial_sincronizaciones.html', context)


# ==================== VISTAS DE ABASTECIMIENTOS ====================

@login_required
def dashboard_control_proyectos_abastecimientos(request):
    """
    Dashboard consolidado multi-contrato para Control de Proyectos
    Muestra resumen de todos los contratos con sus abastecimientos y brocas
    """
    from .models import AbastecimientoArticulo, HistorialBroca, Maquina
    from django.db.models import Count, Sum
    from datetime import datetime
    
    user = request.user
    
    # Verificar que es Control de Proyectos, Gerencia o Superuser
    if not (user.is_superuser or user.role in ['GERENCIA', 'CONTROL_PROYECTOS']):
        messages.error(request, "No tienes acceso a este dashboard.")
        return redirect('dashboard')
    
    # Obtener filtros
    anio_filtro = request.GET.get('anio', datetime.now().year)
    contrato_filtro = request.GET.get('contrato')
    maquina_filtro = request.GET.get('maquina')
    
    # Obtener todos los contratos activos
    contratos = Contrato.objects.filter(estado='ACTIVO')
    
    # Filtrar contratos si se selecciona uno específico
    if contrato_filtro:
        contratos = contratos.filter(id=contrato_filtro)
    
    # Filtrar por máquina si se selecciona (mostrar contrato de la máquina)
    if maquina_filtro:
        contract_ids_by_maquina = Maquina.objects.filter(id=maquina_filtro).values_list('contrato_id', flat=True)
        contratos = contratos.filter(id__in=contract_ids_by_maquina)

    # Preparar datos por contrato
    contratos_data = []
    
    # Listas para comboboxes
    all_contratos = Contrato.objects.filter(estado='ACTIVO')
    all_maquinas = Maquina.objects.filter(estado='OPERATIVA').select_related('contrato')
    
    for contrato in contratos:
        # Base QuerySet para abastecimientos
        qs_abast = AbastecimientoArticulo.objects.filter(contrato=contrato)
        
        # Filtro por año (por defecto año actual si no se especifica)
        if anio_filtro:
            qs_abast = qs_abast.filter(fecha__year=anio_filtro)
            
        stats_abast = qs_abast.aggregate(
            total=Count('id'),
            valor_total=Sum('precio_total')
        )
        
        # Las métricas de brocas (estado actual) se mantienen globales
        # Opcional: Podríamos filtrar brocas_en_uso por máquina si tuviéramos esa relación directa fácil
        if maquina_filtro:
             # Si hay filtro de máquina, intentamos filtrar las brocas EN USO en esa máquina
             # Esto requiere cruzar con TurnoComplemento -> Turno -> Maquina... es complejo para este dashboard resumen
             # Por ahora mostramos métricas globales del contrato, ya que el filtro de máquina seleccionó el contrato.
             pass

        brocas_nuevas = HistorialBroca.objects.filter(
            contrato_actual=contrato,
            estado='NUEVA'
        ).count()
        
        brocas_en_uso = HistorialBroca.objects.filter(
            contrato_actual=contrato,
            estado='EN_USO'
        ).count()
        
        contratos_data.append({
            'id': contrato.id,
            'nombre': contrato.nombre_contrato,
            'centro_costo': contrato.codigo_centro_costo or 'N/A',
            'stats': {
                'total_abastecimientos': stats_abast['total'] or 0,
                'valor_total': stats_abast['valor_total'] or 0,
                'brocas_disponibles': brocas_nuevas + brocas_en_uso,
                'brocas_nuevas': brocas_nuevas,
                'brocas_en_uso': brocas_en_uso,
            }
        })
    
    # Totales generales
    totales = {
        'total_abastecimientos': sum(c['stats']['total_abastecimientos'] for c in contratos_data),
        'total_brocas': sum(c['stats']['brocas_disponibles'] for c in contratos_data),
        'valor_total': sum(c['stats']['valor_total'] for c in contratos_data),
        'periodo_actual': str(anio_filtro),
    }
    
    context = {
        'contratos': all_contratos, # Para el filtro
        'maquinas': all_maquinas,   # Para el filtro
        'contratos_data': contratos_data,
        'totales': totales,
        'anio_filtro': int(anio_filtro),
        'contrato_filtro': int(contrato_filtro) if contrato_filtro else None,
        'maquina_filtro': int(maquina_filtro) if maquina_filtro else None,
        'anios_disponibles': [2024, 2025, 2026],
    }
    
    return render(request, 'drilling/abastecimientos/dashboard_control_proyectos.html', context)


@login_required
def lista_abastecimientos(request):
    """
    Lista de abastecimientos sincronizados desde API externa
    """
    from .models import AbastecimientoArticulo
    from django.db.models import Q
    
    user = request.user
    
    # Determinar contratos accesibles
    if user.is_superuser or user.role in ['GERENCIA', 'CONTROL_PROYECTOS']:
        contratos = Contrato.objects.filter(estado='ACTIVO')
    elif hasattr(user, 'contrato') and user.contrato:
        contratos = Contrato.objects.filter(id=user.contrato.id)
    else:
        messages.error(request, "No tienes acceso a ningún contrato.")
        return redirect('dashboard')
    
    # Contrato seleccionado
    contrato_id = request.GET.get('contrato')
    if contrato_id:
        contrato = get_object_or_404(Contrato, id=contrato_id)
    else:
        contrato = contratos.first()
    
    if not contrato:
        messages.warning(request, "No hay contratos disponibles.")
        return redirect('dashboard')
    
    # Filtros
    familia = request.GET.get('familia', '')
    busqueda = request.GET.get('busqueda', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    
    # Queryset base
    abastecimientos = AbastecimientoArticulo.objects.filter(
        contrato=contrato
    ).select_related('contrato', 'historial_broca')
    
    # Aplicar filtros
    if familia:
        abastecimientos = abastecimientos.filter(familia=familia)
    
    if busqueda:
        abastecimientos = abastecimientos.filter(
            Q(codigo__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(serie__icontains=busqueda) |
            Q(documento__icontains=busqueda)
        )
    
    if fecha_inicio:
        abastecimientos = abastecimientos.filter(fecha__gte=fecha_inicio)
    
    if fecha_fin:
        abastecimientos = abastecimientos.filter(fecha__lte=fecha_fin)
    
    # Ordenar
    abastecimientos = abastecimientos.order_by('-fecha', '-fecha_sincronizacion')

    # Exportar CSV
    if request.GET.get('exportar') == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f"abastecimientos_{contrato.codigo_centro_costo}_{timezone.now().strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff')  # BOM para Excel
        writer = csv.writer(response)
        writer.writerow(['Fecha', 'Código', 'Serie', 'Descripción', 'Familia',
                         'Cantidad', 'Unidad', 'Precio Unitario', 'Precio Total', 'Documento', 'Contrato'])
        for item in abastecimientos.iterator():
            writer.writerow([
                item.fecha.strftime('%d/%m/%Y') if item.fecha else '',
                item.codigo or '',
                item.serie or '',
                item.descripcion or '',
                item.familia or '',
                item.cantidad,
                item.unidad or '',
                item.precio_unitario,
                item.precio_total,
                item.documento or '',
                contrato.nombre_contrato,
            ])
        return response

    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(abastecimientos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    stats = abastecimientos.aggregate(
        total_registros=Count('id'),
        total_cantidad=Sum('cantidad'),
        total_valor=Sum('precio_total'),
        brocas_con_serie=Count('id', filter=Q(familia='PDD', serie__isnull=False))
    )
    
    # Obtener todas las familias disponibles para el filtro
    familias_disponibles = AbastecimientoArticulo.objects.values_list('familia', flat=True).distinct().order_by('familia')
    
    context = {
        'contratos': contratos,
        'contrato': contrato,
        'page_obj': page_obj,
        'stats': stats,
        'familia': familia,
        'busqueda': busqueda,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'familias_disponibles': familias_disponibles,
    }
    
    return render(request, 'drilling/abastecimientos/lista.html', context)


@login_required
def detalle_abastecimiento(request, abastecimiento_id):
    """
    Detalle de un abastecimiento específico
    """
    from .models import AbastecimientoArticulo
    
    abastecimiento = get_object_or_404(
        AbastecimientoArticulo.objects.select_related(
            'contrato', 'historial_broca', 'historial_broca__tipo_complemento'
        ),
        id=abastecimiento_id
    )
    
    # Verificar permisos
    user = request.user
    if not (user.is_superuser or 
            user.role in ['GERENCIA', 'CONTROL_PROYECTOS'] or
            (hasattr(user, 'contrato') and user.contrato == abastecimiento.contrato)):
        messages.error(request, "No tienes permiso para ver este abastecimiento.")
        return redirect('lista-abastecimientos')
    
    # Si es una broca con serie, obtener información adicional
    broca_info = None
    if abastecimiento.historial_broca:
        broca = abastecimiento.historial_broca
        
        # Obtener historial de usos
        from .models import TurnoComplemento
        usos = TurnoComplemento.objects.filter(
            serie_broca=broca.serie
        ).select_related('turno').order_by('-turno__fecha')[:20]
        
        broca_info = {
            'broca': broca,
            'usos_recientes': usos,
            'metraje_total': broca.metraje_acumulado,
            'numero_usos': broca.numero_usos,
        }
    
    context = {
        'abastecimiento': abastecimiento,
        'broca_info': broca_info,
    }
    
    return render(request, 'drilling/abastecimientos/detalle.html', context)


@login_required
@require_POST
def sincronizar_abastecimientos_manual(request):
    """
    Endpoint para ejecutar sincronización manual desde la interfaz
    """
    from .utils.abastecimiento_service import abastecimiento_service
    
    periodo = request.POST.get('periodo')
    centro_costo = request.POST.get('centro_costo', '')
    familia = request.POST.get('familia', '')
    
    if not periodo:
        messages.error(request, "Debe especificar un periodo (formato YYYYMM)")
        return redirect('lista-abastecimientos')
    
    try:
        resultado = abastecimiento_service.sincronizar_periodo(
            periodo=periodo,
            centro_costo=centro_costo if centro_costo else None,
            solo_familia=familia if familia else None
        )
        
        if resultado['errores'] == 0:
            messages.success(
                request,
                f"Sincronización exitosa: {resultado['importados']} importados, "
                f"{resultado['actualizados']} actualizados, "
                f"{resultado['brocas_creadas']} brocas nuevas"
            )
        else:
            messages.warning(
                request,
                f"Sincronización con errores: {resultado['errores']} registros fallidos. "
                f"{resultado['importados']} importados correctamente."
            )
            
    except Exception as e:
        messages.error(request, f"Error en sincronización: {str(e)}")
    
    return redirect('lista-abastecimientos')


@login_required
def dashboard_brocas_disponibles(request):
    """
    Dashboard de Stock PDD - Productos Diamantados disponibles por tipo
    (Brocas, Zapatas, Reaming Shells, Core Lifters)
    """
    from .models import HistorialBroca
    from django.db.models import Avg, Count

    user = request.user

    # Determinar contratos accesibles
    if user.is_superuser or user.role in ['GERENCIA', 'CONTROL_PROYECTOS']:
        contratos = Contrato.objects.filter(estado='ACTIVO')
    elif hasattr(user, 'contrato') and user.contrato:
        contratos = Contrato.objects.filter(id=user.contrato.id)
    else:
        messages.error(request, "No tienes acceso a ningún contrato.")
        return redirect('dashboard')

    # Contrato seleccionado
    contrato_id = request.GET.get('contrato')
    if contrato_id:
        contrato = get_object_or_404(Contrato, id=contrato_id)
    else:
        contrato = contratos.first()

    if not contrato:
        messages.warning(request, "No hay contratos disponibles.")
        return redirect('dashboard')

    # Filtros opcionales
    filtro_tipo = request.GET.get('tipo', '')      # BROCA, ZAPATA, REAMING_SHELL, CORE_LIFTER
    filtro_estado = request.GET.get('estado', '')  # NUEVA, EN_USO
    filtro_marca = request.GET.get('marca', '')

    # Obtener todos los productos disponibles del contrato
    qs_base = HistorialBroca.objects.filter(
        contrato_actual=contrato,
        estado__in=['NUEVA', 'EN_USO']
    ).select_related('tipo_complemento').order_by(
        'tipo_complemento__categoria',
        'tipo_complemento__calibre',
        'tipo_complemento__altura',
        'tipo_complemento__serie_bit',
        'tipo_complemento__marca',
        'serie'
    )

    if filtro_tipo:
        qs_base = qs_base.filter(tipo_complemento__categoria=filtro_tipo)
    if filtro_estado:
        qs_base = qs_base.filter(estado=filtro_estado)
    if filtro_marca:
        qs_base = qs_base.filter(tipo_complemento__marca__icontains=filtro_marca)

    # Agrupar por tipo de producto
    TIPOS = [
        ('BROCA', 'Brocas Diamantadas', 'fas fa-circle-notch', '#28a745'),
        ('ZAPATA', 'Zapatas', 'fas fa-shoe-prints', '#007bff'),
        ('REAMING_SHELL', 'Reaming Shells', 'fas fa-ring', '#fd7e14'),
        ('CORE_LIFTER', 'Core Lifters', 'fas fa-compress-arrows-alt', '#6f42c1'),
    ]

    productos_por_tipo = []
    for tipo_key, tipo_label, icono, color in TIPOS:
        items = qs_base.filter(tipo_complemento__categoria=tipo_key)
        if not filtro_tipo or filtro_tipo == tipo_key:
            productos_por_tipo.append({
                'tipo_key': tipo_key,
                'tipo_label': tipo_label,
                'icono': icono,
                'color': color,
                'items': items,
                'total': items.count(),
                'nuevas': items.filter(estado='NUEVA').count(),
                'en_uso': items.filter(estado='EN_USO').count(),
            })

    # Marcas disponibles para filtro
    marcas_disponibles = (
        HistorialBroca.objects
        .filter(contrato_actual=contrato, estado__in=['NUEVA', 'EN_USO'])
        .exclude(tipo_complemento__marca='')
        .values_list('tipo_complemento__marca', flat=True)
        .distinct()
        .order_by('tipo_complemento__marca')
    )

    # Estadísticas generales
    stats = {
        'total_nuevas': qs_base.filter(estado='NUEVA').count(),
        'total_en_uso': qs_base.filter(estado='EN_USO').count(),
        'total_disponibles': qs_base.count(),
        'metraje_promedio': qs_base.filter(estado='EN_USO').aggregate(
            promedio=Avg('metraje_acumulado')
        )['promedio'] or 0,
        'total_brocas': qs_base.filter(tipo_complemento__categoria='BROCA').count(),
        'total_zapatas': qs_base.filter(tipo_complemento__categoria='ZAPATA').count(),
        'total_reaming': qs_base.filter(tipo_complemento__categoria='REAMING_SHELL').count(),
        'total_core_lifter': qs_base.filter(tipo_complemento__categoria='CORE_LIFTER').count(),
    }

    context = {
        'contratos': contratos,
        'contrato': contrato,
        'productos_por_tipo': productos_por_tipo,
        'stats': stats,
        'marcas_disponibles': marcas_disponibles,
        'filtro_tipo': filtro_tipo,
        'filtro_estado': filtro_estado,
        'filtro_marca': filtro_marca,
        # Compat backwards
        'brocas_nuevas': qs_base.filter(tipo_complemento__categoria='BROCA', estado='NUEVA'),
        'brocas_en_uso': qs_base.filter(tipo_complemento__categoria='BROCA', estado='EN_USO'),
    }

    return render(request, 'drilling/abastecimientos/dashboard_brocas.html', context)

