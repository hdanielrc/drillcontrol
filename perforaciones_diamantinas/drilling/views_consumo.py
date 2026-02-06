from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import ConsumoArticulo, InventarioAlmacen, Contrato

@login_required
def lista_consumos(request):
    """
    Lista verificable de consumos sincronizados (Salidas de Almacén)
    """
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    centro_costo = request.GET.get('centro_costo')
    search = request.GET.get('search')
    
    consumos = ConsumoArticulo.objects.all().select_related('contrato')
    
    # Aplicar filtros
    if fecha_inicio:
        consumos = consumos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        consumos = consumos.filter(fecha__lte=fecha_fin)
    
    if centro_costo:
        consumos = consumos.filter(centro_costo=centro_costo)
        
    if search:
        consumos = consumos.filter(
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(documento__icontains=search) |
            Q(serie__icontains=search)
        )
        
    # Stats
    total_registros = consumos.count()
    if total_registros < 5000: # Optimizacion
        total_items = consumos.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    else:
        total_items = 0
        
    # Paginación
    paginator = Paginator(consumos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Contexto extra
    contratos = Contrato.objects.filter(estado='ACTIVO')
    
    context = {
        'consumos': page_obj,
        'contratos': contratos,
        'total_registros': total_registros,
        'total_items': total_items,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'centro_costo': centro_costo,
        'search': search
    }
    
    return render(request, 'drilling/consumos/lista.html', context)

@login_required
def inventario_actual_list(request):
    """
    Vista de Stock Actual Consolidado (InventarioAlmacen)
    """
    centro_costo = request.GET.get('centro_costo')
    search = request.GET.get('search')
    familia = request.GET.get('familia')
    
    inventario = InventarioAlmacen.objects.all().select_related('contrato')
    
    if centro_costo:
        inventario = inventario.filter(centro_costo=centro_costo)
        
    if search:
        inventario = inventario.filter(
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search)
        )
        
    if familia:
        inventario = inventario.filter(familia=familia)
        
    # Paginación
    paginator = Paginator(inventario, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    contratos = Contrato.objects.filter(estado='ACTIVO')
    
    context = {
        'inventario': page_obj,
        'contratos': contratos,
        'centro_costo': centro_costo,
        'search': search,
        'familia': familia
    }
    
    return render(request, 'drilling/stock/inventario_actual.html', context)
