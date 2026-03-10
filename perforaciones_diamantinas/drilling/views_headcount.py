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
from django.db.models import QuerySet
from .models import HeadCount, Contrato, Trabajador
from .forms import HeadCountForm


@login_required
def headcount_dashboard(request):
    """Dashboard principal de headcount"""
    # Verificar permisos
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT', 'GERENTE_GENERAL']:
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
    ).select_related('contrato')
    
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
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT', 'GERENTE_GENERAL']:
        messages.error(request, 'No tienes permisos para acceder a esta sección')
        return redirect('dashboard')
    
    # Obtener contrato seleccionado
    contrato_id = request.GET.get('contrato', '').strip()
    cargo_id = request.GET.get('cargo', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()
    categoria_filtro = request.GET.get('categoria', '').strip()
    servicio_filtro = request.GET.get('servicio', '').strip()
    ubicacion_filtro = request.GET.get('ubicacion', '').strip()

    nivel_filtro = request.GET.get('nivel', '').strip()

    # Limpiar valores vacíos
    contrato_id = contrato_id if contrato_id else None
    cargo_id = cargo_id if cargo_id else None
    estado_filtro = estado_filtro if estado_filtro else None
    categoria_filtro = categoria_filtro if categoria_filtro else None
    servicio_filtro = servicio_filtro if servicio_filtro else None
    ubicacion_filtro = ubicacion_filtro if ubicacion_filtro else None
    nivel_filtro = nivel_filtro if nivel_filtro else None
    
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
    
    # Construir query base
    headcounts_query = HeadCount.objects.filter(
        contrato=contrato,
        activo=True
    )
    
    # Aplicar filtros adicionales
    if cargo_id:
        headcounts_query = headcounts_query.filter(cargo=cargo_id)
    if categoria_filtro:
        headcounts_query = headcounts_query.filter(categoria=categoria_filtro)
    if servicio_filtro:
        headcounts_query = headcounts_query.filter(servicio=servicio_filtro)
    if ubicacion_filtro:
        headcounts_query = headcounts_query.filter(ubicacion=ubicacion_filtro)
    if nivel_filtro:
        headcounts_query = headcounts_query.filter(nivel=nivel_filtro)

    if estado_filtro == 'completo':
        headcounts_query = [hc for hc in headcounts_query if hc.esta_completo()]
    elif estado_filtro == 'incompleto':
        headcounts_query = [hc for hc in headcounts_query if not hc.esta_completo()]
    
    # Convertir a lista si aún es QuerySet
    if isinstance(headcounts_query, QuerySet):
        headcounts = headcounts_query.order_by('servicio', 'categoria', 'ubicacion', 'cargo', 'nivel')
    else:
        headcounts = sorted(headcounts_query, key=lambda x: (x.servicio, x.categoria, x.ubicacion, x.cargo, x.nivel))
    
    # Obtener cargos con trabajadores activos que NO están en el headcount
    cargos_en_headcount = set(hc.cargo for hc in headcounts)
    trabajadores_sin_headcount = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).exclude(
        cargo__in=cargos_en_headcount
    ).values('cargo').annotate(
        cantidad=Count('id')
    )
    
    # Crear objetos "virtuales" de HeadCount para cargos sin planificar
    headcounts_list = list(headcounts)
    for item in trabajadores_sin_headcount:
        cargo_str = item['cargo']
        class MockHeadCount:
            def __init__(self, contrato, cargo, cantidad_actual):
                self.id = None
                self.contrato = contrato
                self.cargo = cargo
                self.categoria = ''
                self.servicio = ''
                self.ubicacion = ''
                self.nivel = ''
                self.cantidad_requerida = 0
                self.activo = True
                self.observaciones = 'Cargo no planificado en headcount'
                self._cantidad_actual = cantidad_actual
                self.es_no_planificado = True
            
            def get_cantidad_actual(self):
                return self._cantidad_actual
            
            def get_diferencia(self):
                return 0 - self._cantidad_actual
            
            def get_porcentaje_cumplimiento(self):
                return 0
            
            def get_personal_actual(self):
                return Trabajador.objects.filter(
                    contrato=self.contrato,
                    cargo=self.cargo,
                    estado='ACTIVO'
                )
            
            def esta_completo(self):
                return False
        
        mock_hc = MockHeadCount(contrato, cargo_str, item['cantidad'])
        headcounts_list.append(mock_hc)
    
    # Ordenar incluyendo los no planificados
    headcounts_list = sorted(headcounts_list, key=lambda x: (x.servicio, x.categoria, x.ubicacion, x.cargo, x.nivel))
    
    # Agregar datos calculados
    headcounts_data = []
    for hc in headcounts_list:
        headcounts_data.append({
            'headcount': hc,
            'actual': hc.get_cantidad_actual(),
            'diferencia': hc.get_diferencia(),
            'porcentaje': hc.get_porcentaje_cumplimiento(),
            'personal': hc.get_personal_actual(),
            'es_no_planificado': getattr(hc, 'es_no_planificado', False),
        })
    
    # Estadísticas del contrato
    total_requerido = sum(hc.cantidad_requerida for hc in headcounts_list) if headcounts_list else 0
    total_actual = Trabajador.objects.filter(contrato=contrato, estado='ACTIVO').count()
    total_diferencia = total_requerido - total_actual
    porcentaje_general = int((total_actual / total_requerido * 100)) if total_requerido > 0 else 0
    
    # Obtener valores únicos para filtros
    cargos = HeadCount.CARGO_CHOICES
    categorias = HeadCount.CATEGORIA_CHOICES
    servicios = HeadCount.SERVICIO_CHOICES
    ubicaciones = HeadCount.UBICACION_CHOICES
    niveles = HeadCount.NIVEL_CHOICES

    context = {
        'contrato': contrato,
        'contratos': contratos,
        'cargos': cargos,
        'categorias': categorias,
        'servicios': servicios,
        'ubicaciones': ubicaciones,
        'niveles': niveles,
        'headcounts': headcounts_list,  # Para iterar en el template
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
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT', 'GERENTE_GENERAL']:
        messages.error(request, 'No tienes permisos para realizar esta acción')
        return redirect('headcount-dashboard')
    
    if request.method == 'POST':
        form = HeadCountForm(request.POST, user=request.user)
        # Recuperar contrato preseleccionado para re-mostrar en el form si hay error
        contrato_preseleccionado = None
        contrato_id_post = request.POST.get('contrato', '').strip()
        if contrato_id_post:
            try:
                contrato_preseleccionado = Contrato.objects.get(pk=contrato_id_post, estado='ACTIVO')
            except Contrato.DoesNotExist:
                pass
        if form.is_valid():
            try:
                # Verificar si ya existe un headcount activo con los mismos datos
                contrato = form.cleaned_data['contrato']
                cargo = form.cleaned_data['cargo']
                categoria = form.cleaned_data['categoria']
                servicio = form.cleaned_data['servicio']
                ubicacion = form.cleaned_data['ubicacion']
                nivel = form.cleaned_data.get('nivel', '')

                existe = HeadCount.objects.filter(
                    contrato=contrato,
                    cargo=cargo,
                    categoria=categoria,
                    servicio=servicio,
                    ubicacion=ubicacion,
                    nivel=nivel,
                    activo=True
                ).exists()
                
                if existe:
                    messages.warning(request, f'Ya existe un headcount activo para {cargo} en {contrato.nombre_contrato}. '
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
        contrato_id = request.GET.get('contrato', '').strip()
        initial = {}
        contrato_preseleccionado = None
        if contrato_id:
            try:
                contrato_preseleccionado = Contrato.objects.get(pk=contrato_id, estado='ACTIVO')
                initial['contrato'] = contrato_preseleccionado
            except Contrato.DoesNotExist:
                pass
        form = HeadCountForm(user=request.user, initial=initial)

    context = {
        'form': form,
        'is_edit': False,
        'contrato_preseleccionado': contrato_preseleccionado,
    }

    return render(request, 'drilling/headcount/form.html', context)


@login_required
def headcount_update(request, pk):
    """Actualizar headcount existente"""
    headcount = get_object_or_404(HeadCount, pk=pk)
    
    # Verificar permisos
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT', 'GERENTE_GENERAL']:
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
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT', 'GERENTE_GENERAL']:
        messages.error(request, 'Sin permisos para eliminar headcount')
        return redirect('headcount-list')
    
    contrato_id = headcount.contrato_id
    headcount.activo = False
    headcount.save()
    
    messages.success(request, f'Headcount desactivado correctamente')
    return redirect(f"{reverse('headcount-list')}?contrato={contrato_id}")


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
    if not request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'HEADCOUNT', 'GERENTE_GENERAL']:
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
            'cargo': hc.cargo,
            'cantidad': hc.cantidad_requerida,
            'maquina': hc.maquina.nombre if hc.maquina else 'Sin asignar',
            'activo': hc.activo,
            'created': hc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return JsonResponse({'headcounts': data, 'total': len(data)})
