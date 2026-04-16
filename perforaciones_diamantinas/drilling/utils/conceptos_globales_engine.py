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

ZERO = Decimal('0.00')


def _round2(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


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
    Calcula todos los conceptos globales de un contrato para un período.
    Retorna lista de ConceptoGlobalPeriodo actualizados.
    """
    from drilling.models_payroll import ConceptoGlobalPeriodo

    periodos = ConceptoGlobalPeriodo.objects.filter(
        contrato=contrato, anio=anio, mes=mes
    ).select_related('concepto')

    resultados = []
    for cgp in periodos:
        calcular_concepto_global(cgp)
        cgp.save(update_fields=['valor_calculado', 'porcentaje_bono', 'updated_at'])
        resultados.append(cgp)

    return resultados


def inicializar_conceptos_periodo(contrato, anio, mes):
    """
    Crea registros ConceptoGlobalPeriodo para todos los conceptos activos
    de un contrato en un período, si no existen.
    Retorna la cantidad de registros creados.
    """
    from drilling.models_payroll import ConceptoGlobal, ConceptoGlobalPeriodo

    conceptos = ConceptoGlobal.objects.filter(activo=True)
    creados = 0

    for concepto in conceptos:
        _, created = ConceptoGlobalPeriodo.objects.get_or_create(
            contrato=contrato,
            concepto=concepto,
            anio=anio,
            mes=mes,
        )
        if created:
            creados += 1

    return creados
