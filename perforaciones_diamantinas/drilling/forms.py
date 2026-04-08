from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import *

# CargoForm eliminado (Modelo Cargo eliminado)

class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = [
            'contrato', 'dni', 'nombres', 'apepat', 'apemat', 'cargo',
            'cargo_headcount',
            'area', 'maquina_asignada', 'guardia_asignada', 
            'vehiculo_asignado', 'tipo_trabajo', 'regimen_laboral', 'fecha_inicio_ciclo',
            'telefono', 'email', 
            'subestado', 'es_standby',
            'fotocheck_fecha_emision',
            'fecha_contratacion'
        ]
        widgets = {
            'contrato': forms.Select(attrs={'class': 'form-select'}),
            'nombres': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombres',
                'readonly': True
            }),
            'apepat': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apellido Paterno',
                'readonly': True
            }),
            'apemat': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apellido Materno',
                'readonly': True
            }),
            'cargo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Cargo',
                'readonly': True
            }),
            'cargo_headcount': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: RESIDENTE (dejar vacío si coincide con el cargo oficial)'
            }),
            'area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Área de trabajo'}),
            'maquina_asignada': forms.Select(attrs={'class': 'form-select'}),
            'guardia_asignada': forms.Select(attrs={'class': 'form-select'}),
            'vehiculo_asignado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_trabajo': forms.Select(attrs={'class': 'form-select'}),
            'regimen_laboral': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio_ciclo': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'dni': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'DNI',
                'readonly': True
            }),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56 9 1234 5678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'fecha_contratacion': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control', 
                'type': 'date',
                'id': 'id_fecha_contratacion',
                'readonly': True
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'subestado': forms.Select(attrs={'class': 'form-select'}),
            'es_standby': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_es_standby'
            }),
            'fotocheck_fecha_emision': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control', 
                'type': 'date',
                'id': 'id_fotocheck_fecha_emision'
            }),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Establecer valores por defecto para estado y subestado
        if not self.instance.pk:  # Solo para nuevos registros
            self.fields['estado'].initial = 'ACTIVO'
            self.fields['subestado'].initial = 'EN_OPERACION'
            
            # Precargar fecha de ingreso con hoy
            from django.utils import timezone
            if 'fecha_contratacion' in self.fields:
                self.fields['fecha_contratacion'].initial = timezone.now().date()
        
        # Configurar campos opcionales
        self.fields['maquina_asignada'].required = False
        self.fields['guardia_asignada'].required = False
        self.fields['vehiculo_asignado'].required = False
        self.fields['area'].required = False
        self.fields['telefono'].required = False
        self.fields['email'].required = False
        
        # Campos de fotocheck opcionales
        self.fields['fotocheck_fecha_emision'].required = False
        
        # Labels mejorados
        self.fields['maquina_asignada'].label = 'Máquina asignada'
        self.fields['maquina_asignada'].help_text = 'Define agrupación en Tareo y Organigrama'
        self.fields['guardia_asignada'].label = 'Guardia'
        self.fields['guardia_asignada'].help_text = 'A, B o C'
        self.fields['vehiculo_asignado'].label = 'Vehículo asignado'
        self.fields['vehiculo_asignado'].help_text = 'Para conductores'
        
        # Si el usuario tiene acceso limitado, filtrar contratos y preseleccionar
        if user:
            accessible_contracts = user.get_accessible_contracts()
            self.fields['contrato'].queryset = accessible_contracts
            
            # Lógica para filtrar máquinas y vehículos
            base_maquina_qs = Maquina.objects.none()
            base_vehiculo_qs = Vehiculo.objects.none()

            if user.has_access_to_all_contracts():
                # Admin/Gerencia: Ver todas las máquinas operativas
                base_maquina_qs = Maquina.objects.filter(estado='OPERATIVO')
                base_vehiculo_qs = Vehiculo.objects.filter(estado='OPERATIVO')
                
            elif user.contrato:
                # Usuario Contract Manager: Ver solo máquinas de su contrato
                base_maquina_qs = Maquina.objects.filter(contrato=user.contrato, estado='OPERATIVO')
                base_vehiculo_qs = Vehiculo.objects.filter(contrato=user.contrato, estado='OPERATIVO')

            # Asegurar que la máquina actual (si existe) esté en el queryset para evitar errores de validación
            if self.instance.pk and self.instance.maquina_asignada:
                current_maquina = Maquina.objects.filter(pk=self.instance.maquina_asignada.pk)
                base_maquina_qs = (base_maquina_qs | current_maquina).distinct()

            # Asegurar que el vehículo actual (si existe) esté en el queryset
            if self.instance.pk and self.instance.vehiculo_asignado:
                current_vehiculo = Vehiculo.objects.filter(pk=self.instance.vehiculo_asignado.pk)
                base_vehiculo_qs = (base_vehiculo_qs | current_vehiculo).distinct()
            
            # Asignar querysets finales
            self.fields['maquina_asignada'].queryset = base_maquina_qs.order_by('nombre')
            self.fields['vehiculo_asignado'].queryset = base_vehiculo_qs.order_by('placa')
            
            # Si solo tiene acceso a un contrato, preseleccionar y bloquear cambiolo
            if not user.has_access_to_all_contracts() and user.contrato:
                self.fields['contrato'].initial = user.contrato
                # NO usar disabled, solo readonly visual
                self.fields['contrato'].widget.attrs['readonly'] = True
                # Hacer el campo no requerido si ya está preseleccionado
                self.fields['contrato'].required = False

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if dni:
            dni = dni.strip()
            # Validación básica: longitud razonable
            if len(dni) < 6 or len(dni) > 20:
                raise ValidationError("Formato de DNI inválido")
        return dni

class MaquinaForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = ['nombre', 'tipo', 'tipo_trabajo', 'estado', 'horometro']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la máquina'}),
            'tipo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tipo/Modelo de máquina'}),
            'tipo_trabajo': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'horometro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

class SondajeForm(forms.ModelForm):
    class Meta:
        model = Sondaje
        fields = [
            'nombre_sondaje', 'fecha_inicio', 'fecha_fin', 'profundidad', 'inclinacion', 'cota_collar', 'estado',
            # Campos de cierre/desvío
            'motivo_cierre', 'responsable_cierre', 'es_cobrable', 'sondaje_padre',
            'profundidad_alcanzada', 'profundidad_desvio', 'observaciones_cierre',
        ]
        widgets = {
            'nombre_sondaje': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del sondaje'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'profundidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'inclinacion': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '-90', 'max': '90'}),
            'cota_collar': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'motivo_cierre': forms.Select(attrs={'class': 'form-select'}),
            'responsable_cierre': forms.Select(attrs={'class': 'form-select'}),
            'es_cobrable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sondaje_padre': forms.Select(attrs={'class': 'form-select'}),
            'profundidad_alcanzada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'profundidad_desvio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0',
                                                           'placeholder': 'Ej: 100.00'}),
            'observaciones_cierre': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detalle del motivo, acuerdos con el cliente, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)
        # Filtrar sondaje_padre al mismo contrato
        if contrato:
            self.fields['sondaje_padre'].queryset = Sondaje.objects.filter(
                contrato=contrato
            ).exclude(pk=self.instance.pk if self.instance.pk else None).order_by('-fecha_inicio')
        elif self.instance and self.instance.pk and self.instance.contrato_id:
            self.fields['sondaje_padre'].queryset = Sondaje.objects.filter(
                contrato=self.instance.contrato
            ).exclude(pk=self.instance.pk).order_by('-fecha_inicio')
        else:
            self.fields['sondaje_padre'].queryset = Sondaje.objects.none()
        self.fields['sondaje_padre'].empty_label = '--- Ninguno (sondaje nuevo) ---'

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        estado = cleaned_data.get('estado')
        motivo_cierre = cleaned_data.get('motivo_cierre')

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio")

        # Si el estado es CANCELADO o FINALIZADO, exigir motivo de cierre
        if estado in ('CANCELADO', 'FINALIZADO') and not motivo_cierre:
            self.add_error('motivo_cierre', 'Debe indicar el motivo de cierre al finalizar o cancelar un sondaje.')

        return cleaned_data

