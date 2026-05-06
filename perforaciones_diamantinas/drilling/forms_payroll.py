"""
Formularios del módulo de Planilla / Bonos.
"""
from django import forms
from django.forms import inlineformset_factory

from .models_payroll import (
    TipoBono,
    ConceptoBono,
    CriterioBono,
    ConfiguracionBonoContrato,
    ConceptoBonoContrato,
    EscalaBonoContrato,
    PeriodoBono,
    BonoTrabajador,
    BonoTrabajadorDetalle,
    EstructuraSalarial,
    AsignacionEstructuraSalarial,
)


class TipoBonoForm(forms.ModelForm):
    """Form para crear/editar tipos de bono custom."""

    class Meta:
        model = TipoBono
        fields = ['codigo', 'nombre', 'categoria', 'tipo_calculo', 'descripcion', 'activo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: B5'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del bono'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'tipo_calculo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ConceptoBonoForm(forms.ModelForm):
    """Form para conceptos dentro de un tipo de bono."""

    class Meta:
        model = ConceptoBono
        fields = ['codigo', 'nombre', 'es_obligatorio', 'peso_default', 'orden']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: EFICIENCIA'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'es_obligatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'peso_default': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }


ConceptoBonoFormSet = inlineformset_factory(
    TipoBono,
    ConceptoBono,
    form=ConceptoBonoForm,
    extra=1,
    can_delete=True,
)


