from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib import messages
from .models import *
from .auth_views import send_activation_email

# ======================================
# FORMULARIOS PERSONALIZADOS PARA USUARIO
# ======================================

class CustomUserCreationForm(UserCreationForm):
    """Formulario para crear usuario - el admin establecerá contraseña temporal"""
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'contrato', 'role', 'is_system_admin')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer que password1 y password2 NO sean requeridos
        # El admin enviará email de activación y el usuario establecerá su contraseña
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        self.fields['email'].required = True
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Si no se proporcionó contraseña, establecer una temporal no utilizable
        if not self.cleaned_data.get('password1'):
            user.set_unusable_password()
        user.is_active = False  # Inactivo hasta que active su cuenta
        user.is_account_active = False
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = '__all__'

# ======================================
# ADMIN PERSONALIZADO PARA USUARIO
# ======================================

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'role', 'get_contract_access_display', 'is_account_active', 'is_active', 'is_system_admin', 'last_activity'
    ]
    list_filter = [
        'role', 'is_system_admin', 'is_active', 'is_account_active', 'is_staff', 'contrato'
    ]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['username']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información del Contrato', {
            'fields': ('contrato', 'role', 'is_system_admin'),
            'description': 'IMPORTANTE: Si NO asignas contrato, el usuario tendrá acceso a TODOS los contratos (ideal para Control de Proyecto).'
        }),
        ('Activación de Cuenta', {
            'fields': ('is_account_active', 'activation_token', 'token_created_at'),
            'classes': ('collapse',)
        }),
        ('Actividad', {
            'fields': ('last_activity', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 
                      'contrato', 'role', 'is_system_admin'),
            'description': 'Se enviará un email de activación al usuario. Las contraseñas son opcionales. IMPORTANTE: Dejar "Contrato" vacío = acceso a TODOS los contratos.'
        }),
        ('Contraseñas (Opcional)', {
            'classes': ('collapse',),
            'fields': ('password1', 'password2'),
            'description': 'Si no estableces contraseña, el usuario la creará al activar su cuenta.'
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_activity', 'is_account_active', 
                      'activation_token', 'token_created_at']
    
    def get_contract_access_display(self, obj):
        """Mostrar claramente el acceso a contratos"""
        if obj.has_access_to_all_contracts():
            return "🌐 TODOS LOS CONTRATOS"
        elif obj.contrato:
            return f"🏢 {obj.contrato.nombre_contrato}"
        else:
            return "⚠️ Sin acceso"
    get_contract_access_display.short_description = "Acceso a Contratos"
    
    def save_model(self, request, obj, form, change):
        """Enviar email de activación cuando se crea un nuevo usuario"""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        
        if is_new and obj.email:
            try:
                send_activation_email(obj, request)
                messages.success(
                    request, 
                    f'Usuario creado exitosamente. Se ha enviado un email de activación a {obj.email}'
                )
            except Exception as e:
                messages.warning(
                    request,
                    f'Usuario creado pero no se pudo enviar el email: {str(e)}'
                )
    
    actions = ['resend_activation_email']
    
    def resend_activation_email(self, request, queryset):
        """Acción para reenviar email de activación a usuarios seleccionados"""
        count = 0
        for user in queryset:
            if not user.is_account_active and user.email:
                try:
                    send_activation_email(user, request)
                    count += 1
                except Exception as e:
                    messages.warning(request, f'Error al enviar email a {user.username}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'Se enviaron {count} email(s) de activación.')
        else:
            messages.warning(request, 'No se enviaron emails. Verifica que los usuarios tengan email y no estén activados.')
    
    resend_activation_email.short_description = "Reenviar email de activación"

# ======================================
# REGISTRAR MODELOS BÁSICOS
# ======================================

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre']  # Solo campos que existen
    search_fields = ['nombre']
    ordering = ['nombre']

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ['nombre_contrato', 'cliente', 'duracion_turno', 'estado']  # Solo campos que existen
    list_filter = ['estado', 'cliente']
    search_fields = ['nombre_contrato', 'cliente__nombre']
    ordering = ['nombre_contrato']
    raw_id_fields = ['cliente']

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ['apellidos', 'nombres', 'cargo', 'contrato', 'dni', 'estado']
    list_filter = ['cargo', 'estado', 'contrato']
    search_fields = ['nombres', 'apellidos', 'dni']
    ordering = ['apellidos', 'nombres']
    raw_id_fields = ['contrato', 'cargo']

@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'estado', 'horometro', 'contrato']
    list_filter = ['estado', 'contrato']
    search_fields = ['nombre', 'tipo']
    ordering = ['nombre']
    raw_id_fields = ['contrato']

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ['placa', 'tipo', 'marca', 'modelo', 'estado', 'contrato', 'kilometraje_actual', 'ultimo_mantenimiento_fecha', 'requiere_mantenimiento']
    list_filter = ['estado', 'tipo', 'contrato', 'ultimo_mantenimiento_fecha']
    search_fields = ['placa', 'marca', 'modelo']
    ordering = ['placa']
    raw_id_fields = ['contrato']
    fieldsets = (
        ('Información General', {
            'fields': ('contrato', 'placa', 'tipo', 'estado')
        }),
        ('Detalles del Vehículo', {
            'fields': ('marca', 'modelo', 'año', 'capacidad_pasajeros')
        }),
        ('Kilometraje', {
            'fields': ('kilometraje_actual',),
            'description': 'Kilometraje acumulado del vehículo'
        }),
        ('Mantenimiento', {
            'fields': ('ultimo_mantenimiento_fecha', 'ultimo_mantenimiento_km', 'proximo_mantenimiento_km'),
            'description': 'Información de mantenimiento del vehículo'
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
    )
    readonly_fields = ['ultimo_mantenimiento_fecha', 'ultimo_mantenimiento_km']
    
    def requiere_mantenimiento(self, obj):
        """Mostrar si requiere mantenimiento"""
        if obj.requiere_mantenimiento():
            return '⚠️ SÍ'
        return '✅ No'
    requiere_mantenimiento.short_description = 'Requiere Mantenimiento'


@admin.register(MantenimientoVehiculo)
class MantenimientoVehiculoAdmin(admin.ModelAdmin):
    list_display = ['vehiculo', 'fecha_mantenimiento', 'tipo_mantenimiento', 'kilometraje', 'costo', 'proveedor', 'registrado_por']
    list_filter = ['tipo_mantenimiento', 'fecha_mantenimiento', 'vehiculo__contrato']
    search_fields = ['vehiculo__placa', 'descripcion', 'proveedor', 'responsable']
    ordering = ['-fecha_mantenimiento', '-created_at']
    raw_id_fields = ['vehiculo', 'registrado_por']
    date_hierarchy = 'fecha_mantenimiento'
    
    fieldsets = (
        ('Información del Mantenimiento', {
            'fields': ('vehiculo', 'fecha_mantenimiento', 'kilometraje', 'tipo_mantenimiento')
        }),
        ('Detalles del Trabajo', {
            'fields': ('descripcion', 'repuestos_utilizados')
        }),
        ('Costos y Proveedor', {
            'fields': ('costo', 'proveedor')
        }),
        ('Seguimiento', {
            'fields': ('proximo_mantenimiento_sugerido_km', 'responsable', 'observaciones')
        }),
        ('Registro', {
            'fields': ('registrado_por',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Asignar automáticamente el usuario que registra"""
        if not change:  # Solo en creación
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(AsistenciaTrabajador)
class AsistenciaTrabajadorAdmin(admin.ModelAdmin):
    list_display = ['trabajador', 'fecha', 'estado', 'tipo', 'registrado_por', 'created_at']
    list_filter = ['estado', 'tipo', 'fecha', 'trabajador__contrato']
    search_fields = ['trabajador__nombres', 'trabajador__apellidos', 'observaciones']
    ordering = ['-fecha', 'trabajador__apellidos']
    raw_id_fields = ['trabajador', 'registrado_por']
    date_hierarchy = 'fecha'
    
    fieldsets = (
        ('Información', {
            'fields': ('trabajador', 'fecha', 'estado', 'tipo')
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
        ('Registro', {
            'fields': ('registrado_por',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Asignar automáticamente el usuario que registra"""
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Sondaje)
class SondajeAdmin(admin.ModelAdmin):
    list_display = ['nombre_sondaje', 'contrato', 'profundidad', 'estado', 'fecha_inicio']
    list_filter = ['estado', 'contrato', 'fecha_inicio']
    search_fields = ['nombre_sondaje', 'contrato__nombre_contrato']
    ordering = ['nombre_sondaje']
    raw_id_fields = ['contrato']

@admin.register(TipoActividad)
class TipoActividadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']

@admin.register(TipoTurno)
class TipoTurnoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']

@admin.register(TipoComplemento)
class TipoComplementoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'descripcion']
    list_filter = ['categoria']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']

@admin.register(TipoAditivo)
class TipoAditivoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'unidad_medida_default', 'descripcion']
    list_filter = ['categoria']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']
    raw_id_fields = ['unidad_medida_default']

@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'simbolo']
    search_fields = ['nombre', 'simbolo']
    ordering = ['nombre']

# ======================================
# MODELOS DE TURNO (SIMPLIFICADOS)
# ======================================

@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_sondajes_display', 'fecha', 'maquina', 'tipo_turno']
    list_filter = ['fecha', 'tipo_turno', 'sondajes__contrato']
    search_fields = ['sondajes__nombre_sondaje', 'maquina__nombre']
    date_hierarchy = 'fecha'
    ordering = ['-fecha']
    raw_id_fields = ['maquina', 'tipo_turno']

    def get_sondajes_display(self, obj):
        return ', '.join([s.nombre_sondaje for s in obj.sondajes.all()[:3]])
    get_sondajes_display.short_description = 'Sondajes'

# Solo registrar si estos modelos existen
try:
    @admin.register(EstadoTurno)
    class EstadoTurnoAdmin(admin.ModelAdmin):
        list_display = ['nombre', 'descripcion']
        search_fields = ['nombre', 'descripcion']
        ordering = ['nombre']
except:
    pass

try:
    @admin.register(TurnoTrabajador)
    class TurnoTrabajadorAdmin(admin.ModelAdmin):
        list_display = ['turno', 'trabajador', 'funcion']
        list_filter = ['funcion']
        search_fields = ['trabajador__nombres', 'trabajador__apellidos', 'trabajador__dni', 'turno__sondajes__nombre_sondaje']
        raw_id_fields = ['turno', 'trabajador']
except:
    pass

try:
    @admin.register(TurnoComplemento)
    class TurnoComplementoAdmin(admin.ModelAdmin):
        list_display = ['turno', 'tipo_complemento', 'codigo_serie']
        search_fields = ['codigo_serie', 'turno__sondajes__nombre_sondaje']
        raw_id_fields = ['turno', 'tipo_complemento']
except:
    pass

try:
    @admin.register(TurnoAditivo)
    class TurnoAditivoAdmin(admin.ModelAdmin):
        list_display = ['turno', 'tipo_aditivo', 'cantidad_usada']
        search_fields = ['turno__sondajes__nombre_sondaje', 'tipo_aditivo__nombre']
        raw_id_fields = ['turno', 'tipo_aditivo']
except:
    pass

try:
    @admin.register(TurnoActividad)
    class TurnoActividadAdmin(admin.ModelAdmin):
        list_display = ['turno', 'actividad', 'hora_inicio', 'hora_fin']
        search_fields = ['turno__sondajes__nombre_sondaje', 'actividad__nombre']
        raw_id_fields = ['turno', 'actividad']
except:
    pass

try:
    @admin.register(TurnoCorrida)
    class TurnoCorridaAdmin(admin.ModelAdmin):
        list_display = ['turno', 'corrida_numero', 'desde', 'hasta']
        search_fields = ['turno__sondajes__nombre_sondaje', 'corrida_numero']
        raw_id_fields = ['turno']
except:
    pass

try:
    @admin.register(TurnoAvance)
    class TurnoAvanceAdmin(admin.ModelAdmin):
        list_display = ['turno', 'metros_perforados']
        search_fields = ['turno__sondajes__nombre_sondaje']
        raw_id_fields = ['turno']
except:
    pass

try:
    @admin.register(Abastecimiento)
    class AbastecimientoAdmin(admin.ModelAdmin):
        list_display = ['descripcion', 'contrato', 'familia', 'cantidad', 'unidad_medida', 'fecha']
        list_filter = ['familia', 'contrato', 'fecha']
        search_fields = ['descripcion', 'codigo_producto']
        date_hierarchy = 'fecha'
        ordering = ['-fecha']
        raw_id_fields = ['contrato', 'unidad_medida', 'tipo_complemento', 'tipo_aditivo']
except:
    pass

try:
    @admin.register(ConsumoStock)
    class ConsumoStockAdmin(admin.ModelAdmin):
        list_display = ['turno', 'abastecimiento', 'cantidad_consumida']  # Sin fecha_consumo
        search_fields = ['turno__sondajes__nombre_sondaje', 'abastecimiento__descripcion']
        ordering = ['-id']  # Ordenar por ID en lugar de fecha
        raw_id_fields = ['turno', 'abastecimiento']
except:
    pass

try:
    @admin.register(Cargo)
    class CargoAdmin(admin.ModelAdmin):
        list_display = ['id_cargo', 'nombre', 'is_active']
        list_filter = ['is_active']
        search_fields = ['nombre', 'descripcion']
        ordering = ['nombre']
except:
    pass

try:
    @admin.register(ConfiguracionHoraExtra)
    class ConfiguracionHoraExtraAdmin(admin.ModelAdmin):
        list_display = ['contrato', 'maquina', 'metros_minimos', 'horas_extra', 'activo']
        list_filter = ['activo', 'contrato']
        search_fields = ['contrato__nombre_contrato', 'maquina__nombre']
        ordering = ['contrato', 'maquina']
        raw_id_fields = ['contrato', 'maquina']
except:
    pass

try:
    @admin.register(TurnoHoraExtra)
    class TurnoHoraExtraAdmin(admin.ModelAdmin):
        list_display = ['turno', 'trabajador', 'horas_extra', 'metros_turno', 'created_at']
        list_filter = ['turno__fecha', 'turno__contrato']
        search_fields = ['trabajador__nombres', 'trabajador__apellidos', 'turno__id']
        ordering = ['-created_at']
        raw_id_fields = ['turno', 'trabajador', 'configuracion_aplicada']
        readonly_fields = ['created_at']
except:
    pass

# ======================================
# ADMIN PARA METAS DE MÁQUINA
# ======================================

@admin.register(MetaMaquina)
class MetaMaquinaAdmin(admin.ModelAdmin):
    list_display = [
        'get_periodo_display_short',
        'contrato',
        'maquina',
        'servicio',
        'meta_metros',
        'get_precio_unitario_display',
        'activo',
        'get_tipo_periodo',
        'created_by'
    ]
    
    list_filter = [
        'activo',
        'año',
        'mes',
        'contrato',
        'maquina',
        'servicio'
    ]
    
    search_fields = [
        'contrato__nombre_contrato',
        'maquina__nombre',
        'servicio__nombre',
        'observaciones'
    ]
    
    ordering = ['-año', '-mes', 'contrato', 'maquina']
    
    raw_id_fields = ['contrato', 'maquina', 'servicio', 'created_by']
    
    readonly_fields = ['created_at', 'updated_at', 'get_valor_meta_display']
    
    fieldsets = (
        ('Información General', {
            'fields': ('contrato', 'maquina', 'servicio', 'activo')
        }),
        ('Período Estándar (Mes Operativo 26-25)', {
            'fields': ('año', 'mes'),
            'description': 'El mes operativo va del día 26 del mes anterior al 25 del mes especificado.'
        }),
        ('Período Personalizado (Opcional)', {
            'fields': ('fecha_inicio', 'fecha_fin'),
            'classes': ('collapse',),
            'description': 'Solo complete estas fechas si necesita un período diferente al mes operativo estándar.'
        }),
        ('Meta y Valorización', {
            'fields': ('meta_metros', 'get_valor_meta_display', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_periodo_display_short(self, obj):
        """Muestra el período de forma compacta"""
        fecha_inicio = obj.get_fecha_inicio_periodo()
        fecha_fin = obj.get_fecha_fin_periodo()
        return f"{fecha_inicio.strftime('%d/%m/%y')} - {fecha_fin.strftime('%d/%m/%y')}"
    get_periodo_display_short.short_description = 'Período'
    
    def get_tipo_periodo(self, obj):
        """Indica si es mes operativo o personalizado"""
        if obj.fecha_inicio and obj.fecha_fin:
            return '📅 Personalizado'
        return '📆 Mes Operativo'
    get_tipo_periodo.short_description = 'Tipo'
    
    def get_precio_unitario_display(self, obj):
        """Muestra el precio unitario vigente"""
        precio = obj.obtener_precio_unitario()
        if precio:
            return f"{precio.moneda} {precio.precio_unitario}/m"
        return '-'
    get_precio_unitario_display.short_description = 'PU'
    
    def get_valor_meta_display(self, obj):
        """Muestra el valor monetario de la meta"""
        monto, moneda, pu = obj.calcular_valor_meta()
        if monto:
            return f"{moneda} {monto:,.2f} ({pu}/m × {obj.meta_metros}m)"
        return 'Sin precio unitario asignado'
    get_valor_meta_display.short_description = 'Valor de Meta'
    
    def save_model(self, request, obj, form, change):
        """Asignar automáticamente el usuario que crea la meta"""
        if not change:  # Solo al crear (no al editar)
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        """Permitir eliminar metas"""
        if request.user.is_superuser:
            return True
        if obj and obj.created_by == request.user:
            return True
        return False


@admin.register(PrecioUnitarioServicio)
class PrecioUnitarioServicioAdmin(admin.ModelAdmin):
    list_display = [
        'contrato',
        'servicio',
        'precio_unitario',
        'moneda',
        'fecha_inicio_vigencia',
        'fecha_fin_vigencia',
        'activo',
        'get_estado_vigencia'
    ]
    
    list_filter = [
        'activo',
        'moneda',
        'contrato',
        'servicio',
        'fecha_inicio_vigencia'
    ]
    
    search_fields = [
        'contrato__nombre_contrato',
        'servicio__nombre',
        'observaciones'
    ]
    
    ordering = ['-fecha_inicio_vigencia', 'contrato', 'servicio']
    
    raw_id_fields = ['contrato', 'servicio', 'created_by']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información General', {
            'fields': ('contrato', 'servicio', 'activo')
        }),
        ('Precio', {
            'fields': ('precio_unitario', 'moneda')
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio_vigencia', 'fecha_fin_vigencia'),
            'description': 'Defina el período en el que aplica este precio. Dejar fecha fin vacía para vigencia indefinida.'
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_estado_vigencia(self, obj):
        """Muestra si el precio está vigente hoy"""
        from datetime import date
        if obj.esta_vigente(date.today()):
            return '✅ Vigente'
        return '❌ No vigente'
    get_estado_vigencia.short_description = 'Estado'
    
    def save_model(self, request, obj, form, change):
        """Asignar automáticamente el usuario que crea el precio"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ======================================
# ORGANIGRAMA SEMANAL
# ======================================

class AsignacionOrganigramaInline(admin.TabularInline):
    model = AsignacionOrganigrama
    extra = 0
    fields = ['trabajador', 'maquina', 'guardia', 'estado', 'observaciones']
    raw_id_fields = ['trabajador', 'maquina']
    autocomplete_fields = ['trabajador', 'maquina']

class GuardiaConductorInline(admin.TabularInline):
    model = GuardiaConductor
    extra = 0
    fields = ['conductor', 'vehiculo', 'guardia', 'estado', 'observaciones']
    raw_id_fields = ['conductor', 'vehiculo']
    autocomplete_fields = ['conductor', 'vehiculo']

class AsignacionEquipoInlineOrganigrama(admin.TabularInline):
    """Inline para mostrar asignaciones de equipos en el organigrama semanal"""
    model = AsignacionEquipo
    extra = 0
    fields = ['trabajador', 'equipo', 'estado', 'fecha_devolucion', 'acta_entrega']
    raw_id_fields = ['trabajador', 'equipo']
    readonly_fields = ['fecha_asignacion']
    verbose_name = 'Asignación de Equipo'
    verbose_name_plural = 'Asignaciones de Equipos'

@admin.register(OrganigramaSemanal)
class OrganigramaSemanalAdmin(admin.ModelAdmin):
    list_display = [
        'contrato',
        'semana_numero',
        'anio',
        'fecha_inicio',
        'fecha_fin',
        'estado',
        'get_total_asignaciones',
        'modificado_por',
        'updated_at'
    ]
    
    list_filter = [
        'estado',
        'anio',
        'contrato',
        'created_at'
    ]
    
    search_fields = [
        'contrato__nombre_contrato',
        'observaciones'
    ]
    
    ordering = ['-anio', '-semana_numero']
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'creado_por',
        'modificado_por'
    ]
    
    fieldsets = (
        ('Información de Semana', {
            'fields': ('contrato', 'anio', 'semana_numero', 'fecha_inicio', 'fecha_fin')
        }),
        ('Estado', {
            'fields': ('estado', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'modificado_por', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [AsignacionOrganigramaInline, GuardiaConductorInline, AsignacionEquipoInlineOrganigrama]
    
    def get_total_asignaciones(self, obj):
        """Muestra el total de asignaciones en esa semana"""
        total = obj.asignaciones.count()
        operativos = obj.asignaciones.filter(estado='OPERATIVO').count()
        standby = obj.asignaciones.filter(estado='STAND_BY').count()
        return f"{total} total ({operativos} operativos, {standby} stand by)"
    get_total_asignaciones.short_description = 'Asignaciones'
    
    def save_model(self, request, obj, form, change):
        """Asignar usuario que crea/modifica"""
        if not change:
            obj.creado_por = request.user
        else:
            obj.modificado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(AsignacionOrganigrama)
class AsignacionOrganigramaAdmin(admin.ModelAdmin):
    list_display = [
        'trabajador',
        'get_cargo',
        'organigrama_semanal',
        'maquina',
        'guardia',
        'estado',
        'updated_at'
    ]
    
    list_filter = [
        'estado',
        'guardia',
        'organigrama_semanal__anio',
        'organigrama_semanal__semana_numero',
        'maquina'
    ]
    
    search_fields = [
        'trabajador__nombres',
        'trabajador__apellidos',
        'trabajador__dni',
        'maquina__nombre',
        'observaciones'
    ]
    
    ordering = ['-organigrama_semanal__anio', '-organigrama_semanal__semana_numero', 'trabajador__apellidos']
    
    raw_id_fields = ['organigrama_semanal', 'trabajador', 'maquina']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Organigrama', {
            'fields': ('organigrama_semanal',)
        }),
        ('Trabajador', {
            'fields': ('trabajador',)
        }),
        ('Asignación', {
            'fields': ('maquina', 'guardia', 'estado')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_cargo(self, obj):
        """Muestra el cargo del trabajador"""
        return obj.trabajador.cargo.nombre
    get_cargo.short_description = 'Cargo'
    get_cargo.admin_order_field = 'trabajador__cargo__nombre'


@admin.register(GuardiaConductor)
class GuardiaConductorAdmin(admin.ModelAdmin):
    list_display = [
        'conductor',
        'organigrama_semanal',
        'guardia',
        'vehiculo',
        'estado',
        'updated_at'
    ]
    
    list_filter = [
        'guardia',
        'estado',
        'organigrama_semanal__anio',
        'organigrama_semanal__semana_numero'
    ]
    
    search_fields = [
        'conductor__nombres',
        'conductor__apellidos',
        'conductor__dni',
        'vehiculo__placa',
        'observaciones'
    ]
    
    ordering = ['-organigrama_semanal__anio', '-organigrama_semanal__semana_numero', 'guardia', 'conductor__apellidos']
    
    raw_id_fields = ['organigrama_semanal', 'conductor', 'vehiculo']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Organigrama', {
            'fields': ('organigrama_semanal',)
        }),
        ('Conductor', {
            'fields': ('conductor',)
        }),
        ('Guardia y Vehículo', {
            'fields': ('guardia', 'vehiculo', 'estado')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# ============================================================================
# EQUIPOS (Laptops, Celulares, Módems, Impresoras, etc.)
# ============================================================================

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_interno', 
        'tipo', 
        'marca', 
        'modelo', 
        'numero_serie',
        'estado', 
        'contrato',
        'numero_telefono',
        'operador'
    ]
    
    list_filter = [
        'estado', 
        'tipo', 
        'contrato',
        'fecha_adquisicion',
        'operador'
    ]
    
    search_fields = [
        'codigo_interno',
        'marca',
        'modelo',
        'numero_serie',
        'numero_telefono',
        'descripcion'
    ]
    
    ordering = ['tipo', 'codigo_interno']
    
    raw_id_fields = ['contrato']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información General', {
            'fields': ('contrato', 'codigo_interno', 'tipo', 'estado')
        }),
        ('Detalles del Equipo', {
            'fields': ('marca', 'modelo', 'numero_serie', 'descripcion')
        }),
        ('Comunicación (para celulares/radios/módems)', {
            'fields': ('numero_telefono', 'operador'),
            'classes': ('collapse',),
            'description': 'Información relevante para equipos de comunicación'
        }),
        ('Fechas', {
            'fields': ('fecha_adquisicion', 'fecha_garantia_vencimiento')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Optimizar query con select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('contrato')


@admin.register(AsignacionEquipo)
class AsignacionEquipoAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'get_trabajador',
        'get_equipo',
        'get_tipo_equipo',
        'estado',
        'fecha_asignacion',
        'fecha_devolucion',
        'acta_entrega',
        'get_semana_info'
    ]
    
    list_filter = [
        'estado',
        'equipo__tipo',
        'acta_entrega',
        'fecha_asignacion',
        'organigrama_semanal__contrato',
        'organigrama_semanal__anio',
        'organigrama_semanal__semana_numero'
    ]
    
    search_fields = [
        'trabajador__nombres',
        'trabajador__apellidos',
        'trabajador__dni',
        'equipo__codigo_interno',
        'equipo__marca',
        'equipo__modelo',
        'observaciones'
    ]
    
    ordering = ['-fecha_asignacion', 'trabajador__apellidos']
    
    raw_id_fields = ['organigrama_semanal', 'trabajador', 'equipo']
    
    readonly_fields = ['created_at', 'updated_at']
    
    date_hierarchy = 'fecha_asignacion'
    
    fieldsets = (
        ('Organigrama', {
            'fields': ('organigrama_semanal',)
        }),
        ('Asignación', {
            'fields': ('trabajador', 'equipo', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_asignacion', 'fecha_devolucion')
        }),
        ('Responsabilidad', {
            'fields': ('acta_entrega', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_trabajador(self, obj):
        """Mostrar nombre completo del trabajador"""
        return f"{obj.trabajador.nombres} {obj.trabajador.apellidos}"
    get_trabajador.short_description = 'Trabajador'
    get_trabajador.admin_order_field = 'trabajador__apellidos'
    
    def get_equipo(self, obj):
        """Mostrar código del equipo"""
        return obj.equipo.codigo_interno
    get_equipo.short_description = 'Código Equipo'
    get_equipo.admin_order_field = 'equipo__codigo_interno'
    
    def get_tipo_equipo(self, obj):
        """Mostrar tipo de equipo"""
        return obj.equipo.get_tipo_display()
    get_tipo_equipo.short_description = 'Tipo'
    get_tipo_equipo.admin_order_field = 'equipo__tipo'
    
    def get_semana_info(self, obj):
        """Mostrar información de la semana del organigrama"""
        return f"Sem {obj.organigrama_semanal.semana_numero}/{obj.organigrama_semanal.anio}"
    get_semana_info.short_description = 'Semana'
    get_semana_info.admin_order_field = 'organigrama_semanal__semana_numero'
    
    def get_queryset(self, request):
        """Optimizar query con select_related"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'trabajador',
            'trabajador__cargo',
            'equipo',
            'equipo__contrato',
            'organigrama_semanal',
            'organigrama_semanal__contrato'
        )
