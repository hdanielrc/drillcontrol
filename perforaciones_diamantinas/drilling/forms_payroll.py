"""
Formularios del módulo de Planilla / Bonos.
"""
from django import forms
from django.forms import inlineformset_factory

from .models_payroll import (
    TipoBono,
    ConceptoBono,
    ConfiguracionBonoContrato,
    ConceptoBonoContrato,
    EscalaBonoContrato,
    PeriodoBono,
    BonoTrabajador,
    BonoTrabajadorDetalle,
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


class ConfiguracionBonoContratoForm(forms.ModelForm):
    """Form para configurar un bono en un contrato."""

    class Meta:
        model = ConfiguracionBonoContrato
        fields = [
            'contrato', 'tipo_bono', 'monto_base_mensual', 'monto_por_dia',
            'usa_dias_regimen', 'dias_base_fijo', 'activo',
            'vigencia_desde', 'vigencia_hasta', 'observaciones',
        ]
        widgets = {
            'contrato': forms.Select(attrs={'class': 'form-select'}),
            'tipo_bono': forms.Select(attrs={'class': 'form-select'}),
            'monto_base_mensual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'monto_por_dia': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'usa_dias_regimen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_base_fijo': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'vigencia_desde': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'vigencia_hasta': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_bono'].queryset = TipoBono.objects.filter(activo=True)
        if user and not user.has_access_to_all_contracts():
            from .models import Contrato
            self.fields['contrato'].queryset = Contrato.objects.filter(pk=user.contrato_id)


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
