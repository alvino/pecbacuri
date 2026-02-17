
from django.contrib import admin
from django import forms

from django.utils import timezone

from rebanho.models import Animal
from .models import Pasto


class MovimentacaoPastoForm(forms.Form):
    # Seleção do Destino
    pasto_destino = forms.ModelChoiceField(
        queryset=Pasto.objects.all(),
        label="Pasto de Destino",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg mb-4'})
    )

    data_entrada = forms.DateField(
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control mb-4'}),
        label="Data do Manejo",
        initial=timezone.localdate   
    )

    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Observações da Mudança de Lote"
    )

    animais = forms.ModelMultipleChoiceField(
        queryset=Animal.objects.filter(situacao='VIVO'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'animal-checkbox'}),
        label="Selecione os Animais para Mover"
    )


class PastoForm(forms.ModelForm):
    class Meta:
        model = Pasto
        fields = ['nome', 'area_hectares', 'tipo_capim','capacidade_maxima_ua','observacoes']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'area_hectares': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_capim': forms.TextInput(attrs={'class': 'form-control'}),
            'capacidade_maxima_ua': forms.NumberInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),           
        }

# Formulário temporário para a Action
class MudarPastoLoteForm(forms.Form):
    pasto_destino = forms.ModelChoiceField(
        queryset=Pasto.objects.all(),
        label="Pasto de Destino",
        required=True
    )
    data_entrada = forms.DateField(
        initial=timezone.localdate(),
        widget=admin.widgets.AdminDateWidget,
        label="Data da Entrada no Novo Pasto"
    )
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Observações da Movimentação"
    )
