"""
=============================================================================
DRILLING MODELS - Sistema de Perforaciones Diamantinas
=============================================================================

Este archivo contiene todos los modelos del sistema organizados en secciones:

ÍNDICE DE SECCIONES:
--------------------
1. CORE (línea ~30)         - Cliente, Contrato, CustomUser
2. PERSONAL (línea ~250)    - Cargo, Trabajador, Asistencia, Horas Extras
3. MAQUINARIA (línea ~550)  - Maquina, Vehiculo, Equipo
4. SONDAJES (línea ~850)    - Sondaje, TipoActividad, TipoTurno
5. INVENTARIO (línea ~1100) - Unidades, Complementos, Aditivos, Brocas
6. TURNOS (línea ~1400)     - Turno y modelos relacionados
7. METAS (línea ~1850)      - MetaMaquina, PrecioUnitarioServicio
8. ORGANIGRAMA (línea ~2300)- OrganigramaSemanal, Asignaciones

Para navegar: Ctrl+G (ir a línea) o Ctrl+F (buscar "# ===")
=============================================================================
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging


# =============================================================================
# SECCIÓN 1: CORE - Clientes, Contratos y Usuarios
# =============================================================================

class Cliente(models.Model):
    nombre = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.nombre

class Contrato(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('SUSPENDIDO', 'Suspendido'),
        ('FINALIZADO', 'Finalizado'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='contratos')
    nombre_contrato = models.CharField(max_length=200)
    codigo_centro_costo = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name='Código Centro de Costo',
        help_text='Código del centro de costo para APIs de Vilbragroup (ej: 000003)'
    )
    duracion_turno = models.PositiveIntegerField(default=8)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Actividades disponibles/permitidas para este contrato (maestro compartido)
    # Usamos un modelo `through` que mapea a la tabla legacy `contratos_actividades`
    # existente en la base de datos. El modelo `ContratoActividad` se declara
    # más abajo y tiene `Meta.managed = False` para no intentar recrear la
    # tabla en migraciones (la tabla ya existe en la BD según lo indicado).
    actividades = models.ManyToManyField('TipoActividad', blank=True, related_name='contratos', through='ContratoActividad')

    class Meta:
        db_table = 'contratos'
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['codigo_centro_costo']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.cliente.nombre} - {self.nombre_contrato}"

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    """Usuario personalizado con roles y contrato asignado"""
    
    # Definición de roles del sistema
    USER_ROLES = [
        ('ADMINISTRADOR', 'Administrador de Contrato'),
        ('LOGISTICO', 'Logístico'),
        ('RESIDENTE', 'Residente'),
        ('CONTROL_PROYECTOS', 'Control de Proyectos'),
        ('GERENCIA', 'Gerencia'),
        ('GERENTE_GENERAL', 'Gerente General'),
        ('HEADCOUNT', 'Gestión de Personal y Headcount'),
    ]
    
    # Campos adicionales
    contrato = models.ForeignKey(
        'Contrato', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name='Contrato asignado',
        help_text='Contrato al que pertenece este usuario'
    )
    
    role = models.CharField(
        max_length=30, 
        choices=USER_ROLES, 
        default='ADMINISTRADOR',
        verbose_name='Rol del usuario',
        help_text='Define los permisos y accesos del usuario'
    )
    
    is_system_admin = models.BooleanField(
        default=False,
        verbose_name='Es administrador del sistema',
        help_text='Marca si este usuario es administrador de todo el sistema'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    last_activity = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Última actividad',
        help_text='Última vez que el usuario accedió al sistema'
    )
    
    # Campos para activación de cuenta
    is_account_active = models.BooleanField(
        default=False,
        verbose_name='Cuenta activada',
        help_text='Indica si el usuario ha activado su cuenta mediante el enlace de activación'
    )
    
    activation_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Token de activación',
        help_text='Token único para activar la cuenta'
    )
    
    token_created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de creación del token',
        help_text='Fecha en que se generó el token de activación o recuperación'
    )
    
    # Métodos de permisos por rol
    def has_access_to_all_contracts(self):
        """
        Usuario tiene acceso a todos los contratos si:
        - Es Admin del Sistema (is_system_admin=True)
        - Tiene rol GERENCIA, CONTROL_PROYECTOS, GERENTE_GENERAL o HEADCOUNT (independiente del contrato asignado)
        """
        return self.is_system_admin or self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'GERENTE_GENERAL', 'HEADCOUNT']
    
    def can_manage_all_contracts(self):
        """GERENCIA, CONTROL_PROYECTOS, GERENTE_GENERAL y HEADCOUNT pueden gestionar todos los contratos"""
        return self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'GERENTE_GENERAL', 'HEADCOUNT']
    
    def can_manage_contract_users(self):
        """GERENCIA, CONTROL_PROYECTOS, GERENTE_GENERAL y ADMINISTRADOR pueden gestionar usuarios"""
        return self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'GERENTE_GENERAL', 'ADMINISTRADOR', 'LOGISTICO']
    
    def can_supervise_operations(self):
        """GERENCIA, CONTROL_PROYECTOS, GERENTE_GENERAL, RESIDENTE, ADMINISTRADOR y LOGISTICO pueden supervisar operaciones"""  
        return self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'GERENTE_GENERAL', 'RESIDENTE', 'ADMINISTRADOR', 'LOGISTICO']
    
    def can_create_basic_data(self):
        """Crear datos básicos (trabajadores, máquinas, sondajes)"""
        return self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'ADMINISTRADOR', 'RESIDENTE', 'LOGISTICO']
    
    def can_manage_inventory(self):
        """Gestionar inventario y abastecimiento"""
        return self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'ADMINISTRADOR', 'LOGISTICO']
    
    def can_import_data(self):
        """Importar datos desde Excel"""
        return self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'ADMINISTRADOR', 'LOGISTICO']
    
    def can_view_reports(self):
        """Ver reportes del sistema"""
        return self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'ADMINISTRADOR', 'RESIDENTE', 'LOGISTICO']
    
    def can_manage_system_config(self):
        """Gestionar configuración del sistema (tipos, unidades, etc.)"""
        return self.role in ['GERENCIA', 'CONTROL_PROYECTOS', 'ADMINISTRADOR', 'LOGISTICO']
    
    def get_accessible_contracts(self):
        """
        Obtener contratos accesibles para este usuario.
        - Admin del sistema: Todos los contratos
        - Sin contrato asignado: Todos los contratos (Control de Proyecto)
        - Con contrato asignado: Solo su contrato
        """
        from .models import Contrato
        
        if self.has_access_to_all_contracts():
            return Contrato.objects.all()
        elif self.contrato:
            return Contrato.objects.filter(id=self.contrato_id)
        else:
            return Contrato.objects.none()
    
    def get_role_display(self):
        """Obtener el nombre legible del rol"""
        return dict(self.USER_ROLES).get(self.role, self.role)
    
    def get_role_badge_class(self):
        """Obtener la clase CSS para el badge del rol"""
        role_classes = {
            'GERENCIA': 'bg-danger',
            'CONTROL_PROYECTOS': 'bg-primary',
            'ADMINISTRADOR': 'bg-warning text-dark',
            'RESIDENTE': 'bg-info',
            'LOGISTICO': 'bg-success',
            'OPERADOR': 'bg-secondary',
            # Legacy roles
            'ADMIN_SISTEMA': 'bg-danger',
            'MANAGER_CONTRATO': 'bg-warning text-dark',
            'SUPERVISOR': 'bg-info',
        }
        return role_classes.get(self.role, 'bg-secondary')
    
    def get_permissions_summary(self):
        """Obtener resumen de permisos para mostrar en admin o perfiles"""
        permissions = []
        
        if self.has_access_to_all_contracts():
            permissions.append("Acceso a TODOS los contratos")
        elif self.contrato:
            permissions.append(f"Acceso solo a: {self.contrato.nombre_contrato}")
        
        if self.can_manage_all_contracts():
            permissions.append("Gestionar todos los contratos")
        if self.can_manage_contract_users():
            permissions.append("Gestionar usuarios del contrato")
        if self.can_supervise_operations():
            permissions.append("Supervisar operaciones")
        if self.can_create_basic_data():
            permissions.append("Crear datos básicos")
        if self.can_manage_inventory():
            permissions.append("Gestionar inventario")
        if self.can_import_data():
            permissions.append("Importar datos")
        if self.can_view_reports():
            permissions.append("Ver reportes")
        if self.can_manage_system_config():
            permissions.append("Configuración del sistema")
            
        return permissions
    
    def is_active_recently(self, days=30):
        """Verificar si el usuario ha estado activo recientemente"""
        if not self.last_activity:
            return False
        
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.last_activity >= cutoff_date
    
    def update_last_activity(self):
        """Actualizar la última actividad del usuario"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def get_contract_display(self):
        """Obtener información del contrato para mostrar"""
        if self.contrato:
            return f"{self.contrato.nombre_contrato} ({self.contrato.cliente.nombre})"
        return "Sin contrato asignado"
    
    def has_contract_permission(self, contract):
        """Verificar si el usuario tiene permisos sobre un contrato específico"""
        if self.can_manage_all_contracts():
            return True
        return self.contrato == contract
    
    def clean(self):
        """Validaciones personalizadas del modelo"""
        from django.core.exceptions import ValidationError
        
        # Roles de contrato deben tener un contrato asignado
        if self.role in ['ADMINISTRADOR', 'LOGISTICO', 'RESIDENTE'] and not self.contrato:
            raise ValidationError({
                'contrato': f'Los usuarios con rol {self.role} deben tener un contrato asignado'
            })
        
        # Solo GERENCIA y CONTROL_PROYECTOS pueden ser admin del sistema
        if self.is_system_admin and self.role not in ['GERENCIA', 'CONTROL_PROYECTOS']:
            raise ValidationError({
                'is_system_admin': 'Solo los usuarios con rol GERENCIA o CONTROL_PROYECTOS pueden ser administradores del sistema'
            })
    
    def save(self, *args, **kwargs):
        """Override save para aplicar validaciones"""
        # Solo validar si es un usuario nuevo o si se modifican campos críticos
        if not self.pk or 'update_fields' not in kwargs or kwargs.get('update_fields') and 'role' in kwargs.get('update_fields', []):
            # Solo validar si no es una actualización parcial de last_activity
            if 'update_fields' not in kwargs or 'role' in kwargs.get('update_fields', []) or 'contrato' in kwargs.get('update_fields', []):
                self.full_clean()
        
        # Asignar is_staff automáticamente para administradores
        if self.role in ['ADMINISTRADOR', 'GERENCIA', 'CONTROL_PROYECTOS']:
            self.is_staff = True
        
        # GERENCIA tiene acceso de superusuario
        if self.role == 'GERENCIA':
            self.is_superuser = True
        else:
            # Otros roles no tienen acceso de superusuario por defecto
            if not self.can_manage_all_contracts():
                self.is_staff = False
                self.is_superuser = False
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        """Representación en string del usuario"""
        role_display = self.get_role_display()
        if self.contrato:
            return f"{self.username} ({role_display}) - {self.contrato.nombre_contrato}"
        return f"{self.username} ({role_display})"
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['username']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['contrato']),
            models.Index(fields=['is_system_admin']),
            models.Index(fields=['last_activity']),
        ]

class TipoTurno(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'tipo_turnos'

    def __str__(self):
        return self.nombre

class EstadoTurno(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'estados_turno'

    def __str__(self):
        return self.nombre

class TipoActividad(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    descripcion_corta = models.CharField(max_length=200, blank=True)
    TIPO_CHOICES = [
        ('STAND_BY_CLIENTE', 'Stand By Cliente'),
        ('STAND_BY_ROCKDRILL', 'Stand By Rock Drill'),
        ('INOPERATIVO', 'Inoperativo'),
        ('OPERATIVO', 'Operativo'),
        ('OTROS', 'Otros'),
    ]
    tipo_actividad = models.CharField(max_length=32, choices=TIPO_CHOICES, default='OTROS')
    es_cobrable = models.BooleanField(default=False, verbose_name='Es cobrable')

    class Meta:
        db_table = 'tipos_actividad'
        indexes = [
            models.Index(fields=['tipo_actividad']),
            models.Index(fields=['es_cobrable']),
            models.Index(fields=['tipo_actividad', 'es_cobrable']),
        ]

    def __str__(self):
        return self.nombre


class ContratoActividad(models.Model):
    """Modelo que mapea la tabla `contratos_actividades`.
    
    Solo contiene las columnas reales: id, contrato_id, tipoactividad_id
    """
    contrato = models.ForeignKey('Contrato', on_delete=models.CASCADE, db_column='contrato_id', related_name='actividades_asignadas')
    tipoactividad = models.ForeignKey('TipoActividad', on_delete=models.CASCADE, db_column='tipoactividad_id', related_name='contratos_asignados')

    class Meta:
        db_table = 'contratos_actividades'
        managed = False
        verbose_name = 'Contrato Actividad'
        verbose_name_plural = 'Contratos Actividades'
        unique_together = [('contrato', 'tipoactividad')]

    def __str__(self):
        try:
            return f"{self.contrato} - {self.tipoactividad}"
        except Exception:
            return f"ContratoActividad {self.pk}"


# =============================================================================
# SECCIÓN 5: INVENTARIO - Unidades, Complementos, Aditivos, Brocas, Stock
# =============================================================================

class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50)
    simbolo = models.CharField(max_length=10)

    class Meta:
        db_table = 'unidades_medida'

    def __str__(self):
        return f"{self.nombre} ({self.simbolo})"

class TipoComplemento(models.Model):
    CATEGORIA_CHOICES = [
        ('BROCA', 'Broca'),
        ('REAMING_SHELL', 'Reaming Shell'),
        ('ZAPATA', 'Zapata'),
        ('CORE_LIFTER', 'Core Lifter'),
    ]
    
    ESTADO_CHOICES = [
        ('NUEVO', 'Nuevo'),
        ('EN_USO', 'En Uso'),
        ('DESCARTADO', 'Descartado'),
    ]
    
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    # Campos de sincronización con API
    codigo = models.CharField(max_length=100, blank=True, null=True, help_text='Código del producto desde API Vilbragroup')
    serie = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text='Serie única del producto desde API')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='NUEVO', help_text='Estado del producto diamantado')
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='productos_diamantados', null=True, blank=True)

    class Meta:
        db_table = 'tipos_complemento'
        verbose_name = 'Tipo de Complemento'
        verbose_name_plural = 'Tipos de Complemento'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['serie']),
            models.Index(fields=['estado']),
            models.Index(fields=['contrato']),
            models.Index(fields=['contrato', 'estado']),
        ]

    def __str__(self):
        if self.serie:
            return f"{self.nombre} (Serie: {self.serie})"
        return self.nombre

class TipoAditivo(models.Model):
    CATEGORIA_CHOICES = [
        ('BENTONITA', 'Bentonita'),
        ('POLIMEROS', 'Polímeros'),
        ('CMC', 'CMC'),
        ('SODA_ASH', 'Soda Ash'),
        ('DISPERSANTE', 'Dispersante'),
        ('LUBRICANTE', 'Lubricante'),
        ('ESPUMANTE', 'Espumante'),
    ]
    
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, blank=True, null=True)
    unidad_medida_default = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    # Campos de sincronización con API
    codigo = models.CharField(max_length=100, blank=True, null=True, help_text='Código del aditivo desde API Vilbragroup')
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='aditivos', null=True, blank=True)

    class Meta:
        db_table = 'tipos_aditivo'
        verbose_name = 'Tipo de Aditivo'
        verbose_name_plural = 'Tipos de Aditivo'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['contrato']),
            models.Index(fields=['contrato', 'codigo']),
        ]

    def __str__(self):
        if self.codigo:
            return f"{self.nombre} ({self.codigo})"
        return self.nombre


# =============================================================================
# SECCIÓN 4: SONDAJES - Sondajes, Tipos de Actividad, Estados
# =============================================================================

