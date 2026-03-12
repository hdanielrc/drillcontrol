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
import unicodedata
from datetime import date, timedelta
from collections import defaultdict, OrderedDict, deque

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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
                             'LOGISTIC', 'COORDINADOR', 'INSPECTOR', 'MONITOR',
                             'TECNICO MECANICO', 'TECNICO ELECTRICISTA', 'MECANICO', 'ELECTRICISTA']):
        return 'LINEA_MANDO'
    return 'CONDUCTORES'


SERVICE_ORDER = ['DDH', 'SGEO', 'LAB']
SERVICE_DISPLAY_LABELS = {
    'DDH': 'Perforación Diamantina',
    'SGEO': 'Servicios Geológicos',
    'LAB': 'Laboratorio & Soporte',
}

CARGO_PRIORITY_SEQUENCE = [
    (1, ['JEFE DE OPERACIONES', 'JEFE OPERACIONES', 'JEFE OPERACIONAL']),
    (2, ['RESIDENTE']),
    (3, ['ADMINISTRADOR']),
    (4, ['LOGISTICO', 'LOGISTICA', 'JEFE DE LOGISTICA']),
    (5, ['ALMACEN', 'ALMACENERO']),
    (6, ['ASISTENTE ADMINISTRATIVO']),
    (7, ['ASISTENTE LOGISTICO', 'ASISTENTE LOGISTICA']),
    (8, ['INGENIERO DE SEGURIDAD', 'INGENIERO SEGURIDAD', 'INGENIERO']),
    (9, ['SUPERVISOR GENERAL']),
    (10, ['SUPERVISOR OPERATIVO']),
    (11, ['GEOLOGO DE LOGUEO', 'GEOLOGO']),
    (12, ['TOPOGRAFO']),
    (13, ['SUPERVISOR DE MUESTREO']),
    (14, ['MAESTRO MUESTRERO']),
    (15, ['MUESTRERO']),
    (16, ['AYUDANTE MUESTRERO']),
    (17, ['TECNICO MECANICO', 'TECNICO MECANICO I', 'TECNICO MECANICO II']),
    (18, ['PERFORISTA', 'PERFORISTA DDH']),
    (19, ['AYUDANTE DDH', 'AYUDANTE PERFORISTA', 'AYUDANTE']),
    (20, ['CONDUCTOR']),
]

ORG_SECTION_ORDER = [
    ('direccion', 'Línea de mando'),
    ('administracion', 'Administración y logística'),
    ('operaciones', 'Operaciones y campo'),
    ('geologia', 'Servicios geológicos y muestreo'),
    ('conduccion', 'Conducción'),
]

SECTION_KEYWORDS = [
    ('direccion', ['JEFE', 'RESIDENTE', 'INGENIERO', 'SEGURIDAD']),
    ('administracion', ['ADMINISTRADOR', 'ASISTENTE ADMINISTRATIVO', 'LOGISTICO', 'LOGISTICA', 'ALMACEN']),
    ('geologia', ['GEOLOGO', 'GEOLOGIA', 'TOPOGRAFO', 'TOPOGRAFIA', 'MUESTRERO', 'MAESTRO MUESTRERO', 'MUESTREO', 'MUESTRAS', 'QA/QC', 'QA & QC', 'LABORATORIO', 'DENSIDAD', 'GEOMECANICO']),
    ('conduccion', ['CONDUCTOR', 'CHOFER']),
    ('operaciones', ['SUPERVISOR OPERATIVO', 'SUPERVISOR GENERAL', 'PERFORISTA', 'AYUDANTE DE PERFORACION', 'AYUDANTE DDH', 'PERFORISTA SB', 'AYUDANTE SB', 'TECNICO MECANICO', 'MECANICO', 'ELECTRICISTA', 'TECNICO ELECTRICISTA']),
]

DEFAULT_SECTION_KEY = 'operaciones'

NIVEL_LABELS = dict(HeadCount.NIVEL_CHOICES)


def _normalize_text(text):
    if not text:
        return ''
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(ch for ch in normalized if not unicodedata.combining(ch)).upper()


