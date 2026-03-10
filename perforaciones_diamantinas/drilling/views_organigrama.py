"""
Vista para el organigrama organizacional con vista semanal de tareo.

Estructura basada en el campo `grupo` del trabajador:
  - LINEA_MANDO          → Línea de Mando
  - OPERADORES           → Operadores, agrupados por guardia A/B/C con máquina
  - SERVICIOS_GEOLOGICOS → Servicios Geológicos
    - CONDUCTORES    → Conductores
  - Stand By / Sin grupo → al final

Con semana seleccionada se superpone el estado de tareo de cada día
sobre cada tarjeta de trabajador.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
from collections import defaultdict
from .models import Contrato, Trabajador, AsistenciaTrabajador, AsistenciaDiaria, HeadCount

# Mapeo de estados V2 (AsistenciaDiaria) a estados V1 para reutilizar los badges
V2_A_V1 = {
    'TRABAJO':    'TRABAJADO',
    'DESCANSO':   'DIA_LIBRE',
    'FALTA':      'FALTA',
    'DM':         'DESCANSO_MEDICO',
    'VACACIONES': 'VACACIONES',
    'PERMISO':    'PERMISO',
    'SUSPENSION': 'SUSPENSION',
    'LICENCIA':   'LICENCIA_SIN_GOCE',
    'INDUCCION':  'INDUCCION',
    'STAND_BY':   'STAND_BY',
    'DIA_APOYO':  'DIA_APOYO',
}


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


def _grupo_para_cargo(cargo):
    """Clasifica un cargo en uno de los 4 grupos del organigrama usando keywords."""
    c = (cargo or '').upper()
    # Ayudantes siempre van a OPERADORES
    if any(k in c for k in [
        'PERFORISTA', 'AYUDANTE DDH', 'AYUDANTE PERFORISTA', 'AYUD.DE PERFORACION',
        'AYUD. DE PERFORACION', 'AYUDANTE DE PERFORACION', 'AYUDANTE DE SIMBA',
        'OPERADOR DE SIMBA', 'OPERADOR SIMBA', 'TEC. DE PERFORACION', 'TEC.DE PERFORACION',
        'TECNICO DE PERFORACION', 'AYUDANTE', 'AYUDANTE SB', 'AYUDANTE DE MAQUINA', 'AYUDANTE DE EQUIPO']):
        return 'OPERADORES'
    if any(k in c for k in ['GEOLOGO', 'GEOLOG', 'MUESTRERO', 'GEOMECANICO',
                             'GEOLOGICO', 'GEOLOGICA']):
        return 'SERVICIOS_GEOLOGICOS'
    # Asistente Administrativo debe ir a LINEA_MANDO
    if 'ASISTENTE ADMINISTRATIVO' in c:
        return 'LINEA_MANDO'
    if any(k in c for k in ['RESIDENTE', 'SUPERVISOR', 'INGENIERO', 'ADMINISTRADOR',
                             'SEGURIDAD', 'JEFE', 'GERENTE', 'PREVENCION', 'SSOMA',
                             'LOGISTIC', 'COORDINADOR', 'INSPECTOR', 'MONITOR']):
        return 'LINEA_MANDO'
    return 'CONDUCTORES'


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

    # ── Tareo de la semana ──────────────────────────────────────
    # tareo_dict[trabajador_id][fecha] = estado
    # Fuente 1: modelo V1 (AsistenciaTrabajador) – estados granulares
    tareo_dict = {}
    for a in AsistenciaTrabajador.objects.filter(
        trabajador__contrato=contrato,
        fecha__gte=semana_inicio,
        fecha__lte=semana_fin,
    ).values('trabajador_id', 'fecha', 'estado'):
        tareo_dict.setdefault(a['trabajador_id'], {})[a['fecha']] = a['estado']

    # Fuente 2: modelo V2 (AsistenciaDiaria) – correcciones manuales tienen
    # prioridad sobre V1; proyecciones solo se usan si no hay dato V1.
    for a in AsistenciaDiaria.objects.filter(
        empleado__contrato=contrato,
        fecha__gte=semana_inicio,
        fecha__lte=semana_fin,
    ).values('empleado_id', 'fecha', 'estado', 'es_proyeccion'):
        v1_equiv = V2_A_V1.get(a['estado'], a['estado'])
        existing = tareo_dict.get(a['empleado_id'], {}).get(a['fecha'])
        # Corrección manual V2 siempre gana; proyección V2 solo si no hay V1
        if not a['es_proyeccion'] or existing is None:
            tareo_dict.setdefault(a['empleado_id'], {})[a['fecha']] = v1_equiv

    # Agrupar trabajadores por servicio y grupo
    trabajadores_por_servicio_grupo = {}
    for t in trabajadores_qs:
        cargo_hc = t.cargo_headcount if getattr(t, 'cargo_headcount', None) else t.cargo
        grupo = _grupo_para_cargo(cargo_hc)
        servicio = getattr(t, 'servicio', None) or getattr(t, 'tipo_servicio', None) or 'SIN_SERVICIO'
        if grupo == 'OPERADORES':
            # Subagrupar por máquina
            maquina = t.maquina_asignada
            maquina_key = maquina.id if maquina else None
            trabajadores_por_servicio_grupo.setdefault(servicio, {}).setdefault(grupo, {}).setdefault(maquina_key, {'maquina': maquina, 'workers': []})['workers'].append(_build_worker_dict(t, tareo_dict, dias_semana))
        else:
            trabajadores_por_servicio_grupo.setdefault(servicio, {}).setdefault(grupo, []).append(_build_worker_dict(t, tareo_dict, dias_semana))

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

    conductores_raw = [t for t in trabajadores_qs if t.grupo == 'CONDUCTORES']
    conductores = [_build_worker_dict(t, tareo_dict, dias_semana) for t in conductores_raw]

    stand_by_raw = [t for t in trabajadores_qs if t.es_standby]
    stand_by = [_build_worker_dict(t, tareo_dict, dias_semana) for t in stand_by_raw]

    otros_raw = [t for t in trabajadores_qs if not t.grupo and not t.es_standby]
    otros = [_build_worker_dict(t, tareo_dict, dias_semana) for t in otros_raw]

    # ── Slots Vacantes (HeadCount faltantes) agrupados por servicio y grupo ────
    slots_por_servicio_grupo = {}
    for hc in HeadCount.objects.filter(contrato=contrato, activo=True):
        diferencia = hc.get_diferencia()
        if diferencia > 0:
            servicio = hc.servicio
            grupo = _grupo_para_cargo(hc.cargo)
            for _ in range(diferencia):
                slots_por_servicio_grupo.setdefault(servicio, {}).setdefault(grupo, []).append({'cargo': hc.cargo, 'categoria': hc.categoria, 'ubicacion': hc.ubicacion})
    total_vacantes = sum(len(v) for s in slots_por_servicio_grupo.values() for v in s.values())

    context = {
        'contrato': contrato,
        'contratos_disponibles': contratos_disponibles,
        'total_trabajadores': trabajadores_qs.count(),
        'trabajadores_por_servicio_grupo': trabajadores_por_servicio_grupo,
        'slots_vacantes': slots_por_servicio_grupo,
        'total_vacantes': total_vacantes,
        # Semana
        'semana_offset': semana_offset,
        'semana_inicio': semana_inicio,
        'semana_fin': semana_fin,
        'dias_semana': dias_semana,
        'label_semana': label_semana,
        'today': date.today(),
    }

    return render(request, 'drilling/organigrama/view.html', context)