class Sondaje(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('PAUSADO', 'Pausado'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='sondajes')
    nombre_sondaje = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    profundidad = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('3000.00'))])
    inclinacion = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('-90.00')), MaxValueValidator(Decimal('90.00'))])
    cota_collar = models.DecimalField(max_digits=8, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO')

    class Meta:
        db_table = 'sondajes'
        verbose_name = 'Sondaje'
        verbose_name_plural = 'Sondajes'
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['contrato', 'estado']),
            models.Index(fields=['fecha_inicio']),
            models.Index(fields=['-fecha_inicio']),
            models.Index(fields=['fecha_fin']),
        ]

    def clean(self):
        if self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError('La fecha de fin debe ser posterior a la fecha de inicio')

    def __str__(self):
        return f"{self.nombre_sondaje} - {self.contrato.nombre_contrato}"


# =============================================================================
# SECCIÓN 3: MAQUINARIA - Máquinas, Vehículos, Equipos
# =============================================================================

class Maquina(models.Model):
    ESTADO_CHOICES = [
        ('OPERATIVO', 'Operativo'),
        ('MANTENIMIENTO', 'En Mantenimiento'),
        ('FUERA_SERVICIO', 'Fuera de Servicio'),
    ]

    TIPO_TRABAJO_CHOICES = [
        ('SUBTERRANEA', 'Interior Mina'),
        ('SUPERFICIAL', 'Superficial'),
    ]
    
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='maquinas')
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=100)
    tipo_trabajo = models.CharField(max_length=20, choices=TIPO_TRABAJO_CHOICES, default='SUBTERRANEA', verbose_name='Tipo de Trabajo')
    # Horómetro acumulado en horas (decimal con 2 decimales)
    horometro = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='OPERATIVO')

    class Meta:
        db_table = 'maquinas'
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['contrato', 'estado']),
            models.Index(fields=['nombre']),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.contrato.nombre_contrato}"


class MaquinaTransferenciaHistorial(models.Model):
    """
    Modelo para registrar el historial de transferencias de máquinas entre contratos.
    """
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE, related_name='transferencias')
    contrato_origen = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='transferencias_salida')
    contrato_destino = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='transferencias_entrada')
    fecha_transferencia = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey('CustomUser', on_delete=models.PROTECT, related_name='transferencias_realizadas')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')

    class Meta:
        db_table = 'maquina_transferencia_historial'
        ordering = ['-fecha_transferencia']
        verbose_name = 'Transferencia de Máquina'
        verbose_name_plural = 'Transferencias de Máquinas'

    def __str__(self):
        return f"{self.maquina.nombre}: {self.contrato_origen.nombre_contrato} → {self.contrato_destino.nombre_contrato} ({self.fecha_transferencia.strftime('%d/%m/%Y %H:%M')})"


class Vehiculo(models.Model):
    """
    Modelo para vehículos (camiones, camionetas, combis, etc.)
    Asignados principalmente a conductores en el organigrama.
    """
    TIPO_CHOICES = [
        ('CAMION', 'Camión'),
        ('CAMIONETA', 'Camioneta'),
        ('COMBI', 'Combi'),
        ('MINIBUS', 'Minibús'),
        ('STATION_WAGON', 'Station Wagon'),
        ('PICKUP', 'Pickup'),
        ('OTRO', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('OPERATIVO', 'Operativo'),
        ('MANTENIMIENTO', 'En Mantenimiento'),
        ('FUERA_SERVICIO', 'Fuera de Servicio'),
    ]
    
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='vehiculos')
    placa = models.CharField(max_length=20, unique=True, verbose_name='Placa')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='CAMIONETA')
    marca = models.CharField(max_length=100, blank=True, verbose_name='Marca')
    modelo = models.CharField(max_length=100, blank=True, verbose_name='Modelo')
    año = models.PositiveIntegerField(null=True, blank=True, verbose_name='Año')
    kilometraje_actual = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name='Kilometraje Actual (km)',
        help_text='Kilometraje acumulado del vehículo'
    )
    capacidad_pasajeros = models.PositiveIntegerField(null=True, blank=True, verbose_name='Capacidad de pasajeros')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='OPERATIVO')
    
    # Campos de mantenimiento
    ultimo_mantenimiento_fecha = models.DateField(
        null=True, 
        blank=True, 
        verbose_name='Fecha último mantenimiento',
        help_text='Fecha del último mantenimiento realizado'
    )
    ultimo_mantenimiento_km = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='Kilometraje último mantenimiento',
        help_text='Kilometraje registrado en el último mantenimiento'
    )
    proximo_mantenimiento_km = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='Próximo mantenimiento (km)',
        help_text='Kilometraje programado para el próximo mantenimiento'
    )
    
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehiculos'
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
        ordering = ['placa']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['contrato', 'estado']),
            models.Index(fields=['ultimo_mantenimiento_fecha']),
            models.Index(fields=['proximo_mantenimiento_km']),
        ]

    def __str__(self):
        return f"{self.placa} - {self.get_tipo_display()} ({self.contrato.nombre_contrato})"
    
    def km_desde_ultimo_mantenimiento(self):
        """Calcular kilómetros recorridos desde el último mantenimiento"""
        if self.ultimo_mantenimiento_km:
            return self.kilometraje_actual - self.ultimo_mantenimiento_km
        return self.kilometraje_actual
    
    def km_hasta_proximo_mantenimiento(self):
        """Calcular kilómetros faltantes para el próximo mantenimiento"""
        if self.proximo_mantenimiento_km:
            return self.proximo_mantenimiento_km - self.kilometraje_actual
        return None
    
    def requiere_mantenimiento(self):
        """Verificar si el vehículo requiere mantenimiento"""
        if self.proximo_mantenimiento_km:
            return self.kilometraje_actual >= self.proximo_mantenimiento_km
        return False


class MantenimientoVehiculo(models.Model):
    """
    Historial de mantenimientos realizados a los vehículos
    """
    TIPO_MANTENIMIENTO_CHOICES = [
        ('PREVENTIVO', 'Preventivo'),
        ('CORRECTIVO', 'Correctivo'),
        ('RUTINARIO', 'Rutinario'),
        ('EMERGENCIA', 'Emergencia'),
    ]
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='mantenimientos')
    fecha_mantenimiento = models.DateField(verbose_name='Fecha de mantenimiento')
    kilometraje = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Kilometraje en el mantenimiento'
    )
    tipo_mantenimiento = models.CharField(
        max_length=20, 
        choices=TIPO_MANTENIMIENTO_CHOICES,
        default='PREVENTIVO',
        verbose_name='Tipo de mantenimiento'
    )
    descripcion = models.TextField(verbose_name='Descripción del trabajo realizado')
    costo = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='Costo del mantenimiento'
    )
    proveedor = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='Proveedor/Taller'
    )
    repuestos_utilizados = models.TextField(
        blank=True, 
        verbose_name='Repuestos utilizados',
        help_text='Lista de repuestos o partes reemplazadas'
    )
    proximo_mantenimiento_sugerido_km = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='Próximo mantenimiento sugerido (km)'
    )
    responsable = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='Responsable',
        help_text='Persona que autorizó o supervisó el mantenimiento'
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones adicionales')
    
    # Usuario que registró el mantenimiento
    registrado_por = models.ForeignKey(
        'CustomUser', 
        on_delete=models.PROTECT, 
        related_name='mantenimientos_registrados',
        verbose_name='Registrado por'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mantenimiento_vehiculo'
        verbose_name = 'Mantenimiento de Vehículo'
        verbose_name_plural = 'Mantenimientos de Vehículos'
        ordering = ['-fecha_mantenimiento', '-created_at']
        indexes = [
            models.Index(fields=['vehiculo', 'fecha_mantenimiento']),
            models.Index(fields=['tipo_mantenimiento']),
            models.Index(fields=['fecha_mantenimiento']),
        ]

    def __str__(self):
        return f"{self.vehiculo.placa} - {self.get_tipo_mantenimiento_display()} ({self.fecha_mantenimiento.strftime('%d/%m/%Y')})"
    
    def save(self, *args, **kwargs):
        """
        Al guardar un mantenimiento, actualizar automáticamente los campos
        de último mantenimiento en el vehículo
        """
        super().save(*args, **kwargs)
        
        # Actualizar fecha y kilometraje del último mantenimiento en el vehículo
        self.vehiculo.ultimo_mantenimiento_fecha = self.fecha_mantenimiento
        self.vehiculo.ultimo_mantenimiento_km = self.kilometraje
        
        # Si se sugirió un próximo mantenimiento, actualizarlo
        if self.proximo_mantenimiento_sugerido_km:
            self.vehiculo.proximo_mantenimiento_km = self.proximo_mantenimiento_sugerido_km
        
        self.vehiculo.save(update_fields=['ultimo_mantenimiento_fecha', 'ultimo_mantenimiento_km', 'proximo_mantenimiento_km'])


class AsistenciaTrabajador(models.Model):
    """
    Registro diario de asistencia de trabajadores
    Matriz: trabajador x día con diferentes estados posibles
    """
    ESTADO_ASISTENCIA_CHOICES = [
        ('TRABAJADO', 'Trabajado'),
        ('DIA_LIBRE', 'Día Libre'),
        ('DIA_APOYO', 'Día de Apoyo'),
        ('PERMISO_PATERNIDAD', 'Permiso Paternidad'),
        ('DESCANSO_MEDICO', 'Descanso Médico'),
        ('STAND_BY', 'Stand By'),
        ('SUBSIDIO', 'Subsidio'),
        ('INDUCCION', 'Inducción'),
        ('INDUCCION_VIRTUAL', 'Inducción Virtual'),
        ('RECORRIDO', 'Recorrido'),
        ('FALTA', 'Falta'),
        ('PERMISO', 'Permiso'),
        ('SUSPENSION', 'Suspensión'),
        ('VACACIONES', 'Vacaciones'),
        ('LICENCIA_SIN_GOCE', 'Licencia Sin Goce'),
        ('CESADO', 'Cesado'),
        ('TRABAJO_CALIENTE', 'Trabajo en Caliente'),
        ('LICENCIA_FALLECIMIENTO', 'Licencia por Fallecimiento'),
        ('LICENCIA_CON_GOCE', 'Licencia Con Goce'),
    ]
    
    TIPO_CHOICES = [
        ('PAGABLE', 'Pagable'),
        ('NO_PAGABLE', 'No Pagable'),
    ]
    
    # Estados que son pagables por defecto
    ESTADOS_PAGABLES = ['TRABAJADO', 'DIA_LIBRE', 'INDUCCION', 'INDUCCION_VIRTUAL']
    
    trabajador = models.ForeignKey(
        'Trabajador', 
        on_delete=models.CASCADE, 
        related_name='asistencias'
    )
    fecha = models.DateField(verbose_name='Fecha')
    estado = models.CharField(
        max_length=30, 
        choices=ESTADO_ASISTENCIA_CHOICES,
        default='TRABAJADO',
        verbose_name='Estado de asistencia'
    )
    tipo = models.CharField(
        max_length=15,
        choices=TIPO_CHOICES,
        default='PAGABLE',
        verbose_name='Tipo',
        help_text='Define si la asistencia es pagable o no pagable'
    )
    
    # Snapshot fields for historical accuracy
    cargo_snapshot = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name='Cargo (Histórico)',
        help_text='Cargo del trabajador al momento del registro'
    )
    guardia_snapshot = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        verbose_name='Guardia (Histórico)',
        help_text='Guardia asignada al momento del registro'
    )
    observaciones = models.TextField(
        blank=True, 
        verbose_name='Observaciones',
        help_text='Detalles adicionales sobre la asistencia'
    )
    
    # Usuario que registró la asistencia
    registrado_por = models.ForeignKey(
        'CustomUser', 
        on_delete=models.PROTECT, 
        related_name='asistencias_registradas',
        verbose_name='Registrado por'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asistencia_trabajador'
        verbose_name = 'Asistencia de Trabajador'
        verbose_name_plural = 'Asistencias de Trabajadores'
        # Única asistencia por trabajador por día
        unique_together = [['trabajador', 'fecha']]
        ordering = ['-fecha', 'trabajador__apellidos', 'trabajador__nombres']
        indexes = [
            models.Index(fields=['trabajador', 'fecha']),
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
            models.Index(fields=['trabajador', 'estado']),
            models.Index(fields=['tipo']),
        ]

    def save(self, *args, **kwargs):
        # Auto-asignar tipo basado en el estado si no se especifica explícitamente
        if not self.pk and not kwargs.pop('skip_auto_tipo', False):
            if self.estado in self.ESTADOS_PAGABLES:
                self.tipo = 'PAGABLE'
            else:
                self.tipo = 'NO_PAGABLE'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.trabajador.nombres} {self.trabajador.apellidos} - {self.fecha.strftime('%d/%m/%Y')} - {self.get_estado_display()}"


# =============================================================================
# NUEVO MODELO NORMALIZADO PARA TAREO (VERTICAL)
# =============================================================================
class AsistenciaDiaria(models.Model):
    """
    Modelo Normalizado (Vertical) para Registro de Asistencia Diaria
    
    Optimizado para:
    - Alta volumetría (70+ empleados x 30 días = 2,100+ registros/mes)
    - Consultas eficientes por fecha/trabajador/estado
    - Cálculo de costos logísticos (refrigerios/campamento)
    - Proyección mensual automática vs correcciones diarias
    
    Diseño:
    - Normalización: 1 registro = 1 trabajador + 1 fecha + 1 estado
    - Constraint único: trabajador + fecha (evita duplicados)
    - Índices estratégicos para rendimiento
    """
    
    # Choices de Estado - Alineados con AsistenciaTrabajador (legacy)
    ESTADO_CHOICES = [
        ('TRABAJO', 'Trabajo'),
        ('DESCANSO', 'Descanso'),
        ('FALTA', 'Falta'),
        ('DM', 'Descanso Médico'),
        ('VACACIONES', 'Vacaciones'),
        ('PERMISO', 'Permiso'),
        ('SUSPENSION', 'Suspensión'),
        ('LICENCIA', 'Licencia'),
        ('INDUCCION', 'Inducción'),
        ('STAND_BY', 'Stand By'),
        ('DIA_APOYO', 'Día de Apoyo'),
    ]
    
    # Relación al trabajador
    empleado = models.ForeignKey(
        'Trabajador',
        on_delete=models.PROTECT,  # PROTECT para evitar eliminaciones accidentales
        related_name='asistencias_diarias',
        verbose_name='Trabajador',
        db_index=True  # Índice para FK
    )
    
    # Fecha del registro
    fecha = models.DateField(
        verbose_name='Fecha',
        db_index=True  # Índice para consultas por rango de fechas
    )
    
    # Estado de la asistencia
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='TRABAJO',
        verbose_name='Estado',
        db_index=True  # Índice para filtros por estado
    )
    
    # Snapshot de guardia (histórico congelado)
    guardia_snapshot = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        verbose_name='Guardia Asignada (Snapshot)',
        help_text='Guardia del trabajador al momento del registro (A/B/C)'
    )
    
    # Snapshot de máquina asignada ese día específico
    maquina_snapshot = models.ForeignKey(
        'Maquina',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_diarias',
        verbose_name='Máquina Asignada',
        help_text='Máquina específica asignada para este día'
    )
    
    # Flag para distinguir proyección vs corrección
    es_proyeccion = models.BooleanField(
        default=False,
        verbose_name='Es Proyección',
        help_text='True = proyección automática | False = corrección manual',
        db_index=True  # Índice para filtros
    )
    
    # Observaciones
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
        help_text='Detalles adicionales sobre la asistencia'
    )
    
    # Auditoría
    registrado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='asistencias_registradas_v2',
        verbose_name='Registrado por'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    
    class Meta:
        db_table = 'asistencia_diaria'
        verbose_name = 'Asistencia Diaria'
        verbose_name_plural = 'Asistencias Diarias'
        
        # Constraint único: 1 trabajador solo puede tener 1 registro por fecha
        constraints = [
            models.UniqueConstraint(
                fields=['empleado', 'fecha'],
                name='unique_empleado_fecha'
            )
        ]
        
        # Ordenamiento por defecto
        ordering = ['-fecha', 'empleado__apellidos', 'empleado__nombres']
        
        # Índices compuestos para optimización de consultas frecuentes
        indexes = [
            # Consultas por trabajador y fecha (más común)
            models.Index(fields=['empleado', 'fecha'], name='idx_empleado_fecha'),
            
            # Consultas por rango de fechas
            models.Index(fields=['fecha', 'estado'], name='idx_fecha_estado'),
            
            # Filtros por proyección
            models.Index(fields=['es_proyeccion', 'fecha'], name='idx_proyeccion_fecha'),
            
            # Consultas de auditoría
            models.Index(fields=['registrado_por', '-created_at'], name='idx_auditoria'),
        ]
    
    def __str__(self):
        tipo = "PROY" if self.es_proyeccion else "REAL"
        return f"[{tipo}] {self.empleado.apellidos}, {self.empleado.nombres} - {self.fecha.strftime('%d/%m/%Y')} - {self.get_estado_display()}"
    
    def save(self, *args, **kwargs):
        """Override save para capturar snapshots automáticamente"""
        if not self.guardia_snapshot and self.empleado:
            self.guardia_snapshot = self.empleado.guardia_asignada
        if not self.maquina_snapshot and self.empleado and self.empleado.maquina_asignada:
            self.maquina_snapshot = self.empleado.maquina_asignada
        super().save(*args, **kwargs)