class TipoActividadForm(forms.ModelForm):
    class Meta:
        model = TipoActividad
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la actividad'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional'}),
        }

class TipoTurnoForm(forms.ModelForm):
    class Meta:
        model = TipoTurno
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del tipo de turno'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional'}),
        }

class TipoComplementoForm(forms.ModelForm):
    class Meta:
        model = TipoComplemento
        fields = ['nombre', 'categoria', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del complemento'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional'}),
        }

class TipoAditivoForm(forms.ModelForm):
    class Meta:
        model = TipoAditivo
        fields = ['nombre', 'categoria', 'unidad_medida_default', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del aditivo'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidad_medida_default': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional'}),
        }

class UnidadMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ['nombre', 'simbolo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la unidad'}),
            'simbolo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Símbolo (ej: kg, m, L)'}),
        }

class AbastecimientoForm(forms.ModelForm):
    class Meta:
        model = Abastecimiento
        fields = [
            'mes', 'fecha', 'contrato', 'codigo_producto', 'descripcion', 'familia', 'serie',
            'unidad_medida', 'cantidad', 'precio_unitario', 'tipo_complemento', 'tipo_aditivo',
            'numero_guia', 'observaciones'
        ]
        widgets = {
            'mes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ENERO, FEBRERO, etc.'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contrato': forms.Select(attrs={'class': 'form-select'}),
            'codigo_producto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código del producto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del producto'}),
            'familia': forms.Select(attrs={'class': 'form-select'}),
            'serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de serie'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tipo_complemento': forms.Select(attrs={'class': 'form-select'}),
            'tipo_aditivo': forms.Select(attrs={'class': 'form-select'}),
            'numero_guia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de guía'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales'}),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad and cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        return cantidad

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get('precio_unitario')
        if precio and precio <= 0:
            raise ValidationError("El precio unitario debe ser mayor a 0")
        return precio

class ConsumoStockForm(forms.ModelForm):
    class Meta:
        model = ConsumoStock
        fields = [
            'turno', 'abastecimiento', 'cantidad_consumida', 'serie_utilizada',
            'metros_inicio', 'metros_fin', 'estado_final', 'observaciones'
        ]
        widgets = {
            'turno': forms.Select(attrs={'class': 'form-select'}),
            'abastecimiento': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_consumida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'serie_utilizada': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Serie del producto utilizado'}),
            'metros_inicio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'metros_fin': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'estado_final': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones del consumo'}),
        }

    def clean_cantidad_consumida(self):
        cantidad = self.cleaned_data.get('cantidad_consumida')
        if cantidad and cantidad <= 0:
            raise ValidationError("La cantidad consumida debe ser mayor a 0")
        return cantidad

    def clean(self):
        cleaned_data = super().clean()
        metros_inicio = cleaned_data.get('metros_inicio')
        metros_fin = cleaned_data.get('metros_fin')

        if metros_inicio and metros_fin and metros_fin < metros_inicio:
            raise ValidationError("Los metros fin deben ser mayores a los metros inicio")

        return cleaned_data


class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        # sondajes ahora es un campo M2M; usar un select múltiple en el formulario
        fields = ['sondajes', 'maquina', 'tipo_turno', 'fecha', 'estado']
        widgets = {
            'sondajes': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
            'maquina': forms.Select(attrs={'class': 'form-select'}),
            'tipo_turno': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }


