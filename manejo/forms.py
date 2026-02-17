
from django.contrib import admin
from django import forms

from django.utils import timezone

from rebanho.models import Animal

from .models import  TratamentoSaude, Reproducao, Pesagem



class PesagemForm(forms.Form):
    data_pesagem = forms.DateField(
        label="Data da Pesagem",
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'})
    )
    peso_kg = forms.DecimalField(
        max_digits=7, 
        decimal_places=2,
        label="Peso (kg)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    evento = forms.CharField(
        label="Observações/Evento",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    animais = forms.ModelMultipleChoiceField(
        queryset=Animal.objects.filter(situacao='VIVO'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'animal-checkbox'}),
        label="Selecione os animais",
    )


class PesagemModelForm(forms.ModelForm):
    class Meta:
        model = Pesagem
        fields = ['data_pesagem', 'peso_kg', 'evento']
        initial = {'data_pesagem': timezone.localdate()}
        widgets = {
            'data_pesagem': forms.DateInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date'}),
            'peso_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'evento': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class TratamentoForm(forms.ModelForm):
    animais = forms.ModelMultipleChoiceField(
        queryset=Animal.objects.filter(situacao='VIVO'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'animal-checkbox'}),
        label="Selecione os animais",
    )
    class Meta:
        model = TratamentoSaude
        fields = ['data_tratamento', 'tipo_tratamento', 'produto', 'dose', 'descricao', 'data_proximo_tratamento']
        widgets = {
            'data_tratamento': forms.DateInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_tratamento': forms.Select(attrs={'class': 'form-select'}),
            'produto': forms.TextInput(attrs={'class': 'form-control'}),
            'dose': forms.TextInput(attrs={'class': 'form-control'}),
            'data_proximo_tratamento': forms.DateInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ReproducaoForm(forms.ModelForm):
    matriz = forms.ModelMultipleChoiceField(
        queryset=Animal.objects.filter(situacao='VIVO', sexo='F'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'animal-checkbox'}),
        label="Selecione as matrizes",
    )
    class Meta:
        model = Reproducao
        fields = ['data_cio', 'escore', 'tipo', 'touro', 'codigo_semen', 'data_dg', 'resultado']
        widgets = {
            'data_cio': forms.DateInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date'}),
            'escore': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'step': '0.5'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'touro': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_semen': forms.TextInput(attrs={'class': 'form-control'}),
            'data_dg': forms.DateInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
        }
         
