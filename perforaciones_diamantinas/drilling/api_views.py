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
        ).select_related('trabajador', 'trabajador__cargo')
        
        # Log para debug
        debug_info = {}
        for asist in todos_trabajadores:
            guardia = asist.guardia_snapshot
            grupo = asist.trabajador.grupo or 'SIN_GRUPO'
            cargo = asist.trabajador.cargo or 'SIN_CARGO'
            if guardia not in debug_info:
                debug_info[guardia] = []
            debug_info[guardia].append(f"{grupo} - {cargo}")
        
        logger.info(f"DEBUG - Trabajadores por guardia en {fecha_str}: {debug_info}")
        
        # Filtrar por CARGO en lugar de grupo funcional
        # Buscar cargos que contengan palabras clave de operadores
        grupos_query = AsistenciaTrabajador.objects.filter(
            trabajador__contrato=contrato,
            fecha=fecha,
            estado='TRABAJADO',
            guardia_snapshot__isnull=False
        ).filter(
            # Filtrar por cargo que contenga palabras clave de perforistas/ayudantes
            trabajador__cargo__iregex=r'(perforist|ayudante|operador|winch)'
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
        # Filtrar por CARGO en lugar de grupo funcional
        asistencias = AsistenciaTrabajador.objects.filter(
            trabajador__contrato=contrato,
            fecha=fecha,
            guardia_snapshot=grupo,
            estado='TRABAJADO'  # Solo trabajadores que asistieron
        ).filter(
            # Filtrar por cargo que contenga palabras clave de perforistas/ayudantes
            trabajador__cargo__iregex=r'(perforist|ayudante|operador|winch)'
        ).select_related('trabajador') # .select_related('trabajador__cargo')  # Removed incorrect select_related
        
        trabajadores_data = []
        for asistencia in asistencias:
            trabajador = asistencia.trabajador
            trabajadores_data.append({
                'id': trabajador.id,
                'dni': trabajador.dni,
                'nombres': trabajador.nombres,
                'apellidos': trabajador.apellidos,
                'nombre_completo': f"{trabajador.nombres} {trabajador.apellidos}".strip(),
                'cargo': asistencia.cargo_snapshot or trabajador.cargo or '',
                'guardia': asistencia.guardia_snapshot,
                'funcion': trabajador.cargo or ''  # Función por defecto basada en su cargo
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


@login_required
@require_http_methods(["POST"])
def api_crear_sondaje_rapido(request):
    """
    API para crear un sondaje rápido desde el formulario de crear turno
    """
    from .models import Sondaje
    from decimal import Decimal, InvalidOperation
    from django.core.exceptions import ValidationError
    
    try:
        # Validar permisos
        if not request.user.can_supervise_operations():
            return JsonResponse({
                'success': False,
                'error': 'No tiene permisos para crear sondajes'
            }, status=403)
        
        # Obtener contrato del usuario
        if not request.user.contrato:
            return JsonResponse({
                'success': False,
                'error': 'Usuario sin contrato asignado'
            }, status=400)
        
        # Obtener datos del formulario
        nombre_sondaje = request.POST.get('nombre_sondaje', '').strip()
        fecha_inicio = request.POST.get('fecha_inicio')
        profundidad = request.POST.get('profundidad')
        inclinacion = request.POST.get('inclinacion')
        cota_collar = request.POST.get('cota_collar')
        
        # Validar campos requeridos
        if not all([nombre_sondaje, fecha_inicio, profundidad, inclinacion, cota_collar]):
            return JsonResponse({
                'success': False,
                'error': 'Todos los campos son requeridos'
            }, status=400)
        
        # Convertir a Decimal
        try:
            profundidad = Decimal(profundidad)
            inclinacion = Decimal(inclinacion)
            cota_collar = Decimal(cota_collar)
        except (InvalidOperation, ValueError):
            return JsonResponse({
                'success': False,
                'error': 'Valores numéricos inválidos'
            }, status=400)
        
        # Crear sondaje
        sondaje = Sondaje(
            contrato=request.user.contrato,
            nombre_sondaje=nombre_sondaje,
            fecha_inicio=fecha_inicio,
            profundidad=profundidad,
            inclinacion=inclinacion,
            cota_collar=cota_collar,
            estado='ACTIVO'
        )
        
        # Validar modelo
        sondaje.full_clean()
        sondaje.save()
        
        return JsonResponse({
            'success': True,
            'sondaje': {
                'id': sondaje.id,
                'nombre_sondaje': sondaje.nombre_sondaje,
                'fecha_inicio': sondaje.fecha_inicio.isoformat(),
                'profundidad': float(sondaje.profundidad),
                'inclinacion': float(sondaje.inclinacion),
                'cota_collar': float(sondaje.cota_collar),
                'estado': sondaje.estado
            }
        })
        
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error creando sondaje rápido: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno al crear el sondaje'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_actualizar_grupo_trabajador(request, pk):
    """
    Actualiza el campo 'grupo' de un Trabajador vía AJAX.
    Body JSON: { "grupo": "OPERADORES" | "SERVICIOS_GEOLOGICOS" | "PERSONAL_AUXILIAR" | "LINEA_MANDO" | "" }
    """
    import json
    from .models import Trabajador

    GRUPOS_VALIDOS = {'OPERADORES', 'SERVICIOS_GEOLOGICOS', 'PERSONAL_AUXILIAR', 'LINEA_MANDO', ''}

    try:
        data = json.loads(request.body)
        grupo = data.get('grupo', '').strip()
        if grupo not in GRUPOS_VALIDOS:
            return JsonResponse({'success': False, 'error': 'Grupo inválido'}, status=400)

        trabajador = Trabajador.objects.get(pk=pk)

        # Cualquier usuario que pueda crear/editar datos básicos puede asignar grupo
        if not request.user.is_staff and not request.user.can_create_basic_data():
            return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

        # Usar QuerySet.update() para evitar que el model save() sobreescriba el grupo
        # via asignar_grupo_automatico()
        Trabajador.objects.filter(pk=pk).update(grupo=grupo or None)

        grupo_display = dict(Trabajador.GRUPO_CHOICES).get(grupo, '-') if grupo else '-'
        return JsonResponse({'success': True, 'grupo': grupo, 'grupo_display': grupo_display})

    except Trabajador.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Trabajador no encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Error actualizando grupo del trabajador {pk}: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_set_fecha_inicio_labores(request, pk):
    """
    Actualiza el campo 'fecha_inicio_labores' de un Trabajador vía AJAX.
    Body JSON: { "fecha_inicio_labores": "YYYY-MM-DD" | "" }
    Celdas del tareo anteriores a esta fecha quedarán bloqueadas (sin tareo).
    """
    import json
    from datetime import date
    from .models import Trabajador

    try:
        data = json.loads(request.body)
        fecha_str = data.get('fecha_inicio_labores', '').strip()

        if not request.user.is_staff and not request.user.can_create_basic_data():
            return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

        trabajador = Trabajador.objects.get(pk=pk)

        if fecha_str:
            try:
                fecha = date.fromisoformat(fecha_str)
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Fecha inválida, use formato YYYY-MM-DD'}, status=400)
        else:
            fecha = None

        Trabajador.objects.filter(pk=pk).update(fecha_inicio_labores=fecha)

        return JsonResponse({
            'success': True,
            'fecha_inicio_labores': fecha_str or None,
        })

    except Trabajador.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Trabajador no encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Error actualizando fecha_inicio_labores del trabajador {pk}: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_ultima_broca_sondaje(request, sondaje_id):
    """
    Endpoint para obtener la última broca y rimador usados en un sondaje.
    Retorna JSON con la última serie, tipo y metros para pre-rellenar el formulario.
    """
    from .models import TurnoComplemento

    def get_last(categoria_list):
        qs = TurnoComplemento.objects.filter(
            sondaje_id=sondaje_id,
            tipo_complemento__categoria__in=categoria_list
        ).select_related('tipo_complemento', 'turno').order_by('-turno__fecha', '-id')
        return qs.first()

    try:
        last_broca = get_last(['BROCA'])
        last_reamer = get_last(['REAMER', 'RIMADOR'])

        def serialize(comp):
            if not comp:
                return None
            return {
                'serie': comp.codigo_serie or '',
                'tipo_complemento_id': comp.tipo_complemento_id,
                'nombre': comp.tipo_complemento.nombre,
                'categoria': comp.tipo_complemento.categoria or 'BROCA',
                'calibre': comp.tipo_complemento.calibre or '',
                'metros_fin': float(comp.metros_fin) if comp.metros_fin is not None else None,
            }

        return JsonResponse({
            'success': True,
            'broca': serialize(last_broca),
            'reamer': serialize(last_reamer),
        })
    except Exception as e:
        logger.error(f"Error obteniendo última broca del sondaje {sondaje_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_ultimo_horometro_maquina(request, maquina_id):
    """
    Retorna el último horómetro registrado para una máquina.
    Primero busca en TurnoMaquina el último horometro_fin con fecha más reciente;
    si no existe, devuelve el campo horometro del modelo Maquina.
    """
    from .models import Maquina, TurnoMaquina
    try:
        maquina = Maquina.objects.get(pk=maquina_id)
        # Buscar el último TurnoMaquina con horometro_fin registrado
        # TurnoMaquina no tiene FK directa a Maquina; se accede via turno__maquina
        ultimo_tm = (
            TurnoMaquina.objects
            .filter(turno__maquina=maquina, horometro_fin__isnull=False)
            .select_related('turno')
            .order_by('-turno__fecha', '-turno__tipo_turno__nombre', '-id')
            .first()
        )
        if ultimo_tm is not None:
            ultimo_horometro = float(ultimo_tm.horometro_fin)
        elif maquina.horometro:
            ultimo_horometro = float(maquina.horometro)
        else:
            ultimo_horometro = None

        return JsonResponse({
            'success': True,
            'maquina_id': maquina_id,
            'maquina_nombre': maquina.nombre,
            'ultimo_horometro': ultimo_horometro,
        })
    except Maquina.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Máquina no encontrada'}, status=404)
    except Exception as e:
        logger.error(f"Error obteniendo último horómetro de la máquina {maquina_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