class AsignacionEquipoForm(forms.ModelForm):
    """Formulario para asignar equipos a trabajadores"""
    
    trabajador = forms.ModelChoiceField(
        queryset=Trabajador.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Trabajador'
    )
    
    equipo = forms.ModelChoiceField(
        queryset=Equipo.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Equipo'
    )
    
    class Meta:
        model = AsignacionEquipo
        fields = ['trabajador', 'equipo', 'fecha_devolucion', 'estado', 'observaciones', 'acta_entrega']
        widgets = {
            'fecha_devolucion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones sobre la asignación...'}),
            'acta_entrega': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user:
            # Filtrar trabajadores por contrato del usuario
            if user.contrato:
                self.fields['trabajador'].queryset = Trabajador.objects.filter(
                    contrato=user.contrato,
                    estado='ACTIVO'
                ).select_related('cargo').order_by('apepat', 'apemat', 'nombres')
                
                # Filtrar equipos disponibles del contrato
                self.fields['equipo'].queryset = Equipo.objects.filter(
                    contrato=user.contrato,
                    estado__in=['DISPONIBLE', 'ASIGNADO']
                ).order_by('tipo', 'codigo_interno')
            else:
                self.fields['trabajador'].queryset = Trabajador.objects.none()
                self.fields['equipo'].queryset = Equipo.objects.none()
        
        # Configurar campos opcionales
        self.fields['fecha_devolucion'].required = False
        self.fields['observaciones'].required = False
        self.fields['acta_entrega'].required = False
        
        # Ayudas
        self.fields['trabajador'].help_text = 'Seleccione el trabajador al que se asignará el equipo'
        self.fields['equipo'].help_text = 'Seleccione el equipo a asignar. Solo se muestran equipos disponibles o ya asignados.'
        self.fields['fecha_devolucion'].help_text = 'Opcional: fecha programada de devolución'
        self.fields['acta_entrega'].help_text = '¿Se firmó acta de entrega-recepción?'
    
    def clean(self):
        cleaned_data = super().clean()
        equipo = cleaned_data.get('equipo')
        estado = cleaned_data.get('estado')
        fecha_devolucion = cleaned_data.get('fecha_devolucion')
        
        # Validar que el equipo esté disponible si es una nueva asignación
        if equipo and not self.instance.pk:
            if equipo.estado == 'MANTENIMIENTO':
                raise ValidationError('No se puede asignar un equipo en mantenimiento.')
            if equipo.estado == 'FUERA_SERVICIO':
                raise ValidationError('No se puede asignar un equipo fuera de servicio.')
            if equipo.estado == 'BAJA':
                raise ValidationError('No se puede asignar un equipo dado de baja.')
        
        # Validar fecha de devolución
        if fecha_devolucion and fecha_devolucion < timezone.now().date():
            raise ValidationError({'fecha_devolucion': 'La fecha de devolución no puede ser anterior a hoy.'})
        
        # Si el estado es DEVUELTO, debe tener fecha de devolución
        if estado == 'DEVUELTO' and not fecha_devolucion:
            cleaned_data['fecha_devolucion'] = timezone.now().date()
        
        return cleaned_data


class TurnoMaquinaForm(forms.ModelForm):
    class Meta:
        model = TurnoMaquina
        fields = ['hora_inicio', 'hora_fin', 'estado_bomba', 'estado_unidad', 'estado_rotacion']
        widgets = {
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'estado_bomba': forms.Select(attrs={'class': 'form-select'}),
            'estado_unidad': forms.Select(attrs={'class': 'form-select'}),
            'estado_rotacion': forms.Select(attrs={'class': 'form-select'}),
        }


class TurnoAvanceForm(forms.ModelForm):
    class Meta:
        model = TurnoAvance
        fields = ['metros_perforados']
        widgets = {
            'metros_perforados': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class HeadCountForm(forms.ModelForm):
    class Meta:
        model = HeadCount
        fields = ['contrato', 'servicio', 'categoria', 'ubicacion', 'cargo', 'nivel', 'cantidad_requerida', 'observaciones', 'activo']
        widgets = {
            'contrato': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'servicio': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'categoria': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'ubicacion': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'cargo': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_requerida': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'required': True,
                'placeholder': 'Cantidad de personas requeridas'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales (opcional)'
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filtrar contratos según permisos del usuario
        if user:
            if user.has_access_to_all_contracts():
                self.fields['contrato'].queryset = Contrato.objects.filter(estado='ACTIVO')
            else:
                self.fields['contrato'].queryset = Contrato.objects.filter(id=user.contrato.id, estado='ACTIVO')