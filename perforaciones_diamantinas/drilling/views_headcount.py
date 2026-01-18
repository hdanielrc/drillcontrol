"""
Views para el módulo de Headcount (Planificación de Personal)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Sum, Count, Q
from django.urls import reverse
from .models import HeadCount, Contrato, Trabajador, Cargo, Maquina
from .forms import HeadCountForm


@login_required
def headcount_dashboard(request):
    """Dashboard principal de headcount"""
    # Verificar permisos
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT']:
        messages.error(request, 'No tienes permisos para acceder a esta sección')
        return redirect('dashboard')
    
    # Obtener contratos según permisos
    if request.user.has_access_to_all_contracts():
        contratos = Contrato.objects.filter(estado='ACTIVO')
    else:
        contratos = Contrato.objects.filter(id=request.user.contrato.id, estado='ACTIVO')
    
    # Obtener headcount activo
    headcounts = HeadCount.objects.filter(
        contrato__in=contratos,
        activo=True
    ).select_related('contrato', 'cargo', 'maquina')
    
    # Calcular estadísticas
    total_requerido = headcounts.aggregate(total=Sum('cantidad_requerida'))['total'] or 0
    
    # Personal actual por contrato
    trabajadores_activos = Trabajador.objects.filter(
        contrato__in=contratos,
        estado='ACTIVO'
    ).count()
    
    # Calcular cumplimiento por contrato
    contratos_data = []
    for contrato in contratos:
        hc_contrato = headcounts.filter(contrato=contrato)
        requerido = hc_contrato.aggregate(total=Sum('cantidad_requerida'))['total'] or 0
        actual = Trabajador.objects.filter(contrato=contrato, estado='ACTIVO').count()
        diferencia = requerido - actual
        diferencia_abs = abs(diferencia)  # Calcular valor absoluto aquí
        porcentaje = int((actual / requerido * 100)) if requerido > 0 else 0
        
        contratos_data.append({
            'contrato': contrato,
            'requerido': requerido,
            'actual': actual,
            'diferencia': diferencia,
            'diferencia_abs': diferencia_abs,
            'porcentaje': porcentaje,
        })
    
    context = {
        'contratos': contratos,
        'contratos_data': contratos_data,
        'total_requerido': total_requerido,
        'trabajadores_activos': trabajadores_activos,
        'headcounts_count': headcounts.count(),
    }
    
    return render(request, 'drilling/headcount/dashboard.html', context)


@login_required
def headcount_list(request):
    """Lista de headcount por contrato"""
    # Verificar permisos
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT']:
        messages.error(request, 'No tienes permisos para acceder a esta sección')
        return redirect('dashboard')
    
    # Obtener contrato seleccionado
    contrato_id = request.GET.get('contrato')
    
    if request.user.has_access_to_all_contracts():
        contratos = Contrato.objects.filter(estado='ACTIVO')
        if contrato_id:
            contrato = get_object_or_404(Contrato, id=contrato_id)
        else:
            contrato = contratos.first()
    else:
        contrato = request.user.contrato
        contratos = [contrato]
    
    if not contrato:
        messages.warning(request, 'No hay contratos activos disponibles')
        return redirect('headcount-dashboard')
    
    # Obtener headcounts del contrato
    headcounts = HeadCount.objects.filter(
        contrato=contrato,
        activo=True
    ).select_related('cargo', 'maquina').order_by('cargo__nombre', 'maquina__nombre')
    
    # Debug: contar todos los headcounts del contrato (incluso inactivos)
    total_headcounts = HeadCount.objects.filter(contrato=contrato).count()
    if total_headcounts > headcounts.count():
        messages.info(request, f'Hay {total_headcounts - headcounts.count()} headcount(s) inactivo(s) para este contrato')
    
    # Agregar datos calculados
    headcounts_data = []
    for hc in headcounts:
        headcounts_data.append({
            'headcount': hc,
            'actual': hc.get_cantidad_actual(),
            'diferencia': hc.get_diferencia(),
            'porcentaje': hc.get_porcentaje_cumplimiento(),
            'personal': hc.get_personal_actual(),
        })
    
    # Estadísticas del contrato
    total_requerido = headcounts.aggregate(total=Sum('cantidad_requerida'))['total'] or 0
    total_actual = Trabajador.objects.filter(contrato=contrato, estado='ACTIVO').count()
    total_diferencia = total_requerido - total_actual
    porcentaje_general = int((total_actual / total_requerido * 100)) if total_requerido > 0 else 0
    
    context = {
        'contrato': contrato,
        'contratos': contratos,
        'headcounts_data': headcounts_data,
        'total_requerido': total_requerido,
        'total_actual': total_actual,
        'total_diferencia': total_diferencia,
        'porcentaje_general': porcentaje_general,
    }
    
    return render(request, 'drilling/headcount/list.html', context)


@login_required
def headcount_create(request):
    """Crear nuevo headcount"""
    # Verificar permisos
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT']:
        messages.error(request, 'No tienes permisos para realizar esta acción')
        return redirect('headcount-dashboard')
    
    if request.method == 'POST':
        form = HeadCountForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                # Verificar si ya existe un headcount activo con los mismos datos
                contrato = form.cleaned_data['contrato']
                cargo = form.cleaned_data['cargo']
                maquina = form.cleaned_data.get('maquina')
                
                existe = HeadCount.objects.filter(
                    contrato=contrato,
                    cargo=cargo,
                    maquina=maquina,
                    activo=True
                ).exists()
                
                if existe:
                    messages.warning(request, f'Ya existe un headcount activo para {cargo.nombre} en {contrato.nombre_contrato}. '
                                              f'Edite el existente en lugar de crear uno nuevo.')
                    url = reverse('headcount-list') + f'?contrato={contrato.id}'
                    return HttpResponseRedirect(url)
                
                headcount = form.save()
                messages.success(request, f'Headcount creado exitosamente: {headcount}')
                url = reverse('headcount-list') + f'?contrato={headcount.contrato.id}'
                return HttpResponseRedirect(url)
            except Exception as e:
                messages.error(request, f'Error al crear headcount: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = HeadCountForm(user=request.user)
    
    context = {
        'form': form,
        'is_edit': False,
    }
    
    return render(request, 'drilling/headcount/form.html', context)


@login_required
def headcount_update(request, pk):
    """Actualizar headcount existente"""
    headcount = get_object_or_404(HeadCount, pk=pk)
    
    # Verificar permisos
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT']:
        messages.error(request, 'No tienes permisos para realizar esta acción')
        return redirect('headcount-dashboard')
    
    if request.method == 'POST':
        form = HeadCountForm(request.POST, instance=headcount, user=request.user)
        if form.is_valid():
            try:
                headcount = form.save()
                messages.success(request, 'Headcount actualizado exitosamente')
                url = reverse('headcount-list') + f'?contrato={headcount.contrato.id}'
                return HttpResponseRedirect(url)
            except Exception as e:
                messages.error(request, f'Error al actualizar headcount: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = HeadCountForm(instance=headcount, user=request.user)
    
    context = {
        'form': form,
        'headcount': headcount,
        'is_edit': True,
    }
    
    return render(request, 'drilling/headcount/form.html', context)


@login_required
@require_http_methods(["POST"])
def headcount_delete(request, pk):
    """Desactivar headcount"""
    headcount = get_object_or_404(HeadCount, pk=pk)
    
    # Verificar permisos
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT']:
        return JsonResponse({'success': False, 'message': 'Sin permisos'}, status=403)
    
    headcount.activo = False
    headcount.save()
    
    return JsonResponse({'success': True, 'message': 'Headcount desactivado correctamente'})


@login_required
def get_maquinas_by_contrato(request):
    """API para obtener máquinas de un contrato"""
    contrato_id = request.GET.get('contrato_id')
    
    if not contrato_id:
        return JsonResponse({'maquinas': []})
    
    try:
        maquinas = Maquina.objects.filter(
            contrato_id=contrato_id,
            estado='OPERATIVO'
        ).values('id', 'nombre').order_by('nombre')
        
        return JsonResponse({
            'maquinas': list(maquinas)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def debug_headcounts(request):
    """Vista de debug para ver todos los headcounts"""
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT']:
        messages.error(request, 'No tienes permisos')
        return redirect('dashboard')
    
    contrato_id = request.GET.get('contrato')
    
    if contrato_id:
        contrato = get_object_or_404(Contrato, id=contrato_id)
        headcounts = HeadCount.objects.filter(contrato=contrato).order_by('-created_at')
    else:
        headcounts = HeadCount.objects.all().order_by('-created_at')[:50]
    
    data = []
    for hc in headcounts:
        data.append({
            'id': hc.id,
            'contrato': str(hc.contrato),
            'cargo': hc.cargo.nombre,
            'cantidad': hc.cantidad_requerida,
            'maquina': hc.maquina.nombre if hc.maquina else 'Sin asignar',
            'activo': hc.activo,
            'created': hc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return JsonResponse({'headcounts': data, 'total': len(data)})