class CierreMensualTareo(models.Model):
    """
    Modelo para registrar cierres contables mensuales del tareo.
    
    Flujo:
    1. Mes inicia ABIERTO (editable)
    2. Supervisor confirma → EN_REVISION
    3. Gerencia aprueba → CERRADO (inmutable)
    
    Propósito:
    - Congelar datos para nómina/pagos
    - Auditoría y trazabilidad
    - Evitar cambios post-cierre contable
    """
    
    ESTADO_CHOICES = [
        ('ABIERTO', 'Abierto'),
        ('EN_REVISION', 'En Revisión'),
        ('CERRADO', 'Cerrado'),
        ('REABIERTO', 'Reabierto'),
    ]
    
    contrato = models.ForeignKey(
        'Contrato',
        on_delete=models.PROTECT,
        related_name='cierres_tareo',
        verbose_name='Contrato'
    )
    
    anio = models.IntegerField(verbose_name='Año')
    mes = models.IntegerField(verbose_name='Mes', help_text='1-12')
    
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='ABIERTO',
        verbose_name='Estado'
    )
    
    # Estadísticas del mes (snapshot)
    total_trabajadores = models.IntegerField(default=0, verbose_name='Total Trabajadores')
    total_dias_trabajo = models.IntegerField(default=0, verbose_name='Total Días Trabajo')
    total_dias_descanso = models.IntegerField(default=0, verbose_name='Total Días Descanso')
    total_faltas = models.IntegerField(default=0, verbose_name='Total Faltas')
    total_vacaciones = models.IntegerField(default=0, verbose_name='Total Vacaciones')
    total_permisos = models.IntegerField(default=0, verbose_name='Total Permisos')
    
    # Auditoría de cierre
    fecha_cierre = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Cierre')
    cerrado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='cierres_realizados',
        verbose_name='Cerrado por'
    )
    
    # Reapertura (casos excepcionales)
    fecha_reapertura = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Reapertura')
    reabierto_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reaperturas_realizadas',
        verbose_name='Reabierto por'
    )
    motivo_reapertura = models.TextField(blank=True, verbose_name='Motivo de Reapertura')
    
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    
    class Meta:
        db_table = 'cierre_mensual_tareo'
        verbose_name = 'Cierre Mensual de Tareo'
        verbose_name_plural = 'Cierres Mensuales de Tareo'
        ordering = ['-anio', '-mes']
        
        constraints = [
            models.UniqueConstraint(
                fields=['contrato', 'anio', 'mes'],
                name='unique_cierre_contrato_mes'
            )
        ]
        
        indexes = [
            models.Index(fields=['contrato', '-anio', '-mes'], name='idx_cierre_contrato_periodo'),
            models.Index(fields=['estado', 'fecha_cierre'], name='idx_cierre_estado'),
        ]
    
    def __str__(self):
        return f"{self.contrato.nombre_contrato} - {self.mes:02d}/{self.anio} [{self.estado}]"
    
    def puede_editarse(self):
        """Determina si el mes puede ser editado"""
        return self.estado in ['ABIERTO', 'EN_REVISION', 'REABIERTO']
    
    def get_fecha_inicio_periodo(self):
        """Obtiene la fecha de inicio del mes operativo (día 26 del mes anterior)"""
        from datetime import date
        mes_anterior = self.mes - 1 if self.mes > 1 else 12
        anio_anterior = self.anio if self.mes > 1 else self.anio - 1
        return date(anio_anterior, mes_anterior, 26)
    
    def get_fecha_fin_periodo(self):
        """Obtiene la fecha de fin del mes operativo (día 25 del mes actual)"""
        from datetime import date
        return date(self.anio, self.mes, 25)
    
    def get_mes_display(self):
        """Retorna el nombre del mes"""
        meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        return meses[self.mes]
    
    def get_periodo_completo(self):
        """Retorna descripción completa del período"""
        return f"{self.get_fecha_inicio_periodo().strftime('%d/%m/%Y')} - {self.get_fecha_fin_periodo().strftime('%d/%m/%Y')}"
    
    def calcular_estadisticas(self):
        """Calcula y actualiza las estadísticas del mes operativo"""
        from datetime import date
        
        # Mes operativo: del 26 del mes anterior al 25 del mes actual
        mes_anterior = self.mes - 1 if self.mes > 1 else 12
        anio_anterior = self.anio if self.mes > 1 else self.anio - 1
        
        primer_dia = date(anio_anterior, mes_anterior, 26)
        ultimo_dia = date(self.anio, self.mes, 25)
        
        # Obtener asistencias reales (no proyecciones)
        asistencias = AsistenciaDiaria.objects.filter(
            empleado__contrato=self.contrato,
            fecha__gte=primer_dia,
            fecha__lte=ultimo_dia,
            es_proyeccion=False
        )
        
        self.total_trabajadores = asistencias.values('empleado').distinct().count()
        self.total_dias_trabajo = asistencias.filter(estado='TRABAJO').count()
        self.total_dias_descanso = asistencias.filter(estado='DESCANSO').count()
        self.total_faltas = asistencias.filter(estado='FALTA').count()
        self.total_vacaciones = asistencias.filter(estado='VACACIONES').count()
        self.total_permisos = asistencias.filter(estado='PERMISO').count()
        
        self.save()


class HistorialCambioAsistencia(models.Model):
    """
    Auditoría detallada de cambios en asistencias.
    Registra TODOS los cambios para trazabilidad completa.
    
    Casos de uso:
    - Auditoría interna/externa
    - Resolución de disputas
    - Reportes de nómina
    - Análisis de patrones de cambios
    """
    
    asistencia = models.ForeignKey(
        'AsistenciaDiaria',
        on_delete=models.CASCADE,
        related_name='historial_cambios',
        verbose_name='Asistencia'
    )
    
    # Datos antes del cambio
    estado_anterior = models.CharField(max_length=20, verbose_name='Estado Anterior')
    es_proyeccion_anterior = models.BooleanField(verbose_name='Era Proyección')
    
    # Datos después del cambio
    estado_nuevo = models.CharField(max_length=20, verbose_name='Estado Nuevo')
    es_proyeccion_nuevo = models.BooleanField(verbose_name='Es Proyección')
    
    # Auditoría del cambio
    fecha_cambio = models.DateTimeField(auto_now_add=True, verbose_name='Fecha del Cambio')
    usuario = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='cambios_asistencia',
        verbose_name='Usuario que modificó'
    )
    
    motivo = models.TextField(blank=True, verbose_name='Motivo del Cambio')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='Dirección IP')
    
    # Contexto adicional
    mes_cerrado = models.BooleanField(
        default=False,
        verbose_name='Mes estaba cerrado',
        help_text='Indica si el cambio se hizo en un mes cerrado (requiere justificación)'
    )
    
    class Meta:
        db_table = 'historial_cambio_asistencia'
        verbose_name = 'Historial de Cambio de Asistencia'
        verbose_name_plural = 'Historial de Cambios de Asistencia'
        ordering = ['-fecha_cambio']
        
        indexes = [
            models.Index(fields=['asistencia', '-fecha_cambio'], name='idx_hist_asistencia'),
            models.Index(fields=['usuario', '-fecha_cambio'], name='idx_hist_usuario'),
            models.Index(fields=['-fecha_cambio'], name='idx_hist_fecha'),
        ]
    
    def __str__(self):
        return f"{self.asistencia.empleado} - {self.asistencia.fecha}: {self.estado_anterior} → {self.estado_nuevo}"


class ConfiguracionHoraExtra(models.Model):
    """
    Configuración de horas extras por contrato y máquina.
    Define el metraje mínimo requerido para otorgar horas extras.
    """
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='configuraciones_hora_extra')
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE, null=True, blank=True, related_name='configuraciones_hora_extra',
                                help_text='Dejar vacío para aplicar a todas las máquinas del contrato')
    metros_minimos = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        verbose_name='Metraje mínimo (m)',
        help_text='Metraje mínimo del turno para otorgar hora extra'
    )
    horas_extra = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0,
        verbose_name='Horas extra a otorgar',
        help_text='Cantidad de horas extra que se otorgarán'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_inicio = models.DateField(null=True, blank=True, verbose_name='Fecha inicio vigencia')
    fecha_fin = models.DateField(null=True, blank=True, verbose_name='Fecha fin vigencia')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_hora_extra'
        ordering = ['contrato', 'maquina', '-metros_minimos']
        verbose_name = 'Configuración de Hora Extra'
        verbose_name_plural = 'Configuraciones de Horas Extras'
        unique_together = [('contrato', 'maquina')]

    def __str__(self):
        maquina_str = f" - {self.maquina.nombre}" if self.maquina else " - Todas las máquinas"
        return f"{self.contrato.nombre_contrato}{maquina_str}: {self.metros_minimos}m = {self.horas_extra}h extra"

    def aplica_para_turno(self, turno, metros_turno):
        """
        Verifica si esta configuración aplica para un turno dado.
        """
        # Verificar si está activo
        if not self.activo:
            return False
        
        # Verificar vigencia por fechas
        if self.fecha_inicio and turno.fecha < self.fecha_inicio:
            return False
        if self.fecha_fin and turno.fecha > self.fecha_fin:
            return False
        
        # Verificar si aplica a la máquina específica o a todas
        if self.maquina and turno.maquina_id != self.maquina_id:
            return False
        
        # Verificar si el metraje cumple el mínimo
        if metros_turno >= self.metros_minimos:
            return True
        
        return False


