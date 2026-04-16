"""
Motor de Cálculo de Conceptos Globales.

Calcula los indicadores a nivel de contrato por período, que luego son
usados por diversos bonos (Bono por Cumplimiento, etc.).

Reglas de negocio (desde cuadro de bonos):
─────────────────────────────────────────────────────────────────────────
PRODUCCION (40%):
  cumplimiento = metros_acumulados / meta_programada
  Hasta 2 máquinas:
    80% - 87.5%   → 50%
    87.5% - 95%   → 75%
    95% - 100%    → 100%
    100%+         → 100%
  3+ máquinas:
    80% - 87.5%   → 50%
    87.5% - 95%   → 75%
    95% - 100%    → 100%
    100%+         → 150%

SEGURIDAD (15%):
  0 accidentes incapacitantes → 100%
  1+ accidentes              → 0%

VALORIZACION (10%):
  cobro >= 99.7%  → 100%
  cobro < 99.7%   → 0%

CXM - Costo por Metro (20%):
  costo_por_metro = total_abastecido / metros_acumulados
  desviacion % = (costo_por_metro - meta_cxm) / meta_cxm
  desviación <= 0%    → 100%
  desviación 0%-10%   → 70%
  desviación 11%-15%  → 50%
  desviación > 15%    → 0%

RESULTADO OPERATIVO (10%):
  rentabilidad >= 25% → 100%
  rentabilidad < 25%  → 0%
─────────────────────────────────────────────────────────────────────────
"""

from decimal import Decimal, ROUND_HALF_UP

from .periodo_operativo import get_rango_mes_operativo  # noqa: F401 — re-export

ZERO = Decimal('0.00')


