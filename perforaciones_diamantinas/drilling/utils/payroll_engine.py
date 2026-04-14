"""
Motor de Cálculo de Bonos — Payroll Engine.

Responsabilidades:
- Contar días trabajados desde AsistenciaDiaria
- Calcular días base según régimen laboral
- Aplicar fórmulas por tipo de cálculo (FIJO, MULTI_CONCEPTO, POR_DIA, ESCALONADO)
- Generar/actualizar registros BonoTrabajador + BonoTrabajadorDetalle
"""

import calendar
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.db import transaction
from django.utils import timezone

from drilling.models import Trabajador, AsistenciaDiaria
from drilling.models_payroll import (
    ESTADOS_DIA_TRABAJADO,
    TipoBono,
    ConfiguracionBonoContrato,
    ConceptoBonoContrato,
    EscalaBonoContrato,
    PeriodoBono,
    BonoTrabajador,
    BonoTrabajadorDetalle,
)

ZERO = Decimal('0.00')
ONE = Decimal('1.0000')


def contar_dias_trabajados(trabajador, fecha_inicio, fecha_fin):
    """
    Cuenta los días con estado en ESTADOS_DIA_TRABAJADO para un trabajador
    en un rango de fechas, usando AsistenciaDiaria.
    """
    return AsistenciaDiaria.objects.filter(
        trabajador=trabajador,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
        estado__in=ESTADOS_DIA_TRABAJADO,
    ).count()


def calcular_dias_base_regimen(trabajador, fecha_inicio, fecha_fin):
    """
    Calcula los días base (días que le corresponde trabajar) en el período
    según el régimen laboral del trabajador.

    Regímenes soportados: 14x7, 20x10, 28x14, 5x2, 6x1
    Retorna el número de días de trabajo esperados en el rango.
    """
    REGIMEN_MAP = {
        '14x7': (14, 21),
        '20x10': (20, 30),
        '28x14': (28, 42),
        '5x2': (5, 7),
        '6x1': (6, 7),
    }

    regimen = trabajador.regimen_laboral
    if regimen not in REGIMEN_MAP:
        # Fallback: todos los días del período
        return (fecha_fin - fecha_inicio).days + 1

    dias_trabajo, ciclo_total = REGIMEN_MAP[regimen]
    inicio_ciclo = trabajador.fecha_inicio_ciclo

    if not inicio_ciclo:
        # Sin fecha de inicio de ciclo, usar proporción directa
        total_dias = (fecha_fin - fecha_inicio).days + 1
        return round(total_dias * dias_trabajo / ciclo_total)

    dias_base = 0
    current = fecha_inicio
    delta_one = __import__('datetime').timedelta(days=1)
    while current <= fecha_fin:
        dia_en_ciclo = (current - inicio_ciclo).days % ciclo_total
        if dia_en_ciclo < dias_trabajo:
            dias_base += 1
        current += delta_one

    return dias_base


def _round2(value):
    """Redondea a 2 decimales."""
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calcular_bono_fijo(config, dias_trabajados, dias_base):
    """
    FIJO: (monto_mensual / dias_base) × dias_trabajados
    """
    if dias_base == 0:
        return ZERO, ONE
    monto = _round2(config.monto_base_mensual * Decimal(dias_trabajados) / Decimal(dias_base))
    return monto, ONE


def calcular_bono_por_dia(config, dias_trabajados):
    """
    POR_DIA: monto_por_dia × dias_trabajados
    """
    monto = _round2(config.monto_por_dia * Decimal(dias_trabajados))
    return monto, ONE


def calcular_bono_escalonado(config, dias_trabajados):
    """
    ESCALONADO: busca el rango que contiene los días trabajados y retorna el monto.
    """
    escalas = EscalaBonoContrato.objects.filter(configuracion=config).order_by('dias_desde')
    for escala in escalas:
        if escala.dias_desde <= dias_trabajados <= escala.dias_hasta:
            return _round2(escala.monto), ONE
    return ZERO, ONE