class TurnoHoraExtra(models.Model):
    """
    Registro de horas extras otorgadas a trabajadores en un turno específico.
    Se calcula automáticamente al guardar el turno basándose en ConfiguracionHoraExtra.
    """
    turno = models.ForeignKey('Turno', on_delete=models.CASCADE, related_name='horas_extras')
    trabajador = models.ForeignKey('Trabajador', on_delete=models.PROTECT, related_name='horas_extras')
    horas_extra = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name='Horas extra otorgadas'
    )
    metros_turno = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Metraje del turno (m)',
        help_text='Metraje que generó las horas extras'
    )
    configuracion_aplicada = models.ForeignKey(
        ConfiguracionHoraExtra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Configuración aplicada'
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'turno_hora_extra'
        ordering = ['-turno__fecha', 'trabajador__apellidos']
        verbose_name = 'Hora Extra de Turno'
        verbose_name_plural = 'Horas Extras de Turnos'
        unique_together = [('turno', 'trabajador')]

    def __str__(self):
        return f"{self.trabajador} - {self.turno.fecha} - {self.horas_extra}h extra"


# =============================================================================
# SECCIÓN 2: PERSONAL - Cargos, Trabajadores, Asistencia, Horas Extras
# =============================================================================

class Cargo(models.Model):
    id_cargo = models.IntegerField(primary_key=True, verbose_name='ID Cargo')
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre del cargo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    # Jerarquía organizacional
    nivel_jerarquico = models.IntegerField(
        default=99, 
        verbose_name='Nivel Jerárquico',
        help_text='Nivel en el organigrama (1=más alto como RESIDENTE, 99=más bajo)'
    )
    cargo_superior = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subordinados',
        verbose_name='Cargo Superior',
        help_text='Cargo al que reporta este cargo en la jerarquía'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cargos'
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'
        ordering = ['nivel_jerarquico', 'nombre']

    def __str__(self):
        return self.nombre

class Trabajador(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('CESADO', 'Cesado'),
    ]
    
    SUBESTADO_CHOICES = [
        ('EN_OPERACION', 'En Operación'),
        ('DESCANSO_MEDICO', 'Descanso Médico'),
        ('DIAS_LIBRES', 'Días Libres'),
        ('FALTA', 'Falta'),
    ]

    TIPO_TRABAJO_CHOICES = [
        ('SUBTERRANEA', 'Interior Mina'),
        ('SUPERFICIAL', 'Superficial'),
    ]
    
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='trabajadores')
    nombres = models.CharField(max_length=200)
    apellidos = models.CharField(max_length=200, blank=True)
    tipo_trabajo = models.CharField(max_length=20, choices=TIPO_TRABAJO_CHOICES, default='SUBTERRANEA', verbose_name='Tipo de Trabajo')
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name='trabajadores', verbose_name='Cargo')
    area = models.CharField(max_length=100, blank=True, verbose_name='Área', help_text='Área de trabajo del trabajador')
    
    # =====================================================================
    # NOTA IMPORTANTE: Campo para visualización en organigrama únicamente
    # =====================================================================
    # Este campo NO afecta la lógica operativa de turnos, sondajes ni asignaciones diarias.
    # Es solo un campo de referencia esquemático para mostrar estructura organizacional.
    # Las asignaciones reales de trabajadores a máquinas se manejan a través de:
    # - TurnoTrabajador (asignaciones por turno)
    # - TurnoActividad (actividades realizadas en el turno)
    # Mantener SIEMPRE como opcional (null=True, blank=True) para no romper flujos existentes.
    maquina_asignada = models.ForeignKey(
        'Maquina',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trabajadores_asignados',
        verbose_name='Máquina Asignada (Organigrama)',
        help_text='⚠️ SOLO PARA ORGANIGRAMA - No afecta asignaciones operativas reales'
    )
    
    # Guardia asignada para organigrama (A, B, C)
    GUARDIA_CHOICES = [
        ('A', 'Guardia A'),
        ('B', 'Guardia B'),
        ('C', 'Guardia C'),
    ]
    guardia_asignada = models.CharField(
        max_length=1,
        choices=GUARDIA_CHOICES,
        null=True,
        blank=True,
        verbose_name='Guardia (Organigrama)',
        help_text='⚠️ SOLO PARA ORGANIGRAMA - Guardia A, B o C para visualización'
    )
    
    # Personal de reserva / standby
    es_standby = models.BooleanField(
        default=False,
        verbose_name='Personal STANDBY',
        help_text='Marca este trabajador como personal de reserva para cubrir ausencias. No se asigna a guardia fija.'
    )

    # Régimen Laboral
    REGIMEN_CHOICES = [
        ('14x7', '14 Días Trabajo x 7 Días Descanso'),
        ('20x10', '20 Días Trabajo x 10 Días Descanso'),
        ('28x14', '28 Días Trabajo x 14 Días Descanso'),
        ('5x2', '5 Días Trabajo x 2 Días Descanso'),
        ('6x1', '6 Días Trabajo x 1 Día Descanso'),
    ]
    regimen_laboral = models.CharField(
        max_length=10,
        choices=REGIMEN_CHOICES,
        default='14x7',
        verbose_name='Régimen Laboral'
    )
    fecha_inicio_ciclo = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Inicio de Ciclo',
        help_text='Fecha de inicio del ciclo actual (Día 1 de trabajo)'
    )
    
    # =====================================================================
    # Vehículo asignado (principalmente para conductores en organigrama)
    # =====================================================================
    vehiculo_asignado = models.ForeignKey(
        'Vehiculo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conductores_asignados',
        verbose_name='Vehículo Asignado (Organigrama)',
        help_text='⚠️ SOLO PARA ORGANIGRAMA - Vehículo asignado especialmente para conductores'
    )
    
    # `dni` debe ser único y no nulo; mantenemos la columna `id` como PK
    # para evitar romper relaciones existentes en la base de datos.
    dni = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    # Estados del trabajador
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO', help_text='Estado principal del trabajador')
    subestado = models.CharField(max_length=30, choices=SUBESTADO_CHOICES, default='EN_OPERACION', help_text='Estado operacional del trabajador')
    # Fotocheck
    fotocheck_fecha_emision = models.DateField(null=True, blank=True, verbose_name='Fecha emisión fotocheck')
    fotocheck_fecha_caducidad = models.DateField(null=True, blank=True, verbose_name='Fecha caducidad fotocheck')
    # Examen médico ocupacional (EMO)
    emo_fecha_realizado = models.DateField(null=True, blank=True, verbose_name='Fecha EMO realizado')
    emo_fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name='Fecha vencimiento EMO')
    emo_programacion = models.DateField(null=True, blank=True, verbose_name='Programación EMO', help_text='Fecha programada para próximo examen médico')
    emo_estado = models.CharField(max_length=20, blank=True, verbose_name='Estado EMO', help_text='Estado del examen médico ocupacional')
    
    # Grupo funcional del trabajador (se asigna automáticamente según cargo)
    GRUPO_CHOICES = [
        ('OPERADORES_INTERIOR_MINA', 'Operadores Interior Mina'),
        ('OPERADORES_SUPERFICIE', 'Operadores Superficie'),
        ('SERVICIOS_GEOLOGICOS_INTERIOR_MINA', 'Servicios Geológicos Interior Mina'),
        ('SERVICIOS_GEOLOGICOS_SUPERFICIE', 'Servicios Geológicos Superficie'),
        ('PERSONAL_AUXILIAR_INTERIOR_MINA', 'Personal Auxiliar Interior Mina'),
        ('PERSONAL_AUXILIAR_SUPERFICIE', 'Personal Auxiliar Superficie'),
        ('LINEA_MANDO', 'Línea de Mando'),
        # Legacy groups (keep for compatibility until data migration)
        ('OPERADORES', 'Operadores (Legacy)'),
        ('SERVICIOS_GEOLOGICOS', 'Servicios Geológicos (Legacy)'),
        ('PERSONAL_AUXILIAR', 'Personal Auxiliar (Legacy)'),
    ]
    grupo = models.CharField(
        max_length=50,
        choices=GRUPO_CHOICES,
        blank=True,
        verbose_name='Grupo Funcional',
        help_text='Se asigna automáticamente según el cargo y zona de trabajo'
    )
    
    # Timestamps automáticos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trabajadores'
        # Cuando 'dni' es PK global, no es necesaria una constraint ('contrato','dni')
        # unique_together se elimina para evitar duplicación de restricciones.
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['subestado']),
            models.Index(fields=['contrato', 'estado']),
            models.Index(fields=['fotocheck_fecha_caducidad']),
            models.Index(fields=['emo_fecha_vencimiento']),
            models.Index(fields=['emo_programacion']),
            models.Index(fields=['area']),
            models.Index(fields=['grupo']),
            models.Index(fields=['contrato', 'grupo']),
        ]
    # Usar 'dni' como clave primaria para identificar al trabajador
    # (se establece más abajo como primary_key=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos or ''} - {self.cargo.nombre}"
    
    def calcular_estado_regimen(self, fecha_consulta):
        """
        Calcula el estado esperado (TRABAJADO o DIA_LIBRE) según el régimen y fecha de inicio.
        Retorna None si no hay datos suficientes.
        """
        if not self.fecha_inicio_ciclo or not self.regimen_laboral:
            return None
            
        # Parsear régimen (ej: "14x7")
        try:
            dias_trabajo, dias_descanso = map(int, self.regimen_laboral.lower().split('x'))
            ciclo_total = dias_trabajo + dias_descanso
        except ValueError:
            return None
            
        delta = (fecha_consulta - self.fecha_inicio_ciclo).days
        
        # Si la fecha es anterior al inicio, no aplica
        if delta < 0:
            return None
            
        dia_en_ciclo = delta % ciclo_total
        
        # Si está dentro de los días de trabajo (0 a dias_trabajo - 1)
        if dia_en_ciclo < dias_trabajo:
            return 'TRABAJADO'
        else:
            return 'DIA_LIBRE'

    def asignar_maquina_por_defecto(self):
        """
        Asigna una máquina y guardia por defecto cumpliendo la maqueta:
        - 3 Guardias (A, B, C)
        - 1 Perforista por guardia
        - 2 Ayudantes por guardia
        
        Si ya tiene guardia asignada, busca máquina con cupo en esa guardia.
        Si no tiene guardia, busca el primer cupo disponible.
        """
        if not self.cargo:
            return None
        
        cargo_nombre = self.cargo.nombre.upper()
        
        # Identificar rol
        is_perforista = 'PERFORISTA' in cargo_nombre
        is_ayudante = 'AYUDANTE' in cargo_nombre
        
        if not (is_perforista or is_ayudante):
            return None
            
        # Obtener máquinas operativas del contrato
        maquinas = Maquina.objects.filter(
            contrato=self.contrato,
            estado='OPERATIVO'
        ).order_by('nombre')
        
        # Guardias a revisar (preferir la asignada si existe)
        guardias_a_revisar = ['A', 'B', 'C']
        if self.guardia_asignada and self.guardia_asignada in guardias_a_revisar:
             guardias_a_revisar = [self.guardia_asignada]

        # Iterar máquinas y guardias buscando cupo
        # ESTRATEGIA:
        # Perforistas: Llenado simple (si falta 1 -> entra)
        # Ayudantes: Balanceo de carga (primero asegurar 1 ayudante en todas, luego completar el 2do)

        if is_perforista:
            for maquina in maquinas:
                for guardia in guardias_a_revisar:
                    ocupantes = self.__class__.objects.filter(
                        maquina_asignada=maquina,
                        guardia_asignada=guardia,
                        estado='ACTIVO'
                    )
                    if self.pk: ocupantes = ocupantes.exclude(pk=self.pk)
                    
                    cant_perforistas = ocupantes.filter(cargo__nombre__icontains='PERFORISTA').count()
                    
                    if cant_perforistas < 1:
                        if not self.guardia_asignada: self.guardia_asignada = guardia
                        return maquina
        
        elif is_ayudante:
            # Fase 1: Buscar huecos donde NO HAY ayudantes (prioridad operativa)
            for maquina in maquinas:
                for guardia in guardias_a_revisar:
                    ocupantes = self.__class__.objects.filter(
                        maquina_asignada=maquina,
                        guardia_asignada=guardia,
                        estado='ACTIVO'
                    )
                    if self.pk: ocupantes = ocupantes.exclude(pk=self.pk)
                    
                    cant_ayudantes = ocupantes.filter(cargo__nombre__icontains='AYUDANTE').count()
                    
                    if cant_ayudantes < 1: # Prioridad: Asegurar al menos 1
                        if not self.guardia_asignada: self.guardia_asignada = guardia
                        return maquina
            
            # Fase 2: Si todos tienen al menos 1, buscar huecos para el 2do ayudante
            for maquina in maquinas:
                for guardia in guardias_a_revisar:
                    ocupantes = self.__class__.objects.filter(
                        maquina_asignada=maquina,
                        guardia_asignada=guardia,
                        estado='ACTIVO'
                    )
                    if self.pk: ocupantes = ocupantes.exclude(pk=self.pk)
                    
                    cant_ayudantes = ocupantes.filter(cargo__nombre__icontains='AYUDANTE').count()
                    
                    if cant_ayudantes < 2: # Completar dotación ideal
                        if not self.guardia_asignada: self.guardia_asignada = guardia
                        return maquina
        
        return None

    def asignar_grupo_automatico(self):
        """
        Asigna automáticamente el grupo funcional basado en el cargo del trabajador
        y su tipo de trabajo / máquina asignada.
        
        Reglas de asignación:
        - OPERADORES: Perforistas, Ayudantes. Se dividen en Interior Mina / Superficie.
        - SERVICIOS_GEOLOGICOS: Muestreros, Geólogos. Se dividen en Interior Mina / Superficie.
        - PERSONAL_AUXILIAR: Conductores, Mecánicos. Se dividen en Interior Mina / Superficie.
        - LINEA_MANDO: Todos los demás cargos. No se divide.
        """
        if not self.cargo:
            return None
        
        # Determinar zona de trabajo (Interior Mina vs Superficie)
        # Prioridad: 1. Máquina asignada, 2. Tipo de trabajo del trabajador
        es_subterranea = True
        
        # Si tiene máquina asignada, usar su tipo
        if self.maquina_asignada:
            # Si maquina tiene atributo tipo_trabajo (que acabamos de añadir)
            if hasattr(self.maquina_asignada, 'tipo_trabajo'):
                es_subterranea = (self.maquina_asignada.tipo_trabajo == 'SUBTERRANEA')
        else:
            # Usar preferencia del trabajador
            es_subterranea = (self.tipo_trabajo == 'SUBTERRANEA')
            
        suffix = '_INTERIOR_MINA' if es_subterranea else '_SUPERFICIE'
        
        # PERSONAL STANDBY: Se agrupa con Personal Auxiliar
        if self.es_standby:
            return f'PERSONAL_AUXILIAR{suffix}'
        
        cargo_nombre = self.cargo.nombre.upper().strip()
        
        # OPERADORES: Perforistas, Ayudantes DDH y Ayudante Perforista
        operadores_keywords = [
            'PERFORISTA DDH-I',
            'PERFORISTA DDH-II',
            'AYUDANTE DDH-I',
            'AYUDANTE DDH-II',
            'AYUDANTE PERFORISTA',
            'AYUDANTE DE PERFORISTA'
        ]
        if any(keyword in cargo_nombre for keyword in operadores_keywords):
            return f'OPERADORES{suffix}'
        
        # SERVICIOS GEOLÓGICOS
        servicios_geologicos_keywords = [
            'AYUDANTE MUESTRERO',
            'MAESTRO MUESTRERO',
            'CORTADOR DE TESTIGOS',
            'GEOLOGO PLENO LOGUEO GEOMECANICO',
            'GEÓLOGO PLENO LOGUEO GEOMECÁNICO',
            'GEOLOGO JUNIOR DE LOGUEO',
            'GEÓLOGO JUNIOR DE LOGUEO',
            'ASISTENTE DE DENSIDAD'
        ]
        if any(keyword in cargo_nombre for keyword in servicios_geologicos_keywords):
            return f'SERVICIOS_GEOLOGICOS{suffix}'
        
        # PERSONAL AUXILIAR: Conductores y Mecánicos
        auxiliar_keywords = ['CONDUCTOR', 'MECANICO', 'MECÁNICO', 'TECNICO MECANICO']
        if any(keyword in cargo_nombre for keyword in auxiliar_keywords):
            return f'PERSONAL_AUXILIAR{suffix}'
        
        # LINEA DE MANDO: Todos los demás
        return 'LINEA_MANDO'
    
    def save(self, *args, **kwargs):
        """Override save para asignar automáticamente el grupo y máquina"""
        # Asignar grupo automáticamente si no tiene o si cambió el cargo
        if self.cargo:
            grupo_calculado = self.asignar_grupo_automatico()
            if grupo_calculado:
                self.grupo = grupo_calculado
        
        # Asignar máquina por defecto si no tiene una asignada
        # y es perforista o ayudante
        if not self.maquina_asignada and self.cargo:
            try:
                # Verificar si es personal operativo
                cargo_upper = self.cargo.nombre.upper()
                es_operativo = 'PERFORISTA' in cargo_upper or 'AYUDANTE' in cargo_upper
                
                if es_operativo:
                    maquina_sugerida = self.asignar_maquina_por_defecto()
                    if maquina_sugerida:
                        self.maquina_asignada = maquina_sugerida
                        # Si se asignó máquina, ya no es standby (salvo que sea explícito)
                        if self.es_standby and not self.pk: # Solo al crear
                             self.es_standby = False
                    else:
                        # Si NO hay cupo en ninguna máquina, se marca como STANDBY automáticamente
                        if not self.maquina_asignada:
                            self.es_standby = True
                            # Actualizar grupo a Personal Auxiliar
                            nuevo_grupo = self.asignar_grupo_automatico()
                            if nuevo_grupo:
                                self.grupo = nuevo_grupo
            except Exception:
                pass # Evitar errores bloqueantes en save()
        
        super().save(*args, **kwargs)


class HistorialLaboral(models.Model):
    """
    Historial de cambios laborales del trabajador (Cargo, Guardia, Régimen)
    """
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name='historial_laboral')
    fecha_inicio = models.DateField(verbose_name='Fecha Inicio')
    fecha_fin = models.DateField(null=True, blank=True, verbose_name='Fecha Fin')
    
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, verbose_name='Cargo')
    guardia = models.CharField(max_length=1, choices=Trabajador.GUARDIA_CHOICES, null=True, blank=True, verbose_name='Guardia')
    regimen = models.CharField(max_length=10, choices=Trabajador.REGIMEN_CHOICES, null=True, blank=True, verbose_name='Régimen')
    
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'Historial Laboral'
        verbose_name_plural = 'Historiales Laborales'
        ordering = ['-fecha_inicio']


# =============================================================================
# SECCIÓN 6: TURNOS - Turno y modelos relacionados
# =============================================================================

