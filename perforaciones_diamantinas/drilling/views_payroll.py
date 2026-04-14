"""
Vistas del módulo de Planilla / Bonos.
"""
import json
from datetime import date
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse

from .models import Contrato, Trabajador
from .models_payroll import (
    TipoBono,
    ConceptoBono,
    ConfiguracionBonoContrato,
    ConceptoBonoContrato,
    PeriodoBono,
    BonoTrabajador,
    BonoTrabajadorDetalle,
)
from .forms_payroll import (
    TipoBonoForm,
    ConceptoBonoFormSet,
    ConfiguracionBonoContratoForm,
    ConceptoBonoContratoFormSet,
    EscalaBonoContratoFormSet,
    AbrirPeriodoForm,
    PuntajeDetalleForm,
)
from .utils.payroll_engine import (
    abrir_periodo,
    calcular_periodo,
    aprobar_periodo,
    cerrar_periodo,
    resumen_periodo,
)
from .mixins import AdminOrContractFilterMixin


# ===========================================
# HUB PRINCIPAL DE PLANILLA
# ===========================================

@login_required
def planilla_hub(request):
    """Dashboard principal del módulo de planilla."""
    user = request.user
    contrato = user.contrato

    periodos = PeriodoBono.objects.all().order_by('-anio', '-mes')[:10]
    if not user.has_access_to_all_contracts() and contrato:
        periodos = periodos.filter(contrato=contrato)

    tipos_bono = TipoBono.objects.filter(activo=True).order_by('codigo')

    configs = ConfiguracionBonoContrato.objects.filter(activo=True).select_related(
        'contrato', 'tipo_bono'
    )
    if not user.has_access_to_all_contracts() and contrato:
        configs = configs.filter(contrato=contrato)

    context = {
        'periodos': periodos,
        'tipos_bono': tipos_bono,
        'configuraciones': configs[:20],
    }
    return render(request, 'drilling/planilla/hub.html', context)


# ===========================================
# TIPOS DE BONO — CRUD
# ===========================================

@login_required
def tipo_bono_list(request):
    tipos = TipoBono.objects.all().prefetch_related('conceptos').order_by('codigo')
    return render(request, 'drilling/planilla/tipo_bono_list.html', {'tipos': tipos})


@login_required
def tipo_bono_create(request):
    if request.method == 'POST':
        form = TipoBonoForm(request.POST)
        formset = ConceptoBonoFormSet(request.POST, prefix='conceptos')
        if form.is_valid() and formset.is_valid():
            tipo = form.save(commit=False)
            tipo.es_sistema = False
            tipo.save()
            formset.instance = tipo
            formset.save()
            messages.success(request, f'Tipo de bono "{tipo.codigo}" creado.')
            return redirect('planilla-tipo-bono-list')
    else:
        form = TipoBonoForm()
        formset = ConceptoBonoFormSet(prefix='conceptos')
    return render(request, 'drilling/planilla/tipo_bono_form.html', {
        'form': form, 'conceptos_formset': formset, 'titulo': 'Nuevo Tipo de Bono'
    })


@login_required
def tipo_bono_update(request, pk):
    tipo = get_object_or_404(TipoBono, pk=pk)
    if request.method == 'POST':
        form = TipoBonoForm(request.POST, instance=tipo)
        formset = ConceptoBonoFormSet(request.POST, instance=tipo, prefix='conceptos')
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f'Tipo de bono "{tipo.codigo}" actualizado.')
            return redirect('planilla-tipo-bono-list')
    else:
        form = TipoBonoForm(instance=tipo)
        formset = ConceptoBonoFormSet(instance=tipo, prefix='conceptos')
    return render(request, 'drilling/planilla/tipo_bono_form.html', {
        'form': form, 'conceptos_formset': formset, 'tipo': tipo, 'titulo': f'Editar {tipo.codigo}'
    })


# ===========================================
# CONFIGURACIÓN DE BONO POR CONTRATO
# ===========================================

