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
from .mixins import ContratoAccessMixin


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
