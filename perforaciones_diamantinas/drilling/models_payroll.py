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
- EstructuraSalarial: Estructura salarial por contrato/CTR/cargo
- HistorialEstructuraSalarial: Historial de versiones de estructura salarial
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Estados de asistencia que cuentan como "día trabajado" para bonos
# Estados de AsistenciaDiaria que cuentan como día trabajado
# Incluye formas cortas (TD, TN, DL, DA) Y formas largas (TRABAJO_DIA, DIA_LIBRE, etc.)
# Fórmula: TRABAJADO = TD + TN + DL + DA  (mes calendario 1-30)
ESTADOS_DIA_TRABAJADO = (
    'TD', 'TRABAJO_DIA',
    'TN', 'TRABAJO_NOCHE',
    'T',  'TRABAJADO', 'TRABAJO',
    'DL', 'DIA_LIBRE', 'DESCANSO',
    'DA', 'DIA_APOYO', 'DA1',
)


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

    TABLA_CALIFICACION_CHOICES = [
        ('', 'Criterios (checkboxes)'),
        ('INCIDENCIAS', 'Tabla de Incidencias (0 / 1-2 / 3-4 / ≥5)'),
        ('PRODUCCION_META', 'Tabla Producción vs Meta (≥95% / 90-94% / 85-89% / ≤84%)'),
    ]
    tabla_calificacion = models.CharField(
        max_length=20,
        choices=TABLA_CALIFICACION_CHOICES,
        blank=True,
        default='',
        verbose_name='Tabla de Calificación',
        help_text='Si se establece, muestra un desplegable de calificación fija en lugar de checkboxes.',
    )

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
    cargos_aplicables = models.JSONField(
        default=list, blank=True,
        verbose_name='Cargos Aplicables',
        help_text='Lista de cargos a los que aplica este bono en este contrato. Vacío = todos los del tipo de bono.'
    )
    montos_por_cargo = models.JSONField(
        default=dict, blank=True,
        verbose_name='Montos por Cargo',
        help_text='Monto base mensual específico por cargo. Ej: {"RESIDENTE": 1500.00, "ASISTENTE DE RESIDENTE": 800.00}. Sobreescribe monto_base_mensual para ese cargo.'
    )
    tipo_calculo_por_trabajador = models.JSONField(
        default=dict, blank=True,
        verbose_name='Tipo de Cálculo por Trabajador',
        help_text=(
            'DNI → "metraje" | "cumplimiento". '
            'Ej: {"12345678": "metraje"}. '
            'Vacío o sin clave = trabajador calcula por cumplimiento KPI (lógica normal).'
        )
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
    metraje_acumulado = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        verbose_name='Metraje Acumulado (m)',
        help_text='Metros perforados acumulados en el período. Solo para trabajadores de tipo metraje.'
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

    def registrar_historial(self, fuente='CALCULO', usuario=None, observacion=''):
        """Crea un snapshot auditable del estado actual de monto_final."""
        HistorialBonoTrabajador.objects.create(
            bono_trabajador=self,
            periodo=self.periodo,
            trabajador=self.trabajador,
            tipo_bono=self.tipo_bono,
            monto_calculado=self.monto_calculado,
            monto_ajuste=self.monto_ajuste,
            monto_final=self.monto_final,
            dias_trabajados=self.dias_trabajados,
            dias_base=self.dias_base,
            fuente=fuente,
            registrado_por=usuario,
            observacion=observacion,
        )


class HistorialBonoTrabajador(models.Model):
    """
    Registro histórico auditable de cada vez que se recalcula o guarda
    el monto_final de un BonoTrabajador.
    Permite rastrear quién calculó, cuándo y qué valor resultó.
    """
    FUENTE_CHOICES = [
        ('CALCULO',  'Cálculo automático (vista cuadro)'),
        ('GUARDAR',  'Guardado manual por usuario'),
        ('RECALC',   'Recalcular (botón)'),
        ('API',      'API / importación'),
    ]

    bono_trabajador = models.ForeignKey(
        BonoTrabajador, on_delete=models.CASCADE,
        related_name='historial',
        verbose_name='Bono Trabajador'
    )
    # Snapshot de relaciones (para no perder referencia si se borra el período)
    periodo = models.ForeignKey(
        'PeriodoBono', on_delete=models.SET_NULL, null=True,
        related_name='+', verbose_name='Período'
    )
    trabajador = models.ForeignKey(
        'Trabajador', on_delete=models.SET_NULL, null=True,
        related_name='+', verbose_name='Trabajador'
    )
    tipo_bono = models.ForeignKey(
        'TipoBono', on_delete=models.SET_NULL, null=True,
        related_name='+', verbose_name='Tipo de Bono'
    )

    # Snapshot de valores
    monto_calculado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto Calculado (S/)')
    monto_ajuste    = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Ajuste Manual (S/)')
    monto_final     = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto Final (S/)')
    dias_trabajados = models.PositiveSmallIntegerField(default=0, verbose_name='Días Trabajados')
    dias_base       = models.PositiveSmallIntegerField(default=0, verbose_name='Días Operativos')

    # Auditoría
    fuente          = models.CharField(max_length=10, choices=FUENTE_CHOICES, default='CALCULO', verbose_name='Fuente')
    registrado_por  = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='historial_bonos_registrados',
        verbose_name='Registrado por'
    )
    observacion     = models.TextField(blank=True, verbose_name='Observación')
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')

    class Meta:
        db_table  = 'payroll_historial_bono_trabajador'
        ordering  = ['-created_at']
        verbose_name = 'Historial Bono Trabajador'
        verbose_name_plural = 'Historial Bonos Trabajadores'
        indexes = [
            models.Index(fields=['bono_trabajador', '-created_at']),
            models.Index(fields=['trabajador', 'tipo_bono', '-created_at']),
            models.Index(fields=['periodo', 'tipo_bono']),
        ]

    def __str__(self):
        trab = self.trabajador or '—'
        bono = self.tipo_bono.codigo if self.tipo_bono else '—'
        return f"{trab} | {bono} | S/{self.monto_final} | {self.created_at:%d/%m/%Y %H:%M}"


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