def calcular_bono_multi_concepto(bono_trabajador, config, dias_trabajados, dias_base):
    """
    MULTI_CONCEPTO:
    Para cada concepto: monto_concepto × (puntaje/100) × (dias_trabajados/dias_base)
    Total = suma de conceptos.
    Factor = promedio ponderado de puntajes.

    Requiere que BonoTrabajadorDetalle ya exista con puntajes ingresados.
    """
    if dias_base == 0:
        return ZERO, ZERO

    detalles = bono_trabajador.detalles.select_related('concepto').all()
    total_monto = ZERO
    suma_puntaje_ponderado = ZERO
    suma_pesos = ZERO

    for detalle in detalles:
        concepto_contrato = ConceptoBonoContrato.objects.filter(
            configuracion=config,
            concepto=detalle.concepto,
        ).first()

        if not concepto_contrato:
            continue

        monto_max = concepto_contrato.monto
        puntaje_factor = detalle.puntaje / Decimal('100')
        dias_factor = Decimal(dias_trabajados) / Decimal(dias_base)

        monto_concepto = _round2(monto_max * puntaje_factor * dias_factor)
        detalle.monto_max_concepto = monto_max
        detalle.monto_calculado = monto_concepto
        detalle.save(update_fields=['monto_max_concepto', 'monto_calculado'])

        total_monto += monto_concepto

        peso = detalle.concepto.peso_default or Decimal('1')
        suma_puntaje_ponderado += detalle.puntaje * peso
        suma_pesos += peso

    factor = ZERO
    if suma_pesos > 0:
        factor = _round2(suma_puntaje_ponderado / suma_pesos / Decimal('100'))

    return _round2(total_monto), factor


def generar_detalles_vacios(bono_trabajador, config):
    """
    Crea BonoTrabajadorDetalle vacíos (puntaje=0) para cada concepto
    del bono multi-concepto, listos para que el usuario ingrese puntajes.
    """
    conceptos_contrato = ConceptoBonoContrato.objects.filter(
        configuracion=config
    ).select_related('concepto')

    for cc in conceptos_contrato:
        BonoTrabajadorDetalle.objects.get_or_create(
            bono=bono_trabajador,
            concepto=cc.concepto,
            defaults={
                'puntaje': 0,
                'monto_max_concepto': cc.monto,
                'monto_calculado': ZERO,
            }
        )


@transaction.atomic
def abrir_periodo(contrato, anio, mes, usuario=None):
    """
    Abre un período de bonos para un contrato.
    Crea los registros BonoTrabajador vacíos para cada trabajador activo
    y cada bono configurado en el contrato.
    """
    _, ultimo_dia = calendar.monthrange(anio, mes)
    fecha_inicio = date(anio, mes, 1)
    fecha_fin = date(anio, mes, ultimo_dia)

    periodo, created = PeriodoBono.objects.get_or_create(
        contrato=contrato,
        anio=anio,
        mes=mes,
        defaults={
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'estado': 'ABIERTO',
        }
    )

    if not created and periodo.estado != 'ABIERTO':
        raise ValueError(f"El período {mes:02d}/{anio} ya está en estado {periodo.estado}")

    # Obtener trabajadores activos del contrato
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO',
    )

    # Obtener configuraciones de bonos activas para esta fecha
    configs = ConfiguracionBonoContrato.objects.filter(
        contrato=contrato,
        activo=True,
        tipo_bono__activo=True,
    ).select_related('tipo_bono')

    configs_vigentes = [c for c in configs if c.vigente_en_fecha(fecha_inicio)]

    registros_creados = 0
    for trabajador in trabajadores:
        for config in configs_vigentes:
            bono, bono_created = BonoTrabajador.objects.get_or_create(
                periodo=periodo,
                trabajador=trabajador,
                tipo_bono=config.tipo_bono,
                defaults={
                    'configuracion': config,
                    'dias_trabajados': 0,
                    'dias_base': 0,
                    'factor_cumplimiento': ONE,
                    'monto_calculado': ZERO,
                    'monto_ajuste': ZERO,
                    'monto_final': ZERO,
                }
            )
            if bono_created:
                registros_creados += 1
                # Para multi-concepto, crear detalles vacíos
                if config.tipo_bono.tipo_calculo == 'MULTI_CONCEPTO':
                    generar_detalles_vacios(bono, config)

    return periodo, registros_creados


