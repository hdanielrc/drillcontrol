"""
Vista para el organigrama organizacional con vista semanal de tareo.

Estructura basada en el campo `grupo` del trabajador:
  - LINEA_MANDO          → Línea de Mando
  - OPERADORES           → Operadores, agrupados por guardia A/B/C con máquina
  - SERVICIOS_GEOLOGICOS → Servicios Geológicos
  - PERSONAL_AUXILIAR    → Personal Auxiliar
  - Stand By / Sin grupo → al final

Con semana seleccionada se superpone el estado de tareo de cada día
sobre cada tarjeta de trabajador.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
from .models import Contrato, Trabajador, AsistenciaTrabajador


# Días de la semana abreviados (lunes=0)
DIAS_CORTOS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do']

# Código corto y clase CSS por estado de asistencia
ESTADO_BADGE = {
    'TRABAJADO':           ('T',   'sb-t'),
    'DIA_LIBRE':           ('DL',  'sb-dl'),
    'FALTA':               ('F',   'sb-f'),
    'DESCANSO_MEDICO':     ('DM',  'sb-dm'),
    'VACACIONES':          ('V',   'sb-v'),
    'PERMISO':             ('P',   'sb-p'),
    'STAND_BY':            ('SB',  'sb-sb'),
    'INDUCCION':           ('I',   'sb-i'),
    'INDUCCION_VIRTUAL':   ('IV',  'sb-i'),
    'RECORRIDO':           ('R',   'sb-r'),
    'DIA_APOYO':           ('DA',  'sb-da'),
    'SUSPENSION':          ('S',   'sb-f'),
    'LICENCIA_SIN_GOCE':   ('LSG', 'sb-p'),
    'LICENCIA_CON_GOCE':   ('LCG', 'sb-p'),
    'LICENCIA_FALLECIMIENTO': ('LF', 'sb-p'),
    'PERMISO_PATERNIDAD':  ('PT',  'sb-p'),
    'SUBSIDIO':            ('SUB', 'sb-dm'),
    'CESADO':              ('C',   'sb-f'),
    'TRABAJO_CALIENTE':    ('TC',  'sb-t'),
}


def _cargo_order(cargo):
    c = (cargo or '').upper()
    if 'RESIDENTE' in c:      return 1
    if 'JEFE' in c:           return 2
    if 'GERENTE' in c:        return 2
    if 'ADMINISTRADOR' in c:  return 3
    if 'INGENIERO' in c:      return 3
    if 'SUPERVISOR' in c:     return 4
    return 5


def _semana_desde_offset(offset: int, dia_inicio: int = 0):
    """
    Devuelve (inicio, fin) de la semana indicada por offset (0=semana actual).
    dia_inicio: día que arranca la semana según contrato (0=Lun … 6=Dom).
    Ej: dia_inicio=2 → semana Mié–Mar.
    """
    hoy = date.today()
    # Cuántos días retroceder desde hoy para llegar al inicio de la semana actual
    dias_desde_inicio = (hoy.weekday() - dia_inicio) % 7
    inicio_actual = hoy - timedelta(days=dias_desde_inicio)
    inicio = inicio_actual + timedelta(weeks=offset)
    fin    = inicio + timedelta(days=6)
    return inicio, fin


def _build_worker_dict(t, tareo_dict, dias_semana):
    """Construye el dict que el template usa para pintar un trabajador."""
    semana = []
    trabajado_count = 0
    for d in dias_semana:
        asist = tareo_dict.get(t.id, {}).get(d)
        if asist:
            codigo, css = ESTADO_BADGE.get(asist, (asist[:2], 'sb-dl'))
            if asist in ('TRABAJADO', 'TRABAJO_CALIENTE', 'DIA_APOYO',
                         'INDUCCION', 'INDUCCION_VIRTUAL', 'RECORRIDO'):
                trabajado_count += 1
        else:
            codigo, css = '—', 'sb-nd'
        semana.append({
            'dia_corto': DIAS_CORTOS[d.weekday()],
            'fecha': d,
            'codigo': codigo,
            'css': css,
        })
    return {
        'obj': t,
        'semana': semana,
        'trabajado_count': trabajado_count,
    }


@login_required
def organigrama_view(request):
    """Vista del organigrama con navegación semanal de tareo."""
    user = request.user

    # ── Contratos accesibles ─────────────────────────────────────
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

    # Día que inicia la "semana de guardia" según el contrato (0=Lun…6=Dom).
    # Fallback: lunes (0) si no está configurado.
    dia_inicio_semana = contrato.dia_cambio_guardia if contrato.dia_cambio_guardia is not None else 0

    # ── Semana a mostrar ─────────────────────────────────────────
    semana_offset = int(request.GET.get('semana_offset', 0))
    semana_inicio, semana_fin = _semana_desde_offset(semana_offset, dia_inicio_semana)
    dias_semana = [semana_inicio + timedelta(days=i) for i in range(7)]

    meses_es = {
        1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
        7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'
    }
    label_semana = (
        f"{semana_inicio.day} {meses_es[semana_inicio.month]} "
        f"– {semana_fin.day} {meses_es[semana_fin.month]} {semana_fin.year}"
    )

    # ── Trabajadores activos ─────────────────────────────────────
    trabajadores_qs = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).select_related('maquina_asignada').order_by('apepat', 'nombres')

    # ── Tareo de la semana ───────────────────────────────────────
    # tareo_dict[trabajador_id][fecha] = estado
    asistencias = AsistenciaTrabajador.objects.filter(
        trabajador__contrato=contrato,
        fecha__gte=semana_inicio,
        fecha__lte=semana_fin,
    ).values('trabajador_id', 'fecha', 'estado')

    tareo_dict = {}
    for a in asistencias:
        tareo_dict.setdefault(a['trabajador_id'], {})[a['fecha']] = a['estado']

    # ── Construir listas por grupo con datos de tareo ───────────
    linea_mando_raw = sorted(
        [t for t in trabajadores_qs if t.grupo == 'LINEA_MANDO'],
        key=lambda t: (_cargo_order(t.cargo), t.apepat)
    )
    linea_mando = [_build_worker_dict(t, tareo_dict, dias_semana) for t in linea_mando_raw]

    operadores_raw = [t for t in trabajadores_qs if t.grupo == 'OPERADORES']
    guardias_dict = {}
    for t in sorted(
        operadores_raw,
        key=lambda x: (x.guardia_asignada or 'Z', x.maquina_asignada_id or 0, x.apepat)
    ):
        g = t.guardia_asignada or 'SIN_GUARDIA'
        guardias_dict.setdefault(g, []).append(_build_worker_dict(t, tareo_dict, dias_semana))

    operadores_por_guardia = []
    for key in ['A', 'B', 'C', 'SIN_GUARDIA']:
        if key in guardias_dict:
            # sub-agrupar por máquina
            maquinas_sub = {}
            for wd in guardias_dict[key]:
                mq = wd['obj'].maquina_asignada
                mq_key = mq.id if mq else None
                maquinas_sub.setdefault(mq_key, {'maquina': mq, 'workers': []})['workers'].append(wd)
            maquinas_list = []
            for mk, mv in sorted(maquinas_sub.items(), key=lambda x: (x[0] is None, x[0] or 0)):
                maquinas_list.append(mv)
            operadores_por_guardia.append({
                'guardia': key,
                'label': f'Guardia {key}' if key != 'SIN_GUARDIA' else 'Sin Guardia',
                'maquinas': maquinas_list,
                'total': len(guardias_dict[key]),
            })

    servicios_geo_raw = [t for t in trabajadores_qs if t.grupo == 'SERVICIOS_GEOLOGICOS']
    servicios_geo = [_build_worker_dict(t, tareo_dict, dias_semana) for t in servicios_geo_raw]

    personal_auxiliar_raw = [t for t in trabajadores_qs if t.grupo == 'PERSONAL_AUXILIAR']
    personal_auxiliar = [_build_worker_dict(t, tareo_dict, dias_semana) for t in personal_auxiliar_raw]

    stand_by_raw = [t for t in trabajadores_qs if t.es_standby]
    stand_by = [_build_worker_dict(t, tareo_dict, dias_semana) for t in stand_by_raw]

    otros_raw = [t for t in trabajadores_qs if not t.grupo and not t.es_standby]
    otros = [_build_worker_dict(t, tareo_dict, dias_semana) for t in otros_raw]

    context = {
        'contrato': contrato,
        'contratos_disponibles': contratos_disponibles,
        'total_trabajadores': trabajadores_qs.count(),
        'linea_mando': linea_mando,
        'operadores_por_guardia': operadores_por_guardia,
        'servicios_geo': servicios_geo,
        'personal_auxiliar': personal_auxiliar,
        'stand_by': stand_by,
        'otros': otros,
        'total_operadores': len(operadores_raw),
        'total_linea_mando': len(linea_mando_raw),
        'total_servicios_geo': len(servicios_geo_raw),
        'total_auxiliar': len(personal_auxiliar_raw),
        'total_standby': len(stand_by_raw),
        # Semana
        'semana_offset': semana_offset,
        'semana_inicio': semana_inicio,
        'semana_fin': semana_fin,
        'dias_semana': dias_semana,
        'label_semana': label_semana,
        'today': date.today(),
    }

    return render(request, 'drilling/organigrama/view.html', context)


