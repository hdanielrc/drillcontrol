"""
Módulo de Gestión de Mantenimiento de Máquinas — Drillcontrol
Autor: sistema
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q, Avg, F, ExpressionWrapper, DecimalField
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    Maquina, MantenimientoMaquina, MaquinaTransferenciaHistorial,
    Contrato, CustomUser
)


# ─────────────────────────────────────────────────────────────────────────────
# PERMISOS
# ─────────────────────────────────────────────────────────────────────────────

def _puede_gestionar_mantenimiento(user):
    """Puede crear / editar registros de mantenimiento."""
    return user.is_authenticated and user.can_manage_maintenance()

def _puede_ver_mantenimiento(user):
    """Puede ver el módulo de mantenimiento."""
    return user.is_authenticated and (
        user.can_manage_maintenance()
        or user.can_supervise_operations()
    )

def _puede_eliminar(user):
    return user.is_authenticated and user.can_manage_all_maintenance()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _maquinas_usuario(user):
    """Queryset de máquinas visibles para el usuario."""
    qs = Maquina.objects.select_related('contrato').exclude(
        contrato__nombre_contrato__icontains='sistema principal'
    )
    if user.can_manage_all_maintenance() or user.can_manage_all_contracts():
        return qs
    # MANTENIMIENTO de contrato: solo ve máquinas de su contrato
    return qs.filter(contrato=user.contrato)


def _alertas_mantenimiento(maquinas_qs):
    """Genera lista de alertas (dict) para máquinas que requieren atención."""
    alertas = []
    for m in maquinas_qs:
        if m.estado == 'FUERA_SERVICIO':
            alertas.append({'maquina': m, 'nivel': 'danger', 'msg': f'{m.nombre} está FUERA DE SERVICIO'})
        elif m.estado == 'MANTENIMIENTO':
            alertas.append({'maquina': m, 'nivel': 'warning', 'msg': f'{m.nombre} está EN MANTENIMIENTO'})
        elif m.requiere_mantenimiento():
            alertas.append({'maquina': m, 'nivel': 'danger', 'msg': f'{m.nombre} — horómetro supera el próximo mtto. programado'})
        elif m.proximo_mantenimiento_horometro:
            hrs_rest = float(m.proximo_mantenimiento_horometro - m.horometro)
            if 0 < hrs_rest <= 50:
                alertas.append({'maquina': m, 'nivel': 'warning', 'msg': f'{m.nombre} — faltan {hrs_rest:.0f} hrs para el próximo mtto.'})
    return alertas


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD DE MANTENIMIENTO
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mantenimiento_dashboard(request):
    if not _puede_ver_mantenimiento(request.user):
        messages.error(request, 'No tiene permisos para acceder al módulo de mantenimiento.')
        return redirect('dashboard')
    maquinas = _maquinas_usuario(request.user)

    # KPIs
    total        = maquinas.count()
    operativas   = maquinas.filter(estado='OPERATIVO').count()
    en_mtto      = maquinas.filter(estado='MANTENIMIENTO').count()
    fuera_srv    = maquinas.filter(estado='FUERA_SERVICIO').count()

    # Últimas bitácoras (30 días)
    hace_30 = date.today() - timedelta(days=30)
    ot_recientes = MantenimientoMaquina.objects.filter(
        maquina__in=maquinas,
        fecha_inicio__gte=hace_30
    ).select_related('maquina', 'maquina__contrato', 'registrado_por').order_by('-fecha_inicio')[:10]

    # OTs abiertas (PENDIENTE o EN_PROCESO)
    ot_abiertas = MantenimientoMaquina.objects.filter(
        maquina__in=maquinas,
        estado_ot__in=['PENDIENTE', 'EN_PROCESO']
    ).select_related('maquina', 'maquina__contrato').order_by('prioridad', 'fecha_inicio')

    # Costo mensual (mes actual)
    hoy = date.today()
    costo_mes = MantenimientoMaquina.objects.filter(
        maquina__in=maquinas,
        fecha_inicio__year=hoy.year,
        fecha_inicio__month=hoy.month,
    ).aggregate(total=Sum('costo_total'))['total'] or Decimal('0')

    # Distribución por tipo (últimos 90 días)
    hace_90 = date.today() - timedelta(days=90)
    dist_tipo = MantenimientoMaquina.objects.filter(
        maquina__in=maquinas,
        fecha_inicio__gte=hace_90
    ).values('tipo').annotate(cantidad=Count('id')).order_by('-cantidad')

    # Alertas
    alertas = _alertas_mantenimiento(maquinas)

    # Máquinas ordenadas por porcentaje de vida (desc = más urgentes primero)
    maquinas_list = sorted(
        maquinas.filter(estado='OPERATIVO'),
        key=lambda m: m.porcentaje_vida_mantenimiento(),
        reverse=True
    )[:15]

    context = {
        'total': total, 'operativas': operativas,
        'en_mtto': en_mtto, 'fuera_srv': fuera_srv,
        'ot_recientes': ot_recientes,
        'ot_abiertas': ot_abiertas,
        'costo_mes': costo_mes,
        'dist_tipo': list(dist_tipo),
        'alertas': alertas,
        'maquinas_list': maquinas_list,
    }
    return render(request, 'drilling/mantenimiento/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# LISTA DE MÁQUINAS (vista mantenimiento)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mantenimiento_maquinas(request):
    if not _puede_ver_mantenimiento(request.user):
        messages.error(request, 'No tiene permisos para acceder al módulo de mantenimiento.')
        return redirect('dashboard')
    maquinas = _maquinas_usuario(request.user).order_by('contrato__nombre_contrato', 'nombre')

    # Filtros
    estado_f   = request.GET.get('estado', '')
    contrato_f = request.GET.get('contrato', '')
    q_f        = request.GET.get('q', '')

    if estado_f:
        maquinas = maquinas.filter(estado=estado_f)
    if contrato_f:
        maquinas = maquinas.filter(contrato_id=contrato_f)
    if q_f:
        maquinas = maquinas.filter(Q(nombre__icontains=q_f) | Q(numero_serie__icontains=q_f) | Q(marca__icontains=q_f))

    contratos = Contrato.objects.filter(estado='ACTIVO').exclude(
        nombre_contrato__icontains='sistema principal'
    ).order_by('nombre_contrato')

    context = {
        'maquinas': maquinas,
        'contratos': contratos,
        'estado_f': estado_f,
        'contrato_f': contrato_f,
        'q_f': q_f,
        'alertas': _alertas_mantenimiento(maquinas),
    }
    return render(request, 'drilling/mantenimiento/maquinas.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# CREAR / EDITAR MÁQUINA
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mantenimiento_maquina_form(request, pk=None):
    if not _puede_gestionar_mantenimiento(request.user):
        messages.error(request, 'No tiene permisos para gestionar máquinas.')
        return redirect('mantenimiento-dashboard')

    maquina = get_object_or_404(Maquina, pk=pk) if pk else None
    contratos = Contrato.objects.filter(estado='ACTIVO').exclude(
        nombre_contrato__icontains='sistema principal'
    ).order_by('nombre_contrato')

    if request.method == 'POST':
        try:
            data = request.POST
            contrato = get_object_or_404(Contrato, pk=data['contrato'])

            fields = {
                'contrato':           contrato,
                'nombre':             data['nombre'].strip(),
                'tipo':               data.get('tipo', ''),
                'tipo_trabajo':       data.get('tipo_trabajo', 'SUBTERRANEA'),
                'estado':             data.get('estado', 'OPERATIVO'),
                'horometro':          Decimal(data.get('horometro', '0') or '0'),
                'numero_serie':       data.get('numero_serie', ''),
                'marca':              data.get('marca', ''),
                'modelo_equipo':      data.get('modelo_equipo', ''),
                'potencia_hp':        Decimal(data['potencia_hp']) if data.get('potencia_hp') else None,
                'año_fabricacion':    int(data['año_fabricacion']) if data.get('año_fabricacion') else None,
                'intervalo_mantenimiento_horas': Decimal(data.get('intervalo_mantenimiento_horas') or '250'),
                'observaciones':      data.get('observaciones', ''),
            }

            if maquina:
                for k, v in fields.items():
                    setattr(maquina, k, v)
                maquina.save()
                messages.success(request, f'Máquina "{maquina.nombre}" actualizada.')
            else:
                maquina = Maquina.objects.create(**fields)
                messages.success(request, f'Máquina "{maquina.nombre}" creada.')

            return redirect('mantenimiento-maquina-detalle', pk=maquina.pk)
        except Exception as e:
            messages.error(request, f'Error: {e}')

    context = {'maquina': maquina, 'contratos': contratos}
    return render(request, 'drilling/mantenimiento/maquina_form.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# DETALLE DE MÁQUINA (historial completo)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mantenimiento_maquina_detalle(request, pk):
    if not _puede_ver_mantenimiento(request.user):
        messages.error(request, 'No tiene permisos para acceder al módulo de mantenimiento.')
        return redirect('dashboard')
    maquina = get_object_or_404(_maquinas_usuario(request.user), pk=pk)

    bitacoras = MantenimientoMaquina.objects.filter(
        maquina=maquina
    ).select_related('registrado_por', 'aprobado_por').order_by('-fecha_inicio')

    # Historial de traslados
    traslados = MaquinaTransferenciaHistorial.objects.filter(
        maquina=maquina
    ).select_related('contrato_origen', 'contrato_destino', 'usuario').order_by('-fecha_transferencia')

    # Estadísticas
    costo_acumulado = bitacoras.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
    horas_paradas   = bitacoras.aggregate(total=Sum('tiempo_parada_horas'))['total'] or Decimal('0')
    total_mttos     = bitacoras.count()

    context = {
        'maquina':        maquina,
        'bitacoras':      bitacoras,
        'traslados':      traslados,
        'costo_acumulado': costo_acumulado,
        'horas_paradas':  horas_paradas,
        'total_mttos':    total_mttos,
        'puede_gestionar': _puede_gestionar_mantenimiento(request.user),
    }
    return render(request, 'drilling/mantenimiento/maquina_detalle.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# BITÁCORA: CREAR / EDITAR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def bitacora_form(request, maquina_pk, pk=None):
    if not _puede_gestionar_mantenimiento(request.user):
        messages.error(request, 'No tiene permisos para registrar mantenimientos.')
        return redirect('mantenimiento-dashboard')

    maquina  = get_object_or_404(_maquinas_usuario(request.user), pk=maquina_pk)
    registro = get_object_or_404(MantenimientoMaquina, pk=pk, maquina=maquina) if pk else None

    if request.method == 'POST':
        d = request.POST
        try:
            def _dec(key, default=None):
                v = d.get(key, '').strip()
                return Decimal(v) if v else default

            fecha_inicio = date.fromisoformat(d['fecha_inicio'])
            fecha_fin    = date.fromisoformat(d['fecha_fin']) if d.get('fecha_fin') else None

            kwargs = {
                'maquina':                         maquina,
                'fecha_inicio':                    fecha_inicio,
                'fecha_fin':                       fecha_fin,
                'horometro_registro':              Decimal(d['horometro_registro']),
                'tipo':                            d['tipo'],
                'prioridad':                       d.get('prioridad', 'MEDIA'),
                'estado_ot':                       d.get('estado_ot', 'PENDIENTE'),
                'descripcion':                     d['descripcion'],
                'trabajo_realizado':               d.get('trabajo_realizado', ''),
                'repuestos_utilizados':            d.get('repuestos_utilizados', ''),
                'tiempo_parada_horas':             _dec('tiempo_parada_horas'),
                'costo_mano_obra':                 _dec('costo_mano_obra'),
                'costo_repuestos':                 _dec('costo_repuestos'),
                'costo_total':                     _dec('costo_total'),
                'proveedor_taller':                d.get('proveedor_taller', ''),
                'proxima_intervencion_horometro':  _dec('proxima_intervencion_horometro'),
                'estado_posterior':                d.get('estado_posterior', 'OPERATIVO'),
                'responsable_tecnico':             d.get('responsable_tecnico', ''),
                'observaciones':                   d.get('observaciones', ''),
                'registrado_por':                  request.user,
            }

            if registro:
                for k, v in kwargs.items():
                    setattr(registro, k, v)
                registro.save()
                messages.success(request, 'Registro actualizado correctamente.')
            else:
                registro = MantenimientoMaquina.objects.create(**kwargs)
                messages.success(request, 'Registro de mantenimiento guardado.')

            return redirect('mantenimiento-maquina-detalle', pk=maquina.pk)
        except Exception as e:
            messages.error(request, f'Error al guardar: {e}')

    context = {
        'maquina':  maquina,
        'registro': registro,
        'hoy':      date.today().isoformat(),
        'TIPO_CHOICES':      MantenimientoMaquina.TIPO_CHOICES,
        'PRIORIDAD_CHOICES': MantenimientoMaquina.PRIORIDAD_CHOICES,
        'ESTADO_OT_CHOICES': MantenimientoMaquina.ESTADO_OT_CHOICES,
        'ESTADO_CHOICES':    Maquina.ESTADO_CHOICES,
    }
    return render(request, 'drilling/mantenimiento/bitacora_form.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# BITÁCORA: ELIMINAR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def bitacora_delete(request, pk):
    if not _puede_eliminar(request.user):
        messages.error(request, 'No tiene permisos para eliminar registros.')
        return redirect('mantenimiento-dashboard')

    registro = get_object_or_404(MantenimientoMaquina, pk=pk)
    maquina_pk = registro.maquina_id
    if request.method == 'POST':
        registro.delete()
        messages.success(request, 'Registro eliminado.')
        return redirect('mantenimiento-maquina-detalle', pk=maquina_pk)
    return render(request, 'drilling/mantenimiento/confirm_delete.html', {'registro': registro})


# ─────────────────────────────────────────────────────────────────────────────
# TRASLADO DE MÁQUINA
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mantenimiento_traslado(request, pk=None):
    """Vista dedicada al traslado de máquinas entre contratos con selección mejorada."""
    if not _puede_gestionar_mantenimiento(request.user):
        messages.error(request, 'No tiene permisos para trasladar máquinas.')
        return redirect('mantenimiento-maquinas')

    maquina_presel = get_object_or_404(_maquinas_usuario(request.user), pk=pk) if pk else None

    contratos = Contrato.objects.filter(estado='ACTIVO').exclude(
        nombre_contrato__icontains='sistema principal'
    ).order_by('nombre_contrato')

    maquinas = _maquinas_usuario(request.user).order_by('nombre')

    if request.method == 'POST':
        maquina_id     = request.POST.get('maquina_id')
        nuevo_ctr_id   = request.POST.get('nuevo_contrato')
        observaciones  = request.POST.get('observaciones', '')

        if not maquina_id or not nuevo_ctr_id:
            messages.error(request, 'Faltan datos para el traslado.')
        else:
            maquina       = get_object_or_404(Maquina, pk=maquina_id)
            nuevo_contrato = get_object_or_404(Contrato, pk=nuevo_ctr_id)

            if not request.user.can_manage_all_contracts():
                if maquina.contrato != request.user.contrato:
                    messages.error(request, 'No tiene permisos para trasladar esta máquina.')
                    return redirect('mantenimiento-traslado')

            if maquina.contrato == nuevo_contrato:
                messages.warning(request, f'La máquina ya pertenece a {nuevo_contrato.nombre_contrato}.')
            else:
                contrato_ant = maquina.contrato
                with transaction.atomic():
                    maquina.contrato = nuevo_contrato
                    maquina.save(update_fields=['contrato'])
                    MaquinaTransferenciaHistorial.objects.create(
                        maquina=maquina,
                        contrato_origen=contrato_ant,
                        contrato_destino=nuevo_contrato,
                        usuario=request.user,
                        observaciones=observaciones,
                    )
                messages.success(request, f'"{maquina.nombre}" trasladada de {contrato_ant.nombre_contrato} → {nuevo_contrato.nombre_contrato}.')
                return redirect('mantenimiento-maquina-detalle', pk=maquina.pk)

    # Historial reciente
    historial = MaquinaTransferenciaHistorial.objects.filter(
        maquina__in=maquinas
    ).select_related('maquina', 'contrato_origen', 'contrato_destino', 'usuario').order_by('-fecha_transferencia')[:20]

    context = {
        'maquinas':      maquinas,
        'contratos':     contratos,
        'historial':     historial,
        'maquina_presel': maquina_presel,
    }
    return render(request, 'drilling/mantenimiento/traslado.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX: Cambiar estado de máquina
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def api_cambiar_estado_maquina(request, pk):
    if not _puede_gestionar_mantenimiento(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    try:
        body   = json.loads(request.body)
        estado = body['estado']
        maquina = get_object_or_404(_maquinas_usuario(request.user), pk=pk)
        if estado not in dict(Maquina.ESTADO_CHOICES):
            return JsonResponse({'error': 'Estado inválido'}, status=400)
        maquina.estado = estado
        maquina.save(update_fields=['estado'])
        return JsonResponse({'ok': True, 'estado': estado, 'label': maquina.get_estado_display()})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