@transaction.atomic
def calcular_periodo(periodo, usuario=None):
    """
    Ejecuta el cálculo masivo de todos los bonos de un período.
    Requiere que los puntajes de MULTI_CONCEPTO estén ingresados.
    """
    if periodo.estado == 'CERRADO':
        raise ValueError("No se puede recalcular un período cerrado.")

    bonos = BonoTrabajador.objects.filter(
        periodo=periodo
    ).select_related('trabajador', 'tipo_bono', 'configuracion')

    for bono in bonos:
        config = bono.configuracion
        if not config:
            continue

        trabajador = bono.trabajador
        tipo = config.tipo_bono.tipo_calculo

        # 1. Contar días trabajados
        dias_trabajados = contar_dias_trabajados(
            trabajador, periodo.fecha_inicio, periodo.fecha_fin
        )

        # 2. Calcular días base
        if config.usa_dias_regimen:
            dias_base = calcular_dias_base_regimen(
                trabajador, periodo.fecha_inicio, periodo.fecha_fin
            )
        else:
            dias_base = config.dias_base_fijo or 30

        bono.dias_trabajados = dias_trabajados
        bono.dias_base = dias_base

        # 3. Calcular según tipo
        if tipo == 'FIJO':
            monto, factor = calcular_bono_fijo(config, dias_trabajados, dias_base)
        elif tipo == 'POR_DIA':
            monto, factor = calcular_bono_por_dia(config, dias_trabajados)
        elif tipo == 'ESCALONADO':
            monto, factor = calcular_bono_escalonado(config, dias_trabajados)
        elif tipo == 'MULTI_CONCEPTO':
            monto, factor = calcular_bono_multi_concepto(
                bono, config, dias_trabajados, dias_base
            )
        else:
            monto, factor = ZERO, ONE

        bono.factor_cumplimiento = factor
        bono.monto_calculado = monto
        bono.monto_final = _round2(monto + bono.monto_ajuste)
        bono.save()

    periodo.estado = 'CALCULADO'
    periodo.calculado_por = usuario
    periodo.calculado_at = timezone.now()
    periodo.save(update_fields=['estado', 'calculado_por', 'calculado_at', 'updated_at'])

    return periodo


@transaction.atomic
def aprobar_periodo(periodo, usuario):
    """Marca el período como aprobado."""
    if periodo.estado not in ('CALCULADO', 'APROBADO'):
        raise ValueError(f"Solo se puede aprobar un período calculado. Estado actual: {periodo.estado}")
    periodo.estado = 'APROBADO'
    periodo.aprobado_por = usuario
    periodo.aprobado_at = timezone.now()
    periodo.save(update_fields=['estado', 'aprobado_por', 'aprobado_at', 'updated_at'])
    return periodo


@transaction.atomic
def cerrar_periodo(periodo):
    """Cierra definitivamente el período. No se puede reabrir."""
    if periodo.estado != 'APROBADO':
        raise ValueError(f"Solo se puede cerrar un período aprobado. Estado actual: {periodo.estado}")
    periodo.estado = 'CERRADO'
    periodo.save(update_fields=['estado', 'updated_at'])
    return periodo


def resumen_periodo(periodo):
    """
    Retorna un diccionario con estadísticas del período.
    """
    bonos = BonoTrabajador.objects.filter(periodo=periodo)
    total_trabajadores = bonos.values('trabajador').distinct().count()
    total_bonos = bonos.count()

    from django.db.models import Sum
    por_tipo = bonos.values(
        'tipo_bono__codigo', 'tipo_bono__nombre', 'tipo_bono__categoria'
    ).annotate(
        total_monto=Sum('monto_final'),
        cantidad=__import__('django').db.models.Count('id'),
    ).order_by('tipo_bono__codigo')

    total_remunerativo = bonos.filter(
        tipo_bono__categoria='REMUNERATIVO'
    ).aggregate(total=Sum('monto_final'))['total'] or ZERO

    total_extraordinario = bonos.filter(
        tipo_bono__categoria='EXTRAORDINARIO'
    ).aggregate(total=Sum('monto_final'))['total'] or ZERO

    return {
        'periodo': periodo,
        'total_trabajadores': total_trabajadores,
        'total_bonos': total_bonos,
        'por_tipo': list(por_tipo),
        'total_remunerativo': total_remunerativo,
        'total_extraordinario': total_extraordinario,
        'total_general': total_remunerativo + total_extraordinario,
    }