def _round2(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# ======================================================================
# AUTO-CARGA DE DATOS DESDE SISTEMA
# ======================================================================

def cargar_metros_acumulados(contrato, fecha_inicio, fecha_fin):
    """
    Total de metros perforados (TurnoAvance) para un contrato
    en el rango del mes operativo. Solo turnos COMPLETADO/APROBADO.
    """
    from django.db.models import Sum
    from drilling.models import TurnoAvance

    resultado = TurnoAvance.objects.filter(
        turno__contrato=contrato,
        turno__fecha__gte=fecha_inicio,
        turno__fecha__lte=fecha_fin,
        turno__estado__in=['COMPLETADO', 'APROBADO'],
    ).aggregate(total=Sum('metros_perforados'))

    return resultado['total'] or Decimal('0')


def cargar_meta_programada(contrato, anio, mes):
    """
    Calcula la META PROGRAMADA (PROG.FINAL) para un contrato.

    Usa ProgramacionMes + MetaTurno (la misma lógica que /gerencia/programacion/).
    PROG.FINAL = suma de celdas activas del calendario:
      - Cada día tiene 2 celdas (TD y TN)
      - Valor por defecto de cada celda = meta_metros / 30 / 2
      - MetaTurno puede sobreescribir celdas individuales
      - Solo se suman días donde fecha >= dia_inicio de la máquina
    """
    from collections import defaultdict
    from datetime import timedelta

    from drilling.models import Maquina, ProgramacionMes, MetaTurno, TipoTurno

    fecha_inicio, fecha_fin = get_rango_mes_operativo(anio, mes)
    cantidad_dias = (fecha_fin - fecha_inicio).days + 1

    # Máquinas operativas del contrato
    maquinas_ids = list(
        Maquina.objects.filter(contrato=contrato, estado='OPERATIVO')
        .values_list('id', flat=True)
    )
    if not maquinas_ids:
        return Decimal('0')

    # Programaciones del período para estas máquinas
    progs = ProgramacionMes.objects.filter(
        maquina_id__in=maquinas_ids, año=anio, mes=mes
    )
    prog_dict = {p.maquina_id: p for p in progs}

    if not prog_dict:
        return Decimal('0')

    # Clasificar TipoTurno en TD (día) y TN (noche) — misma lógica que views_gerencia
    tipos_turno_all = list(TipoTurno.objects.values('id', 'nombre').order_by('nombre'))
    td_ids = {t['id'] for t in tipos_turno_all
              if any(kw in t['nombre'].lower() for kw in ['día', 'dia', 'diurno', ' td', 'td '])}
    tn_ids = {t['id'] for t in tipos_turno_all
              if any(kw in t['nombre'].lower() for kw in ['noche', 'nocturno', ' tn', 'tn '])}
    if not td_ids and not tn_ids and tipos_turno_all:
        td_ids = {tipos_turno_all[0]['id']}
        tn_ids = {t['id'] for t in tipos_turno_all[1:]}

    tipo_td_id = next(iter(td_ids), None)
    tipo_tn_id = next(iter(tn_ids), None)

    # Overrides de MetaTurno para el período
    mt_qs = MetaTurno.objects.filter(
        maquina_id__in=list(prog_dict.keys()),
        fecha__range=[fecha_inicio, fecha_fin],
    ).values('maquina_id', 'fecha', 'tipo_turno_id', 'meta_metros')

    mt_dict = defaultdict(lambda: defaultdict(dict))
    for mt in mt_qs:
        mt_dict[mt['maquina_id']][mt['fecha']][mt['tipo_turno_id']] = float(mt['meta_metros'])

    # Calcular PROG.FINAL por máquina y sumar
    total_prog_final = Decimal('0')

    for maq_id, prog in prog_dict.items():
        meta = float(prog.meta_metros)
        if not meta:
            continue

        meta_turno = meta / 30 / 2  # valor por defecto de cada celda
        dia_ini = prog.dia_inicio
        prog_final_maq = 0.0

        for offset in range(cantidad_dias):
            fecha_dia = fecha_inicio + timedelta(days=offset)
            activo = (dia_ini is None) or (fecha_dia >= dia_ini)
            if not activo:
                continue

            overrides_dia = mt_dict[maq_id].get(fecha_dia, {})
            val_td = overrides_dia.get(tipo_td_id, meta_turno)
            val_tn = overrides_dia.get(tipo_tn_id, meta_turno)
            prog_final_maq += val_td + val_tn

        total_prog_final += Decimal(str(round(prog_final_maq, 2)))

    return total_prog_final


def cargar_cantidad_maquinas(contrato):
    """
    Cantidad de máquinas OPERATIVAS en el contrato.
    """
    from drilling.models import Maquina
    return Maquina.objects.filter(
        contrato=contrato,
        estado='OPERATIVO',
    ).count()


def auto_cargar_datos_produccion(cgp, anio, mes):
    """
    Autocarga metros_acumulados, meta_programada y cantidad_maquinas
    para un ConceptoGlobalPeriodo de tipo PRODUCCION.
    Retorna True si se actualizó algo.
    """
    fecha_inicio, fecha_fin = get_rango_mes_operativo(anio, mes)
    contrato = cgp.contrato

    metros = cargar_metros_acumulados(contrato, fecha_inicio, fecha_fin)
    meta = cargar_meta_programada(contrato, anio, mes)
    maquinas = cargar_cantidad_maquinas(contrato)

    cgp.metros_acumulados = metros
    cgp.meta_programada = meta
    cgp.cantidad_maquinas = maquinas
    return True


def auto_cargar_datos_cxm(cgp, anio, mes):
    """
    Autocarga metros_acumulados para CXM (mismo dato que producción).
    total_abastecido y meta_cxm_programada se cargan manualmente.
    """
    fecha_inicio, fecha_fin = get_rango_mes_operativo(anio, mes)
    cgp.metros_acumulados = cargar_metros_acumulados(cgp.contrato, fecha_inicio, fecha_fin)
    return True


def _round4(value):
    return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


# ======================================================================
# PRODUCCIÓN
# ======================================================================

def calcular_produccion(metros_acumulados, meta_programada, cantidad_maquinas):
    """
    Calcula el % de bono por producción.

    Returns:
        (cumplimiento_decimal, porcentaje_bono)
        Ej: (Decimal('0.9200'), Decimal('75.00'))
    """
    if not meta_programada or meta_programada <= 0:
        return ZERO, ZERO

    cumplimiento = _round4(Decimal(str(metros_acumulados)) / Decimal(str(meta_programada)))
    cumplimiento_pct = cumplimiento * Decimal('100')

    muchas_maquinas = int(cantidad_maquinas) >= 3

    if cumplimiento_pct >= Decimal('100'):
        porcentaje = Decimal('150') if muchas_maquinas else Decimal('100')
    elif cumplimiento_pct >= Decimal('95'):
        porcentaje = Decimal('100')
    elif cumplimiento_pct >= Decimal('87.5'):
        porcentaje = Decimal('75')
    elif cumplimiento_pct >= Decimal('80'):
        porcentaje = Decimal('50')
    else:
        porcentaje = ZERO

    return cumplimiento, porcentaje


# ======================================================================
# SEGURIDAD
# ======================================================================

def calcular_seguridad(accidentes_incapacitantes):
    """
    0 accidentes → 100%, 1+ → 0%.

    Returns:
        (accidentes, porcentaje_bono)
    """
    accidentes = int(accidentes_incapacitantes)
    porcentaje = Decimal('100') if accidentes == 0 else ZERO
    return Decimal(str(accidentes)), porcentaje


# ======================================================================
# VALORIZACIÓN
# ======================================================================

def calcular_valorizacion(eficiencia_cobro):
    """
    Cobro >= 99.7% → 100%, < 99.7% → 0%.

    Returns:
        (eficiencia_decimal, porcentaje_bono)
    """
    eficiencia = Decimal(str(eficiencia_cobro))
    porcentaje = Decimal('100') if eficiencia >= Decimal('99.7') else ZERO
    return eficiencia, porcentaje


# ======================================================================
# CXM — COSTO POR METRO
# ======================================================================

def calcular_cxm(total_abastecido, metros_acumulados, meta_cxm_programada):
    """
    costo_por_metro = total_abastecido / metros_acumulados
    desviación % = (costo_por_metro - meta_cxm) / meta_cxm

    Desviación <= 0%    → 100%
    Desviación 0%-10%   → 70%
    Desviación 11%-15%  → 50%
    Desviación > 15%    → 0%

    Returns:
        (desviacion_decimal, porcentaje_bono)
    """
    total = Decimal(str(total_abastecido))
    metros = Decimal(str(metros_acumulados))
    meta = Decimal(str(meta_cxm_programada))

    if metros <= 0 or meta <= 0:
        return ZERO, ZERO

    costo_por_metro = _round2(total / metros)
    desviacion = _round4((costo_por_metro - meta) / meta * Decimal('100'))

    if desviacion <= ZERO:
        porcentaje = Decimal('100')
    elif desviacion <= Decimal('10'):
        porcentaje = Decimal('70')
    elif desviacion <= Decimal('15'):
        porcentaje = Decimal('50')
    else:
        porcentaje = ZERO

    return desviacion, porcentaje


# ======================================================================
# RESULTADO OPERATIVO
# ======================================================================

def calcular_resultado_operativo(rentabilidad):
    """
    Rentabilidad >= 25% → 100%, < 25% → 0%.

    Returns:
        (rentabilidad_decimal, porcentaje_bono)
    """
    rent = Decimal(str(rentabilidad))
    porcentaje = Decimal('100') if rent >= Decimal('25') else ZERO
    return rent, porcentaje


# ======================================================================
# DISPATCHER — Calcula un ConceptoGlobalPeriodo según su tipo
# ======================================================================

CALCULADORES = {
    'PRODUCCION': lambda cgp: calcular_produccion(
        cgp.metros_acumulados, cgp.meta_programada, cgp.cantidad_maquinas
    ),
    'SEGURIDAD': lambda cgp: calcular_seguridad(
        cgp.accidentes_incapacitantes
    ),
    'VALORIZACION': lambda cgp: calcular_valorizacion(
        cgp.eficiencia_cobro
    ),
    'CXM': lambda cgp: calcular_cxm(
        cgp.total_abastecido, cgp.metros_acumulados, cgp.meta_cxm_programada
    ),
    'RESULTADO_OPERATIVO': lambda cgp: calcular_resultado_operativo(
        cgp.rentabilidad
    ),
}


def calcular_concepto_global(concepto_global_periodo):
    """
    Calcula valor_calculado y porcentaje_bono de un ConceptoGlobalPeriodo
    según el tipo de su concepto.
    Guarda el resultado en la instancia (sin hacer save).

    Returns:
        (valor_calculado, porcentaje_bono)
    """
    tipo = concepto_global_periodo.concepto.tipo
    calculador = CALCULADORES.get(tipo)

    if calculador is None:
        return ZERO, ZERO

    valor, porcentaje = calculador(concepto_global_periodo)
    concepto_global_periodo.valor_calculado = valor
    concepto_global_periodo.porcentaje_bono = porcentaje
    return valor, porcentaje


def calcular_todos_conceptos_contrato(contrato, anio, mes):
    """
    Auto-carga datos del sistema + calcula todos los conceptos globales
    de un contrato para un período.
    Retorna lista de ConceptoGlobalPeriodo actualizados.
    """
    from drilling.models_payroll import ConceptoGlobalPeriodo

    periodos = ConceptoGlobalPeriodo.objects.filter(
        contrato=contrato, anio=anio, mes=mes
    ).select_related('concepto')

    resultados = []
    for cgp in periodos:
        # Auto-cargar datos del sistema según tipo
        _auto_cargar_datos(cgp, anio, mes)
        # Calcular
        calcular_concepto_global(cgp)
        cgp.save()
        resultados.append(cgp)

    return resultados


def _auto_cargar_datos(cgp, anio, mes):
    """Carga automática de datos según el tipo de concepto."""
    tipo = cgp.concepto.tipo
    if tipo == 'PRODUCCION':
        auto_cargar_datos_produccion(cgp, anio, mes)
    elif tipo == 'CXM':
        auto_cargar_datos_cxm(cgp, anio, mes)


def inicializar_conceptos_periodo(contrato, anio, mes):
    """
    Crea registros ConceptoGlobalPeriodo para todos los conceptos activos
    de un contrato en un período, si no existen.
    Auto-carga datos del sistema para conceptos nuevos.
    Retorna la cantidad de registros creados.
    """
    from drilling.models_payroll import ConceptoGlobal, ConceptoGlobalPeriodo

    conceptos = ConceptoGlobal.objects.filter(activo=True)
    creados = 0

    for concepto in conceptos:
        cgp, created = ConceptoGlobalPeriodo.objects.get_or_create(
            contrato=contrato,
            concepto=concepto,
            anio=anio,
            mes=mes,
        )
        if created:
            creados += 1
            # Auto-cargar datos del sistema
            _auto_cargar_datos(cgp, anio, mes)
            calcular_concepto_global(cgp)
            cgp.save()

    return creados
