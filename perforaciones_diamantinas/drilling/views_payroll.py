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
    CriterioBono,
    CalificacionCriterio,
    ESTADOS_DIA_TRABAJADO,
)
from .forms_payroll import (
    TipoBonoForm,
    ConceptoBonoFormSet,
    CriterioBonoFormSet,
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
    contar_dias_trabajados,
    calcular_dias_base_regimen,
    filtrar_trabajadores_por_cargo,
    generar_calificaciones_criterios,
    generar_detalles_vacios,
    calcular_bono_multi_concepto,
)
from .mixins import AdminOrContractFilterMixin


# ===========================================
# HUB PRINCIPAL DE PLANILLA
# ===========================================

@login_required
def planilla_hub(request):
    """Dashboard principal del módulo de planilla — centrado en cuadros."""
    user = request.user
    contrato = user.contrato
    today = date.today()

    # Tipos de bono activos (cada uno es un "cuadro")
    tipos_bono = TipoBono.objects.filter(activo=True).prefetch_related('conceptos').order_by('codigo')

    # Últimos períodos
    periodos = PeriodoBono.objects.all().order_by('-anio', '-mes')[:10]
    if not user.has_access_to_all_contracts() and contrato:
        periodos = periodos.filter(contrato=contrato)

    # Contratos disponibles
    if user.has_access_to_all_contracts():
        contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    elif contrato:
        contratos = Contrato.objects.filter(pk=contrato.pk)
    else:
        contratos = Contrato.objects.none()

    context = {
        'tipos_bono': tipos_bono,
        'periodos': periodos,
        'contratos': contratos,
        'anio_actual': today.year,
        'mes_actual': today.month,
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
            return redirect('planilla-tipo-bono-edit', pk=tipo.pk)
    else:
        form = TipoBonoForm(instance=tipo)
        formset = ConceptoBonoFormSet(instance=tipo, prefix='conceptos')
    return render(request, 'drilling/planilla/tipo_bono_form.html', {
        'form': form, 'conceptos_formset': formset, 'tipo': tipo, 'titulo': f'Editar {tipo.codigo}'
    })


@login_required
def criterios_concepto(request, concepto_pk):
    """Gestionar criterios (sub-conceptos / checkboxes) de un concepto."""
    concepto = get_object_or_404(
        ConceptoBono.objects.select_related('tipo_bono'),
        pk=concepto_pk
    )
    if request.method == 'POST':
        formset = CriterioBonoFormSet(request.POST, instance=concepto, prefix='criterios')
        if formset.is_valid():
            formset.save()
            messages.success(request, f'Criterios de "{concepto.nombre}" actualizados.')
            return redirect('planilla-criterios-concepto', concepto_pk=concepto.pk)
    else:
        formset = CriterioBonoFormSet(instance=concepto, prefix='criterios')
    return render(request, 'drilling/planilla/criterios_concepto.html', {
        'concepto': concepto,
        'formset': formset,
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


# ===========================================
# CUADRO DE EVALUACIÓN (formato Excel)
# ===========================================

@login_required
def cuadro_evaluacion(request, tipo_bono_pk):
    """
    Vista principal del cuadro de evaluación estilo Excel.
    Muestra todos los trabajadores agrupados por contrato, con secciones
    y criterios como columnas de checkboxes.
    Query params: ?anio=2026&mes=4
    """
    import calendar
    from collections import OrderedDict

    tipo_bono = get_object_or_404(TipoBono, pk=tipo_bono_pk, activo=True)
    anio = int(request.GET.get('anio') or date.today().year)
    mes = int(request.GET.get('mes') or date.today().month)
    _, ultimo_dia = calendar.monthrange(anio, mes)
    fecha_inicio = date(anio, mes, 1)
    fecha_fin = date(anio, mes, ultimo_dia)

    user = request.user

    # Secciones y criterios del tipo de bono
    secciones = ConceptoBono.objects.filter(
        tipo_bono=tipo_bono
    ).prefetch_related('criterios').order_by('orden')

    # Obtener contratos con configuración activa para este tipo de bono
    configs = ConfiguracionBonoContrato.objects.filter(
        tipo_bono=tipo_bono, activo=True,
    ).select_related('contrato')
    if not user.has_access_to_all_contracts() and user.contrato:
        configs = configs.filter(contrato=user.contrato)

    datos_por_contrato = OrderedDict()

    for config in configs:
        contrato = config.contrato
        # Obtener o crear período
        periodo, _ = PeriodoBono.objects.get_or_create(
            contrato=contrato, anio=anio, mes=mes,
            defaults={'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'estado': 'ABIERTO'}
        )

        # Obtener trabajadores del contrato que aplican al cuadro
        trabajadores = Trabajador.objects.filter(
            contrato=contrato, estado='ACTIVO'
        ).order_by('apepat', 'apemat', 'nombres')
        trabajadores = filtrar_trabajadores_por_cargo(trabajadores, tipo_bono)

        filas = []
        for trab in trabajadores:
            # Obtener o crear BonoTrabajador
            bono_trab, bt_created = BonoTrabajador.objects.get_or_create(
                periodo=periodo, trabajador=trab, tipo_bono=tipo_bono,
                defaults={
                    'configuracion': config,
                    'bono_base': config.monto_base_mensual,
                    'dias_trabajados': 0, 'dias_base': 0,
                    'factor_cumplimiento': Decimal('1'),
                    'monto_calculado': Decimal('0'),
                    'monto_ajuste': Decimal('0'),
                    'monto_final': Decimal('0'),
                }
            )

            if bt_created or bono_trab.dias_trabajados == 0:
                # Calcular días automáticamente
                dias_trab = contar_dias_trabajados(trab, fecha_inicio, fecha_fin)
                dias_base = calcular_dias_base_regimen(trab, fecha_inicio, fecha_fin)
                bono_trab.dias_trabajados = dias_trab
                bono_trab.dias_base = dias_base or 30
                bono_trab.save(update_fields=['dias_trabajados', 'dias_base'])

            # Generar detalles y calificaciones si faltan
            if bt_created:
                generar_detalles_vacios(bono_trab, config)
                generar_calificaciones_criterios(bono_trab)

            # Construir datos de secciones con criterios
            secciones_data = []
            total_monto_trab = Decimal('0')
            for seccion in secciones:
                criterios_seccion = seccion.criterios.filter(activo=True).order_by('orden')
                criterios_data = []
                cumplidos = 0
                total_crit = criterios_seccion.count()

                for criterio in criterios_seccion:
                    calif, _ = CalificacionCriterio.objects.get_or_create(
                        bono_trabajador=bono_trab, criterio=criterio,
                        defaults={'cumple': True}
                    )
                    criterios_data.append({
                        'criterio_pk': criterio.pk,
                        'nombre': criterio.nombre,
                        'cumple': calif.cumple,
                    })
                    if calif.cumple:
                        cumplidos += 1

                puntaje = round(cumplidos * 100 / total_crit) if total_crit > 0 else 100
                peso = float(seccion.peso_default)
                bono_base = float(bono_trab.bono_base)
                dias_trab = bono_trab.dias_trabajados
                dias_base = bono_trab.dias_base or 30
                dias_factor = dias_trab / dias_base if dias_base > 0 else 0
                monto_seccion = round(bono_base * (peso / 100) * (puntaje / 100) * dias_factor, 2)
                total_monto_trab += Decimal(str(monto_seccion))

                secciones_data.append({
                    'concepto_pk': seccion.pk,
                    'nombre': seccion.nombre,
                    'peso': peso,
                    'criterios': criterios_data,
                    'puntaje': puntaje,
                    'monto': monto_seccion,
                })

            filas.append({
                'bono_pk': bono_trab.pk,
                'trabajador_pk': trab.pk,
                'nombre_completo': f"{trab.apepat} {trab.apemat} {trab.nombres}".strip(),
                'cargo': trab.cargo or trab.cargo_headcount or '',
                'dias_trabajados': bono_trab.dias_trabajados,
                'dias_operativos': bono_trab.dias_base,
                'bono_base': float(bono_trab.bono_base),
                'secciones': secciones_data,
                'total': float(total_monto_trab),
            })

        if filas:
            datos_por_contrato[contrato.nombre_contrato] = {
                'contrato_pk': contrato.pk,
                'periodo_pk': periodo.pk,
                'filas': filas,
            }

    # Preparar estructura de secciones para el header
    secciones_header = []
    for seccion in secciones:
        criterios = seccion.criterios.filter(activo=True).order_by('orden')
        secciones_header.append({
            'nombre': seccion.nombre,
            'peso': float(seccion.peso_default),
            'criterios': list(criterios.values_list('nombre', flat=True)),
            'colspan': criterios.count() + 2,  # criterios + % + monto
        })

    MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    context = {
        'tipo_bono': tipo_bono,
        'anio': anio,
        'mes': mes,
        'mes_nombre': MESES[mes],
        'secciones_header': secciones_header,
        'datos_por_contrato': datos_por_contrato,
        'rango_anios': range(2025, date.today().year + 2),
    }
    return render(request, 'drilling/planilla/cuadro_evaluacion.html', context)


@login_required
def cuadro_guardar(request, tipo_bono_pk):
    """
    Endpoint AJAX para guardar calificaciones de criterios y bono_base.
    POST body JSON: {
        "bonos": [
            {"bono_pk": 1, "bono_base": 1300, "criterios": {"55": true, "56": false, ...}},
            ...
        ]
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requerido'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    bonos_data = data.get('bonos', [])
    actualizados = 0

    for bd in bonos_data:
        bono_pk = bd.get('bono_pk')
        if not bono_pk:
            continue

        try:
            bono_trab = BonoTrabajador.objects.get(pk=bono_pk)
        except BonoTrabajador.DoesNotExist:
            continue

        # Actualizar bono_base si cambió
        nuevo_base = bd.get('bono_base')
        if nuevo_base is not None:
            bono_trab.bono_base = Decimal(str(nuevo_base))
            bono_trab.save(update_fields=['bono_base'])

        # Actualizar días si los envían
        dias_trab = bd.get('dias_trabajados')
        dias_op = bd.get('dias_operativos')
        if dias_trab is not None:
            bono_trab.dias_trabajados = int(dias_trab)
        if dias_op is not None:
            bono_trab.dias_base = int(dias_op)
        if dias_trab is not None or dias_op is not None:
            bono_trab.save(update_fields=['dias_trabajados', 'dias_base'])

        # Actualizar criterios
        criterios_dict = bd.get('criterios', {})
        for crit_pk_str, cumple in criterios_dict.items():
            CalificacionCriterio.objects.filter(
                bono_trabajador=bono_trab,
                criterio_id=int(crit_pk_str),
            ).update(cumple=bool(cumple))

        actualizados += 1

    return JsonResponse({'ok': True, 'actualizados': actualizados})


@login_required
def cuadro_calcular(request, tipo_bono_pk):
    """
    Recalcula todos los bonos de un tipo para un mes/año dado.
    POST params: anio, mes
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requerido'}, status=405)

    import calendar
    from decimal import ROUND_HALF_UP

    tipo_bono = get_object_or_404(TipoBono, pk=tipo_bono_pk)
    anio = int(request.POST.get('anio', date.today().year))
    mes = int(request.POST.get('mes', date.today().month))

    periodos = PeriodoBono.objects.filter(anio=anio, mes=mes)
    user = request.user
    if not user.has_access_to_all_contracts() and user.contrato:
        periodos = periodos.filter(contrato=user.contrato)

    total_calculados = 0
    for periodo in periodos:
        bonos = BonoTrabajador.objects.filter(
            periodo=periodo, tipo_bono=tipo_bono,
        ).select_related('trabajador', 'configuracion')

        for bono in bonos:
            config = bono.configuracion
            if not config:
                continue

            dias_trab = bono.dias_trabajados
            dias_base = bono.dias_base or 30

            if tipo_bono.tipo_calculo == 'MULTI_CONCEPTO':
                from .utils.payroll_engine import _round2, ZERO
                monto, factor = calcular_bono_multi_concepto(bono, config, dias_trab, dias_base)
                bono.factor_cumplimiento = factor
                bono.monto_calculado = monto
                bono.monto_final = _round2(monto + bono.monto_ajuste)
                bono.save()
                total_calculados += 1

    messages.success(request, f'Se recalcularon {total_calculados} bonos para {tipo_bono.nombre}.')
    return redirect(f"{reverse('planilla-cuadro', args=[tipo_bono_pk])}?anio={anio}&mes={mes}")


# ===========================================
# CONCEPTOS GLOBALES DE CONTRATO
# ===========================================

@login_required
def conceptos_globales(request):
    """
    Vista principal de conceptos globales: muestra todos los indicadores
    por contrato/período con sus valores y % de bono calculado.
    Usa mes operativo: día 26 del mes anterior al día 25 del mes actual.
    Query params: ?anio=2026&mes=4&contrato=ID
    """
    from .models_payroll import ConceptoGlobal, ConceptoGlobalPeriodo
    from .utils.conceptos_globales_engine import (
        inicializar_conceptos_periodo,
        get_rango_mes_operativo,
        _auto_cargar_datos,
        calcular_concepto_global,
    )

    user = request.user
    today = date.today()
    anio = int(request.GET.get('anio') or today.year)
    mes = int(request.GET.get('mes') or today.month)

    # Rango del mes operativo
    fecha_inicio_op, fecha_fin_op = get_rango_mes_operativo(anio, mes)

    # Contratos disponibles según permisos
    if user.has_access_to_all_contracts():
        contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    elif user.contrato:
        contratos = Contrato.objects.filter(pk=user.contrato.pk)
    else:
        contratos = Contrato.objects.none()

    contrato_id = request.GET.get('contrato')
    if contrato_id:
        contratos = contratos.filter(pk=contrato_id)

    conceptos = ConceptoGlobal.objects.filter(activo=True).order_by('orden')

    datos_por_contrato = {}
    for contrato in contratos:
        # Inicializar si no existen
        inicializar_conceptos_periodo(contrato, anio, mes)

        periodos = ConceptoGlobalPeriodo.objects.filter(
            contrato=contrato, anio=anio, mes=mes
        ).select_related('concepto').order_by('concepto__orden')

        # Siempre recargar datos automáticos (metros, meta, máquinas)
        # para que reflejen el estado actual de los reportes
        for cgp in periodos:
            if cgp.concepto.tipo in ('PRODUCCION', 'CXM'):
                _auto_cargar_datos(cgp, anio, mes)
                calcular_concepto_global(cgp)
                cgp.save()

        datos_por_contrato[contrato] = list(periodos)

    MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    context = {
        'anio': anio,
        'mes': mes,
        'mes_nombre': MESES[mes],
        'fecha_inicio_op': fecha_inicio_op,
        'fecha_fin_op': fecha_fin_op,
        'conceptos': conceptos,
        'datos_por_contrato': datos_por_contrato,
        'contratos_disponibles': Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato') if user.has_access_to_all_contracts() else contratos,
        'contrato_seleccionado': contrato_id,
        'rango_anios': range(2025, today.year + 2),
    }
    return render(request, 'drilling/planilla/conceptos_globales.html', context)


@login_required
def conceptos_globales_guardar(request):
    """
    Endpoint AJAX para guardar valores de conceptos globales.
    POST JSON: {
        "registros": [
            {
                "id": 1,
                "metros_acumulados": 1500.0,
                "meta_programada": 1200.0,
                "cantidad_maquinas": 2,
                ...
            },
            ...
        ]
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requerido'}, status=405)

    from .models_payroll import ConceptoGlobalPeriodo
    from .utils.conceptos_globales_engine import calcular_concepto_global

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    registros = data.get('registros', [])
    actualizados = 0
    resultados = []

    CAMPOS_NUMERICOS = [
        'metros_acumulados', 'meta_programada', 'cantidad_maquinas',
        'accidentes_incapacitantes', 'eficiencia_cobro',
        'total_abastecido', 'meta_cxm_programada', 'rentabilidad',
    ]
    CAMPOS_ENTEROS = ['cantidad_maquinas', 'accidentes_incapacitantes']

    for reg in registros:
        pk = reg.get('id')
        if not pk:
            continue
        try:
            cgp = ConceptoGlobalPeriodo.objects.select_related('concepto').get(pk=pk)
        except ConceptoGlobalPeriodo.DoesNotExist:
            continue

        # Actualizar campos de entrada
        campos_actualizados = []
        for campo in CAMPOS_NUMERICOS:
            if campo in reg:
                valor = reg[campo]
                if campo in CAMPOS_ENTEROS:
                    setattr(cgp, campo, int(valor))
                else:
                    setattr(cgp, campo, Decimal(str(valor)))
                campos_actualizados.append(campo)

        if reg.get('observaciones') is not None:
            cgp.observaciones = reg['observaciones']
            campos_actualizados.append('observaciones')

        # Recalcular
        valor, porcentaje = calcular_concepto_global(cgp)
        campos_actualizados.extend(['valor_calculado', 'porcentaje_bono', 'updated_at'])
        cgp.save(update_fields=campos_actualizados)
        actualizados += 1

        resultados.append({
            'id': cgp.pk,
            'codigo': cgp.concepto.codigo,
            'valor_calculado': float(valor),
            'porcentaje_bono': float(porcentaje),
        })

    return JsonResponse({'ok': True, 'actualizados': actualizados, 'resultados': resultados})


@login_required
def conceptos_globales_calcular(request):
    """
    Recalcula todos los conceptos globales de un contrato para un período.
    POST params: contrato_id, anio, mes
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requerido'}, status=405)

    from .utils.conceptos_globales_engine import calcular_todos_conceptos_contrato

    contrato_id = request.POST.get('contrato_id')
    anio = int(request.POST.get('anio', date.today().year))
    mes = int(request.POST.get('mes', date.today().month))

    contrato = get_object_or_404(Contrato, pk=contrato_id)
    resultados = calcular_todos_conceptos_contrato(contrato, anio, mes)

    messages.success(request, f'Se calcularon {len(resultados)} conceptos globales para {contrato.nombre_contrato}.')
    return redirect(f"{reverse('planilla-conceptos-globales')}?anio={anio}&mes={mes}&contrato={contrato_id}")


@login_required
def api_conceptos_globales_contrato(request, contrato_id, anio, mes):
    """
    API que retorna los conceptos globales calculados de un contrato/período.
    Útil para que otros módulos consulten los % de bono.
    """
    from .models_payroll import ConceptoGlobalPeriodo

    periodos = ConceptoGlobalPeriodo.objects.filter(
        contrato_id=contrato_id, anio=anio, mes=mes
    ).select_related('concepto').order_by('concepto__orden')

    data = {}
    for cgp in periodos:
        data[cgp.concepto.codigo] = {
            'id': cgp.pk,
            'nombre': cgp.concepto.nombre,
            'tipo': cgp.concepto.tipo,
            'valor_calculado': float(cgp.valor_calculado),
            'porcentaje_bono': float(cgp.porcentaje_bono),
            'inputs': {
                'metros_acumulados': float(cgp.metros_acumulados),
                'meta_programada': float(cgp.meta_programada),
                'cantidad_maquinas': cgp.cantidad_maquinas,
                'accidentes_incapacitantes': cgp.accidentes_incapacitantes,
                'eficiencia_cobro': float(cgp.eficiencia_cobro),
                'total_abastecido': float(cgp.total_abastecido),
                'meta_cxm_programada': float(cgp.meta_cxm_programada),
                'rentabilidad': float(cgp.rentabilidad),
            },
        }

    return JsonResponse(data)
