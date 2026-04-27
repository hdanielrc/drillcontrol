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
from .models import TurnoAvance, TurnoTrabajador  # metraje acumulado por trabajador
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
    EstructuraSalarial,
    HistorialEstructuraSalarial,
    HistorialBonoTrabajador,
    HistorialBonoTrabajador,
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
    EstructuraSalarialForm,
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
# DEMO — template standalone cuadro evaluación
# ===========================================

@login_required
def cuadro_evaluacion_demo(request):
    return render(request, 'drilling/planilla/cuadro_evaluacion_demo.html')


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
    periodos_qs = PeriodoBono.objects.all().order_by('-anio', '-mes')
    if not user.has_access_to_all_contracts() and contrato:
        periodos_qs = periodos_qs.filter(contrato=contrato)
    periodos = periodos_qs[:10]

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

    import json as _json
    return render(request, 'drilling/planilla/config_bono_form.html', {
        'form': form,
        'config': config,
        'conceptos_formset': conceptos_formset,
        'escalas_formset': escalas_formset,
        'es_multi': es_multi,
        'es_escalon': es_escalon,
        'titulo': f'Editar Configuración — {config.tipo_bono.codigo}',
        # JSON pre-serializado para el JS del template
        'cargos_aplicables_json': _json.dumps(config.cargos_aplicables or []),
        'montos_por_cargo_json': _json.dumps(config.montos_por_cargo or {}),
        'tipo_calculo_json': _json.dumps(config.tipo_calculo_por_trabajador or {}),
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
    El % de cada sección se toma de ConceptoGlobalPeriodo cuando el código del
    ConceptoBono coincide con un ConceptoGlobal del sistema; si no existe se usa
    el conteo de criterios manual (checkboxes).
    Query params: ?anio=2026&mes=4
    """
    import calendar
    from collections import OrderedDict
    import unicodedata
    from .models_payroll import ConceptoGlobalPeriodo

    # Prefijos ordenados de mayor a menor longitud para evitar falsos matches.
    # Cualquier ConceptoBono.codigo que empiece con uno de estos prefijos
    # (tras quitar tildes y mayúsculas) se mapea al código oficial de ConceptoGlobal.
    _PREFIJOS_GLOBAL = [
        ('RESULTADO_OPERATIVO', 'RESULTADO_OPERATIVO'),
        ('RESULTADO_OP',        'RESULTADO_OPERATIVO'),
        ('RESULTADO',           'RESULTADO_OPERATIVO'),
        ('PRODUCCION',          'PRODUCCION'),
        ('SEGURIDAD',           'SEGURIDAD'),
        ('VALORIZACION',        'VALORIZACION'),
        ('COSTO_METRO',         'CXM'),
        ('COSTO',               'CXM'),
        ('RROO',                'RESULTADO_OPERATIVO'),
        ('PROD',                'PRODUCCION'),
        ('SEGU',                'SEGURIDAD'),
        ('SEG',                 'SEGURIDAD'),
        ('VALO',                'VALORIZACION'),
        ('VAL',                 'VALORIZACION'),
        ('CXM',                 'CXM'),
        ('RO',                  'RESULTADO_OPERATIVO'),
    ]

    # Multiplicadores de bono para trabajadores de tipo METRAJE.
    # Si el indicador global llega al 100 %, se suma ese porcentaje al bono base por metro.
    _METRAJE_MULT = {
        'SEGURIDAD': Decimal('0.04'),   # SEG al 100 % → +4 %
        'CXM':       Decimal('0.04'),   # CXM al 100 % → +4 %
    }

    def _strip_accents(s):
        """Quita tildes y devuelve en mayúsculas."""
        return ''.join(
            c for c in unicodedata.normalize('NFD', s.upper())
            if unicodedata.category(c) != 'Mn'
        )

    def _codigo_a_global(codigo_seccion):
        """
        Convierte el código de un ConceptoBono al código oficial de ConceptoGlobal.
        Primero busca coincidencia exacta en el dict de prefijos, luego startswith
        (de mayor a menor longitud) para tolerar sufijos extras como '_01', etc.
        """
        norm = _strip_accents(codigo_seccion)
        for prefijo, global_cod in _PREFIJOS_GLOBAL:
            if norm == prefijo or norm.startswith(prefijo):
                return global_cod
        return None

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
        # Cargar conceptos globales del período para este contrato
        # Indexados por código normalizado (sin acentos, mayúsculas)
        cgp_qs = ConceptoGlobalPeriodo.objects.filter(
            contrato=contrato, anio=anio, mes=mes
        ).select_related('concepto')
        conceptos_globales_periodo = {
            _strip_accents(cgp.concepto.codigo): cgp
            for cgp in cgp_qs
        }

        # Sincronizar V1 (AsistenciaTrabajador) → V2 (AsistenciaDiaria) para
        # este contrato y período operativo, igual que hace la vista del tareo.
        # Garantiza que contar_dias_trabajados refleje los mismos datos que el
        # Resumen de Planilla.
        try:
            from .utils.tareo_service import TareoService as _TareoService
            _mes_ant = mes - 1 if mes > 1 else 12
            _anio_ant = anio if mes > 1 else anio - 1
            _sync_inicio = date(_anio_ant, _mes_ant, 23)
            _TareoService.importar_desde_v1(
                contrato=contrato,
                fecha_inicio=_sync_inicio,
                fecha_fin=fecha_fin,
                usuario=request.user,
            )
        except Exception:
            pass  # El sync es best-effort; no debe romper la vista

        # Obtener o crear período
        periodo, _ = PeriodoBono.objects.get_or_create(
            contrato=contrato, anio=anio, mes=mes,
            defaults={'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'estado': 'ABIERTO'}
        )

        # Obtener trabajadores del contrato que aplican al cuadro
        trabajadores = Trabajador.objects.filter(
            contrato=contrato, estado='ACTIVO'
        ).order_by('apepat', 'apemat', 'nombres')
        trabajadores = filtrar_trabajadores_por_cargo(trabajadores, tipo_bono, config=config)

        filas_cumplimiento = []
        filas_metraje = []

        # ── Pre-carga para prorrateo de metraje ──────────────────────────────
        from .models import AsistenciaDiaria
        from .utils.periodo_operativo import get_rango_mes_operativo, cantidad_dias_mes_operativo
        from django.db.models import Sum as _SumM, Count as _CountM

        # Todo usa el mismo período operativo 26-25 para consistencia
        _op_inicio, _op_fin = get_rango_mes_operativo(anio, mes)
        _dias_mes_op = cantidad_dias_mes_operativo(anio, mes)

        # metros_acumulados por maquina_id en el período operativo
        _metros_maquina = {}
        _rows = (
            TurnoAvance.objects.filter(
                turno__contrato=contrato,
                turno__fecha__gte=_op_inicio,
                turno__fecha__lte=_op_fin,
                turno__estado__in=['COMPLETADO', 'APROBADO'],
            )
            .values('turno__maquina_id')
            .annotate(total=_SumM('metros_perforados'))
        )
        for _r in _rows:
            if _r['turno__maquina_id']:
                _metros_maquina[_r['turno__maquina_id']] = Decimal(str(_r['total'] or 0))

        # nombre de máquinas para el desglose en template
        from .models import Maquina as _Maquina
        _maquina_nombres = dict(_Maquina.objects.filter(contrato=contrato).values_list('id', 'nombre'))

        # días trabajados por trabajador+máquina en el período operativo 26-25
        # estados que cuentan: T, TD, TN, TI, DL, DA, DA1
        # solo registros reales (es_proyeccion=False), igual que la tabla Excel del tareo
        # resultado: {trabajador_id: [(maquina_id, dias), ...]}
        _ESTADOS_EN_MAQUINA = ['T', 'TD', 'TN', 'TI', 'DL', 'DA', 'DA1']
        _dias_trab_maquinas = {}
        _ad_rows = (
            AsistenciaDiaria.objects.filter(
                trabajador__contrato=contrato,
                fecha__gte=_op_inicio,
                fecha__lte=_op_fin,
                maquina_snapshot__isnull=False,
                es_proyeccion=False,
                estado__in=_ESTADOS_EN_MAQUINA,
            )
            .values('trabajador_id', 'maquina_snapshot_id')
            .annotate(dias=_CountM('id'))
        )
        for _ad in _ad_rows:
            _tid = _ad['trabajador_id']
            _dias_trab_maquinas.setdefault(_tid, []).append(
                (_ad['maquina_snapshot_id'], _ad['dias'])
            )

        for trab in trabajadores:
            cargo_trab = trab.cargo or trab.cargo_headcount or ''
            from decimal import Decimal as _D

            # ── Determinar tipo de cálculo del trabajador ─────────────────────
            tipo_calc = (config.tipo_calculo_por_trabajador or {}).get(trab.dni, 'cumplimiento')

            def _bono_base_para(cfg, cargo, tipo):
                """Retorna el monto base según el tipo de cálculo del trabajador."""
                if tipo == 'metraje':
                    est = EstructuraSalarial.objects.filter(
                        contrato=cfg.contrato,
                        cargo_contratado=cargo,
                        activo=True,
                    ).first()
                    if est and est.bono_por_metraje:
                        # Almacenar solo la TARIFA por metro (no el producto con metraje_base)
                        return est.bono_por_metraje
                # cumplimiento (default): per-cargo o global
                if cfg.montos_por_cargo and cargo in cfg.montos_por_cargo:
                    return _D(str(cfg.montos_por_cargo[cargo]))
                return cfg.monto_base_mensual

            monto_inicial = _bono_base_para(config, cargo_trab, tipo_calc)

            # Obtener o crear BonoTrabajador
            bono_trab, bt_created = BonoTrabajador.objects.get_or_create(
                periodo=periodo, trabajador=trab, tipo_bono=tipo_bono,
                defaults={
                    'configuracion': config,
                    'bono_base': monto_inicial,
                    'dias_trabajados': 0, 'dias_base': 0,
                    'factor_cumplimiento': Decimal('1'),
                    'monto_calculado': Decimal('0'),
                    'monto_ajuste': Decimal('0'),
                    'monto_final': Decimal('0'),
                }
            )

            # Siempre sincronizar bono_base desde la configuración si está vacío o desactualizado
            cargo_trab = trab.cargo or trab.cargo_headcount or ''
            monto_esperado = _bono_base_para(config, cargo_trab, tipo_calc)

            fields_to_update = []
            if not bono_trab.bono_base or bono_trab.bono_base != monto_esperado:
                bono_trab.bono_base = monto_esperado
                fields_to_update.append('bono_base')

            # Siempre recalcular días desde el tareo para mantener datos frescos
            # (fórmula: TD+TN+DL+DA en rango calendario 1-30, igual que Resumen de Planilla)
            dias_trab = contar_dias_trabajados(trab, fecha_inicio, fecha_fin)
            dias_base = calcular_dias_base_regimen(trab, fecha_inicio, fecha_fin)
            bono_trab.dias_trabajados = dias_trab
            bono_trab.dias_base = dias_base or 30
            fields_to_update += ['dias_trabajados', 'dias_base']

            if fields_to_update:
                bono_trab.save(update_fields=fields_to_update)

            # Generar detalles y calificaciones si faltan (solo cumplimiento)
            if bt_created and tipo_calc != 'metraje':
                generar_detalles_vacios(bono_trab, config)
                generar_calificaciones_criterios(bono_trab)

            # ── TRABAJADORES DE METRAJE: cálculo directo ──────────────────────
            if tipo_calc == 'metraje':
                seg_cgp = conceptos_globales_periodo.get('SEGURIDAD')
                seg_puntaje = float(seg_cgp.porcentaje_bono) if seg_cgp else 0.0
                seg_activo = seg_puntaje >= 100

                # CXM no aplica para BA-OPERADORES — solo Seguridad suma bonificación
                mult_seg = Decimal('0.04') if seg_activo else Decimal('0')
                mult_total = Decimal('1') + mult_seg
                mult_total_pct = int(mult_total * 100)  # 100 o 104

                est_m = EstructuraSalarial.objects.filter(
                    contrato=config.contrato, cargo_contratado=cargo_trab, activo=True
                ).first()
                metraje_base_val = est_m.metraje_base if est_m and est_m.metraje_base else Decimal('0')

                # Metraje acumulado del trabajador: suma de metros perforados
                # en los turnos donde aparece como trabajador en el período.
                from django.db.models import Sum as _Sum
                _metros = TurnoAvance.objects.filter(
                    turno__contrato=contrato,
                    turno__fecha__gte=fecha_inicio,
                    turno__fecha__lte=fecha_fin,
                    turno__trabajadores_turno__trabajador=trab,
                ).aggregate(total=_Sum('metros_perforados'))['total']
                metraje_acum_val = (
                    Decimal(str(_metros)).quantize(Decimal('0.001'))
                    if _metros else Decimal('0')
                )
                bono_por_metro_val = bono_trab.bono_base  # tarifa por metro (unit rate)

                # Persiste el valor calculado para referencia histórica
                if bono_trab.metraje_acumulado != metraje_acum_val:
                    bono_trab.metraje_acumulado = metraje_acum_val
                    bono_trab.save(update_fields=['metraje_acumulado'])

                monto_ajustado = (bono_por_metro_val * mult_total).quantize(Decimal('0.001'))
                bono_calculado = ((metraje_acum_val - metraje_base_val) * monto_ajustado).quantize(Decimal('0.01'))

                # Auto-persistir monto_final en cada carga (no esperar a que el usuario pulse Guardar)
                if bono_trab.monto_final != bono_calculado:
                    bono_trab.monto_calculado = bono_calculado
                    bono_trab.monto_final = (bono_calculado + bono_trab.monto_ajuste).quantize(Decimal('0.01'))
                    bono_trab.registrar_historial(
                        fuente='CALCULO',
                        usuario=request.user,
                        observacion=f'Cálculo automático metraje: {float(metraje_acum_val):.3f}m × {float(monto_ajustado):.3f}',
                    )
                    bono_trab.save(update_fields=['monto_calculado', 'monto_final'])
                    bono_trab.registrar_historial(
                        fuente='CALCULO',
                        usuario=request.user,
                        observacion=f'Cálculo automático metraje: {float(metraje_acum_val):.3f}m × {float(monto_ajustado):.3f}',
                    )

                # Prorrateo por máquina: una entrada por cada máquina donde trabajó
                _d_op = Decimal(str(_dias_mes_op))
                _maq_entradas = _dias_trab_maquinas.get(trab.pk, [])
                _desglose_maquinas = []
                _base_prorrateo_total = Decimal('0')
                _acum_prorrateo_total = Decimal('0')
                _total_prorrateo_total = Decimal('0')
                _total_dias_en_maq = 0

                for _maq_id, _dias_raw in _maq_entradas:
                    _dias_en_maq = min(_dias_raw, _dias_mes_op)
                    _d_en_maq = Decimal(str(_dias_en_maq))
                    _metros_maq = _metros_maquina.get(_maq_id, Decimal('0'))
                    _base_p = (
                        (metraje_base_val / _d_op * _d_en_maq).quantize(Decimal('0.01'))
                        if _d_op > 0 else Decimal('0')
                    )
                    _acum_p = (
                        (_metros_maq / _d_op * _d_en_maq).quantize(Decimal('0.01'))
                        if _d_op > 0 else Decimal('0')
                    )
                    _total_p = ((_acum_p - _base_p) * monto_ajustado).quantize(Decimal('0.01'))
                    _desglose_maquinas.append({
                        'maquina_id': _maq_id,
                        'maquina_nombre': _maquina_nombres.get(_maq_id, f'Máq. {_maq_id}'),
                        'dias': _dias_en_maq,
                        'metros_acum': float(_metros_maq),
                        'base_prorrateo': float(_base_p),
                        'acum_prorrateo': float(_acum_p),
                        'total': float(_total_p),
                    })
                    _base_prorrateo_total += _base_p
                    _acum_prorrateo_total += _acum_p
                    _total_prorrateo_total += _total_p
                    _total_dias_en_maq += _dias_en_maq

                # Si el trabajador no tiene asistencias con máquina, fila vacía
                if not _maq_entradas:
                    _desglose_maquinas = []

                filas_metraje.append({
                    'bono_pk': bono_trab.pk,
                    'trabajador_pk': trab.pk,
                    'nombre_completo': f"{trab.apepat} {trab.apemat} {trab.nombres}".strip(),
                    'cargo': cargo_trab,
                    'dias_trabajados': bono_trab.dias_trabajados,
                    'dias_operativos': bono_trab.dias_base,
                    'bono_por_metraje': float(bono_por_metro_val),
                    'metraje_base': float(metraje_base_val),
                    'seg_puntaje': seg_puntaje,
                    'seg_activo': seg_activo,
                    'mult_total_pct': mult_total_pct,
                    'monto_ajustado': float(monto_ajustado),
                    'bono_calculado': float(bono_calculado),
                    'total': float(_total_prorrateo_total),
                    'dias_mes_operativo': _dias_mes_op,
                    'dias_en_maquina': _total_dias_en_maq,
                    'metraje_base_prorrateo': float(_base_prorrateo_total),
                    'metraje_acum_prorrateo': float(_acum_prorrateo_total),
                    'desglose_maquinas': _desglose_maquinas,
                })
                continue  # no procesar secciones para trabajadores de metraje

            # Construir datos de secciones con criterios (solo cumplimiento)
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

                # Puntaje: según modalidad de la sección
                global_codigo = _codigo_a_global(seccion.codigo)
                cgp = conceptos_globales_periodo.get(global_codigo) if global_codigo else None

                if cgp is not None:
                    # Concepto global del contrato: mayor prioridad en todos los bonos.
                    # Esto hace que PRODUCCIÓN en BA-ADMINISTRACIÓN use el mismo %
                    # que en logísticos y residentes.
                    puntaje = float(cgp.porcentaje_bono)
                    fuente_puntaje = 'global'
                elif seccion.tabla_calificacion:
                    # Tabla fija: leer desde BonoTrabajadorDetalle (persistido)
                    detalle_tc, _ = BonoTrabajadorDetalle.objects.get_or_create(
                        bono=bono_trab,
                        concepto=seccion,
                        defaults={
                            'puntaje': Decimal('100'),
                            'monto_max_concepto': Decimal(str(
                                float(bono_trab.bono_base) * float(seccion.peso_default) / 100
                            )),
                            'monto_calculado': Decimal('0'),
                        }
                    )
                    puntaje = int(detalle_tc.puntaje)
                    fuente_puntaje = 'tabla_fija'
                else:
                    # Fallback: conteo manual de criterios (checkboxes)
                    puntaje = round(cumplidos * 100 / total_crit) if total_crit > 0 else 100
                    fuente_puntaje = 'manual'

                peso = float(seccion.peso_default)
                bono_base = float(bono_trab.bono_base)

                # Multiplicador metraje para esta sección (0 si no aplica)
                metraje_mult = _METRAJE_MULT.get(global_codigo, Decimal('0'))

                # Fórmula cumplimiento: bono_base × peso% × puntaje%
                monto_seccion = round(bono_base * (peso / 100) * (puntaje / 100), 2)

                total_monto_trab += Decimal(str(monto_seccion))

                secciones_data.append({
                    'concepto_pk': seccion.pk,
                    'nombre': seccion.nombre,
                    'peso': peso,
                    'criterios': criterios_data,
                    'puntaje': puntaje,
                    'fuente_puntaje': fuente_puntaje,
                    'monto': monto_seccion,
                    'metraje_mult_pct': float(metraje_mult * 100),  # 0, 4 ó 8
                    'tabla_calificacion': seccion.tabla_calificacion,
                })

            # Fórmula cumplimiento: suma de secciones (sin factor días — se
            # aplicará más adelante cuando se integre el cálculo por días).
            total_monto_trab = total_monto_trab.quantize(Decimal('0.01'))

            # Auto-persistir monto_final en cada carga (no esperar a que el usuario pulse Guardar)
            if bono_trab.monto_final != total_monto_trab:
                bono_trab.monto_calculado = total_monto_trab
                bono_trab.monto_final = (total_monto_trab + bono_trab.monto_ajuste).quantize(Decimal('0.01'))
                bono_trab.save(update_fields=['monto_calculado', 'monto_final'])
                bono_trab.registrar_historial(
                    fuente='CALCULO',
                    usuario=request.user,
                    observacion=f'Cálculo automático cumplimiento: {bono_trab.dias_trabajados}/{bono_trab.dias_base} días',
                )

            filas_cumplimiento.append({
                'bono_pk': bono_trab.pk,
                'trabajador_pk': trab.pk,
                'nombre_completo': f"{trab.apepat} {trab.apemat} {trab.nombres}".strip(),
                'cargo': trab.cargo or trab.cargo_headcount or '',
                'dias_trabajados': bono_trab.dias_trabajados,
                'dias_operativos': bono_trab.dias_base,
                'bono_base': float(bono_trab.bono_base),
                'tipo_calculo': tipo_calc,
                'secciones': secciones_data,
                'total': float(total_monto_trab),
            })

        if filas_cumplimiento or filas_metraje:
            datos_por_contrato[contrato.nombre_contrato] = {
                'contrato_pk': contrato.pk,
                'periodo_pk': periodo.pk,
                'filas': filas_cumplimiento,
                'filas_metraje': filas_metraje,
            }

    # Preparar estructura de secciones para el header
    secciones_header = []
    for seccion in secciones:
        criterios = seccion.criterios.filter(activo=True).order_by('orden')
        # Para secciones con tabla_calificacion no hay columnas de criterios:
        # solo 2 columnas (dropdown-% y monto)
        num_crit_cols = 0 if seccion.tabla_calificacion else criterios.count()
        secciones_header.append({
            'nombre': seccion.nombre,
            'peso': float(seccion.peso_default),
            'criterios': list(criterios.values_list('nombre', flat=True)),
            'colspan': num_crit_cols + 2,
            'tabla_calificacion': seccion.tabla_calificacion,
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

        # Actualizar metraje_acumulado (trabajadores de tipo metraje)
        metraje_acumulado = bd.get('metraje_acumulado')
        if metraje_acumulado is not None:
            bono_trab.metraje_acumulado = Decimal(str(metraje_acumulado))
            bono_trab.save(update_fields=['metraje_acumulado'])

        # Actualizar monto_final (total calculado enviado desde el DOM)
        monto_final = bd.get('monto_final')
        if monto_final is not None:
            monto_final_dec = Decimal(str(monto_final))
            bono_trab.monto_calculado = monto_final_dec
            bono_trab.monto_final = monto_final_dec + bono_trab.monto_ajuste
            bono_trab.save(update_fields=['monto_calculado', 'monto_final'])
            bono_trab.registrar_historial(
                fuente='GUARDAR',
                usuario=request.user,
                observacion='Guardado manual desde cuadro de calificación',
            )

        # Actualizar criterios
        criterios_dict = bd.get('criterios', {})
        for crit_pk_str, cumple in criterios_dict.items():
            CalificacionCriterio.objects.filter(
                bono_trabajador=bono_trab,
                criterio_id=int(crit_pk_str),
            ).update(cumple=bool(cumple))

        # Actualizar puntajes de tabla fija (INCIDENCIAS / PRODUCCION_META)
        puntajes_tabla = bd.get('puntajes_tabla', {})
        for concepto_pk_str, puntaje_val in puntajes_tabla.items():
            BonoTrabajadorDetalle.objects.update_or_create(
                bono=bono_trab,
                concepto_id=int(concepto_pk_str),
                defaults={'puntaje': Decimal(str(puntaje_val))},
            )

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
                bono.registrar_historial(
                    fuente='RECALC',
                    usuario=user,
                    observacion=f'Recalcular manual: factor={float(factor):.4f}',
                )
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
    import logging
    logger = logging.getLogger('drilling')

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
    debug_autocarga = []
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
                try:
                    _auto_cargar_datos(cgp, anio, mes)
                    calcular_concepto_global(cgp)
                    cgp.save()
                    debug_autocarga.append(
                        f"OK {cgp.concepto.codigo}/{contrato.nombre_contrato}: "
                        f"metros={cgp.metros_acumulados}, meta={cgp.meta_programada}, "
                        f"maquinas={cgp.cantidad_maquinas}"
                    )
                except Exception as e:
                    debug_autocarga.append(
                        f"ERROR {cgp.concepto.codigo}/{contrato.nombre_contrato}: {e}"
                    )
                    logger.error(
                        f"[ConceptosGlobales] Error auto-cargando {cgp.concepto.codigo} "
                        f"contrato={contrato.nombre_contrato}: {e}",
                        exc_info=True,
                    )

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
        'debug_autocarga': debug_autocarga,
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


@login_required
def api_diagnostico_conceptos(request):
    """
    Diagnóstico: muestra qué datos encuentra el sistema para cargar metros y metas.
    GET params: contrato_id, anio, mes
    """
    from django.db.models import Sum, Count
    from .models import TurnoAvance, Turno, Maquina, ProgramacionMes, MetaTurno
    from .utils.periodo_operativo import get_rango_mes_operativo

    contrato_id = request.GET.get('contrato_id')
    anio = int(request.GET.get('anio', date.today().year))
    mes = int(request.GET.get('mes', date.today().month))

    # Acepta ID numérico o nombre parcial del contrato
    if contrato_id and contrato_id.isdigit():
        contrato = get_object_or_404(Contrato, pk=int(contrato_id))
    elif contrato_id:
        contrato = Contrato.objects.filter(
            nombre_contrato__icontains=contrato_id
        ).first()
        if not contrato:
            return JsonResponse({'error': f'No se encontró contrato con nombre "{contrato_id}"'}, status=404)
    else:
        # Listar contratos disponibles
        contratos = list(Contrato.objects.filter(estado='ACTIVO').values('id', 'nombre_contrato'))
        return JsonResponse({'error': 'Falta contrato_id', 'contratos_disponibles': contratos})
    fecha_inicio, fecha_fin = get_rango_mes_operativo(anio, mes)

    # 1. Máquinas operativas
    maquinas = list(Maquina.objects.filter(
        contrato=contrato, estado='OPERATIVO'
    ).values('id', 'nombre', 'estado'))

    maquinas_todas = list(Maquina.objects.filter(
        contrato=contrato
    ).values('id', 'nombre', 'estado'))

    # 2. Turnos en el período
    turnos_por_estado = list(Turno.objects.filter(
        contrato=contrato,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
    ).values('estado').annotate(cnt=Count('id')))

    # 3. TurnoAvance en el período (todos los estados)
    avance_todos = TurnoAvance.objects.filter(
        turno__contrato=contrato,
        turno__fecha__gte=fecha_inicio,
        turno__fecha__lte=fecha_fin,
    ).aggregate(
        total=Sum('metros_perforados'),
        count=Count('id'),
    )

    # 4. TurnoAvance solo COMPLETADO/APROBADO
    avance_filtrado = TurnoAvance.objects.filter(
        turno__contrato=contrato,
        turno__fecha__gte=fecha_inicio,
        turno__fecha__lte=fecha_fin,
        turno__estado__in=['COMPLETADO', 'APROBADO'],
    ).aggregate(
        total=Sum('metros_perforados'),
        count=Count('id'),
    )

    # 5. Muestra de TurnoAvance
    samples = list(TurnoAvance.objects.filter(
        turno__contrato=contrato,
        turno__fecha__gte=fecha_inicio,
        turno__fecha__lte=fecha_fin,
    ).select_related('turno', 'turno__maquina').values(
        'turno__fecha', 'turno__estado', 'turno__maquina__nombre',
        'metros_perforados',
    ).order_by('-turno__fecha')[:10])

    # 6. ProgramacionMes
    maquinas_ids = [m['id'] for m in maquinas]
    progs = list(ProgramacionMes.objects.filter(
        maquina_id__in=maquinas_ids, año=anio, mes=mes,
    ).values('maquina__nombre', 'meta_metros', 'dia_inicio'))

    # 7. Turnos sin TurnoAvance (posible causa: reportes sin avance creado)
    turnos_sin_avance = Turno.objects.filter(
        contrato=contrato,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
    ).exclude(
        avance__isnull=False,
    ).count()

    # 8. Test directo de las funciones de auto-carga
    from .utils.conceptos_globales_engine import (
        cargar_metros_acumulados,
        cargar_meta_programada,
        cargar_cantidad_maquinas,
    )
    test_autocarga = {}
    try:
        metros = cargar_metros_acumulados(contrato, fecha_inicio, fecha_fin)
        test_autocarga['metros_acumulados'] = float(metros)
    except Exception as e:
        test_autocarga['metros_acumulados_error'] = str(e)

    try:
        meta = cargar_meta_programada(contrato, anio, mes)
        test_autocarga['meta_programada'] = float(meta)
    except Exception as e:
        test_autocarga['meta_programada_error'] = str(e)

    try:
        maq = cargar_cantidad_maquinas(contrato)
        test_autocarga['cantidad_maquinas'] = maq
    except Exception as e:
        test_autocarga['cantidad_maquinas_error'] = str(e)

    # 9. Estado actual de ConceptoGlobalPeriodo
    from .models_payroll import ConceptoGlobalPeriodo
    cgps = list(ConceptoGlobalPeriodo.objects.filter(
        contrato=contrato, anio=anio, mes=mes,
    ).select_related('concepto').values(
        'id', 'concepto__codigo', 'concepto__tipo',
        'metros_acumulados', 'meta_programada', 'cantidad_maquinas',
        'valor_calculado', 'porcentaje_bono',
    ))

    return JsonResponse({
        'contrato': contrato.nombre_contrato,
        'periodo': f'{fecha_inicio} a {fecha_fin}',
        'anio': anio,
        'mes': mes,
        'maquinas_operativas': maquinas,
        'maquinas_todas': maquinas_todas,
        'turnos_por_estado': turnos_por_estado,
        'turno_avance_todos_estados': {
            'total_metros': float(avance_todos['total'] or 0),
            'count': avance_todos['count'],
        },
        'turno_avance_completado_aprobado': {
            'total_metros': float(avance_filtrado['total'] or 0),
            'count': avance_filtrado['count'],
        },
        'muestra_avances': samples,
        'programacion_mes': progs,
        'turnos_sin_avance': turnos_sin_avance,
        'test_autocarga': test_autocarga,
        'conceptos_globales_periodo_actual': cgps,
    })


# ===========================================
# ESTRUCTURA SALARIAL — CRUD
# ===========================================


def _sync_sueldo_trabajadores(estructura):
    """Actualiza Trabajador.sueldo para todos los activos que coincidan
    con el contrato + centro_costo + cargo de la estructura."""
    cc = estructura.contrato_servicio.codigo_centro_costo
    actualizados = Trabajador.objects.filter(
        contrato=estructura.contrato,
        centro_costo=cc,
        cargo=estructura.cargo_contratado,
        estado='ACTIVO',
    ).update(sueldo=estructura.sueldo_basico)
    return actualizados

@login_required
def estructura_salarial_list(request):
    """Lista de todas las estructuras salariales."""
    user = request.user
    contrato_filter = request.GET.get('contrato', '')

    estructuras = EstructuraSalarial.objects.select_related(
        'contrato', 'contrato_servicio', 'creado_por'
    ).order_by('contrato__nombre_contrato', 'contrato_servicio__tipo_servicio', 'cargo_contratado')

    if not user.has_access_to_all_contracts() and user.contrato:
        estructuras = estructuras.filter(contrato=user.contrato)
    elif contrato_filter:
        estructuras = estructuras.filter(contrato_id=contrato_filter)

    if user.has_access_to_all_contracts():
        contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    elif user.contrato:
        contratos = Contrato.objects.filter(pk=user.contrato.pk)
    else:
        contratos = Contrato.objects.none()

    return render(request, 'drilling/planilla/estructura_salarial_list.html', {
        'estructuras': estructuras,
        'contratos': contratos,
        'contrato_filter': contrato_filter,
    })


@login_required
def estructura_salarial_create(request):
    """Crear/actualizar estructuras salariales en bloque para un contrato+CTR."""
    from .models import ContratoServicio

    if request.method == 'POST':
        contrato_id = request.POST.get('contrato')
        ctr_id = request.POST.get('ctr_id')

        contrato = get_object_or_404(Contrato, pk=contrato_id)
        ctr = get_object_or_404(ContratoServicio, pk=ctr_id)

        # Recopilar datos de cada fila de cargo del POST
        i = 0
        creados = 0
        actualizados = 0
        while f'cargo_{i}' in request.POST:
            if not request.POST.get(f'incluir_{i}'):
                i += 1
                continue

            cargo = request.POST[f'cargo_{i}'].strip()
            if not cargo:
                i += 1
                continue

            sueldo = request.POST.get(f'sueldo_basico_{i}', '0') or '0'
            bono = request.POST.get(f'bono_por_metraje_{i}', '0') or '0'
            metraje = request.POST.get(f'metraje_base_{i}', '0') or '0'
            bonif = request.POST.get(f'bonificacion_area_{i}', '0') or '0'

            existing = EstructuraSalarial.objects.filter(
                contrato=contrato,
                contrato_servicio=ctr,
                cargo_contratado=cargo,
            ).first()

            if existing:
                existing.guardar_historial(request.user, 'Actualización masiva')
                existing.sueldo_basico = Decimal(sueldo)
                existing.bono_por_metraje = Decimal(bono)
                existing.metraje_base = Decimal(metraje)
                existing.bonificacion_area = Decimal(bonif)
                existing.version += 1
                existing.save()
                _sync_sueldo_trabajadores(existing)
                actualizados += 1
            else:
                est = EstructuraSalarial.objects.create(
                    contrato=contrato,
                    contrato_servicio=ctr,
                    cargo_contratado=cargo,
                    sueldo_basico=Decimal(sueldo),
                    bono_por_metraje=Decimal(bono),
                    metraje_base=Decimal(metraje),
                    bonificacion_area=Decimal(bonif),
                    creado_por=request.user,
                    version=1,
                )
                est.guardar_historial(request.user, 'Creación inicial')
                _sync_sueldo_trabajadores(est)
                creados += 1
            i += 1

        partes = []
        if creados:
            partes.append(f'{creados} creadas')
        if actualizados:
            partes.append(f'{actualizados} actualizadas')
        if partes:
            messages.success(request, f'Estructuras salariales: {", ".join(partes)}.')
        else:
            messages.warning(request, 'No se seleccionó ningún cargo.')
        return redirect('planilla-estructura-salarial-list')

    # GET: mostrar selector de contrato + CTR
    user = request.user
    if user.has_access_to_all_contracts():
        contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    elif user.contrato:
        contratos = Contrato.objects.filter(pk=user.contrato.pk)
    else:
        contratos = Contrato.objects.none()

    return render(request, 'drilling/planilla/estructura_salarial_form.html', {
        'contratos': contratos,
        'titulo': 'Nueva Estructura Salarial',
    })


@login_required
def estructura_salarial_edit(request, pk):
    """Editar estructura salarial existente (genera historial de versión)."""
    estructura = get_object_or_404(EstructuraSalarial, pk=pk)

    if request.method == 'POST':
        form = EstructuraSalarialForm(request.POST, instance=estructura)
        if form.is_valid():
            motivo = form.cleaned_data.get('motivo_cambio', '')
            if not motivo:
                form.add_error('motivo_cambio', 'Debe indicar el motivo del cambio al editar.')
                cargos = list(
                    Trabajador.objects.filter(estado='ACTIVO')
                    .values_list('cargo', flat=True).distinct().order_by('cargo')
                )
                return render(request, 'drilling/planilla/estructura_salarial_form.html', {
                    'form': form,
                    'titulo': f'Editar Estructura Salarial — {estructura.cargo_contratado}',
                    'estructura': estructura,
                    'cargos': cargos,
                })

            # Guardar snapshot de la versión anterior
            estructura.guardar_historial(
                usuario=request.user,
                motivo=motivo,
            )
            # Incrementar versión y guardar
            estructura = form.save(commit=False)
            estructura.version += 1
            estructura.save()
            _sync_sueldo_trabajadores(estructura)
            messages.success(request, f'Estructura salarial actualizada a v{estructura.version}.')
            return redirect('planilla-estructura-salarial-list')
    else:
        form = EstructuraSalarialForm(instance=estructura)

    cargos = list(
        Trabajador.objects.filter(estado='ACTIVO')
        .values_list('cargo', flat=True).distinct().order_by('cargo')
    )

    return render(request, 'drilling/planilla/estructura_salarial_form.html', {
        'form': form,
        'titulo': f'Editar Estructura Salarial — {estructura.cargo_contratado}',
        'estructura': estructura,
        'cargos': cargos,
    })


@login_required
def estructura_salarial_historial(request, pk):
    """Ver historial de versiones de una estructura salarial."""
    estructura = get_object_or_404(
        EstructuraSalarial.objects.select_related('contrato', 'contrato_servicio'),
        pk=pk
    )
    historial = estructura.historial.select_related('modificado_por').order_by('-version')

    return render(request, 'drilling/planilla/estructura_salarial_historial.html', {
        'estructura': estructura,
        'historial': historial,
    })


@login_required
def api_ctr_por_contrato(request, contrato_id):
    """API: devuelve los CTR (ContratoServicio) de un contrato, para filtrar dinámicamente.
    Incluye tanto los ContratoServicio existentes como el CC principal del Contrato si no está ya registrado.
    """
    from .models import Contrato, ContratoServicio

    ctrs = list(ContratoServicio.objects.filter(
        contrato_id=contrato_id, activo=True
    ).values('id', 'tipo_servicio', 'codigo_centro_costo', 'descripcion'))

    # Safety net: si el CC principal del contrato no está en ContratoServicio, agregarlo
    try:
        contrato = Contrato.objects.get(pk=contrato_id)
        if contrato.codigo_centro_costo:
            cc_existentes = {c['codigo_centro_costo'] for c in ctrs}
            if contrato.codigo_centro_costo not in cc_existentes:
                ctrs.insert(0, {
                    'id': None,
                    'tipo_servicio': 'DDH',
                    'codigo_centro_costo': contrato.codigo_centro_costo,
                    'descripcion': f'CTR Principal ({contrato.nombre_contrato})',
                })
    except Contrato.DoesNotExist:
        pass

    return JsonResponse(ctrs, safe=False)


@login_required
def api_cargos_por_ctr(request, contrato_id, ctr_id):
    """API: devuelve los cargos distintos de trabajadores activos para un contrato+CTR,
    junto con la estructura salarial existente si la hay."""
    from django.db.models import Count
    from .models import ContratoServicio

    ctr = get_object_or_404(ContratoServicio, pk=ctr_id)
    codigo_cc = ctr.codigo_centro_costo

    cargos = (
        Trabajador.objects.filter(
            contrato_id=contrato_id,
            centro_costo=codigo_cc,
            estado='ACTIVO',
        )
        .exclude(cargo='')
        .values('cargo')
        .annotate(cantidad=Count('id'))
        .order_by('cargo')
    )

    result = []
    for c in cargos:
        existing = EstructuraSalarial.objects.filter(
            contrato_id=contrato_id,
            contrato_servicio=ctr,
            cargo_contratado=c['cargo'],
        ).first()

        item = {
            'cargo': c['cargo'],
            'cantidad': c['cantidad'],
            'tiene_estructura': existing is not None,
        }
        if existing:
            item['estructura'] = {
                'id': existing.pk,
                'sueldo_basico': str(existing.sueldo_basico),
                'bono_por_metraje': str(existing.bono_por_metraje),
                'metraje_base': str(existing.metraje_base),
                'bonificacion_area': str(existing.bonificacion_area),
                'version': existing.version,
            }
        result.append(item)

    return JsonResponse({'ctr_id': ctr.pk, 'codigo_cc': codigo_cc, 'cargos': result})


# ===========================================
# APIs PARA CONFIGURACIÓN DE BONOS
# ===========================================

@login_required
def api_cargos_activos_contrato(request, contrato_id):
    """
    API: devuelve los cargos distintos de trabajadores ACTIVOS en un contrato.
    Usado para poblar el selector de cargos en el formulario de configuración de bono.
    """
    cargos = (
        Trabajador.objects.filter(contrato_id=contrato_id, estado='ACTIVO')
        .exclude(cargo__isnull=True)
        .exclude(cargo='')
        .values_list('cargo', flat=True)
        .distinct()
        .order_by('cargo')
    )
    return JsonResponse({'cargos': list(cargos)})


@login_required
def api_bonificacion_area_cargo(request):
    """
    API: dado un contrato_id y una lista de cargos, devuelve el bonificacion_area
    desde EstructuraSalarial para cada cargo.
    GET params: contrato_id, cargos (lista separada por comas)

    Retorna: {
        "cargos": {
            "OPERADOR": {"bonificacion_area": "1200.00", "encontrado": true},
            "ASISTENTE": {"bonificacion_area": "0.00", "encontrado": false},
        },
        "sugerido": "1200.00"   <- primer valor encontrado, o promedio si difieren
    }
    """
    contrato_id = request.GET.get('contrato_id')
    cargos_param = request.GET.get('cargos', '')

    if not contrato_id:
        return JsonResponse({'error': 'contrato_id requerido'}, status=400)

    cargos_list = [c.strip() for c in cargos_param.split(',') if c.strip()]
    if not cargos_list:
        return JsonResponse({'cargos': {}, 'sugerido': None})

    resultado = {}
    valores = []

    for cargo in cargos_list:
        # Buscar en estructura salarial; si hay varias entradas (distintos CTR)
        # tomamos el primer valor no nulo de bonificacion_area
        estructura = (
            EstructuraSalarial.objects.filter(
                contrato_id=contrato_id,
                cargo_contratado=cargo,
                activo=True,
            )
            .order_by('-bonificacion_area')  # primero los de mayor valor
            .first()
        )
        if estructura:
            val = float(estructura.bonificacion_area or 0)
            resultado[cargo] = {
                'bonificacion_area': str(estructura.bonificacion_area or '0.00'),
                'bono_por_metraje':  str(estructura.bono_por_metraje or '0.00'),
                'metraje_base':      str(estructura.metraje_base or '0.00'),
                'sueldo_basico':     str(estructura.sueldo_basico or '0.00'),
                'encontrado': True,
            }
            if val:
                valores.append(val)
        else:
            resultado[cargo] = {
                'bonificacion_area': '0.00',
                'bono_por_metraje':  '0.00',
                'metraje_base':      '0.00',
                'sueldo_basico':     '0.00',
                'encontrado': False,
            }

    # Valor sugerido: si todos son iguales → ese valor; si difieren → el mayor
    sugerido = None
    if valores:
        sugerido = f"{max(valores):.2f}"

    return JsonResponse({'cargos': resultado, 'sugerido': sugerido})


@login_required
def api_trabajadores_por_cargo(request):
    """
    API: dado un contrato_id y una lista de cargos (opcionales), devuelve los
    trabajadores ACTIVOS del contrato agrupados por cargo, con nombre y DNI.
    GET params:
        contrato_id  — requerido
        cargos       — comma-separated; vacío = todos los cargos
    Response: { cargos: { "CARGO": [{ dni, nombre }, ...] } }
    """
    contrato_id = request.GET.get('contrato_id')
    cargos_param = request.GET.get('cargos', '')

    if not contrato_id:
        return JsonResponse({'error': 'contrato_id requerido'}, status=400)

    cargos_list = [c.strip() for c in cargos_param.split(',') if c.strip()]

    from django.db.models import Q
    qs = Trabajador.objects.filter(
        contrato_id=contrato_id, estado='ACTIVO'
    ).order_by('cargo', 'apepat', 'apemat', 'nombres')

    if cargos_list:
        qs = qs.filter(
            Q(cargo__in=cargos_list) | Q(cargo_headcount__in=cargos_list)
        )

    resultado = {}
    for trab in qs:
        cargo = trab.cargo_headcount or trab.cargo or ''
        if not cargo:
            continue
        if cargo not in resultado:
            resultado[cargo] = []
        resultado[cargo].append({
            'dni': trab.dni,
            'nombre': f"{trab.apepat} {trab.apemat} {trab.nombres}".strip(),
        })

    return JsonResponse({'cargos': resultado})
