"""
Vistas para integración con APIs de Vilbragroup
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .api_client import get_api_client
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def api_stock_productos_diamantados(request):
    """
    Endpoint para obtener stock de productos diamantados desde API
    Retorna JSON para consumo desde frontend (AJAX)
    """
    # Obtener centro de costo del usuario logueado
    centro_costo = None
    if hasattr(request.user, 'contrato') and request.user.contrato:
        centro_costo = request.user.contrato.codigo_centro_costo
    
    # Permitir override por query param (para testing o admin)
    if request.GET.get('centro_costo'):
        centro_costo = request.GET.get('centro_costo')
    
    try:
        client = get_api_client()
        productos = client.obtener_productos_diamantados(centro_costo=centro_costo or None)
        
        return JsonResponse({
            'success': True,
            'centro_costo_usado': centro_costo,
            'data': productos,
            'count': len(productos)
        })
    except Exception as e:
        logger.error(f"Error obteniendo productos diamantados: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_stock_aditivos(request):
    """
    Endpoint para obtener stock de aditivos desde API
    Retorna JSON para consumo desde frontend (AJAX)
    """
    # Obtener centro de costo del usuario logueado
    centro_costo = None
    if hasattr(request.user, 'contrato') and request.user.contrato:
        centro_costo = request.user.contrato.codigo_centro_costo
    
    # Permitir override por query param (para testing o admin)
    if request.GET.get('centro_costo'):
        centro_costo = request.GET.get('centro_costo')
    
    try:
        client = get_api_client()
        aditivos = client.obtener_aditivos(centro_costo=centro_costo or None)
        
        return JsonResponse({
            'success': True,
            'centro_costo_usado': centro_costo,
            'data': aditivos,
            'count': len(aditivos)
        })
    except Exception as e:
        logger.error(f"Error obteniendo aditivos: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def vista_stock_almacen(request):
    """
    Vista HTML para visualizar el stock del almacén
    Muestra productos diamantados y aditivos
    """
    return render(request, 'drilling/almacen/stock.html')


@login_required
@require_http_methods(["GET"])
def api_sondaje_estado(request, sondaje_id):
    """
    Endpoint para obtener el estado actual de un sondaje
    Retorna JSON para consumo desde frontend (AJAX)
    """
    from .models import Sondaje
    
    try:
        sondaje = Sondaje.objects.get(id=sondaje_id)
        
        # Verificar permisos: usuario debe tener acceso al contrato del sondaje
        if not request.user.is_staff:
            if not hasattr(request.user, 'contrato') or request.user.contrato != sondaje.contrato:
                return JsonResponse({
                    'success': False,
                    'error': 'No tiene permisos para ver este sondaje'
                }, status=403)
        
        return JsonResponse({
            'success': True,
            'estado': sondaje.estado,
            'estado_display': sondaje.get_estado_display(),
            'nombre_sondaje': sondaje.nombre_sondaje
        })
    except Sondaje.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Sondaje no encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Error obteniendo estado del sondaje {sondaje_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