def _cargo_priority_for_hierarchy(cargo):
    normalized = _normalize_text(cargo)
    for priority, keywords in CARGO_PRIORITY_SEQUENCE:
        for keyword in keywords:
            if keyword in normalized:
                return priority
    return max(rule[0] for rule in CARGO_PRIORITY_SEQUENCE) + 1

def _section_for_cargo(cargo):
    normalized = _normalize_text(cargo)
    for section_key, keywords in SECTION_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return section_key
    return DEFAULT_SECTION_KEY



def _normalize_service_code(servicio):
    if not servicio:
        return 'DDH'
    svc = servicio.upper()
    if svc == 'SGEOL':
        svc = 'SGEO'
    if svc in ('WDTH', 'VCR'):
        svc = 'DDH'
    if svc not in SERVICE_ORDER:
        return 'LAB'
    return svc


def _service_key_for_trabajador(trabajador):
    servicio_raw = getattr(trabajador, 'servicio', None) or getattr(trabajador, 'tipo_servicio', None)
    return _normalize_service_code(servicio_raw)

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

    trabajadores_por_servicio_cargo = defaultdict(lambda: defaultdict(deque))
    trabajador_lookup = {}
    for t in trabajadores_qs:
        worker = _build_worker_dict(t, tareo_dict, dias_semana)
        servicio_key = _service_key_for_trabajador(t)
        # Only index workers that have an explicit `cargo_headcount` assigned.
        # Workers without a headcount assignment will remain in `trabajadores_sin_headcount`.
        cargo_hc = getattr(t, 'cargo_headcount', None)
        if cargo_hc:
            cargo_key = _normalize_text(cargo_hc)
            trabajadores_por_servicio_cargo[servicio_key][cargo_key].append(worker)
        trabajador_lookup[t.id] = worker

    headcount_map = defaultdict(list)
    for hc in HeadCount.objects.filter(contrato=contrato, activo=True):
        headcount_map[hc.servicio].append(hc)

    services_layout = []
    assigned_worker_ids = set()
    total_slots = 0
    total_vacantes = 0

    ordered_services = list(dict.fromkeys(SERVICE_ORDER + list(headcount_map.keys())))
    for service_code in ordered_services:
        headcounts = headcount_map.get(service_code)
        if not headcounts:
            continue
        service_slots = []
        for hc in sorted(headcounts, key=lambda hc: (_cargo_priority_for_hierarchy(hc.cargo), hc.cargo)):
            # Skip headcount definitions that don't request any slots
            if not getattr(hc, 'cantidad_requerida', 0):
                continue
            priority = _cargo_priority_for_hierarchy(hc.cargo)
            cargo_key = _normalize_text(hc.cargo)
            available_queue = trabajadores_por_servicio_cargo.get(service_code, {}).get(cargo_key, deque())
            assigned_count = 0
            assignments = []
            for _ in range(hc.cantidad_requerida):
                if available_queue:
                    worker = available_queue.popleft()
                    assignments.append({'type': 'worker', 'worker': worker})
                    assigned_worker_ids.add(worker['obj'].id)
                    assigned_count += 1
            vacantes = hc.cantidad_requerida - assigned_count
            total_vacantes += vacantes
            total_slots += hc.cantidad_requerida
            slot = {
                'cargo': hc.cargo,
                'label': hc.get_cargo_display() or hc.cargo,
                'nivel': hc.nivel,
                'nivel_label': NIVEL_LABELS.get(hc.nivel),
                'cantidad': hc.cantidad_requerida,
                'assignments': assignments,
                'vacantes': vacantes,
                'section': _section_for_cargo(hc.cargo),
                'categoria': hc.categoria,
                'servicio': service_code,
                'priority': priority,
            }
            service_slots.append(slot)
        if not service_slots:
            continue
        sections_by_key = OrderedDict(
            (key, {'key': key, 'label': label, 'slots': []})
            for key, label in ORG_SECTION_ORDER
        )
        for slot in service_slots:
            section_bucket = sections_by_key.get(slot['section']) or sections_by_key[DEFAULT_SECTION_KEY]
            section_bucket['slots'].append(slot)
        services_layout.append({
            'code': service_code,
            'label': SERVICE_DISPLAY_LABELS.get(service_code, service_code),
            'sections': list(sections_by_key.values()),
            'total_slots': sum(slot['cantidad'] for slot in service_slots),
            'total_assigned': sum(
                1 for slot in service_slots for assignment in slot['assignments'] if assignment['type'] == 'worker'
            ),
            'total_vacantes': sum(slot['vacantes'] for slot in service_slots),
        })

    # Build groups layout (Línea de mando, Operativos, Conductores) from all services
    groups_map = OrderedDict([
        ('LINEA DE MANDO', {'key': 'LINEA DE MANDO', 'label': 'Línea de mando', 'slots': [], 'total_slots': 0, 'total_assigned': 0, 'total_vacantes': 0}),
        ('OPERATIVO', {'key': 'OPERATIVO', 'label': 'Operativos', 'maquinas': {}, 'total_slots': 0, 'total_assigned': 0, 'total_vacantes': 0}),
        ('CONDUCTORES', {'key': 'CONDUCTORES', 'label': 'Conductores', 'slots': [], 'total_slots': 0, 'total_assigned': 0, 'total_vacantes': 0}),
    ])

    for service in services_layout:
        for section in service['sections']:
            for slot in section['slots']:
                # Skip any 'direccion' slots here; they are rendered in the unified root row
                if slot.get('section') == 'direccion':
                    continue
                cat = slot.get('categoria') or 'OPERATIVO'
                if cat == 'OPERATIVO':
                    # distribute assignments by maquina
                    maq_buckets = groups_map['OPERATIVO']['maquinas']
                    for assignment in slot['assignments']:
                        w = assignment['worker']
                        maq = getattr(w['obj'], 'maquina_asignada', None)
                        maq_id = maq.id if maq else None
                        if maq_id not in maq_buckets:
                            maq_buckets[maq_id] = {'maquina': maq, 'workers': [], 'vacantes': 0}
                        maq_buckets[maq_id]['workers'].append(w)
                        groups_map['OPERATIVO']['total_assigned'] += 1
                        groups_map['OPERATIVO']['total_slots'] += 0
                    # account vacantes to a generic bucket (None)
                    if slot.get('vacantes'):
                        if None not in maq_buckets:
                            maq_buckets[None] = {'maquina': None, 'workers': [], 'vacantes': 0}
                        maq_buckets[None]['vacantes'] += slot.get('vacantes', 0)
                        groups_map['OPERATIVO']['total_vacantes'] += slot.get('vacantes', 0)
                else:
                    group = groups_map.get(cat)
                    if group is None:
                        # create on the fly for unexpected categories
                        groups_map[cat] = {'key': cat, 'label': cat.title(), 'slots': [], 'total_slots': 0, 'total_assigned': 0, 'total_vacantes': 0}
                        group = groups_map[cat]
                    group['slots'].append(slot)
                    group['total_slots'] += slot.get('cantidad', 0)
                    group['total_assigned'] += sum(1 for a in slot.get('assignments', []) if a.get('type') == 'worker')
                    group['total_vacantes'] += slot.get('vacantes', 0)

    groups_layout = list(groups_map.values())

        

    trabajadores_sin_headcount = sorted(
        [worker for wid, worker in trabajador_lookup.items() if wid not in assigned_worker_ids],
        key=lambda w: (_normalize_text(w['obj'].apepat), _normalize_text(w['obj'].nombres))
    )

    context = {
        'contrato': contrato,
        'contratos_disponibles': contratos_disponibles,
        'total_trabajadores': trabajadores_qs.count(),
        'total_headcount_slots': total_slots,
        'total_headcount_assignments': len(assigned_worker_ids),
        'total_vacantes': total_vacantes,
        'services_layout': services_layout,
        'groups_layout': groups_layout,
        # Services available in the headcount (used to render selection buttons)
        'services_present': [{'code': s['code'], 'label': s['label']} for s in services_layout],
        'org_sections': [{'key': key, 'label': label} for key, label in ORG_SECTION_ORDER],
        'trabajadores_sin_headcount': trabajadores_sin_headcount,
        # Semana
        'semana_offset': semana_offset,
        'semana_inicio': semana_inicio,
        'semana_fin': semana_fin,
        'dias_semana': dias_semana,
        'label_semana': label_semana,
        'today': date.today(),
    }

    return render(request, 'drilling/organigrama/view.html', context)