@login_required
def config_bono_list(request):
    configs = ConfiguracionBonoContrato.objects.select_related(
        'contrato', 'tipo_bono'
    ).order_by('contrato__nombre_contrato', 'tipo_bono__codigo')
    if not request.user.has_access_to_all_contracts() and request.user.contrato:
        configs = configs.filter(contrato=request.user.contrato)
    return render(request, 'drilling/planilla/config_bono_list.html', {'configuraciones': configs})


@login_required
def config_bono_create(request):
    if request.method == 'POST':
        form = ConfiguracionBonoContratoForm(request.POST, user=request.user)
        if form.is_valid():
            config = form.save()
            messages.success(request, f'Configuración creada: {config}')
            return redirect('planilla-config-bono-edit', pk=config.pk)
    else:
        form = ConfiguracionBonoContratoForm(user=request.user)
    return render(request, 'drilling/planilla/config_bono_form.html', {
        'form': form, 'titulo': 'Nueva Configuración de Bono'
    })


@login_required
def config_bono_edit(request, pk):
    config = get_object_or_404(ConfiguracionBonoContrato, pk=pk)
    es_multi = config.tipo_bono.tipo_calculo == 'MULTI_CONCEPTO'
    es_escalon = config.tipo_bono.tipo_calculo == 'ESCALONADO'

    if request.method == 'POST':
        form = ConfiguracionBonoContratoForm(request.POST, instance=config, user=request.user)
        conceptos_formset = ConceptoBonoContratoFormSet(
            request.POST, instance=config, prefix='conceptos'
        ) if es_multi else None
        escalas_formset = EscalaBonoContratoFormSet(
            request.POST, instance=config, prefix='escalas'
        ) if es_escalon else None

        all_valid = form.is_valid()
        if conceptos_formset:
            all_valid = all_valid and conceptos_formset.is_valid()
        if escalas_formset:
            all_valid = all_valid and escalas_formset.is_valid()

        if all_valid:
            form.save()
            if conceptos_formset:
                conceptos_formset.save()
            if escalas_formset:
                escalas_formset.save()
            messages.success(request, 'Configuración actualizada.')
            return redirect('planilla-config-bono-list')
    else:
        form = ConfiguracionBonoContratoForm(instance=config, user=request.user)
        conceptos_formset = ConceptoBonoContratoFormSet(
            instance=config, prefix='conceptos'
        ) if es_multi else None
        escalas_formset = EscalaBonoContratoFormSet(
            instance=config, prefix='escalas'
        ) if es_escalon else None

    return render(request, 'drilling/planilla/config_bono_form.html', {
        'form': form,
        'config': config,
        'conceptos_formset': conceptos_formset,
        'escalas_formset': escalas_formset,
        'es_multi': es_multi,
        'es_escalon': es_escalon,
        'titulo': f'Editar Configuración — {config.tipo_bono.codigo}',
    })


# ===========================================
# PERÍODOS DE BONOS
# ===========================================

@login_required
def periodo_list(request):
    user = request.user
    periodos = PeriodoBono.objects.select_related('contrato', 'calculado_por', 'aprobado_por')
    if not user.has_access_to_all_contracts() and user.contrato:
        periodos = periodos.filter(contrato=user.contrato)
    periodos = periodos.order_by('-anio', '-mes')

    form = AbrirPeriodoForm(initial={'anio': date.today().year, 'mes': date.today().month})

    return render(request, 'drilling/planilla/periodo_list.html', {
        'periodos': periodos,
        'form_abrir': form,
    })


@login_required
def periodo_abrir(request):
    if request.method != 'POST':
        return redirect('planilla-periodo-list')

    form = AbrirPeriodoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Datos del período inválidos.')
        return redirect('planilla-periodo-list')

    user = request.user
    contrato = user.contrato
    if not contrato:
        messages.error(request, 'No tienes contrato asignado.')
        return redirect('planilla-periodo-list')

    anio = int(form.cleaned_data['anio'])
    mes = int(form.cleaned_data['mes'])

    try:
        periodo, registros = abrir_periodo(contrato, anio, mes, user)
        messages.success(request, f'Período {mes:02d}/{anio} abierto. {registros} registros de bonos creados.')
    except ValueError as e:
        messages.warning(request, str(e))

    return redirect('planilla-periodo-list')


