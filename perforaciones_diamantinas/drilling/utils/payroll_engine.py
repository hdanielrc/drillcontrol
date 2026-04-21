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
    CriterioBono,
    CalificacionCriterio,
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
    MULTI_CONCEPTO con criterios:
    Para cada sección (ConceptoBono):
      - Calcula puntaje desde CalificacionCriterio: (cumplidos / total) × 100
      - monto_seccion = bono_base × peso_seccion × (puntaje/100) × (dias_trab/dias_op)
    Total = suma de secciones.
    """
    if dias_base == 0:
        return ZERO, ZERO

    bono_base = bono_trabajador.bono_base or config.monto_base_mensual
    detalles = bono_trabajador.detalles.select_related('concepto').all()
    total_monto = ZERO
    suma_puntaje_ponderado = ZERO
    suma_pesos = ZERO
    dias_factor = Decimal(dias_trabajados) / Decimal(dias_base)

    for detalle in detalles:
        concepto = detalle.concepto
        peso = concepto.peso_default / Decimal('100')  # 30 → 0.30

        # Calcular puntaje desde criterios si existen
        criterios = CriterioBono.objects.filter(concepto=concepto, activo=True)
        if criterios.exists():
            total_criterios = criterios.count()
            cumplidos = CalificacionCriterio.objects.filter(
                bono_trabajador=bono_trabajador,
                criterio__in=criterios,
                cumple=True,
            ).count()
            puntaje = Decimal(cumplidos * 100) / Decimal(total_criterios) if total_criterios > 0 else ZERO
            detalle.puntaje = _round2(puntaje)
        else:
            puntaje = detalle.puntaje  # Puntaje manual si no hay criterios

        puntaje_factor = puntaje / Decimal('100')
        monto_seccion = _round2(bono_base * peso * puntaje_factor * dias_factor)

        detalle.monto_max_concepto = _round2(bono_base * peso)
        detalle.monto_calculado = monto_seccion
        detalle.save(update_fields=['puntaje', 'monto_max_concepto', 'monto_calculado'])

        total_monto += monto_seccion
        suma_puntaje_ponderado += puntaje * peso
        suma_pesos += peso

    factor = ZERO
    if suma_pesos > 0:
        factor = _round2(suma_puntaje_ponderado / suma_pesos / Decimal('100'))

    return _round2(total_monto), factor


def generar_calificaciones_criterios(bono_trabajador):
    """
    Crea CalificacionCriterio para cada criterio activo del tipo de bono.
    Por defecto cumple=True (checkbox marcado).
    """
    conceptos = bono_trabajador.tipo_bono.conceptos.all()
    for concepto in conceptos:
        criterios = CriterioBono.objects.filter(concepto=concepto, activo=True)
        for criterio in criterios:
            CalificacionCriterio.objects.get_or_create(
                bono_trabajador=bono_trabajador,
                criterio=criterio,
                defaults={'cumple': True}
            )


def filtrar_trabajadores_por_cargo(trabajadores_qs, tipo_bono, config=None):
    """
    Filtra un queryset de trabajadores según los cargos_aplicables.
    Si se pasa una ConfiguracionBonoContrato y ésta tiene cargos_aplicables propios,
    éstos tienen precedencia sobre los del TipoBono.
    Usa coincidencia exacta para los cargos de la config (selección explícita)
    y coincidencia parcial (icontains) para los patrones del TipoBono.
    """
    # Prioridad: config.cargos_aplicables > tipo_bono.cargos_aplicables
    if config is not None and config.cargos_aplicables:
        from django.db.models import Q
        q = Q()
        for cargo in config.cargos_aplicables:
            q |= Q(cargo=cargo) | Q(cargo_headcount=cargo)
        return trabajadores_qs.filter(q)

    cargos = tipo_bono.cargos_aplicables
    if not cargos:
        return trabajadores_qs

    from django.db.models import Q
    q = Q()
    for patron in cargos:
        q |= Q(cargo__icontains=patron) | Q(cargo_headcount__icontains=patron)
    return trabajadores_qs.filter(q)


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
            # Filtrar por cargos: config.cargos_aplicables tiene prioridad
            tipo_bono = config.tipo_bono
            cargos_filter = config.cargos_aplicables if config.cargos_aplicables else tipo_bono.cargos_aplicables
            if cargos_filter:
                from django.db.models import Q
                q = Q()
                if config.cargos_aplicables:
                    # Coincidencia exacta para selección explícita en la config
                    for cargo in cargos_filter:
                        q |= Q(cargo=cargo) | Q(cargo_headcount=cargo)
                else:
                    # Coincidencia parcial para patrones del TipoBono
                    for patron in cargos_filter:
                        q |= Q(cargo__icontains=patron) | Q(cargo_headcount__icontains=patron)
                if not Trabajador.objects.filter(pk=trabajador.pk).filter(q).exists():
                    continue

            bono, bono_created = BonoTrabajador.objects.get_or_create(
                periodo=periodo,
                trabajador=trabajador,
                tipo_bono=config.tipo_bono,
                defaults={
                    'configuracion': config,
                    'bono_base': config.monto_base_mensual,
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
                # Para multi-concepto, crear detalles vacíos y calificaciones
                if config.tipo_bono.tipo_calculo == 'MULTI_CONCEPTO':
                    generar_detalles_vacios(bono, config)
                    generar_calificaciones_criterios(bono)

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