class CriterioBonoForm(forms.ModelForm):
    """Form para criterios (sub-conceptos / checkboxes) de un concepto."""

    class Meta:
        model = CriterioBono
        fields = ['nombre', 'orden', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del criterio'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


CriterioBonoFormSet = inlineformset_factory(
    ConceptoBono,
    CriterioBono,
    form=CriterioBonoForm,
    extra=3,
    can_delete=True,
)


class ConfiguracionBonoContratoForm(forms.ModelForm):
    """Form para configurar un bono en un contrato."""

    # Campo extra: selección múltiple de cargos (no es un campo del modelo,
    # se mapea a cargos_aplicables JSONField en save())
    cargos_seleccionados = forms.MultipleChoiceField(
        choices=[],
        required=False,
        label='Cargos Aplicables',
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'id': 'id_cargos_seleccionados',
            'size': '8',
        }),
        help_text='Mantén Ctrl (Windows) o ⌘ (Mac) para seleccionar varios cargos. '
                  'Al seleccionar un cargo se auto-completa el Monto Base desde la Estructura Salarial.',
    )

    # Campo oculto: JSON con montos específicos por cargo {"CARGO": monto}
    montos_por_cargo_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_montos_por_cargo_json'}),
    )

    # Campo oculto: JSON con tipo de cálculo por trabajador {"DNI": "metraje"|"cumplimiento"}
    tipo_calculo_por_trabajador_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_tipo_calculo_por_trabajador_json'}),
    )

    class Meta:
        model = ConfiguracionBonoContrato
        fields = [
            'contrato', 'tipo_bono', 'monto_base_mensual', 'monto_por_dia',
            'usa_dias_regimen', 'dias_base_fijo', 'tipo_calculo_default', 'activo',
            'vigencia_desde', 'vigencia_hasta', 'observaciones',
        ]
        widgets = {
            'contrato': forms.Select(attrs={'class': 'form-select', 'id': 'id_contrato'}),
            'tipo_bono': forms.Select(attrs={'class': 'form-select'}),
            'monto_base_mensual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_monto_base_mensual'}),
            'monto_por_dia': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'usa_dias_regimen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_base_fijo': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'tipo_calculo_default': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'vigencia_desde': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'vigencia_hasta': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        import json
        super().__init__(*args, **kwargs)
        self.fields['tipo_bono'].queryset = TipoBono.objects.filter(activo=True)
        if user and not user.has_access_to_all_contracts():
            from .models import Contrato
            self.fields['contrato'].queryset = Contrato.objects.filter(pk=user.contrato_id)

        # Si hay instancia con contrato, cargar los cargos disponibles
        instance = kwargs.get('instance')
        contrato_id = None
        if instance and instance.contrato_id:
            contrato_id = instance.contrato_id
        elif args and args[0]:  # POST data
            contrato_id = args[0].get('contrato')

        if contrato_id:
            from .models import Trabajador
            cargos = (
                Trabajador.objects.filter(contrato_id=contrato_id, estado='ACTIVO')
                .values_list('cargo', flat=True)
                .distinct()
                .order_by('cargo')
            )
            choices = [(c, c) for c in cargos if c]
            self.fields['cargos_seleccionados'].choices = choices

            # Pre-seleccionar los cargos guardados en la instancia
            if instance and instance.cargos_aplicables:
                self.fields['cargos_seleccionados'].initial = list(instance.cargos_aplicables)

            # Pre-cargar montos_por_cargo como JSON para el template JS
            if instance and instance.montos_por_cargo:
                self.fields['montos_por_cargo_json'].initial = json.dumps(instance.montos_por_cargo)

            # Pre-cargar tipo_calculo_por_trabajador como JSON para el template JS
            if instance and instance.tipo_calculo_por_trabajador:
                self.fields['tipo_calculo_por_trabajador_json'].initial = json.dumps(
                    instance.tipo_calculo_por_trabajador
                )

    def save(self, commit=True):
        import json
        instance = super().save(commit=False)
        cargos = self.cleaned_data.get('cargos_seleccionados', [])
        instance.cargos_aplicables = list(cargos)

        # Deserializar montos por cargo desde el campo oculto
        montos_json = self.cleaned_data.get('montos_por_cargo_json', '')
        try:
            montos = json.loads(montos_json) if montos_json else {}
            # Solo guardar montos para cargos que están en la selección actual
            instance.montos_por_cargo = {
                cargo: float(montos[cargo])
                for cargo in cargos
                if cargo in montos and montos[cargo]
            }
        except (ValueError, TypeError, KeyError):
            instance.montos_por_cargo = {}

        # monto_base_mensual = máximo de los montos por cargo (fallback global)
        if instance.montos_por_cargo:
            instance.monto_base_mensual = max(instance.montos_por_cargo.values())

        # Deserializar tipo_calculo_por_trabajador desde el campo oculto
        tipo_calc_json = self.cleaned_data.get('tipo_calculo_por_trabajador_json', '')
        try:
            tipo_calc_raw = json.loads(tipo_calc_json) if tipo_calc_json else {}
            instance.tipo_calculo_por_trabajador = {
                dni: tipo
                for dni, tipo in tipo_calc_raw.items()
                if tipo in ('metraje', 'cumplimiento', 'ambos')
            }
        except (ValueError, TypeError):
            instance.tipo_calculo_por_trabajador = {}

        if commit:
            instance.save()
        return instance


