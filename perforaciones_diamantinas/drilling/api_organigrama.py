"""
API para gestión del organigrama semanal
Permite guardar, editar y consultar asignaciones de trabajadores por semana
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json
from datetime import datetime, timedelta
from .models import (
    Trabajador, Maquina, Vehiculo, Equipo, OrganigramaSemanal, 
    AsignacionOrganigrama, GuardiaConductor, AsignacionEquipo
)


@login_required
@require_http_methods(["POST"])
def guardar_asignaciones_masivas(request):
    """
    Guarda múltiples asignaciones de trabajadores a máquinas y guardias para una semana
    Permite editar asignaciones existentes
    """
    try:
        data = json.loads(request.body)
        asignaciones = data.get('asignaciones', [])
        organigrama_semanal_id = data.get('organigrama_semanal_id')
        
        if not asignaciones:
            return JsonResponse({'success': False, 'message': 'No hay asignaciones para guardar'}, status=400)
        
        if not organigrama_semanal_id:
            return JsonResponse({'success': False, 'message': 'Falta ID de organigrama semanal'}, status=400)
        
        # Obtener organigrama semanal
        try:
            organigrama = OrganigramaSemanal.objects.get(id=organigrama_semanal_id)
        except OrganigramaSemanal.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Organigrama semanal no encontrado'}, status=404)
        
        # Validar acceso al contrato
        if not request.user.has_access_to_all_contracts():
            if organigrama.contrato != request.user.contrato:
                return JsonResponse({'success': False, 'message': 'No tiene acceso a este contrato'}, status=403)
        
        # Usar transacción para asegurar atomicidad
        with transaction.atomic():
            actualizados = 0
            creados = 0
            errores = []
            
            for asig in asignaciones:
                try:
                    trabajador_id = asig.get('trabajador_id')
                    maquina_id = asig.get('maquina_id')
                    guardia = asig.get('guardia')
                    estado = asig.get('estado', 'OPERATIVO')
                    
                    # Obtener trabajador
                    trabajador = Trabajador.objects.get(id=trabajador_id)
                    
                    # Validar que el trabajador sea del mismo contrato
                    if trabajador.contrato != organigrama.contrato:
                        errores.append(f'Trabajador {trabajador_id} no pertenece al contrato')
                        continue
                    
                    # Obtener o crear asignación
                    asignacion, created = AsignacionOrganigrama.objects.get_or_create(
                        organigrama_semanal=organigrama,
                        trabajador=trabajador,
                        defaults={
                            'estado': estado
                        }
                    )
                    
                    # Actualizar datos
                    if maquina_id:
                        maquina = Maquina.objects.get(id=maquina_id, contrato=organigrama.contrato)
                        asignacion.maquina = maquina
                    else:
                        asignacion.maquina = None
                    
                    asignacion.guardia = guardia
                    asignacion.estado = estado
                    asignacion.save()
                    
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
                    
                except Trabajador.DoesNotExist:
                    errores.append(f'Trabajador {trabajador_id} no encontrado')
                except Maquina.DoesNotExist:
                    errores.append(f'Máquina {maquina_id} no encontrada')
                except Exception as e:
                    errores.append(f'Error en asignación: {str(e)}')
            
            # Actualizar organigrama como modificado
            organigrama.modificado_por = request.user
            organigrama.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Se procesaron {creados + actualizados} asignaciones ({creados} nuevas, {actualizados} actualizadas)',
                'creados': creados,
                'actualizados': actualizados,
                'errores': errores
            })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def marcar_stand_by(request):
    """
    Marca trabajadores como Stand By para la semana
    """
    try:
        data = json.loads(request.body)
        trabajador_id = data.get('trabajador_id')
        organigrama_semanal_id = data.get('organigrama_semanal_id')
        estado = data.get('estado', 'STAND_BY')  # STAND_BY, OPERATIVO, etc.
        
        if not trabajador_id or not organigrama_semanal_id:
            return JsonResponse({'success': False, 'message': 'Faltan parámetros'}, status=400)
        
        # Obtener organigrama y trabajador
        organigrama = OrganigramaSemanal.objects.get(id=organigrama_semanal_id)
        trabajador = Trabajador.objects.get(id=trabajador_id)
        
        # Validar acceso
        if not request.user.has_access_to_all_contracts():
            if organigrama.contrato != request.user.contrato:
                return JsonResponse({'success': False, 'message': 'No tiene acceso'}, status=403)
        
        # Obtener o crear asignación
        asignacion, created = AsignacionOrganigrama.objects.get_or_create(
            organigrama_semanal=organigrama,
            trabajador=trabajador,
            defaults={'estado': estado}
        )
        
        if not created:
            asignacion.estado = estado
            # Si se marca como stand by, limpiar máquina y guardia
            if estado == 'STAND_BY':
                asignacion.maquina = None
                asignacion.guardia = None
            asignacion.save()
        
        # Actualizar organigrama
        organigrama.modificado_por = request.user
        organigrama.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{trabajador.nombres} marcado como {asignacion.get_estado_display()}',
            'asignacion': {
                'id': asignacion.id,
                'trabajador_id': trabajador.id,
                'estado': asignacion.estado
            }
        })
        
    except (OrganigramaSemanal.DoesNotExist, Trabajador.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Registro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def guardar_guardias_conductores(request):
    """
    Guarda las guardias de conductores (A, B, C) con sus vehículos asignados
    """
    try:
        data = json.loads(request.body)
        guardias = data.get('guardias', [])
        organigrama_semanal_id = data.get('organigrama_semanal_id')
        
        if not guardias:
            return JsonResponse({'success': False, 'message': 'No hay guardias para guardar'}, status=400)
        
        if not organigrama_semanal_id:
            return JsonResponse({'success': False, 'message': 'Falta ID de organigrama semanal'}, status=400)
        
        # Obtener organigrama
        organigrama = OrganigramaSemanal.objects.get(id=organigrama_semanal_id)
        
        # Validar acceso
        if not request.user.has_access_to_all_contracts():
            if organigrama.contrato != request.user.contrato:
                return JsonResponse({'success': False, 'message': 'No tiene acceso'}, status=403)
        
        with transaction.atomic():
            actualizados = 0
            creados = 0
            errores = []
            
            for guardia_data in guardias:
                try:
                    conductor_id = guardia_data.get('conductor_id')
                    vehiculo_id = guardia_data.get('vehiculo_id')
                    guardia = guardia_data.get('guardia')
                    estado = guardia_data.get('estado', 'ACTIVO')
                    
                    # Obtener conductor
                    conductor = Trabajador.objects.get(id=conductor_id)
                    
                    # Validar que sea del mismo contrato
                    if conductor.contrato != organigrama.contrato:
                        errores.append(f'Conductor {conductor_id} no pertenece al contrato')
                        continue
                    
                    # Obtener o crear guardia de conductor
                    guardia_conductor, created = GuardiaConductor.objects.get_or_create(
                        organigrama_semanal=organigrama,
                        conductor=conductor,
                        defaults={
                            'guardia': guardia,
                            'estado': estado
                        }
                    )
                    
                    # Actualizar datos
                    if vehiculo_id:
                        vehiculo = Vehiculo.objects.get(id=vehiculo_id, contrato=organigrama.contrato)
                        guardia_conductor.vehiculo = vehiculo
                    else:
                        guardia_conductor.vehiculo = None
                    
                    guardia_conductor.guardia = guardia
                    guardia_conductor.estado = estado
                    guardia_conductor.save()
                    
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
                    
                except Trabajador.DoesNotExist:
                    errores.append(f'Conductor {conductor_id} no encontrado')
                except Vehiculo.DoesNotExist:
                    errores.append(f'Vehículo {vehiculo_id} no encontrado')
                except Exception as e:
                    errores.append(f'Error en guardia: {str(e)}')
            
            # Actualizar organigrama
            organigrama.modificado_por = request.user
            organigrama.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Se procesaron {creados + actualizados} guardias ({creados} nuevas, {actualizados} actualizadas)',
                'creados': creados,
                'actualizados': actualizados,
                'errores': errores
            })
        
    except OrganigramaSemanal.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Organigrama semanal no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def eliminar_asignacion(request):
    """
    Elimina una asignación específica o la marca como Stand By
    """
    try:
        data = json.loads(request.body)
        asignacion_id = data.get('asignacion_id')
        
        if not asignacion_id:
            return JsonResponse({'success': False, 'message': 'Falta ID de asignación'}, status=400)
        
        asignacion = AsignacionOrganigrama.objects.get(id=asignacion_id)
        
        # Validar acceso
        if not request.user.has_access_to_all_contracts():
            if asignacion.organigrama_semanal.contrato != request.user.contrato:
                return JsonResponse({'success': False, 'message': 'No tiene acceso'}, status=403)
        
        # Marcar como stand by en lugar de eliminar para mantener histórico
        asignacion.maquina = None
        asignacion.guardia = None
        asignacion.estado = 'STAND_BY'
        asignacion.save()
        
        # Actualizar organigrama
        organigrama = asignacion.organigrama_semanal
        organigrama.modificado_por = request.user
        organigrama.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{asignacion.trabajador.nombres} movido a Stand By'
        })
        
    except AsignacionOrganigrama.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Asignación no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def guardar_asignaciones_equipos(request):
    """
    Guarda las asignaciones de equipos a trabajadores
    Equipos: laptops, celulares, módems, impresoras, detector de tormentas, enmicadora, radios
    """
    try:
        data = json.loads(request.body)
        asignaciones = data.get('asignaciones', [])
        organigrama_semanal_id = data.get('organigrama_semanal_id')
        
        if not organigrama_semanal_id:
            return JsonResponse({'success': False, 'message': 'Falta ID de organigrama semanal'}, status=400)
        
        # Obtener organigrama
        organigrama = OrganigramaSemanal.objects.get(id=organigrama_semanal_id)
        
        # Validar acceso
        if not request.user.has_access_to_all_contracts():
            if organigrama.contrato != request.user.contrato:
                return JsonResponse({'success': False, 'message': 'No tiene acceso'}, status=403)
        
        with transaction.atomic():
            actualizados = 0
            creados = 0
            errores = []
            
            for asig_data in asignaciones:
                try:
                    trabajador_id = asig_data.get('trabajador_id')
                    equipo_id = asig_data.get('equipo_id')
                    estado = asig_data.get('estado', 'ACTIVO')
                    acta_entrega = asig_data.get('acta_entrega', False)
                    observaciones = asig_data.get('observaciones', '')
                    
                    # Validar datos requeridos
                    if not trabajador_id or not equipo_id:
                        errores.append('Faltan trabajador_id o equipo_id')
                        continue
                    
                    # Obtener trabajador y equipo
                    trabajador = Trabajador.objects.get(id=trabajador_id)
                    equipo = Equipo.objects.get(id=equipo_id)
                    
                    # Validar que sean del mismo contrato
                    if trabajador.contrato != organigrama.contrato:
                        errores.append(f'Trabajador {trabajador_id} no pertenece al contrato')
                        continue
                    
                    if equipo.contrato != organigrama.contrato:
                        errores.append(f'Equipo {equipo_id} no pertenece al contrato')
                        continue
                    
                    # Crear o actualizar asignación
                    asignacion, created = AsignacionEquipo.objects.get_or_create(
                        organigrama_semanal=organigrama,
                        trabajador=trabajador,
                        equipo=equipo,
                        defaults={
                            'estado': estado,
                            'acta_entrega': acta_entrega,
                            'observaciones': observaciones
                        }
                    )
                    
                    # Si ya existía, actualizar
                    if not created:
                        asignacion.estado = estado
                        asignacion.acta_entrega = acta_entrega
                        asignacion.observaciones = observaciones
                        asignacion.save()
                        actualizados += 1
                    else:
                        creados += 1
                    
                    # Actualizar estado del equipo
                    if estado == 'ACTIVO':
                        equipo.estado = 'ASIGNADO'
                    elif estado == 'DEVUELTO':
                        equipo.estado = 'DISPONIBLE'
                    equipo.save()
                    
                except Trabajador.DoesNotExist:
                    errores.append(f'Trabajador {trabajador_id} no encontrado')
                except Equipo.DoesNotExist:
                    errores.append(f'Equipo {equipo_id} no encontrado')
                except Exception as e:
                    errores.append(f'Error en asignación: {str(e)}')
            
            # Actualizar organigrama
            organigrama.modificado_por = request.user
            organigrama.save()
            
            mensaje = f'Se procesaron {creados + actualizados} asignaciones de equipos'
            if creados > 0:
                mensaje += f' ({creados} nuevas)'
            if actualizados > 0:
                mensaje += f' ({actualizados} actualizadas)'
            
            return JsonResponse({
                'success': True,
                'message': mensaje,
                'creados': creados,
                'actualizados': actualizados,
                'errores': errores
            })
        
    except OrganigramaSemanal.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Organigrama semanal no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

