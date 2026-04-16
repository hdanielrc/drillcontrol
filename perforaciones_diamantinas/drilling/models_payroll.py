"""
Módulo de Planilla — Modelos de Bonos y Cálculo de Pagos.

Arquitectura:
- ConceptoGlobal: Indicadores globales de contrato (PRODUCCION, CXM, SEGURIDAD, etc.)
- ConceptoGlobalPeriodo: Valores calculados por contrato/período
- TipoBono: Catálogo de bonos (B1-B4 del sistema + custom)
- ConceptoBono: Sub-conceptos evaluables por bono (para MULTI_CONCEPTO)
- ConfiguracionBonoContrato: Parámetros de un bono por contrato (montos, vigencia)
- ConceptoBonoContrato: Monto por concepto dentro de una configuración
- EscalaBonoContrato: Rangos escalonados (para tipo ESCALONADO)
- PeriodoBono: Período mensual de cálculo por contrato
- BonoTrabajador: Resultado calculado por trabajador
- BonoTrabajadorDetalle: Desglose por concepto (multi-concepto)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Estados de asistencia que cuentan como "día trabajado" para bonos
ESTADOS_DIA_TRABAJADO = ('DL', 'TD', 'TN', 'DA')


class TipoBono(models.Model):
    """
    Catálogo maestro de tipos de bono.
    Los B1-B4 son del sistema (es_sistema=True, no eliminables).
    El usuario puede crear tipos adicionales.
    """
    CATEGORIA_CHOICES = [
        ('REMUNERATIVO', 'Bono Remunerativo'),
        ('EXTRAORDINARIO', 'Bono Extraordinario'),
    ]
    TIPO_CALCULO_CHOICES = [
        ('FIJO', 'Monto Fijo — (monto_mensual / días_base) × días_trabajados'),
        ('MULTI_CONCEPTO', 'Múltiples Conceptos con Puntaje (0-100)'),
        ('POR_DIA', 'Monto Directo por Día Trabajado'),
        ('ESCALONADO', 'Escalonado por Rango de Días'),
    ]

    codigo = models.CharField(max_length=20, unique=True, verbose_name='Código')
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Bono')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name='Categoría')
    tipo_calculo = models.CharField(max_length=20, choices=TIPO_CALCULO_CHOICES, verbose_name='Tipo de Cálculo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    es_sistema = models.BooleanField(default=False, help_text='Los bonos del sistema (B1-B4) no se pueden eliminar')
    activo = models.BooleanField(default=True)
    cargos_aplicables = models.JSONField(
        default=list, blank=True,
        verbose_name='Cargos Aplicables',
        help_text='Lista de patrones de cargo. Ej: ["ADMINISTRADOR", "ASISTENTE ADMINISTRATIVO"]. Vacío = todos.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payroll_tipo_bono'
        ordering = ['codigo']
        verbose_name = 'Tipo de Bono'
        verbose_name_plural = 'Tipos de Bono'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ConceptoBono(models.Model):
    """
    Conceptos evaluables dentro de un bono MULTI_CONCEPTO.
    Ej: B2 tiene 'Eficiencia' y 'Cuidado del Equipo'.
        B3 tiene 'Producción', 'Seguridad', 'Costo por Metro', etc.
    """
    tipo_bono = models.ForeignKey(TipoBono, on_delete=models.CASCADE, related_name='conceptos')
    codigo = models.CharField(max_length=30, verbose_name='Código')
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Concepto')
    es_obligatorio = models.BooleanField(default=True, verbose_name='Obligatorio')
    peso_default = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Peso Default (%)',
        help_text='Peso relativo del concepto. Los pesos del bono deben sumar 100%.'
    )
    orden = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')

    class Meta:
        db_table = 'payroll_concepto_bono'
        ordering = ['tipo_bono', 'orden']
        unique_together = [('tipo_bono', 'codigo')]
        verbose_name = 'Concepto de Bono'
        verbose_name_plural = 'Conceptos de Bono'

    def __str__(self):
        return f"{self.tipo_bono.codigo} → {self.nombre}"


class ConfiguracionBonoContrato(models.Model):
    """
    Configura un bono para un contrato específico.
    Define el monto mensual máximo y las reglas de cálculo.
    """
    contrato = models.ForeignKey(
        'Contrato', on_delete=models.CASCADE, related_name='configuraciones_bono'
    )
    tipo_bono = models.ForeignKey(TipoBono, on_delete=models.PROTECT, related_name='configuraciones')
    monto_base_mensual = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Monto Base Mensual (S/)',
        help_text='Monto máximo mensual del bono (para FIJO y MULTI_CONCEPTO)'
    )
    monto_por_dia = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name='Monto por Día (S/)',
        help_text='Solo para tipo POR_DIA'
    )
    usa_dias_regimen = models.BooleanField(
        default=True,
        verbose_name='Usar días del régimen laboral',
        help_text='Si es True, se calculan los días base según el régimen del trabajador. Si es False, usa el valor fijo.'
    )
    dias_base_fijo = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='Días Base Fijo',
        help_text='Días base fijos (solo si no usa régimen). Ej: 30'
    )
    activo = models.BooleanField(default=True)
    vigencia_desde = models.DateField(verbose_name='Vigencia Desde')
    vigencia_hasta = models.DateField(null=True, blank=True, verbose_name='Vigencia Hasta')
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_config_bono_contrato'
        ordering = ['contrato', 'tipo_bono__codigo']
        unique_together = [('contrato', 'tipo_bono')]
        verbose_name = 'Configuración de Bono por Contrato'
        verbose_name_plural = 'Configuraciones de Bono por Contrato'

    def __str__(self):
        return f"{self.contrato.nombre_contrato} — {self.tipo_bono.codigo}: S/{self.monto_base_mensual}"

    def vigente_en_fecha(self, fecha):
        if self.vigencia_desde and fecha < self.vigencia_desde:
            return False
        if self.vigencia_hasta and fecha > self.vigencia_hasta:
            return False
        return self.activo


class ConceptoBonoContrato(models.Model):
    """
    Monto asignado a cada concepto de un bono multi-concepto en un contrato.
    La suma de montos de todos los conceptos = monto_base_mensual de la configuración.
    """
    configuracion = models.ForeignKey(
        ConfiguracionBonoContrato, on_delete=models.CASCADE, related_name='conceptos_contrato'
    )
    concepto = models.ForeignKey(ConceptoBono, on_delete=models.CASCADE, related_name='configuraciones_contrato')
    monto = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Monto Máximo (S/)',
        help_text='Monto máximo por este concepto en el mes'
    )

    class Meta:
        db_table = 'payroll_concepto_bono_contrato'
        unique_together = [('configuracion', 'concepto')]
        verbose_name = 'Concepto de Bono por Contrato'
        verbose_name_plural = 'Conceptos de Bono por Contrato'

    def __str__(self):
        return f"{self.configuracion} → {self.concepto.nombre}: S/{self.monto}"


class EscalaBonoContrato(models.Model):
    """
    Rangos para bonos ESCALONADOS.
    Ej: 1-10 días = S/100, 11-20 días = S/200, 21-30 días = S/350
    """
    configuracion = models.ForeignKey(
        ConfiguracionBonoContrato, on_delete=models.CASCADE, related_name='escalas'
    )
    dias_desde = models.PositiveSmallIntegerField(verbose_name='Desde (días)')
    dias_hasta = models.PositiveSmallIntegerField(verbose_name='Hasta (días)')
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto (S/)')

    class Meta:
        db_table = 'payroll_escala_bono_contrato'
        ordering = ['configuracion', 'dias_desde']
        verbose_name = 'Escala de Bono'
        verbose_name_plural = 'Escalas de Bono'

    def __str__(self):
        return f"{self.dias_desde}-{self.dias_hasta} días → S/{self.monto}"


# =========================================
# PERÍODO Y RESULTADOS DE CÁLCULO
# =========================================

class PeriodoBono(models.Model):
    """
    Período mensual de cálculo de bonos por contrato.
    Flujo: ABIERTO → CALCULADO → APROBADO → CERRADO
    """
    ESTADO_CHOICES = [
        ('ABIERTO', 'Abierto'),
        ('CALCULADO', 'Calculado'),
        ('APROBADO', 'Aprobado'),
        ('CERRADO', 'Cerrado'),
    ]
    contrato = models.ForeignKey(
        'Contrato', on_delete=models.CASCADE, related_name='periodos_bono'
    )
    anio = models.PositiveSmallIntegerField(verbose_name='Año')
    mes = models.PositiveSmallIntegerField(
        verbose_name='Mes',
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    fecha_inicio = models.DateField(verbose_name='Fecha Inicio Período')
    fecha_fin = models.DateField(verbose_name='Fecha Fin Período')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='ABIERTO')
    calculado_por = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='periodos_bono_calculados'
    )
    calculado_at = models.DateTimeField(null=True, blank=True)
    aprobado_por = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='periodos_bono_aprobados'
    )
    aprobado_at = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_periodo_bono'
        ordering = ['-anio', '-mes']
        unique_together = [('contrato', 'anio', 'mes')]
        verbose_name = 'Período de Bonos'
        verbose_name_plural = 'Períodos de Bonos'

    def __str__(self):
        return f"{self.contrato.nombre_contrato} — {self.mes:02d}/{self.anio} ({self.estado})"


class BonoTrabajador(models.Model):
    """
    Resultado calculado de un bono para un trabajador en un período.
    """
    periodo = models.ForeignKey(PeriodoBono, on_delete=models.CASCADE, related_name='bonos')
    trabajador = models.ForeignKey('Trabajador', on_delete=models.PROTECT, related_name='bonos_calculados')
    tipo_bono = models.ForeignKey(TipoBono, on_delete=models.PROTECT, related_name='resultados')
    configuracion = models.ForeignKey(
        ConfiguracionBonoContrato, on_delete=models.SET_NULL, null=True, related_name='resultados'
    )
    bono_base = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Bono Base (S/)',
        help_text='Monto base del bono para este trabajador. Editable por usuario.'
    )
    dias_trabajados = models.PositiveSmallIntegerField(default=0, verbose_name='Días Trabajados')
    dias_base = models.PositiveSmallIntegerField(default=0, verbose_name='Días Operativos')
    factor_cumplimiento = models.DecimalField(
        max_digits=5, decimal_places=4, default=1,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Factor de Cumplimiento',
        help_text='1.0000 = 100% cumplimiento. Para FIJO siempre es 1.0'
    )
    monto_calculado = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Monto Calculado (S/)'
    )
    monto_ajuste = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Ajuste Manual (S/)',
        help_text='Monto positivo o negativo de ajuste manual'
    )
    monto_final = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Monto Final (S/)'
    )
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_bono_trabajador'
        ordering = ['periodo', 'trabajador__apepat', 'tipo_bono__codigo']
        unique_together = [('periodo', 'trabajador', 'tipo_bono')]
        verbose_name = 'Bono de Trabajador'
        verbose_name_plural = 'Bonos de Trabajadores'

    def __str__(self):
        return f"{self.trabajador} — {self.tipo_bono.codigo}: S/{self.monto_final}"


class BonoTrabajadorDetalle(models.Model):
    """
    Desglose por concepto para bonos MULTI_CONCEPTO.
    El puntaje se ingresa manualmente; el monto se calcula.
    """
    bono = models.ForeignKey(BonoTrabajador, on_delete=models.CASCADE, related_name='detalles')
    concepto = models.ForeignKey(ConceptoBono, on_delete=models.PROTECT, related_name='resultados')
    puntaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Puntaje (0-100)',
        help_text='Calificación del concepto: 0=no cumple, 100=cumplimiento total'
    )
    monto_max_concepto = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Monto Máx. Concepto (S/)'
    )
    monto_calculado = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Monto Calculado (S/)'
    )

    class Meta:
        db_table = 'payroll_bono_trabajador_detalle'
        ordering = ['bono', 'concepto__orden']
        unique_together = [('bono', 'concepto')]
        verbose_name = 'Detalle de Bono'
        verbose_name_plural = 'Detalles de Bono'

    def __str__(self):
        return f"{self.concepto.nombre}: {self.puntaje}% → S/{self.monto_calculado}"


class CriterioBono(models.Model):
    """
    Criterio individual de evaluación (checkbox) dentro de un concepto/sección.
    Cada sección (ConceptoBono) tiene múltiples criterios que se evalúan como cumple/no cumple.
    El puntaje de la sección = (criterios cumplidos / total criterios) × 100.
    """
    concepto = models.ForeignKey(ConceptoBono, on_delete=models.CASCADE, related_name='criterios')
    nombre = models.CharField(max_length=300, verbose_name='Nombre del Criterio')
    orden = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'payroll_criterio_bono'
        ordering = ['concepto', 'orden']
        verbose_name = 'Criterio de Bono'
        verbose_name_plural = 'Criterios de Bono'

    def __str__(self):
        return f"{self.concepto.nombre} → {self.nombre}"


class CalificacionCriterio(models.Model):
    """
    Calificación individual de un criterio para un trabajador.
    cumple=True = checkbox marcado, cumple=False = no marcado.
    """
    bono_trabajador = models.ForeignKey(BonoTrabajador, on_delete=models.CASCADE, related_name='calificaciones')
    criterio = models.ForeignKey(CriterioBono, on_delete=models.CASCADE, related_name='calificaciones')
    cumple = models.BooleanField(default=True, verbose_name='Cumple')

    class Meta:
        db_table = 'payroll_calificacion_criterio'
        unique_together = [('bono_trabajador', 'criterio')]
        verbose_name = 'Calificación de Criterio'
        verbose_name_plural = 'Calificaciones de Criterios'

    def __str__(self):
        return f"{self.criterio.nombre}: {'✓' if self.cumple else '✗'}"


# =========================================
# CONCEPTOS GLOBALES DE CONTRATO
# =========================================

class ConceptoGlobal(models.Model):
    """
    Catálogo de indicadores globales a nivel de contrato.
    Cada concepto tiene un código único y una lógica de cálculo asociada.
    Múltiples bonos pueden referenciar el mismo concepto global.

    Conceptos del sistema:
      PRODUCCION         — Cumplimiento de metros (acumulados vs meta)
      SEGURIDAD          — Accidentes incapacitantes
      VALORIZACION       — Eficiencia de cobro
      CXM                — Costo por metro vs meta programada
      RESULTADO_OPERATIVO — Rentabilidad del contrato
    """
    TIPO_CHOICES = [
        ('PRODUCCION', 'Producción — Cumplimiento de Metros'),
        ('SEGURIDAD', 'Seguridad — Accidentes Incapacitantes'),
        ('VALORIZACION', 'Valorización — Eficiencia de Cobro'),
        ('CXM', 'Costo por Metro — Desviación CXM'),
        ('RESULTADO_OPERATIVO', 'Resultado Operativo — Rentabilidad'),
        ('CUSTOM', 'Personalizado'),
    ]

    codigo = models.CharField(max_length=30, unique=True, verbose_name='Código')
    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name='Tipo de Cálculo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    es_sistema = models.BooleanField(default=False, help_text='Los conceptos del sistema no se pueden eliminar')
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payroll_concepto_global'
        ordering = ['orden', 'codigo']
        verbose_name = 'Concepto Global'
        verbose_name_plural = 'Conceptos Globales'

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class ConceptoGlobalPeriodo(models.Model):
    """
    Valores de un concepto global para un contrato en un período mensual.
    Almacena las entradas, el cálculo intermedio y el % de bono resultante.

    Campos de entrada por tipo:
    ─────────────────────────────────────────────────────────────────────
    PRODUCCION:
      metros_acumulados    — Total metraje acumulado (todas las máquinas)
      meta_programada      — Meta propuesta (desde control de proyectos)
      cantidad_maquinas    — Cantidad de máquinas en el contrato
    SEGURIDAD:
      accidentes_incapacitantes — Número de accidentes incapacitantes
    VALORIZACION:
      eficiencia_cobro     — % de eficiencia en el cobro
    CXM:
      total_abastecido     — Monto total $ de materiales abastecidos
      metros_acumulados    — Total metraje acumulado
      meta_cxm_programada  — Meta de costo por metro por contrato
    RESULTADO_OPERATIVO:
      rentabilidad         — % de rentabilidad del contrato
    """
    contrato = models.ForeignKey(
        'Contrato', on_delete=models.CASCADE, related_name='conceptos_globales_periodo'
    )
    concepto = models.ForeignKey(
        ConceptoGlobal, on_delete=models.CASCADE, related_name='periodos'
    )
    anio = models.PositiveSmallIntegerField(verbose_name='Año')
    mes = models.PositiveSmallIntegerField(
        verbose_name='Mes',
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )

    # --- Campos de entrada (se usan según el tipo de concepto) ---
    metros_acumulados = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Metros Acumulados',
        help_text='Total metraje acumulado por todas las máquinas del contrato'
    )
    meta_programada = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Meta Programada',
        help_text='Meta propuesta por cada máquina desde control de proyectos'
    )
    cantidad_maquinas = models.PositiveSmallIntegerField(
        default=0, verbose_name='Cantidad de Máquinas',
        help_text='Cantidad de máquinas en el contrato'
    )
    accidentes_incapacitantes = models.PositiveSmallIntegerField(
        default=0, verbose_name='Accidentes Incapacitantes'
    )
    eficiencia_cobro = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name='Eficiencia de Cobro (%)',
        help_text='Porcentaje de eficiencia en el cobro'
    )
    total_abastecido = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Total Abastecido ($)',
        help_text='Monto total de materiales abastecidos al centro de costo'
    )
    meta_cxm_programada = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Meta CXM Programada',
        help_text='Meta de costo por metro por contrato'
    )
    rentabilidad = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name='Rentabilidad (%)',
        help_text='Porcentaje de rentabilidad del contrato'
    )

    # --- Resultados calculados ---
    valor_calculado = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        verbose_name='Valor Calculado',
        help_text='Métrica intermedia (cumplimiento %, desviación %, etc.)'
    )
    porcentaje_bono = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name='% de Bono Resultante',
        help_text='Porcentaje de bono resultante según reglas (0-150%)'
    )

    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_concepto_global_periodo'
        unique_together = [('contrato', 'concepto', 'anio', 'mes')]
        ordering = ['anio', 'mes', 'concepto__orden']
        verbose_name = 'Concepto Global por Período'
        verbose_name_plural = 'Conceptos Globales por Período'

    def __str__(self):
        return f"{self.contrato} — {self.concepto.codigo} — {self.mes:02d}/{self.anio}: {self.porcentaje_bono}%"