@login_required
def periodo_detalle(request, pk):
    periodo = get_object_or_404(PeriodoBono, pk=pk)

    # Resumen
    resumen = resumen_periodo(periodo)

    # Bonos agrupados por tipo
    bonos_por_tipo = {}
    bonos_qs = BonoTrabajador.objects.filter(
        periodo=periodo
    ).select_related('trabajador', 'tipo_bono').order_by('tipo_bono__codigo', 'trabajador__apepat')

    for bono in bonos_qs:
        codigo = bono.tipo_bono.codigo
        if codigo not in bonos_por_tipo:
            bonos_por_tipo[codigo] = {
                'tipo_bono': bono.tipo_bono,
                'bonos': [],
            }
        bonos_por_tipo[codigo]['bonos'].append(bono)

    context = {
        'periodo': periodo,
        'resumen': resumen,
        'bonos_por_tipo': bonos_por_tipo,
    }
    return render(request, 'drilling/planilla/periodo_detalle.html', context)


@login_required
def periodo_calcular(request, pk):
    periodo = get_object_or_404(PeriodoBono, pk=pk)
    try:
        calcular_periodo(periodo, request.user)
        messages.success(request, f'Período {periodo.mes:02d}/{periodo.anio} calculado exitosamente.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('planilla-periodo-detalle', pk=pk)


@login_required
def periodo_aprobar(request, pk):
    periodo = get_object_or_404(PeriodoBono, pk=pk)
    try:
        aprobar_periodo(periodo, request.user)
        messages.success(request, f'Período {periodo.mes:02d}/{periodo.anio} aprobado.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('planilla-periodo-detalle', pk=pk)


# ===========================================
# EVALUACIÓN DE PUNTAJES (MULTI-CONCEPTO)
# ===========================================

@login_required
def evaluar_bono(request, bono_pk):
    """Vista para ingresar puntajes de un bono multi-concepto."""
    bono = get_object_or_404(
        BonoTrabajador.objects.select_related('trabajador', 'tipo_bono', 'periodo'),
        pk=bono_pk
    )

    if bono.periodo.estado == 'CERRADO':
        messages.error(request, 'El período está cerrado.')
        return redirect('planilla-periodo-detalle', pk=bono.periodo.pk)

    detalles = bono.detalles.select_related('concepto').order_by('concepto__orden')

    if request.method == 'POST':
        all_valid = True
        for detalle in detalles:
            field_name = f'puntaje_{detalle.pk}'
            try:
                puntaje = Decimal(request.POST.get(field_name, '0'))
                if 0 <= puntaje <= 100:
                    detalle.puntaje = puntaje
                    detalle.save(update_fields=['puntaje'])
                else:
                    all_valid = False
            except (ValueError, TypeError):
                all_valid = False

        if all_valid:
            messages.success(request, f'Puntajes guardados para {bono.trabajador.get_full_name}.')
        else:
            messages.warning(request, 'Algunos puntajes no son válidos (deben ser 0-100).')
        return redirect('planilla-evaluar-bono', bono_pk=bono_pk)

    return render(request, 'drilling/planilla/evaluar_bono.html', {
        'bono': bono,
        'detalles': detalles,
    })


@login_required
def evaluar_bono_masivo(request, periodo_pk, tipo_bono_pk):
    """Vista para ingresar puntajes masivamente por tipo de bono."""
    periodo = get_object_or_404(PeriodoBono, pk=periodo_pk)
    tipo_bono = get_object_or_404(TipoBono, pk=tipo_bono_pk)

    if tipo_bono.tipo_calculo != 'MULTI_CONCEPTO':
        messages.info(request, 'Este bono no requiere evaluación de conceptos.')
        return redirect('planilla-periodo-detalle', pk=periodo_pk)

    conceptos = ConceptoBono.objects.filter(tipo_bono=tipo_bono).order_by('orden')

    bonos = BonoTrabajador.objects.filter(
        periodo=periodo,
        tipo_bono=tipo_bono,
    ).select_related('trabajador').prefetch_related('detalles__concepto').order_by('trabajador__apepat')

    if request.method == 'POST':
        for bono in bonos:
            for detalle in bono.detalles.all():
                field_name = f'puntaje_{bono.pk}_{detalle.concepto.pk}'
                try:
                    puntaje = Decimal(request.POST.get(field_name, '0'))
                    if 0 <= puntaje <= 100:
                        detalle.puntaje = puntaje
                        detalle.save(update_fields=['puntaje'])
                except (ValueError, TypeError):
                    pass
        messages.success(request, f'Puntajes masivos guardados para {tipo_bono.nombre}.')
        return redirect('planilla-periodo-detalle', pk=periodo_pk)

    # Crear matriz para el template
    matriz = []
    for bono in bonos:
        detalles_dict = {d.concepto_id: d for d in bono.detalles.all()}
        fila = {
            'bono': bono,
            'trabajador': bono.trabajador,
            'detalles': [detalles_dict.get(c.pk) for c in conceptos],
        }
        matriz.append(fila)

    return render(request, 'drilling/planilla/evaluar_masivo.html', {
        'periodo': periodo,
        'tipo_bono': tipo_bono,
        'conceptos': conceptos,
        'matriz': matriz,
    })


# ===========================================
# API ENDPOINTS
# ===========================================

@login_required
def api_conceptos_tipo_bono(request, tipo_bono_pk):
    """Retorna los conceptos de un tipo de bono (para carga dinámica)."""
    conceptos = ConceptoBono.objects.filter(tipo_bono_id=tipo_bono_pk).order_by('orden')
    data = [{'id': c.pk, 'codigo': c.codigo, 'nombre': c.nombre, 'peso': float(c.peso_default)} for c in conceptos]
    return JsonResponse(data, safe=False)


@login_required
def api_exportar_bonos_excel(request, periodo_pk):
    """Exporta los bonos de un período a Excel."""
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    periodo = get_object_or_404(PeriodoBono, pk=periodo_pk)
    bonos = BonoTrabajador.objects.filter(
        periodo=periodo
    ).select_related('trabajador', 'tipo_bono').order_by('trabajador__apepat', 'tipo_bono__codigo')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'Bonos {periodo.mes:02d}-{periodo.anio}'

    # Estilos
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='0470AC', end_color='0470AC', fill_type='solid')
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # Headers
    headers = ['DNI', 'Nombres', 'Apellido Pat.', 'Cargo', 'Código Bono', 'Nombre Bono',
               'Categoría', 'Días Trab.', 'Días Base', 'Factor', 'Calculado', 'Ajuste', 'Final']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')

    # Datos
    for row, bono in enumerate(bonos, 2):
        data = [
            bono.trabajador.dni,
            bono.trabajador.nombres,
            bono.trabajador.apepat,
            bono.trabajador.cargo,
            bono.tipo_bono.codigo,
            bono.tipo_bono.nombre,
            bono.tipo_bono.categoria,
            bono.dias_trabajados,
            bono.dias_base,
            float(bono.factor_cumplimiento),
            float(bono.monto_calculado),
            float(bono.monto_ajuste),
            float(bono.monto_final),
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = border

    # Auto-width
    for col in ws.columns:
        max_width = max(len(str(cell.value or '')) for cell in col) + 2
        ws.column_dimensions[col[0].column_letter].width = min(max_width, 30)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=bonos_{periodo.contrato.nombre_contrato}_{periodo.mes:02d}_{periodo.anio}.xlsx'
    wb.save(response)
    return response