class Turno(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('COMPLETADO', 'Completado'),
        ('APROBADO', 'Aprobado'),
    ]
    
    # Relación directa con contrato (requerida para integridad)
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='turnos')
    # Un turno puede ahora estar asociado a uno o varios sondajes.
    # Usamos un modelo intermedio `TurnoSondaje` (through) para permitir
    # extender la relación en el futuro con datos por sondaje si es necesario.
    sondajes = models.ManyToManyField(Sondaje, related_name='turnos', through='TurnoSondaje', blank=True)
    maquina = models.ForeignKey(Maquina, on_delete=models.PROTECT, related_name='turnos')
    tipo_turno = models.ForeignKey(TipoTurno, on_delete=models.PROTECT)
    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR')
    comentarios_perforistas = models.TextField(blank=True, verbose_name='Comentarios de Perforistas')
    litologia_general = models.TextField(blank=True, verbose_name='Litología General')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'turnos'
        verbose_name = 'Turno'
        verbose_name_plural = 'Turnos'
        # Constraint: un turno es único por contrato, máquina, fecha y tipo_turno
        # Esto asegura que no haya turnos duplicados para la misma máquina en el mismo día
        unique_together = ['contrato', 'maquina', 'fecha', 'tipo_turno']
        indexes = [
            models.Index(fields=['contrato', 'fecha']),
            models.Index(fields=['maquina', 'fecha']),
        ]

    def clean(self):
        """Validaciones personalizadas del modelo"""
        # Validar que máquina pertenece al mismo contrato
        if self.maquina and self.maquina.contrato != self.contrato:
            raise ValidationError(
                'La máquina seleccionada no pertenece al contrato del turno'
            )

    def save(self, *args, **kwargs):
        """Override save para aplicar validaciones"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        try:
            # Mostrar uno o varios sondajes si existen
            if self.pk:
                sondajes = list(self.sondajes.all()[:3])
                if len(sondajes) == 1:
                    return f"Turno {self.id} - {sondajes[0].nombre_sondaje} - {self.fecha}"
                elif len(sondajes) > 1:
                    names = ', '.join([s.nombre_sondaje for s in sondajes])
                    return f"Turno {self.id} - {names} - {self.fecha}"
        except Exception:
            pass
        return f"Turno {self.id} - {self.fecha}"

class TurnoTrabajador(models.Model):
    FUNCION_CHOICES = [
        ('PERFORISTA', 'Perforista'),
        ('AYUDANTE', 'Ayudante'),
    ]
    
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='trabajadores_turno')
    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT)
    funcion = models.CharField(max_length=30, choices=FUNCION_CHOICES)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'turno_trabajador'
        unique_together = ['turno', 'trabajador']
        indexes = [
            models.Index(fields=['turno']),
            models.Index(fields=['trabajador']),
            models.Index(fields=['funcion']),
        ]
    
class TurnoSondaje(models.Model):
    """Modelo intermedio que asocia un Turno con un Sondaje.

    Dejarlo simple por ahora (turno, sondaje, created_at). En el futuro se
    pueden añadir métricas por sondaje (metros_perforados, observaciones, etc.)
    sin romper la relación M2M.
    """
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='turno_sondajes')
    sondaje = models.ForeignKey(Sondaje, on_delete=models.PROTECT, related_name='sondaje_turnos')
    metros_turno = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'turno_sondaje'
        unique_together = ['turno', 'sondaje']
        indexes = [
            models.Index(fields=['turno']),
            models.Index(fields=['sondaje']),
        ]

    def clean(self):
        """Validaciones personalizadas del modelo"""
        # Validar que el sondaje pertenece al mismo contrato del turno
        if self.sondaje and self.turno and self.sondaje.contrato != self.turno.contrato:
            raise ValidationError(
                f'El sondaje "{self.sondaje.nombre_sondaje}" no pertenece al contrato del turno. '
                f'Sondaje contrato: {self.sondaje.contrato}, Turno contrato: {self.turno.contrato}'
            )

    def save(self, *args, **kwargs):
        """Override save para aplicar validaciones"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Turno {self.turno_id} - Sondaje {self.sondaje_id}"