# =============================================================================
# ESTRUCTURA SALARIAL POR CONTRATO / CTR / CARGO
# =============================================================================

class EstructuraSalarial(models.Model):
    """
    Estructura salarial vigente por Contrato + CTR (centro de costo) + Cargo contratado.
    Define los componentes salariales para cada combinación única.
    Cada modificación genera un registro en HistorialEstructuraSalarial.
    """
    contrato = models.ForeignKey(
        'Contrato', on_delete=models.CASCADE,
        related_name='estructuras_salariales',
        verbose_name='Contrato'
    )
    contrato_servicio = models.ForeignKey(
        'ContratoServicio', on_delete=models.CASCADE,
        related_name='estructuras_salariales',
        verbose_name='CTR (Centro de Costo)',
        help_text='Centro de costo / servicio del contrato'
    )
    cargo_contratado = models.CharField(
        max_length=200,
        verbose_name='Cargo Contratado',
        help_text='Nombre del cargo (debe coincidir con el campo cargo del Trabajador)'
    )
    maquina = models.ForeignKey(
        'Maquina', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='estructuras_salariales',
        verbose_name='Máquina',
        help_text='Máquina específica a la que aplica esta estructura. Dejar vacío para aplicar a todas.'
    )

    # --- Componentes Salariales ---
    sueldo_basico = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Sueldo Básico (S/)',
        help_text='Sueldo base mensual para este cargo'
    )
    bono_por_metraje = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Bono por Metraje (S/)',
        help_text='Monto del bono por cumplimiento de metraje'
    )
    metraje_base = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Metraje Base (m)',
        help_text='Metraje base requerido para acceder al bono por metraje'
    )
    bonificacion_area = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Bonificación Área (S/)',
        help_text='Bonificación adicional por zona o área de trabajo'
    )

    # --- Control ---
    version = models.PositiveIntegerField(
        default=1,
        verbose_name='Versión',
        help_text='Número de versión actual (se incrementa en cada cambio)'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    creado_por = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='estructuras_salariales_creadas',
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_estructura_salarial'
        ordering = ['contrato__nombre_contrato', 'contrato_servicio__tipo_servicio', 'cargo_contratado', 'maquina__nombre']
        verbose_name = 'Estructura Salarial'
        verbose_name_plural = 'Estructuras Salariales'
        indexes = [
            models.Index(fields=['contrato', 'activo']),
            models.Index(fields=['cargo_contratado']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['contrato', 'contrato_servicio', 'cargo_contratado'],
                condition=models.Q(maquina__isnull=True),
                name='unique_estructura_sin_maquina',
            ),
            models.UniqueConstraint(
                fields=['contrato', 'contrato_servicio', 'cargo_contratado', 'maquina'],
                condition=models.Q(maquina__isnull=False),
                name='unique_estructura_con_maquina',
            ),
        ]

    def __str__(self):
        ctr = self.contrato_servicio.codigo_centro_costo if self.contrato_servicio else '—'
        maq = f' | Máq:{self.maquina.nombre}' if self.maquina_id else ''
        return f"{self.contrato} | CTR:{ctr} | {self.cargo_contratado}{maq} (v{self.version})"

    def validate_constraints(self, exclude=None):
        """Evita falsos positivos: solo valida cada UniqueConstraint condicional
        cuando la instancia cumple la condición del constraint."""
        from django.core.exceptions import ValidationError
        for constraint in self._meta.constraints:
            name = getattr(constraint, 'name', '')
            # unique_estructura_sin_maquina solo aplica a estructuras SIN máquina
            if name == 'unique_estructura_sin_maquina' and self.maquina_id is not None:
                continue
            # unique_estructura_con_maquina solo aplica a estructuras CON máquina
            if name == 'unique_estructura_con_maquina' and self.maquina_id is None:
                continue
            try:
                constraint.validate(self.__class__, self, exclude=exclude, using=self._state.db)
            except ValidationError as exc:
                raise exc

    def guardar_historial(self, usuario=None, motivo=''):
        """Crea un snapshot del estado actual antes de modificar."""
        HistorialEstructuraSalarial.objects.create(
            estructura=self,
            version=self.version,
            sueldo_basico=self.sueldo_basico,
            bono_por_metraje=self.bono_por_metraje,
            metraje_base=self.metraje_base,
            bonificacion_area=self.bonificacion_area,
            modificado_por=usuario,
            motivo_cambio=motivo,
        )


class HistorialEstructuraSalarial(models.Model):
    """
    Registro histórico de cada versión de una estructura salarial.
    Se crea automáticamente cada vez que se modifica una EstructuraSalarial.
    """
    estructura = models.ForeignKey(
        EstructuraSalarial, on_delete=models.CASCADE,
        related_name='historial',
        verbose_name='Estructura Salarial'
    )
    version = models.PositiveIntegerField(verbose_name='Versión')

    # --- Snapshot de los valores en esta versión ---
    sueldo_basico = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Sueldo Básico (S/)'
    )
    bono_por_metraje = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Bono por Metraje (S/)'
    )
    metraje_base = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Metraje Base (m)'
    )
    bonificacion_area = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Bonificación Área (S/)'
    )

    # --- Auditoría ---
    modificado_por = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cambios_estructura_salarial',
        verbose_name='Modificado por'
    )
    motivo_cambio = models.TextField(
        blank=True,
        verbose_name='Motivo del Cambio',
        help_text='Descripción del motivo de la modificación'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha del Cambio')

    class Meta:
        db_table = 'payroll_historial_estructura_salarial'
        ordering = ['-version']
        verbose_name = 'Historial Estructura Salarial'
        verbose_name_plural = 'Historial Estructuras Salariales'
        indexes = [
            models.Index(fields=['estructura', '-version']),
        ]

    def __str__(self):
        return f"{self.estructura.cargo_contratado} — v{self.version} ({self.created_at:%d/%m/%Y %H:%M})"


# =============================================================================
# ASIGNACIÓN DE ESTRUCTURA SALARIAL POR TRABAJADOR
# =============================================================================

class AsignacionEstructuraSalarial(models.Model):
    """
    Puente entre un trabajador y su EstructuraSalarial específica.
    Necesario cuando existen múltiples estructuras para el mismo cargo
    diferenciadas por máquina (ej: AYUDANTE DDH-I con XRD80, XRD120, XLM75).
    Solo puede haber una asignación activa por trabajador a la vez.
    """
    contrato = models.ForeignKey(
        'Contrato', on_delete=models.CASCADE,
        related_name='asignaciones_estructura_salarial',
        verbose_name='Contrato'
    )
    trabajador = models.ForeignKey(
        'Trabajador', on_delete=models.CASCADE,
        related_name='asignaciones_estructura_salarial',
        verbose_name='Trabajador'
    )
    estructura_salarial = models.ForeignKey(
        EstructuraSalarial, on_delete=models.PROTECT,
        related_name='asignaciones',
        verbose_name='Estructura Salarial'
    )
    fecha_inicio = models.DateField(verbose_name='Fecha de Inicio')
    fecha_fin = models.DateField(
        null=True, blank=True,
        verbose_name='Fecha de Fin',
        help_text='Dejar vacío si la asignación está vigente'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    creado_por = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='asignaciones_estructura_salarial_creadas',
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_asignacion_estructura_salarial'
        ordering = ['trabajador__apepat', 'trabajador__nombres', '-created_at']
        verbose_name = 'Asignación Estructura Salarial'
        verbose_name_plural = 'Asignaciones Estructura Salarial'
        indexes = [
            models.Index(fields=['contrato', 'activo']),
            models.Index(fields=['trabajador', 'activo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['trabajador'],
                condition=models.Q(activo=True),
                name='unique_asignacion_activa_por_trabajador',
            )
        ]

    def __str__(self):
        cargo = self.estructura_salarial.cargo_contratado if self.estructura_salarial_id else '—'
        nombre = f"{self.trabajador.apepat} {self.trabajador.nombres}" if self.trabajador_id else '—'
        return f"{nombre} → {cargo}"
