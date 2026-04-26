
"""
Nuevos modelos para el módulo Tareo (versión rehacida).

Este archivo contiene un esquema inicial y normalizado para:
- Períodos operativos de tareo
- Entradas diarias normalizadas (una por trabajador+fecha)
- Auditoría de cambios por entrada
- Cierres mensuales (snapshot contable)

Se deja como módulo separado para facilitar la migración incremental
desde `models.py` original. Después de revisar este diseño se
crearán migraciones y se adaptarán servicios/vistas.
"""
from django.db import models


class TareoPeriod(models.Model):
    """Período operativo para agrupación de registros de tareo.

    Ej: periodo operativo enero 2026 = 2026-01 (periodo que va del 26/12/2025 al 25/01/2026)
    """

    contrato = models.ForeignKey(
        'drilling.Contrato',
        on_delete=models.PROTECT,
        related_name='tareo_periods',
        verbose_name='Contrato'
    )
    anio = models.IntegerField(verbose_name='Año')
    mes = models.IntegerField(verbose_name='Mes')
    fecha_inicio = models.DateField(null=True, blank=True, verbose_name='Fecha inicio periodo')
    fecha_fin = models.DateField(null=True, blank=True, verbose_name='Fecha fin periodo')

    ESTADO_CHOICES = [
        ('ABIERTO', 'Abierto'),
        ('EN_REVISION', 'En Revisión'),
        ('CERRADO', 'Cerrado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ABIERTO')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tareo_period'
        unique_together = [('contrato', 'anio', 'mes')]
        ordering = ['-anio', '-mes']

    def __str__(self):
        return f"{self.contrato} - {self.mes:02d}/{self.anio} [{self.estado}]"


class TareoEntry(models.Model):
    """Entrada normalizada de tareo: 1 registro = 1 trabajador + 1 fecha.

    Diseñado para alta volumetría y consultas eficientes.
    """

    TIPO_CHOICES = [('PROY', 'Proyección'), ('REAL', 'Real')]

    periodo = models.ForeignKey(
        TareoPeriod,
        on_delete=models.CASCADE,
        related_name='entries',
        null=True,
        blank=True,
        verbose_name='Periodo operativo'
    )
    trabajador = models.ForeignKey(
        'drilling.Trabajador',
        on_delete=models.PROTECT,
        related_name='tareo_entries',
        verbose_name='Trabajador',
    )
    fecha = models.DateField(db_index=True)

    ESTADO_CHOICES = [
        ('TRABAJO', 'Trabajo'),
        ('TD', 'Turno Día'),
        ('TN', 'Turno Noche'),
        ('DESCANSO', 'Descanso'),
        ('FALTA', 'Falta'),
        ('VACACIONES', 'Vacaciones'),
        ('PERMISO', 'Permiso'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='TRABAJO', db_index=True)

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='REAL', db_index=True)
    guardia_snapshot = models.CharField(max_length=1, null=True, blank=True)
    maquina_snapshot = models.ForeignKey('drilling.Maquina', on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True)

    registrado_por = models.ForeignKey('drilling.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tareo_entry'
        verbose_name = 'Entrada Tareo'
        verbose_name_plural = 'Entradas Tareo'
        unique_together = [('trabajador', 'fecha')]
        indexes = [
            models.Index(fields=['trabajador', 'fecha'], name='idx_tareo_trab_fecha'),
            models.Index(fields=['fecha', 'estado'], name='idx_tareo_fecha_estado'),
        ]

    def __str__(self):
        return f"{self.trabajador} - {self.fecha} [{self.estado}] ({self.tipo})"


class TareoEntryAudit(models.Model):
    """Auditoría de cambios por entrada de tareo."""

    entrada = models.ForeignKey(TareoEntry, on_delete=models.CASCADE, related_name='audits')
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    tipo_anterior = models.CharField(max_length=10, null=True, blank=True)
    tipo_nuevo = models.CharField(max_length=10, null=True, blank=True)
    usuario = models.ForeignKey('drilling.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.TextField(blank=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'tareo_entry_audit'
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"Audit {self.entrada_id} @ {self.fecha_cambio}"


class TareoClosure(models.Model):
    """Snapshot contable / cierre mensual del tareo."""

    periodo = models.OneToOneField(TareoPeriod, on_delete=models.PROTECT, related_name='closure')
    cerrado_por = models.ForeignKey('drilling.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    # Campos estadísticos (snapshot)
    total_trabajadores = models.IntegerField(default=0)
    total_dias_trabajo = models.IntegerField(default=0)
    total_descansos = models.IntegerField(default=0)
    total_faltas = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tareo_closure'

    def __str__(self):
        return f"Closure {self.periodo}"