class TurnoAvance(models.Model):
    turno = models.OneToOneField(Turno, on_delete=models.CASCADE, related_name='avance')
    metros_perforados = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'turno_avance'
        indexes = [
            models.Index(fields=['turno']),
            models.Index(fields=['-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """
        Guardar el avance y calcular horas extras para todos los trabajadores del turno
        """
        super().save(*args, **kwargs)
        
        # Después de guardar el avance, calcular horas extras
        self.calcular_horas_extras()
    
    def calcular_horas_extras(self):
        """
        Calcula y asigna horas extras a todos los trabajadores del turno
        según las reglas específicas por contrato:
        
        - Americana: > 25 metros → 1 hora extra
        - Colquisiri: > 15 metros → 1 hora extra
        """
        from decimal import Decimal
        
        # Reglas de horas extras por contrato (nombre del contrato)
        REGLAS_HORAS_EXTRAS = {
            'AMERICANA': {'metros_minimos': Decimal('25.00'), 'horas_extra': Decimal('1.00')},
            'COLQUISIRI': {'metros_minimos': Decimal('15.00'), 'horas_extra': Decimal('1.00')},
        }
        
        # Obtener nombre del contrato en mayúsculas para comparación
        nombre_contrato = self.turno.contrato.nombre_contrato.upper().strip()
        
        # Buscar si existe una regla para este contrato
        regla = None
        for contrato_key, config in REGLAS_HORAS_EXTRAS.items():
            if contrato_key in nombre_contrato:
                regla = config
                break
        
        # Si no hay regla específica, buscar configuración en BD (fallback)
        if not regla:
            configuraciones = ConfiguracionHoraExtra.objects.filter(
                contrato=self.turno.contrato,
                activo=True
            ).select_related('maquina')
            
            config_aplicable = None
            
            # Primero buscar configuración específica de la máquina
            for config in configuraciones:
                if config.maquina and config.maquina_id == self.turno.maquina_id:
                    if config.aplica_para_turno(self.turno, self.metros_perforados):
                        config_aplicable = config
                        break
            
            # Si no hay configuración específica, buscar configuración general
            if not config_aplicable:
                for config in configuraciones:
                    if not config.maquina:
                        if config.aplica_para_turno(self.turno, self.metros_perforados):
                            config_aplicable = config
                            break
            
            if config_aplicable:
                regla = {
                    'metros_minimos': config_aplicable.metros_minimos,
                    'horas_extra': config_aplicable.horas_extra,
                    'config_obj': config_aplicable
                }
        
        # Verificar si se cumplen las condiciones para otorgar horas extras
        aplica_horas_extras = False
        if regla and self.metros_perforados > regla['metros_minimos']:
            aplica_horas_extras = True
        
        # Eliminar horas extras previas de este turno (por si se está actualizando)
        TurnoHoraExtra.objects.filter(turno=self.turno).delete()
        
        # Si aplica, crear registros de horas extras para cada trabajador
        if aplica_horas_extras:
            # Obtener todos los trabajadores del turno
            trabajadores_turno = self.turno.trabajadores_turno.select_related('trabajador')
            
            # Crear registro de horas extras para cada trabajador
            horas_extras_list = []
            for tt in trabajadores_turno:
                horas_extras_list.append(
                    TurnoHoraExtra(
                        turno=self.turno,
                        trabajador=tt.trabajador,
                        horas_extra=regla['horas_extra'],
                        metros_turno=self.metros_perforados,
                        configuracion_aplicada=regla.get('config_obj'),
                        observaciones=f'Generado automáticamente. Contrato: {nombre_contrato}. Metraje: {self.metros_perforados}m > {regla["metros_minimos"]}m'
                    )
                )
            
            # Crear todos los registros en una sola operación
            if horas_extras_list:
                TurnoHoraExtra.objects.bulk_create(horas_extras_list)

class TurnoMaquina(models.Model):
    ESTADO_CHOICES = [
        ('OPERATIVO', 'Operativo'),
        ('DEFICIENTE', 'Deficiente'),
        ('INOPERATIVO', 'Inoperativo'),
    ]
    
    turno = models.OneToOneField(Turno, on_delete=models.CASCADE, related_name='maquina_estado')
    # Horas expresadas como lectura de horómetro (contador) o como time. Preferimos
    # usar las lecturas de horómetro cuando están disponibles (horometro_inicio/fin).
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    horometro_inicio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    horometro_fin = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    horas_trabajadas_calc = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    estado_bomba = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    estado_unidad = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    estado_rotacion = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    comentarios_mantenimiento = models.TextField(blank=True, verbose_name='Comentarios de Mantenimiento')

    class Meta:
        db_table = 'turno_maquina'

    def save(self, *args, **kwargs):
        from datetime import datetime, timedelta

        # Priorizar cálculo a partir de lecturas de horómetro (si se proporcionaron)
        try:
            if self.horometro_inicio is not None and self.horometro_fin is not None:
                # Horómetro representa un contador; la diferencia es la cantidad a sumar
                try:
                    self.horas_trabajadas_calc = Decimal(self.horometro_fin) - Decimal(self.horometro_inicio)
                except Exception:
                    self.horas_trabajadas_calc = Decimal('0')
                return super().save(*args, **kwargs)
        except Exception:
            # Caer a cálculo por tiempo si algo falla
            pass

        # Si no hay lecturas de horómetro completas, intentar calcular desde times
        if not self.hora_inicio or not self.hora_fin:
            try:
                self.horas_trabajadas_calc = Decimal('0')
            except Exception:
                self.horas_trabajadas_calc = 0
            return super().save(*args, **kwargs)

        # Ambos tiempos presentes, calcular horas trabajadas (horas decimales)
        inicio = datetime.combine(datetime.today(), self.hora_inicio)
        fin = datetime.combine(datetime.today(), self.hora_fin)
        if fin < inicio:
            fin += timedelta(days=1)
        diff = fin - inicio
        self.horas_trabajadas_calc = Decimal(str(diff.total_seconds() / 3600))
        super().save(*args, **kwargs)

class TurnoComplemento(models.Model):
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='complementos')
    sondaje = models.ForeignKey(Sondaje, on_delete=models.PROTECT, null=True, blank=True, related_name='complementos_turno')
    tipo_complemento = models.ForeignKey(TipoComplemento, on_delete=models.PROTECT)
    codigo_serie = models.CharField(max_length=100)
    metros_inicio = models.DecimalField(max_digits=8, decimal_places=2)
    metros_fin = models.DecimalField(max_digits=8, decimal_places=2)
    metros_turno_calc = models.DecimalField(max_digits=8, decimal_places=2, editable=False)

    class Meta:
        db_table = 'turno_complemento'
        indexes = [
            models.Index(fields=['turno']),
            models.Index(fields=['sondaje']),
            models.Index(fields=['tipo_complemento']),
            models.Index(fields=['codigo_serie']),
        ]

    def clean(self):
        """Validaciones personalizadas"""
        if self.sondaje and self.turno:
            if self.sondaje.contrato != self.turno.contrato:
                raise ValidationError(
                    f'El sondaje no pertenece al contrato del turno. '
                    f'Sondaje contrato: {self.sondaje.contrato}, Turno contrato: {self.turno.contrato}'
                )

    def save(self, *args, **kwargs):
        # Verificar si ya se calculó metros_turno_calc (por bulk_create)
        if not self.metros_turno_calc:
            self.full_clean()
            self.metros_turno_calc = self.metros_fin - self.metros_inicio
        super().save(*args, **kwargs)
        
        # Actualizar historial de la broca automáticamente
        # Solo si no viene de bulk_create (indicado por skip_historial)
        if not kwargs.get('skip_historial', False):
            self.actualizar_historial_broca()
    
    def actualizar_historial_broca(self):
        """
        Actualiza el historial consolidado de la broca.
        Se ejecuta automáticamente al guardar un registro de uso.
        """
        from django.db.models import F
        
        # Obtener o crear el registro de historial para esta serie
        historial, created = HistorialBroca.objects.get_or_create(
            serie=self.codigo_serie,
            defaults={
                'tipo_complemento': self.tipo_complemento,
                'contrato_actual': self.turno.contrato,
                'fecha_primer_uso': self.turno.fecha,
                'estado': 'NUEVA'
            }
        )
        
        # Actualizar métricas acumuladas
        historial.metraje_acumulado = F('metraje_acumulado') + self.metros_turno_calc
        historial.numero_usos = F('numero_usos') + 1
        historial.fecha_ultimo_uso = self.turno.fecha
        
        # Actualizar estado automáticamente si es nueva y ya se usó
        if created or historial.estado == 'NUEVA':
            historial.estado = 'EN_USO'
        
        historial.save(update_fields=['metraje_acumulado', 'numero_usos', 'fecha_ultimo_uso', 'estado'])
        
        # Refrescar para obtener valores reales (después de F() expressions)
        historial.refresh_from_db()


class HistorialBroca(models.Model):
    """
    Historial consolidado y seguimiento individual de cada broca diamantada por serie.
    Acumula automáticamente el metraje de todos los usos registrados en TurnoComplemento.
    
    Este modelo permite:
    - Consultar rápidamente el metraje total acumulado de una broca
    - Hacer seguimiento del ciclo de vida (Nueva → En Uso → Desgastada → Quemada)
    - Obtener estadísticas de uso sin queries agregadas pesadas
    - Identificar brocas próximas a fin de vida útil
    """
    
    ESTADO_CHOICES = [
        ('NUEVA', 'Nueva'),
        ('EN_USO', 'En Uso'),
        ('DESGASTADA', 'Desgastada'),
        ('QUEMADA', 'Quemada'),
        ('FUERA_SERVICIO', 'Fuera de Servicio'),
        ('PERDIDA', 'Perdida'),
    ]
    
    # Identificación de la broca
    serie = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name='Serie',
        help_text='Código de serie único de la broca'
    )
    
    tipo_complemento = models.ForeignKey(
        TipoComplemento,
        on_delete=models.PROTECT,
        related_name='historiales',
        verbose_name='Tipo de Producto'
    )
    
    contrato_actual = models.ForeignKey(
        Contrato,
        on_delete=models.PROTECT,
        related_name='brocas_historial',
        verbose_name='Contrato Actual',
        help_text='Último contrato donde se usó la broca'
    )
    
    # Métricas de vida útil (se actualizan automáticamente)
    metraje_acumulado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Metraje Acumulado (m)',
        help_text='Total de metros perforados con esta broca'
    )
    
    numero_usos = models.PositiveIntegerField(
        default=0,
        verbose_name='Número de Usos',
        help_text='Cantidad de turnos donde se usó esta broca'
    )
    
    # Estado y fechas
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='NUEVA',
        db_index=True,
        verbose_name='Estado'
    )
    
    fecha_primer_uso = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha Primer Uso'
    )
    
    fecha_ultimo_uso = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Fecha Último Uso'
    )
    
    fecha_baja = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Baja',
        help_text='Fecha en que se dio de baja la broca (quemada, perdida, etc.)'
    )
    
    # Observaciones
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
        help_text='Notas sobre el estado de la broca, desgaste observado, etc.'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'historial_broca'
        verbose_name = 'Historial de Broca'
        verbose_name_plural = 'Historiales de Brocas'
        ordering = ['-fecha_ultimo_uso', '-metraje_acumulado']
        indexes = [
            models.Index(fields=['serie']),
            models.Index(fields=['estado']),
            models.Index(fields=['contrato_actual', 'estado']),
            models.Index(fields=['-metraje_acumulado']),
            models.Index(fields=['-fecha_ultimo_uso']),
        ]
    
    def __str__(self):
        return f"{self.serie} - {self.tipo_complemento.nombre} [{self.get_estado_display()}] - {self.metraje_acumulado}m"
    
    def metraje_promedio_por_uso(self):
        """Calcula el metraje promedio por uso"""
        if self.numero_usos == 0:
            return Decimal('0.00')
        return self.metraje_acumulado / self.numero_usos
    
    def dias_desde_primer_uso(self):
        """Calcula los días transcurridos desde el primer uso"""
        from datetime import date
        if not self.fecha_primer_uso:
            return None
        return (date.today() - self.fecha_primer_uso).days
    
    def dias_sin_uso(self):
        """Calcula los días sin usar la broca"""
        from datetime import date
        if not self.fecha_ultimo_uso:
            return None
        return (date.today() - self.fecha_ultimo_uso).days
    
    def esta_activa(self):
        """Verifica si la broca está activa (no quemada, perdida o fuera de servicio)"""
        return self.estado in ['NUEVA', 'EN_USO', 'DESGASTADA']
    
    def marcar_como_quemada(self, observaciones=''):
        """Marca la broca como quemada y registra la fecha"""
        from datetime import date
        self.estado = 'QUEMADA'
        self.fecha_baja = date.today()
        if observaciones:
            self.observaciones = f"{self.observaciones}\n{observaciones}" if self.observaciones else observaciones
        self.save(update_fields=['estado', 'fecha_baja', 'observaciones', 'updated_at'])
    
    def obtener_historial_detallado(self):
        """Obtiene todos los usos detallados de esta broca desde TurnoComplemento"""
        return TurnoComplemento.objects.filter(
            codigo_serie=self.serie
        ).select_related(
            'turno',
            'turno__maquina',
            'turno__contrato',
            'sondaje',
            'tipo_complemento'
        ).order_by('turno__fecha')


class TurnoAditivo(models.Model):
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='aditivos')
    sondaje = models.ForeignKey(Sondaje, on_delete=models.PROTECT, null=True, blank=True, related_name='aditivos_turno')
    tipo_aditivo = models.ForeignKey(TipoAditivo, on_delete=models.PROTECT)
    cantidad_usada = models.DecimalField(max_digits=8, decimal_places=2)
    unidad_medida = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT)

    class Meta:
        db_table = 'turno_aditivo'

    def clean(self):
        """Validaciones personalizadas"""
        if self.sondaje and self.turno:
            if self.sondaje.contrato != self.turno.contrato:
                raise ValidationError(
                    f'El sondaje no pertenece al contrato del turno. '
                    f'Sondaje contrato: {self.sondaje.contrato}, Turno contrato: {self.turno.contrato}'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class TurnoCorrida(models.Model):
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='corridas')
    corrida_numero = models.PositiveIntegerField()
    desde = models.DecimalField(max_digits=8, decimal_places=2)
    hasta = models.DecimalField(max_digits=8, decimal_places=2)
    total_calc = models.DecimalField(max_digits=8, decimal_places=2, editable=False)
    longitud_testigo = models.DecimalField(max_digits=8, decimal_places=2)
    pct_recuperacion = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))])
    pct_retorno_agua = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))])
    litologia = models.TextField()

    class Meta:
        db_table = 'turno_corrida'
        unique_together = ['turno', 'corrida_numero']

    def save(self, *args, **kwargs):
        self.total_calc = self.hasta - self.desde
        super().save(*args, **kwargs)

class TurnoActividad(models.Model):
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='actividades')
    actividad = models.ForeignKey(TipoActividad, on_delete=models.PROTECT)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)  
    tiempo_calc = models.DecimalField(max_digits=4, decimal_places=2, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'turno_actividad'

    def save(self, *args, **kwargs):
        from datetime import datetime, timedelta

        # Manejar casos donde las horas no estén completas
        if not self.hora_inicio or not self.hora_fin:
            try:
                self.tiempo_calc = Decimal('0')
            except Exception:
                self.tiempo_calc = 0
            return super().save(*args, **kwargs)

        inicio = datetime.combine(datetime.today(), self.hora_inicio)
        fin = datetime.combine(datetime.today(), self.hora_fin)

        if fin < inicio:
            fin += timedelta(days=1)

        diff = fin - inicio
        self.tiempo_calc = Decimal(str(diff.total_seconds() / 3600))
        super().save(*args, **kwargs)

class Abastecimiento(models.Model):
    FAMILIA_CHOICES = [
        ('PRODUCTOS_DIAMANTADOS', 'Productos Diamantados'),
        ('ADITIVOS_PERFORACION', 'Aditivos de Perforación'),
        ('CONSUMIBLES', 'Consumibles'),
        ('REPUESTOS', 'Repuestos'),
    ]
    
    mes = models.CharField(max_length=20)
    fecha = models.DateField()
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='abastecimientos')
    codigo_producto = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField()
    familia = models.CharField(max_length=30, choices=FAMILIA_CHOICES)
    serie = models.CharField(max_length=50, blank=True, null=True)
    unidad_medida = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    tipo_complemento = models.ForeignKey(TipoComplemento, on_delete=models.PROTECT, null=True, blank=True)
    tipo_aditivo = models.ForeignKey(TipoAditivo, on_delete=models.PROTECT, null=True, blank=True)
    numero_guia = models.CharField(max_length=50, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abastecimiento'
        verbose_name = 'Abastecimiento'
        verbose_name_plural = 'Abastecimientos'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['contrato']),
            models.Index(fields=['contrato', 'fecha']),
            models.Index(fields=['familia']),
            models.Index(fields=['-fecha']),
            models.Index(fields=['codigo_producto']),
            models.Index(fields=['serie']),
        ]

    def save(self, *args, **kwargs):
        self.total = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contrato.nombre_contrato} - {self.descripcion[:50]} ({self.fecha})"

class ConsumoStock(models.Model):
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='consumos')
    abastecimiento = models.ForeignKey(Abastecimiento, on_delete=models.PROTECT)
    cantidad_consumida = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    serie_utilizada = models.CharField(max_length=50, blank=True)
    metros_inicio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    metros_fin = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    metros_utilizados = models.DecimalField(max_digits=8, decimal_places=2, editable=False, null=True, blank=True)
    ESTADO_CHOICES = [
        ('OPTIMO', 'Óptimo'),
        ('BUENO', 'Bueno'),
        ('REGULAR', 'Regular'),
        ('DESGASTADO', 'Desgastado'),
        ('INUTILIZABLE', 'Inutilizable'),
    ]
    estado_final = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='OPTIMO')
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'consumo_stock'
        verbose_name = 'Consumo de Stock'
        verbose_name_plural = 'Consumos de Stock'

    def save(self, *args, **kwargs):
        if self.metros_inicio and self.metros_fin:
            self.metros_utilizados = self.metros_fin - self.metros_inicio
        super().save(*args, **kwargs)


class AbastecimientoArticulo(models.Model):
    """
    Registro de artículos abastecidos desde la API externa.
    Almacena el historial de todos los abastecimientos recibidos con su información completa.
    Se sincroniza periódicamente con el endpoint de abastecidos.
    """
    
    # Identificación y fecha
    fecha = models.DateField(
        db_index=True,
        verbose_name='Fecha de Abastecimiento'
    )
    
    centro_costo = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='Centro de Costo'
    )
    
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.PROTECT,
        related_name='abastecimientos_api',
        verbose_name='Contrato',
        help_text='Contrato asociado al centro de costo'
    )
    
    # Documentación
    documento = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='Número de Documento',
        help_text='Número de documento del abastecimiento'
    )
    
    documento_referencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Documento de Referencia',
        help_text='Documento de referencia asociado'
    )
    
    # Artículo
    codigo = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='Código de Artículo'
    )
    
    serie = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Serie',
        help_text='Serie individual del artículo (especialmente importante para brocas)'
    )
    
    descripcion = models.TextField(
        verbose_name='Descripción'
    )
    
    codigo_movimiento = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='Código de Movimiento'
    )
    
    # Cantidades y medidas
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad'
    )
    
    unidad = models.CharField(
        max_length=20,
        verbose_name='Unidad de Medida'
    )
    
    familia = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name='Familia',
        help_text='Familia del artículo (PDD, ADIT, etc.)'
    )
    
    # Precios
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio Unitario'
    )
    
    precio_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Precio Total'
    )
    
    # Relación con HistorialBroca (si es una broca con serie)
    historial_broca = models.ForeignKey(
        'HistorialBroca',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='abastecimientos',
        verbose_name='Historial de Broca',
        help_text='Referencia al historial de la broca (si aplica)'
    )
    
    # Timestamps
    fecha_sincronizacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Sincronización',
        help_text='Fecha en que se sincronizó este registro desde la API'
    )
    
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Actualización'
    )
    
    class Meta:
        db_table = 'abastecimiento_articulo'
        verbose_name = 'Abastecimiento de Artículo'
        verbose_name_plural = 'Abastecimientos de Artículos'
        ordering = ['-fecha', '-fecha_sincronizacion']
        unique_together = [
            ('documento', 'codigo', 'serie'),  # Un documento no puede tener el mismo artículo+serie duplicado
        ]
        indexes = [
            models.Index(fields=['fecha', 'centro_costo']),
            models.Index(fields=['familia', 'codigo']),
            models.Index(fields=['serie'], name='idx_abastec_serie'),
            models.Index(fields=['contrato', 'fecha']),
        ]
    
    def __str__(self):
        serie_info = f" - Serie: {self.serie}" if self.serie else ""
        return f"{self.codigo} ({self.descripcion[:30]}){serie_info} - {self.fecha}"
    
    def save(self, *args, **kwargs):
        """
        Al guardar, si es una broca con serie (familia PDD y tiene serie),
        crea o actualiza automáticamente el registro en HistorialBroca
        """
        super().save(*args, **kwargs)
        
        # Si es una broca con serie, sincronizar con HistorialBroca
        if self.familia == 'PDD' and self.serie:
            self._sincronizar_historial_broca()
    
    def _sincronizar_historial_broca(self):
        """
        Crea o actualiza el registro en HistorialBroca para esta broca
        """
        # Importar logging localmente por si falla la importación global
        import logging
        from django.utils import timezone
        
        try:
            # Buscar o crear el tipo de complemento basado en la descripción
            # Usar filter().first() para evitar error si existen duplicados
            tipo_complemento = TipoComplemento.objects.filter(nombre=self.descripcion[:100]).first()
            if not tipo_complemento:
                tipo_complemento = TipoComplemento.objects.create(
                    nombre=self.descripcion[:100],
                    categoria='BROCA',
                    descripcion=self.descripcion
                )
            
            # Buscar o crear el historial de broca
            historial, created = HistorialBroca.objects.get_or_create(
                serie=self.serie,
                defaults={
                    'tipo_complemento': tipo_complemento,
                    'contrato_actual': self.contrato,
                    'estado': 'NUEVA',
                    'metraje_acumulado': 0,
                    'numero_usos': 0,
                }
            )
            
            # Actualizar la referencia
            if self.historial_broca != historial:
                self.historial_broca = historial
                # Usar update para evitar recursión infinita
                AbastecimientoArticulo.objects.filter(pk=self.pk).update(
                    historial_broca=historial
                )
            
            # Si se creó el historial, registrar en observaciones
            if created:
                historial.observaciones = (
                    f"Abastecido el {self.fecha.strftime('%d/%m/%Y')} - "
                    f"Documento: {self.documento} - "
                    f"Precio: S/ {self.precio_unitario}"
                )
                historial.save(update_fields=['observaciones'])
                
        except Exception as e:
            try:
                logger = logging.getLogger(__name__)
                logger.error(f"Error al sincronizar historial de broca {self.serie}: {e}")
            except:
                print(f"FATAL ERROR syncing broca {self.serie}: {e}")
                # Re-raise para que no se oculte el error original si el logging falla
                raise e


class PrecioUnitarioServicio(models.Model):
    """
    Precios unitarios de servicios por contrato.
    Cada servicio (tipo de actividad) tiene un precio unitario que varía por contrato.
    """
    
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='precios_unitarios',
        verbose_name='Contrato'
    )
    
    servicio = models.ForeignKey(
        TipoActividad,
        on_delete=models.CASCADE,
        related_name='precios_unitarios',
        verbose_name='Servicio',
        help_text='Tipo de actividad/servicio a valorizar'
    )
    
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Precio Unitario (PU)',
        help_text='Precio por metro perforado en la moneda del contrato'
    )
    
    moneda = models.CharField(
        max_length=3,
        choices=[
            ('USD', 'Dólares (USD)'),
            ('BOB', 'Bolivianos (BOB)'),
            ('PEN', 'Soles (PEN)'),
        ],
        default='USD',
        verbose_name='Moneda'
    )
    
    fecha_inicio_vigencia = models.DateField(
        verbose_name='Fecha inicio vigencia',
        help_text='Desde cuándo aplica este precio'
    )
    
    fecha_fin_vigencia = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha fin vigencia',
        help_text='Hasta cuándo aplica (dejar vacío si es indefinido)'
    )
    
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    # Auditoría
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='precios_creados',
        verbose_name='Creado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    
    class Meta:
        db_table = 'precio_unitario_servicio'
        verbose_name = 'Precio Unitario de Servicio'
        verbose_name_plural = 'Precios Unitarios de Servicios'
        ordering = ['-fecha_inicio_vigencia', 'contrato', 'servicio']
        indexes = [
            models.Index(fields=['contrato', 'servicio', 'activo']),
            models.Index(fields=['fecha_inicio_vigencia', 'fecha_fin_vigencia']),
        ]
        unique_together = [('contrato', 'servicio', 'fecha_inicio_vigencia')]
    
    def __str__(self):
        return f"{self.contrato.nombre_contrato} - {self.servicio.nombre}: {self.moneda} {self.precio_unitario}/m"
    
    def esta_vigente(self, fecha=None):
        """Verifica si el precio está vigente en una fecha dada"""
        from datetime import date as date_class
        
        if fecha is None:
            fecha = date_class.today()
        
        if not self.activo:
            return False
        
        if fecha < self.fecha_inicio_vigencia:
            return False
        
        if self.fecha_fin_vigencia and fecha > self.fecha_fin_vigencia:
            return False
        
        return True
    
    def clean(self):
        """Validaciones personalizadas"""
        super().clean()
        
        if self.fecha_fin_vigencia and self.fecha_inicio_vigencia:
            if self.fecha_fin_vigencia < self.fecha_inicio_vigencia:
                raise ValidationError({
                    'fecha_fin_vigencia': 'La fecha fin no puede ser anterior a la fecha inicio'
                })


# =============================================================================
# SECCIÓN 7: METAS - Metas de Máquinas y Precios Unitarios
# =============================================================================

class MetaMaquina(models.Model):
    """
    Metas de perforación para máquinas por período.
    
    Soporta dos modos:
    1. Mes operativo estándar (26-25): solo especificar año y mes
    2. Período personalizado: especificar fecha_inicio y fecha_fin
    
    Ejemplos:
    - Meta noviembre 2024: año=2024, mes=11 (automáticamente 26-oct a 25-nov)
    - Meta partida: fecha_inicio=2024-11-01, fecha_fin=2024-11-15
    """
    
    contrato = models.ForeignKey(
        Contrato, 
        on_delete=models.CASCADE, 
        related_name='metas_maquinas',
        verbose_name='Contrato'
    )
    
    maquina = models.ForeignKey(
        Maquina, 
        on_delete=models.CASCADE, 
        related_name='metas',
        verbose_name='Máquina'
    )
    
    # Servicio/Actividad para valorización
    servicio = models.ForeignKey(
        TipoActividad,
        on_delete=models.PROTECT,
        related_name='metas',
        null=True,
        blank=True,
        verbose_name='Servicio',
        help_text='Servicio/actividad para valorización (vincula con precio unitario)'
    )
    
    # Mes operativo (para metas estándar 26-25)
    año = models.IntegerField(
        verbose_name='Año',
        help_text='Año del mes operativo'
    )
    
    mes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name='Mes',
        help_text='Mes operativo (1-12). El período será del 26 del mes anterior al 25 de este mes'
    )
    
    # Fechas personalizadas (opcional, para metas partidas)
    fecha_inicio = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Fecha inicio (personalizada)',
        help_text='Dejar vacío para usar mes operativo estándar (26-25)'
    )
    
    fecha_fin = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Fecha fin (personalizada)',
        help_text='Dejar vacío para usar mes operativo estándar (26-25)'
    )
    
    # Meta en metros
    meta_metros = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Meta en metros',
        help_text='Metraje objetivo para el período'
    )
    
    # Información adicional
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
        help_text='Notas sobre la meta (ej: "Meta ajustada por mantenimiento")'
    )
    
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Desmarcar para desactivar la meta sin eliminarla'
    )
    
    # Auditoría
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.PROTECT, 
        related_name='metas_creadas',
        verbose_name='Creado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'meta_maquina'
        verbose_name = 'Meta de Máquina'
        verbose_name_plural = 'Metas de Máquinas'
        ordering = ['-año', '-mes', 'contrato', 'maquina']
        indexes = [
            models.Index(fields=['contrato', 'año', 'mes']),
            models.Index(fields=['maquina', 'año', 'mes']),
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
            models.Index(fields=['activo']),
        ]

    def clean(self):
        """Validaciones personalizadas"""
        from datetime import date
        
        # Validar que la máquina pertenece al contrato
        if self.maquina and self.contrato and self.maquina.contrato != self.contrato:
            raise ValidationError({
                'maquina': f'La máquina {self.maquina.nombre} no pertenece al contrato {self.contrato.nombre_contrato}'
            })
        
        # Si se especifican fechas personalizadas, ambas deben estar presentes
        if (self.fecha_inicio and not self.fecha_fin) or (not self.fecha_inicio and self.fecha_fin):
            raise ValidationError({
                'fecha_inicio': 'Debe especificar tanto fecha de inicio como fecha de fin para período personalizado',
                'fecha_fin': 'Debe especificar tanto fecha de inicio como fecha de fin para período personalizado'
            })
        
        # Validar que fecha_fin > fecha_inicio
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            raise ValidationError({
                'fecha_fin': 'La fecha de fin debe ser posterior a la fecha de inicio'
            })
        
        # Validar que el mes es válido
        if not (1 <= self.mes <= 12):
            raise ValidationError({
                'mes': 'El mes debe estar entre 1 y 12'
            })
        
        # Validar que el año es razonable
        current_year = date.today().year
        if not (2020 <= self.año <= current_year + 5):
            raise ValidationError({
                'año': f'El año debe estar entre 2020 y {current_year + 5}'
            })

    def save(self, *args, **kwargs):
        """Override save para aplicar validaciones"""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_fecha_inicio_periodo(self):
        """
        Obtiene la fecha de inicio del período.
        Si hay fecha personalizada, la usa; sino calcula mes operativo (día 26 del mes anterior)
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        if self.fecha_inicio:
            return self.fecha_inicio
        
        # Calcular día 26 del mes anterior
        primer_dia_mes = date(self.año, self.mes, 1)
        mes_anterior = primer_dia_mes - relativedelta(months=1)
        return date(mes_anterior.year, mes_anterior.month, 26)

    def get_fecha_fin_periodo(self):
        """
        Obtiene la fecha de fin del período.
        Si hay fecha personalizada, la usa; sino calcula mes operativo (día 25 del mes actual)
        """
        from datetime import date
        
        if self.fecha_fin:
            return self.fecha_fin
        
        # Día 25 del mes operativo
        return date(self.año, self.mes, 25)

    def get_periodo_display(self):
        """Retorna una representación legible del período"""
        fecha_inicio = self.get_fecha_inicio_periodo()
        fecha_fin = self.get_fecha_fin_periodo()
        
        if self.fecha_inicio and self.fecha_fin:
            return f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')} (Personalizado)"
        else:
            return f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')} (Mes operativo {self.get_mes_nombre()})"

    def get_mes_nombre(self):
        """Retorna el nombre del mes"""
        meses = [
            '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
        return meses[self.mes]

    def calcular_cumplimiento(self, metros_reales):
        """
        Calcula el porcentaje de cumplimiento de la meta.
        
        Args:
            metros_reales (Decimal): Metros reales perforados en el período
            
        Returns:
            Decimal: Porcentaje de cumplimiento (0-100+)
        """
        if self.meta_metros == 0:
            return Decimal('0.00')
        
        return (metros_reales / self.meta_metros) * Decimal('100.00')

    def esta_en_periodo(self, fecha):
        """
        Verifica si una fecha está dentro del período de esta meta.
        
        Args:
            fecha (date): Fecha a verificar
            
        Returns:
            bool: True si la fecha está en el período
        """
        fecha_inicio = self.get_fecha_inicio_periodo()
        fecha_fin = self.get_fecha_fin_periodo()
        
        return fecha_inicio <= fecha <= fecha_fin
    
    def obtener_precio_unitario(self, fecha=None):
        """
        Obtiene el precio unitario vigente para el servicio de esta meta.
        
        Args:
            fecha (date): Fecha para la cual buscar el precio (default: hoy)
            
        Returns:
            PrecioUnitarioServicio o None: Precio unitario vigente o None si no hay
        """
        from datetime import date as date_class
        
        if not self.servicio:
            return None
        
        if fecha is None:
            fecha = date_class.today()
        
        # Buscar precio vigente para la fecha
        precios = PrecioUnitarioServicio.objects.filter(
            contrato=self.contrato,
            servicio=self.servicio,
            activo=True,
            fecha_inicio_vigencia__lte=fecha
        ).filter(
            models.Q(fecha_fin_vigencia__isnull=True) | 
            models.Q(fecha_fin_vigencia__gte=fecha)
        ).order_by('-fecha_inicio_vigencia')
        
        return precios.first()
    
    def calcular_valor_meta(self, fecha=None):
        """
        Calcula el valor monetario de la meta según el precio unitario.
        
        Args:
            fecha (date): Fecha para obtener precio unitario (default: hoy)
            
        Returns:
            tuple: (monto, moneda, precio_unitario) o (None, None, None) si no hay PU
        """
        precio = self.obtener_precio_unitario(fecha)
        
        if not precio:
            return (None, None, None)
        
        monto = self.meta_metros * precio.precio_unitario
        return (monto, precio.moneda, precio.precio_unitario)
    
    def calcular_valor_real(self, metros_reales, fecha=None):
        """
        Calcula el valor monetario de los metros reales perforados.
        
        Args:
            metros_reales (Decimal): Metros realmente perforados
            fecha (date): Fecha para obtener precio unitario (default: hoy)
            
        Returns:
            tuple: (monto, moneda, precio_unitario) o (None, None, None) si no hay PU
        """
        precio = self.obtener_precio_unitario(fecha)
        
        if not precio:
            return (None, None, None)
        
        monto = metros_reales * precio.precio_unitario
        return (monto, precio.moneda, precio.precio_unitario)
    
    def calcular_valorizacion_completa(self, metros_reales, fecha=None):
        """
        Calcula la valorización completa: meta, real, diferencia y porcentajes.
        
        Args:
            metros_reales (Decimal): Metros realmente perforados
            fecha (date): Fecha para obtener precio unitario
            
        Returns:
            dict: Diccionario con toda la información de valorización
        """
        precio = self.obtener_precio_unitario(fecha)
        
        resultado = {
            'tiene_precio': precio is not None,
            'precio_unitario': precio.precio_unitario if precio else None,
            'moneda': precio.moneda if precio else None,
            'meta_metros': self.meta_metros,
            'real_metros': metros_reales,
            'meta_monto': None,
            'real_monto': None,
            'diferencia_metros': metros_reales - self.meta_metros,
            'diferencia_monto': None,
            'porcentaje_cumplimiento': self.calcular_cumplimiento(metros_reales),
            'porcentaje_valor': None,
        }
        
        if precio:
            resultado['meta_monto'] = self.meta_metros * precio.precio_unitario
            resultado['real_monto'] = metros_reales * precio.precio_unitario
            resultado['diferencia_monto'] = resultado['real_monto'] - resultado['meta_monto']
            
            if resultado['meta_monto'] > 0:
                resultado['porcentaje_valor'] = (resultado['real_monto'] / resultado['meta_monto']) * Decimal('100.00')
        
        return resultado

    def __str__(self):
        periodo = self.get_periodo_display()
        estado = "✓" if self.activo else "✗"
        servicio_str = f" [{self.servicio.nombre}]" if self.servicio else ""
        return f"{estado} {self.maquina.nombre}{servicio_str} - {periodo} - Meta: {self.meta_metros}m"


# =============================================================================
# SECCIÓN 8: ORGANIGRAMA - Organigrama Semanal y Asignaciones
# =============================================================================

class OrganigramaSemanal(models.Model):
    """
    Registro semanal del organigrama - Similar al tareo mensual pero para estructura organizacional
    Permite gestionar y consultar la distribución de personal por semana
    """
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='organigramas_semanales')
    fecha_inicio = models.DateField(verbose_name='Fecha inicio de semana')
    fecha_fin = models.DateField(verbose_name='Fecha fin de semana')
    semana_numero = models.PositiveIntegerField(verbose_name='Número de semana del año', help_text='Semana 1-53')
    anio = models.PositiveIntegerField(verbose_name='Año')
    
    # Usuario que creó/modificó el organigrama de esa semana
    creado_por = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, related_name='organigramas_creados')
    modificado_por = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, related_name='organigramas_modificados')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Estado del organigrama
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('CONFIRMADO', 'Confirmado'),
        ('ARCHIVADO', 'Archivado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR')
    
    # Observaciones generales de la semana
    observaciones = models.TextField(blank=True, verbose_name='Observaciones generales')
    
    class Meta:
        db_table = 'organigrama_semanal'
        verbose_name = 'Organigrama Semanal'
        verbose_name_plural = 'Organigramas Semanales'
        ordering = ['-anio', '-semana_numero']
        unique_together = ['contrato', 'anio', 'semana_numero']
        indexes = [
            models.Index(fields=['contrato', 'anio', 'semana_numero']),
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
        ]
    
    def __str__(self):
        return f"{self.contrato.nombre_contrato} - Semana {self.semana_numero}/{self.anio} ({self.fecha_inicio} - {self.fecha_fin})"


class AsignacionOrganigrama(models.Model):
    """
    Asignación de trabajadores a máquinas/guardias para una semana específica
    Permite editar y mantener histórico de asignaciones
    """
    organigrama_semanal = models.ForeignKey(OrganigramaSemanal, on_delete=models.CASCADE, related_name='asignaciones')
    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT, related_name='asignaciones_organigrama')
    
    # Asignación a máquina (para personal operativo)
    maquina = models.ForeignKey(Maquina, on_delete=models.PROTECT, null=True, blank=True, related_name='asignaciones_semanales')
    
    # Guardia asignada (A, B, C)
    GUARDIA_CHOICES = [
        ('A', 'Guardia A'),
        ('B', 'Guardia B'),
        ('C', 'Guardia C'),
    ]
    guardia = models.CharField(max_length=1, choices=GUARDIA_CHOICES, null=True, blank=True)
    
    # Estado del trabajador en esa semana
    ESTADO_ASIGNACION_CHOICES = [
        ('OPERATIVO', 'Operativo'),
        ('STAND_BY', 'Stand By'),
        ('DESCANSO_MEDICO', 'Descanso Médico'),
        ('VACACIONES', 'Vacaciones'),
        ('LICENCIA', 'Licencia'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_ASIGNACION_CHOICES, default='OPERATIVO')
    
    # Observaciones específicas de esta asignación
    observaciones = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'asignacion_organigrama'
        verbose_name = 'Asignación de Organigrama'
        verbose_name_plural = 'Asignaciones de Organigrama'
        ordering = ['trabajador__apellidos', 'trabajador__nombres']
        unique_together = ['organigrama_semanal', 'trabajador']
        indexes = [
            models.Index(fields=['organigrama_semanal', 'maquina']),
            models.Index(fields=['organigrama_semanal', 'guardia']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        maquina_str = f" - {self.maquina.nombre}" if self.maquina else ""
        guardia_str = f" [{self.guardia}]" if self.guardia else ""
        return f"{self.trabajador.nombres} {self.trabajador.apellidos}{maquina_str}{guardia_str}"


class GuardiaConductor(models.Model):
    """
    Guardias específicas para conductores (A, B, C)
    Separado de las asignaciones de máquinas porque los conductores tienen su propia rotación
    """
    organigrama_semanal = models.ForeignKey(OrganigramaSemanal, on_delete=models.CASCADE, related_name='guardias_conductores')
    conductor = models.ForeignKey(Trabajador, on_delete=models.PROTECT, related_name='guardias_conductor', limit_choices_to={'cargo__nombre__icontains': 'conductor'})
    
    # Vehículo asignado
    vehiculo = models.ForeignKey('Vehiculo', on_delete=models.PROTECT, null=True, blank=True, related_name='guardias_asignadas')
    
    # Guardia del conductor
    GUARDIA_CHOICES = [
        ('A', 'Guardia A'),
        ('B', 'Guardia B'),
        ('C', 'Guardia C'),
    ]
    guardia = models.CharField(max_length=1, choices=GUARDIA_CHOICES)
    
    # Estado
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('STAND_BY', 'Stand By'),
        ('DESCANSO', 'Descanso'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO')
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'guardia_conductor'
        verbose_name = 'Guardia de Conductor'
        verbose_name_plural = 'Guardias de Conductores'
        ordering = ['guardia', 'conductor__apellidos']
        unique_together = ['organigrama_semanal', 'conductor']
        indexes = [
            models.Index(fields=['organigrama_semanal', 'guardia']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        vehiculo_str = f" - {self.vehiculo.placa}" if self.vehiculo else ""
        return f"{self.conductor.nombres} {self.conductor.apellidos} [Guardia {self.guardia}]{vehiculo_str}"


class Equipo(models.Model):
    """
    Modelo para equipos asignables a trabajadores 
    (laptops, celulares, módems, impresoras, detector de tormentas, enmicadora, radios)
    """
    TIPO_CHOICES = [
        ('LAPTOP', 'Laptop'),
        ('CELULAR', 'Celular'),
        ('MODEM', 'Módem'),
        ('IMPRESORA', 'Impresora'),
        ('DETECTOR_TORMENTAS', 'Detector de Tormentas'),
        ('ENMICADORA', 'Enmicadora'),
        ('RADIO', 'Radio'),
        ('TABLET', 'Tablet'),
        ('GPS', 'GPS'),
        ('OTRO', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('ASIGNADO', 'Asignado'),
        ('MANTENIMIENTO', 'En Mantenimiento'),
        ('FUERA_SERVICIO', 'Fuera de Servicio'),
        ('BAJA', 'Dado de Baja'),
    ]
    
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='equipos')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    codigo_interno = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name='Código Interno',
        help_text='Código único de identificación del equipo'
    )
    marca = models.CharField(max_length=100, blank=True, verbose_name='Marca')
    modelo = models.CharField(max_length=100, blank=True, verbose_name='Modelo')
    numero_serie = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Número de Serie',
        help_text='Número de serie del fabricante'
    )
    
    # Para equipos de comunicación (celulares, radios, módems)
    numero_telefono = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name='Número de Teléfono/IMEI',
        help_text='Para celulares, radios o módems'
    )
    operador = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name='Operador',
        help_text='Operador de telefonía o servicio'
    )
    
    # Información adicional
    descripcion = models.TextField(
        blank=True, 
        verbose_name='Descripción',
        help_text='Características adicionales del equipo'
    )
    fecha_adquisicion = models.DateField(
        null=True, 
        blank=True, 
        verbose_name='Fecha de Adquisición'
    )
    fecha_garantia_vencimiento = models.DateField(
        null=True, 
        blank=True, 
        verbose_name='Vencimiento de Garantía'
    )
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='DISPONIBLE')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'equipos'
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ['tipo', 'codigo_interno']
        indexes = [
            models.Index(fields=['contrato', 'tipo']),
            models.Index(fields=['estado']),
            models.Index(fields=['codigo_interno']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.codigo_interno}"
    
    def nombre_completo(self):
        """Retorna nombre completo con marca y modelo"""
        partes = [self.get_tipo_display(), self.codigo_interno]
        if self.marca:
            partes.append(self.marca)
        if self.modelo:
            partes.append(self.modelo)
        return ' - '.join(partes)


class AsignacionEquipo(models.Model):
    """
    Modelo para registrar asignaciones de equipos a trabajadores en el organigrama semanal
    Similar a AsignacionOrganigrama y GuardiaConductor
    """
    organigrama_semanal = models.ForeignKey(
        OrganigramaSemanal,
        on_delete=models.SET_NULL,
        related_name='asignaciones_equipos',
        null=True,
        blank=True,
        help_text='Opcional: vinculado al organigrama semanal si aplica'
    )
    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.CASCADE,
        related_name='equipos_asignados'
    )
    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.PROTECT,
        related_name='asignaciones'
    )
    
    fecha_asignacion = models.DateField(
        auto_now_add=True,
        verbose_name='Fecha de Asignación'
    )
    fecha_devolucion = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Devolución',
        help_text='Fecha en que el trabajador devolvió el equipo'
    )
    
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('DEVUELTO', 'Devuelto'),
        ('PERDIDO', 'Perdido/Extraviado'),
        ('DAÑADO', 'Dañado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO')
    
    # Observaciones y responsabilidades
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
        help_text='Notas sobre la asignación, estado del equipo, etc.'
    )
    acta_entrega = models.BooleanField(
        default=False,
        verbose_name='Acta de Entrega',
        help_text='¿Se firmó acta de entrega-recepción?'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'asignacion_equipo'
        verbose_name = 'Asignación de Equipo'
        verbose_name_plural = 'Asignaciones de Equipos'
        ordering = ['-fecha_asignacion', 'trabajador__apellidos']
        indexes = [
            models.Index(fields=['trabajador', 'estado']),
            models.Index(fields=['equipo', 'estado']),
            models.Index(fields=['fecha_asignacion']),
        ]
    
    def __str__(self):
        return f"{self.equipo} → {self.trabajador.nombres} {self.trabajador.apellidos} ({self.get_estado_display()})"


# =============================================================================
# SECCIÓN 10: STOCK - Snapshots de Stock y Sistema de Alertas
# =============================================================================

class StockSnapshot(models.Model):
    """
    Foto del estado del stock en un momento dado.
    Se crea automáticamente cada vez que se sincroniza con la API de Vilbragroup.
    Permite análisis histórico, tendencias y proyecciones de agotamiento.
    """
    FAMILIA_CHOICES = [
        ('PDD', 'Productos Diamantados'),
        ('ADIT', 'Aditivos'),
    ]
    
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='stock_snapshots',
        verbose_name='Contrato'
    )
    fecha_sync = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Sincronización',
        help_text='Momento exacto en que se tomó la foto del stock'
    )
    familia = models.CharField(
        max_length=10,
        choices=FAMILIA_CHOICES,
        verbose_name='Familia de Producto'
    )
    codigo_articulo = models.CharField(
        max_length=50,
        verbose_name='Código Artículo',
        help_text='Código del artículo en el sistema Vilbragroup'
    )
    descripcion = models.CharField(
        max_length=255,
        verbose_name='Descripción'
    )
    stock_cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad en Stock'
    )
    unidad_medida = models.CharField(
        max_length=20,
        verbose_name='Unidad de Medida'
    )
    # Campos adicionales de la API (opcionales)
    lote = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Lote'
    )
    ubicacion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Ubicación en Almacén'
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Precio Unitario'
    )
    valor_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Valor Total',
        editable=False
    )
    
    class Meta:
        db_table = 'stock_snapshot'
        verbose_name = 'Snapshot de Stock'
        verbose_name_plural = 'Snapshots de Stock'
        ordering = ['-fecha_sync', 'familia', 'codigo_articulo']
        indexes = [
            models.Index(fields=['contrato', 'fecha_sync']),
            models.Index(fields=['contrato', 'familia']),
            models.Index(fields=['codigo_articulo']),
            models.Index(fields=['contrato', 'codigo_articulo', '-fecha_sync']),
            models.Index(fields=['-fecha_sync']),
        ]
    
    def save(self, *args, **kwargs):
        # Calcular valor total si hay precio unitario
        if self.precio_unitario and self.stock_cantidad:
            self.valor_total = self.stock_cantidad * self.precio_unitario
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.contrato.nombre_contrato} | {self.codigo_articulo} | {self.stock_cantidad} {self.unidad_medida} ({self.fecha_sync.strftime('%Y-%m-%d %H:%M')})"
    
    @classmethod
    def get_ultimo_snapshot(cls, contrato, codigo_articulo=None):
        """
        Obtiene el último snapshot para un contrato y opcionalmente un artículo específico.
        """
        queryset = cls.objects.filter(contrato=contrato)
        if codigo_articulo:
            queryset = queryset.filter(codigo_articulo=codigo_articulo)
        return queryset.order_by('-fecha_sync').first()
    
    @classmethod
    def get_stock_actual(cls, contrato, familia=None):
        """
        Obtiene el stock actual (último snapshot) de todos los artículos de un contrato.
        Usa una subquery para obtener solo el registro más reciente de cada artículo.
        """
        from django.db.models import Subquery, OuterRef
        
        # Subquery para obtener la fecha más reciente por artículo
        latest_sync = cls.objects.filter(
            contrato=contrato,
            codigo_articulo=OuterRef('codigo_articulo')
        ).order_by('-fecha_sync').values('fecha_sync')[:1]
        
        queryset = cls.objects.filter(
            contrato=contrato,
            fecha_sync=Subquery(latest_sync)
        )
        
        if familia:
            queryset = queryset.filter(familia=familia)
        
        return queryset.order_by('familia', 'descripcion')
    
    @classmethod
    def get_historial_articulo(cls, contrato, codigo_articulo, dias=30):
        """
        Obtiene el historial de un artículo específico en los últimos N días.
        Útil para gráficas de tendencia.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        fecha_inicio = timezone.now() - timedelta(days=dias)
        
        return cls.objects.filter(
            contrato=contrato,
            codigo_articulo=codigo_articulo,
            fecha_sync__gte=fecha_inicio
        ).order_by('fecha_sync')


class AlertaStock(models.Model):
    """
    Sistema de alertas automáticas para gestión proactiva del stock.
    Se generan automáticamente durante la sincronización basándose en reglas definidas.
    """
    TIPO_CHOICES = [
        ('STOCK_BAJO', 'Stock Bajo'),
        ('STOCK_CRITICO', 'Stock Crítico'),
        ('AGOTADO', 'Agotado'),
        ('SIN_ROTACION', 'Sin Rotación'),
        ('CONSUMO_ANORMAL', 'Consumo Anormal'),
        ('REPOSICION_URGENTE', 'Reposición Urgente'),
    ]
    
    PRIORIDAD_CHOICES = [
        (1, 'Crítica'),
        (2, 'Alta'),
        (3, 'Media'),
        (4, 'Baja'),
    ]
    
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='alertas_stock',
        verbose_name='Contrato'
    )
    codigo_articulo = models.CharField(
        max_length=50,
        verbose_name='Código Artículo'
    )
    descripcion_articulo = models.CharField(
        max_length=255,
        verbose_name='Descripción Artículo'
    )
    familia = models.CharField(
        max_length=10,
        choices=StockSnapshot.FAMILIA_CHOICES,
        verbose_name='Familia'
    )
    tipo_alerta = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de Alerta'
    )
    prioridad = models.PositiveSmallIntegerField(
        choices=PRIORIDAD_CHOICES,
        default=3,
        verbose_name='Prioridad'
    )
    mensaje = models.TextField(
        verbose_name='Mensaje de Alerta'
    )
    
    # Datos contextuales
    stock_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Stock Actual'
    )
    consumo_diario_promedio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Consumo Diario Promedio'
    )
    dias_stock_restante = models.DecimalField(
        max_digits=8,
        decimal_places=1,
        blank=True,
        null=True,
        verbose_name='Días de Stock Restante'
    )
    umbral_configurado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Umbral Configurado',
        help_text='Valor del umbral que disparó la alerta'
    )
    
    # Estado de la alerta
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    leida = models.BooleanField(
        default=False,
        verbose_name='Leída'
    )
    fecha_lectura = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Lectura'
    )
    leida_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='alertas_stock_leidas',
        verbose_name='Leída por'
    )
    resuelta = models.BooleanField(
        default=False,
        verbose_name='Resuelta'
    )
    fecha_resolucion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Resolución'
    )
    resuelta_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='alertas_stock_resueltas',
        verbose_name='Resuelta por'
    )
    nota_resolucion = models.TextField(
        blank=True,
        verbose_name='Nota de Resolución'
    )
    
    # Para evitar alertas duplicadas
    hash_alerta = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Hash Único',
        help_text='Para evitar alertas duplicadas del mismo evento'
    )
    
    class Meta:
        db_table = 'alerta_stock'
        verbose_name = 'Alerta de Stock'
        verbose_name_plural = 'Alertas de Stock'
        ordering = ['prioridad', '-fecha_creacion']
        indexes = [
            models.Index(fields=['contrato', 'resuelta']),
            models.Index(fields=['contrato', 'tipo_alerta']),
            models.Index(fields=['prioridad', '-fecha_creacion']),
            models.Index(fields=['codigo_articulo']),
            models.Index(fields=['hash_alerta']),
        ]
    
    def __str__(self):
        return f"[{self.get_prioridad_display()}] {self.get_tipo_alerta_display()}: {self.descripcion_articulo}"
    
    def marcar_leida(self, usuario):
        """Marca la alerta como leída"""
        from django.utils import timezone
        self.leida = True
        self.fecha_lectura = timezone.now()
        self.leida_por = usuario
        self.save(update_fields=['leida', 'fecha_lectura', 'leida_por'])
    
    def resolver(self, usuario, nota=''):
        """Marca la alerta como resuelta"""
        from django.utils import timezone
        self.resuelta = True
        self.fecha_resolucion = timezone.now()
        self.resuelta_por = usuario
        self.nota_resolucion = nota
        if not self.leida:
            self.leida = True
            self.fecha_lectura = timezone.now()
            self.leida_por = usuario
        self.save()
    
    @classmethod
    def generar_hash(cls, contrato_id, codigo_articulo, tipo_alerta, fecha):
        """
        Genera un hash único para evitar alertas duplicadas del mismo día.
        """
        import hashlib
        cadena = f"{contrato_id}|{codigo_articulo}|{tipo_alerta}|{fecha.strftime('%Y-%m-%d')}"
        return hashlib.sha256(cadena.encode()).hexdigest()
    
    @classmethod
    def crear_alerta(cls, contrato, codigo_articulo, descripcion, familia, tipo_alerta,
                     mensaje, stock_actual, prioridad=3, consumo_diario=None, 
                     dias_restante=None, umbral=None):
        """
        Crea una alerta si no existe una igual del mismo día.
        Retorna la alerta creada o None si ya existía.
        """
        from django.utils import timezone
        
        hash_alerta = cls.generar_hash(
            contrato.id, codigo_articulo, tipo_alerta, timezone.now()
        )
        
        # Verificar si ya existe
        if cls.objects.filter(hash_alerta=hash_alerta).exists():
            return None
        
        return cls.objects.create(
            contrato=contrato,
            codigo_articulo=codigo_articulo,
            descripcion_articulo=descripcion,
            familia=familia,
            tipo_alerta=tipo_alerta,
            prioridad=prioridad,
            mensaje=mensaje,
            stock_actual=stock_actual,
            consumo_diario_promedio=consumo_diario,
            dias_stock_restante=dias_restante,
            umbral_configurado=umbral,
            hash_alerta=hash_alerta
        )
    
    @classmethod
    def get_alertas_activas(cls, contrato=None, usuario=None):
        """
        Obtiene alertas activas (no resueltas).
        Filtra por contrato o por contratos accesibles al usuario.
        """
        queryset = cls.objects.filter(resuelta=False)
        
        if contrato:
            queryset = queryset.filter(contrato=contrato)
        elif usuario and not usuario.is_superuser:
            if hasattr(usuario, 'contrato') and usuario.contrato:
                queryset = queryset.filter(contrato=usuario.contrato)
        
        return queryset.order_by('prioridad', '-fecha_creacion')


class ConfiguracionAlertaStock(models.Model):
    """
    Configuración de umbrales para alertas de stock por contrato.
    Permite personalizar cuándo se disparan las alertas.
    """
    contrato = models.OneToOneField(
        Contrato,
        on_delete=models.CASCADE,
        related_name='config_alertas_stock',
        verbose_name='Contrato'
    )
    
    # Umbrales para días de stock restante
    dias_stock_critico = models.PositiveIntegerField(
        default=5,
        verbose_name='Días para Stock Crítico',
        help_text='Se genera alerta crítica si quedan menos de estos días'
    )
    dias_stock_bajo = models.PositiveIntegerField(
        default=15,
        verbose_name='Días para Stock Bajo',
        help_text='Se genera alerta de stock bajo si quedan menos de estos días'
    )
    dias_stock_alerta = models.PositiveIntegerField(
        default=30,
        verbose_name='Días para Pre-alerta',
        help_text='Se genera pre-alerta si quedan menos de estos días'
    )
    
    # Umbral de sin rotación
    dias_sin_rotacion = models.PositiveIntegerField(
        default=30,
        verbose_name='Días sin Rotación',
        help_text='Alertar si un artículo no ha tenido movimiento en estos días'
    )
    
    # Umbral de consumo anormal (porcentaje sobre promedio)
    pct_consumo_anormal = models.PositiveIntegerField(
        default=150,
        verbose_name='% Consumo Anormal',
        help_text='Alertar si el consumo supera este % del promedio'
    )
    
    # Configuración de notificaciones
    enviar_email = models.BooleanField(
        default=True,
        verbose_name='Enviar Email',
        help_text='Enviar notificación por email cuando se genere una alerta crítica'
    )
    emails_notificacion = models.TextField(
        blank=True,
        verbose_name='Emails de Notificación',
        help_text='Lista de emails separados por coma para notificaciones'
    )
    
    # Activar/desactivar tipos de alerta
    alertar_stock_bajo = models.BooleanField(default=True, verbose_name='Alertar Stock Bajo')
    alertar_agotado = models.BooleanField(default=True, verbose_name='Alertar Agotado')
    alertar_sin_rotacion = models.BooleanField(default=True, verbose_name='Alertar Sin Rotación')
    alertar_consumo_anormal = models.BooleanField(default=True, verbose_name='Alertar Consumo Anormal')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'configuracion_alerta_stock'
        verbose_name = 'Configuración de Alertas de Stock'
        verbose_name_plural = 'Configuraciones de Alertas de Stock'
    
    def __str__(self):
        return f"Config. Alertas: {self.contrato.nombre_contrato}"
    
    @classmethod
    def get_o_crear(cls, contrato):
        """Obtiene o crea la configuración para un contrato"""
        config, created = cls.objects.get_or_create(contrato=contrato)
        return config


# =============================================================================
# SECCIÓN: HEADCOUNT - Planificación de Personal
# =============================================================================

class HeadCount(models.Model):
    """
    Modelo para definir el personal planificado/requerido por contrato.
    Define cuántos trabajadores de cada cargo se necesitan y opcionalmente
    a qué máquina están asignados.
    """
    contrato = models.ForeignKey(
        Contrato, 
        on_delete=models.CASCADE, 
        related_name='headcounts',
        verbose_name='Contrato'
    )
    cargo = models.ForeignKey(
        'Cargo',
        on_delete=models.PROTECT,
        related_name='headcounts',
        verbose_name='Cargo'
    )
    cantidad_requerida = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Cantidad Requerida',
        help_text='Número de trabajadores requeridos para este cargo'
    )
    maquina = models.ForeignKey(
        'Maquina',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headcounts',
        verbose_name='Máquina Asignada',
        help_text='Máquina a la que se asignará el personal (opcional)'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
        help_text='Comentarios adicionales sobre este requerimiento'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si este requerimiento está vigente'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    
    class Meta:
        db_table = 'headcount'
        verbose_name = 'Headcount'
        verbose_name_plural = 'Headcounts'
        unique_together = ['contrato', 'cargo', 'maquina']
        indexes = [
            models.Index(fields=['contrato', 'activo']),
            models.Index(fields=['cargo']),
            models.Index(fields=['maquina']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['contrato', 'cargo__nombre']
    
    def __str__(self):
        maquina_str = f" - {self.maquina.nombre}" if self.maquina else ""
        return f"{self.contrato.nombre_contrato} - {self.cargo.nombre}: {self.cantidad_requerida}{maquina_str}"
    
    def get_personal_actual(self):
        """Obtiene el personal activo que cumple con este headcount"""
        filtros = {
            'contrato': self.contrato,
            'cargo': self.cargo,
            'estado': 'ACTIVO'
        }
        if self.maquina:
            filtros['maquina_asignada'] = self.maquina
        
        return Trabajador.objects.filter(**filtros)
    
    def get_cantidad_actual(self):
        """Retorna la cantidad actual de personal"""
        return self.get_personal_actual().count()
    
    def get_diferencia(self):
        """Retorna la diferencia entre requerido y actual (positivo = falta, negativo = sobra)"""
        return self.cantidad_requerida - self.get_cantidad_actual()
    
    def get_porcentaje_cumplimiento(self):
        """Retorna el porcentaje de cumplimiento del headcount"""
        if self.cantidad_requerida == 0:
            return 100
        return min(100, int((self.get_cantidad_actual() / self.cantidad_requerida) * 100))
    
    def esta_completo(self):
        """Verifica si el headcount está completo"""
        return self.get_cantidad_actual() >= self.cantidad_requerida

