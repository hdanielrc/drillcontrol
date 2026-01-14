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


@login_required
@require_http_methods(["GET"])
def api_grupos_disponibles_por_fecha(request):
    """
    Endpoint para obtener los grupos (guardias A, B, C) disponibles en una fecha específica
    según el tareo de asistencia.
    
    Parámetros:
        - fecha: Fecha en formato YYYY-MM-DD
        - contrato_id: ID del contrato (opcional, se obtiene del usuario si no se proporciona)
    
    Retorna:
        JSON con los grupos disponibles en esa fecha
    """
    from .models import AsistenciaTrabajador, Contrato
    from datetime import datetime
    
    fecha_str = request.GET.get('fecha')
    contrato_id = request.GET.get('contrato_id')
    
    if not fecha_str:
        return JsonResponse({
            'success': False,
            'error': 'Debe proporcionar una fecha'
        }, status=400)
    
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
        }, status=400)
    
    # Determinar el contrato
    if contrato_id:
        try:
            contrato = Contrato.objects.get(id=contrato_id)
        except Contrato.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Contrato no encontrado'
            }, status=404)
    elif hasattr(request.user, 'contrato') and request.user.contrato:
        contrato = request.user.contrato
    else:
        return JsonResponse({
            'success': False,
            'error': 'No se pudo determinar el contrato'
        }, status=400)
    
    try:
        # Buscar grupos disponibles en la fecha específica del contrato
        # Primero verificar TODOS los trabajadores para debug
        todos_trabajadores = AsistenciaTrabajador.objects.filter(
            trabajador__contrato=contrato,
            fecha=fecha,
            estado='TRABAJADO',
            guardia_snapshot__isnull=False
        ).exclude(
            guardia_snapshot=''
        ).select_related('trabajador')
        
        # Log para debug
        debug_info = {}
        for asist in todos_trabajadores:
            guardia = asist.guardia_snapshot
            grupo = asist.trabajador.grupo or 'SIN_GRUPO'
            cargo = asist.trabajador.cargo.nombre if asist.trabajador.cargo else 'SIN_CARGO'
            if guardia not in debug_info:
                debug_info[guardia] = []
            debug_info[guardia].append(f"{grupo} - {cargo}")
        
        logger.info(f"DEBUG - Trabajadores por guardia en {fecha_str}: {debug_info}")
        
        # Ahora filtrar solo OPERADORES
        grupos_query = AsistenciaTrabajador.objects.filter(
            trabajador__contrato=contrato,
            fecha=fecha,
            estado='TRABAJADO',
            guardia_snapshot__isnull=False
        ).filter(
            # Filtrar solo por grupos de operadores (perforistas y ayudantes)
            trabajador__grupo__in=[
                'OPERADORES_INTERIOR_MINA',
                'OPERADORES_SUPERFICIE',
                'OPERADORES'  # Legacy
            ]
        ).exclude(
            guardia_snapshot=''
        ).values_list('guardia_snapshot', flat=True).distinct().order_by('guardia_snapshot')
        
        grupos = list(grupos_query)
        
        logger.info(f"Grupos con OPERADORES para fecha {fecha_str}: {grupos}")
        
        return JsonResponse({
            'success': True,
            'fecha': fecha_str,
            'contrato': contrato.nombre_contrato,
            'grupos': grupos,
            'count': len(grupos),
            'debug': debug_info  # Agregar info de debug en respuesta
        })
    except Exception as e:
        logger.error(f"Error obteniendo grupos disponibles para fecha {fecha_str}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_trabajadores_por_grupo_fecha(request):
    """
    Endpoint para obtener los trabajadores de un grupo específico en una fecha dada
    según el tareo de asistencia.
    
    Parámetros:
        - fecha: Fecha en formato YYYY-MM-DD
        - grupo: Grupo/Guardia (A, B, C)
        - contrato_id: ID del contrato (opcional, se obtiene del usuario si no se proporciona)
    
    Retorna:
        JSON con los trabajadores del grupo en esa fecha con sus funciones
    """
    from .models import AsistenciaTrabajador, Contrato, Trabajador
    from datetime import datetime
    
    fecha_str = request.GET.get('fecha')
    grupo = request.GET.get('grupo')
    contrato_id = request.GET.get('contrato_id')
    
    if not fecha_str or not grupo:
        return JsonResponse({
            'success': False,
            'error': 'Debe proporcionar fecha y grupo'
        }, status=400)
    
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
        }, status=400)
    
    # Determinar el contrato
    if contrato_id:
        try:
            contrato = Contrato.objects.get(id=contrato_id)
        except Contrato.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Contrato no encontrado'
            }, status=404)
    elif hasattr(request.user, 'contrato') and request.user.contrato:
        contrato = request.user.contrato
    else:
        return JsonResponse({
            'success': False,
            'error': 'No se pudo determinar el contrato'
        }, status=400)
    
    try:
        # Obtener trabajadores del grupo en la fecha específica
        # Filtrar solo OPERADORES (perforistas y ayudantes)
        asistencias = AsistenciaTrabajador.objects.filter(
            trabajador__contrato=contrato,
            fecha=fecha,
            guardia_snapshot=grupo,
            estado='TRABAJADO'  # Solo trabajadores que asistieron
        ).filter(
            # Filtrar solo por grupos de operadores
            trabajador__grupo__in=[
                'OPERADORES_INTERIOR_MINA',
                'OPERADORES_SUPERFICIE',
                'OPERADORES'  # Legacy
            ]
        ).select_related('trabajador', 'trabajador__cargo')
        
        trabajadores_data = []
        for asistencia in asistencias:
            trabajador = asistencia.trabajador
            trabajadores_data.append({
                'id': trabajador.id,
                'dni': trabajador.dni,
                'nombres': trabajador.nombres,
                'apellidos': trabajador.apellidos,
                'nombre_completo': f"{trabajador.nombres} {trabajador.apellidos}".strip(),
                'cargo': asistencia.cargo_snapshot or (trabajador.cargo.nombre if trabajador.cargo else ''),
                'guardia': asistencia.guardia_snapshot,
                'funcion': trabajador.cargo.nombre if trabajador.cargo else ''  # Función por defecto basada en su cargo
            })
        
        return JsonResponse({
            'success': True,
            'fecha': fecha_str,
            'grupo': grupo,
            'contrato': contrato.nombre_contrato,
            'trabajadores': trabajadores_data,
            'count': len(trabajadores_data)
        })
    except Exception as e:
        logger.error(f"Error obteniendo trabajadores del grupo {grupo} para fecha {fecha_str}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