class ConceptoBonoContratoForm(forms.ModelForm):

    class Meta:
        model = ConceptoBonoContrato
        fields = ['concepto', 'monto']
        widgets = {
            'concepto': forms.Select(attrs={'class': 'form-select'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


ConceptoBonoContratoFormSet = inlineformset_factory(
    ConfiguracionBonoContrato,
    ConceptoBonoContrato,
    form=ConceptoBonoContratoForm,
    extra=0,
    can_delete=True,
)


class EscalaBonoContratoForm(forms.ModelForm):

    class Meta:
        model = EscalaBonoContrato
        fields = ['dias_desde', 'dias_hasta', 'monto']
        widgets = {
            'dias_desde': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'dias_hasta': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


EscalaBonoContratoFormSet = inlineformset_factory(
    ConfiguracionBonoContrato,
    EscalaBonoContrato,
    form=EscalaBonoContratoForm,
    extra=1,
    can_delete=True,
)


class AbrirPeriodoForm(forms.Form):
    """Form para abrir un período de bonos."""
    MES_CHOICES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
    ]
    anio = forms.IntegerField(
        min_value=2024, max_value=2030,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Año'
    )
    mes = forms.ChoiceField(
        choices=MES_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Mes'
    )


class PuntajeDetalleForm(forms.ModelForm):
    """Form para ingresar puntaje de un concepto."""

    class Meta:
        model = BonoTrabajadorDetalle
        fields = ['puntaje']
        widgets = {
            'puntaje': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-center',
                'step': '1',
                'min': '0',
                'max': '100',
                'style': 'width: 80px;',
            }),
        }


class EstructuraSalarialForm(forms.ModelForm):
    """Form para crear/editar estructura salarial por CTR y cargo."""

    motivo_cambio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Motivo del cambio (requerido al editar)',
        }),
        label='Motivo del Cambio',
    )

    class Meta:
        model = EstructuraSalarial
        fields = [
            'contrato', 'contrato_servicio', 'cargo_contratado', 'maquina',
            'sueldo_basico', 'bono_por_metraje', 'metraje_base',
            'bonificacion_area', 'activo', 'observaciones',
        ]
        widgets = {
            'contrato': forms.Select(attrs={'class': 'form-select'}),
            'contrato_servicio': forms.Select(attrs={'class': 'form-select'}),
            'cargo_contratado': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: PERFORISTA, AYUDANTE PERFORISTA',
                'list': 'cargos-list',
            }),
            'maquina': forms.Select(attrs={'class': 'form-select'}),
            'sueldo_basico': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
            'bono_por_metraje': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
            'metraje_base': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
            'bonificacion_area': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Contrato, ContratoServicio, Maquina
        self.fields['contrato'].queryset = Contrato.objects.filter(
            estado='ACTIVO'
        ).order_by('nombre_contrato')
        self.fields['contrato_servicio'].queryset = ContratoServicio.objects.filter(
            activo=True
        ).select_related('contrato').order_by('contrato__nombre_contrato', 'tipo_servicio')
        # Filter machines by the instance's contract if editing
        if self.instance and self.instance.pk and self.instance.contrato_id:
            self.fields['maquina'].queryset = Maquina.objects.filter(
                contrato=self.instance.contrato
            ).order_by('nombre')
        else:
            self.fields['maquina'].queryset = Maquina.objects.none()
        self.fields['maquina'].required = False
        self.fields['maquina'].empty_label = '— General (todas las máquinas) —'


class AsignacionEstructuraSalarialForm(forms.ModelForm):
    """Form para asignar una EstructuraSalarial específica a un trabajador."""

    class Meta:
        model = AsignacionEstructuraSalarial
        fields = ['trabajador', 'estructura_salarial', 'fecha_inicio', 'fecha_fin', 'observaciones']
        widgets = {
            'trabajador': forms.HiddenInput(),
            'estructura_salarial': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, contrato=None, cargo=None, maquina_trabajador=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._maquina_trabajador = maquina_trabajador
        self.add_warning = False
        self.fields['estructura_salarial'].empty_label = '— Seleccionar estructura —'
        if contrato and cargo:
            self.fields['estructura_salarial'].queryset = EstructuraSalarial.objects.filter(
                contrato=contrato,
                cargo_contratado=cargo,
                activo=True,
            ).select_related('maquina').order_by('maquina__nombre')
        elif contrato:
            self.fields['estructura_salarial'].queryset = EstructuraSalarial.objects.filter(
                contrato=contrato,
                activo=True,
            ).select_related('maquina').order_by('cargo_contratado', 'maquina__nombre')
        else:
            self.fields['estructura_salarial'].queryset = EstructuraSalarial.objects.none()
        self.fields['fecha_fin'].required = False

    def clean_estructura_salarial(self):
        estructura = self.cleaned_data.get('estructura_salarial')
        if (estructura and self._maquina_trabajador
                and estructura.maquina_id
                and estructura.maquina_id != self._maquina_trabajador.pk):
            self.add_warning = True
        return estructura
