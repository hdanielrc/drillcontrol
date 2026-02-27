"""
Vista para el organigrama organizacional - Solo visualización.

Estructura basada en el campo `grupo` del trabajador:
  - LINEA_MANDO   → Línea de Mando (Residente, Jefes, Ingenieros, Supervisores)
  - OPERADORES    → Operadores, agrupados por guardia A/B/C con máquina asignada
  - SERVICIOS_GEOLOGICOS → Servicios Geológicos
  - PERSONAL_AUXILIAR   → Personal Auxiliar
  - Stand By / Sin grupo → al final
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Contrato, Trabajador


def _cargo_order(cargo):
    """Retorna un número de prioridad para ordenar dentro de Línea de Mando."""
    c = (cargo or '').upper()
    if 'RESIDENTE' in c:        return 1
    if 'JEFE' in c:             return 2
    if 'GERENTE' in c:          return 2
    if 'ADMINISTRADOR' in c:    return 3
    if 'INGENIERO' in c:        return 3
    if 'SUPERVISOR' in c:       return 4
    return 5


@login_required
def organigrama_view(request):
    """Vista para mostrar el organigrama del contrato - Solo visualización."""
    user = request.user

    # Determinar contratos accesibles
    if user.has_access_to_all_contracts():
        contrato_id = request.GET.get('contrato')
        if contrato_id:
            try:
                contrato = Contrato.objects.get(id=contrato_id, estado='ACTIVO')
            except Contrato.DoesNotExist:
                messages.error(request, 'Contrato no encontrado')
                contrato = None
        else:
            contrato = Contrato.objects.filter(estado='ACTIVO').first()
        contratos_disponibles = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    else:
        contrato = user.contrato
        contratos_disponibles = None

    if not contrato:
        messages.warning(request, 'No hay contratos activos disponibles')
        return redirect('dashboard')

    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).select_related('maquina_asignada').order_by('apepat', 'nombres')

    # ── Línea de Mando ──────────────────────────────────────────────
    linea_mando = sorted(
        [t for t in trabajadores if t.grupo == 'LINEA_MANDO'],
        key=lambda t: (_cargo_order(t.cargo), t.apepat)
    )

    # ── Operadores agrupados por guardia A/B/C ───────────────────────
    # Sorted por (guardia, maquina_id, apepat) para que {% regroup %} funcione
    operadores_raw = [t for t in trabajadores if t.grupo == 'OPERADORES']
    guardias_operadores = {}
    for t in sorted(
        operadores_raw,
        key=lambda x: (
            x.guardia_asignada or 'Z',
            x.maquina_asignada_id or 0,
            x.apepat,
        )
    ):
        g = t.guardia_asignada or 'SIN_GUARDIA'
        guardias_operadores.setdefault(g, []).append(t)

    operadores_por_guardia = []
    for key in ['A', 'B', 'C', 'SIN_GUARDIA']:
        if key in guardias_operadores:
            operadores_por_guardia.append({
                'guardia': key,
                'label': f'Guardia {key}' if key != 'SIN_GUARDIA' else 'Sin Guardia',
                'trabajadores': guardias_operadores[key],
            })

    # ── Servicios Geológicos ─────────────────────────────────────────
    servicios_geo = [t for t in trabajadores if t.grupo == 'SERVICIOS_GEOLOGICOS']

    # ── Personal Auxiliar ────────────────────────────────────────────
    personal_auxiliar = [t for t in trabajadores if t.grupo == 'PERSONAL_AUXILIAR']

    # ── Stand By + Sin grupo ─────────────────────────────────────────
    otros = [t for t in trabajadores if not t.grupo or t.es_standby]

    context = {
        'contrato': contrato,
        'contratos_disponibles': contratos_disponibles,
        'total_trabajadores': trabajadores.count(),
        'linea_mando': linea_mando,
        'operadores_por_guardia': operadores_por_guardia,
        'servicios_geo': servicios_geo,
        'personal_auxiliar': personal_auxiliar,
        'otros': otros,
        'total_operadores': len(operadores_raw),
        'total_linea_mando': len(linea_mando),
        'total_servicios_geo': len(servicios_geo),
        'total_auxiliar': len(personal_auxiliar),
    }

    return render(request, 'drilling/organigrama/view.html', context)

