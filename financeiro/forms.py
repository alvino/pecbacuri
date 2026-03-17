
from django.utils import timezone
from django import forms

from rebanho.models import Animal
from .models import CategoriaDespesa, Despesa, Venda


class CategoriaDespesaForm(forms.ModelForm):
    class Meta:
        model = CategoriaDespesa
        fields = ['nome']
        
        widgets = {
            'nome': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: Nutrição, Medicamentos, Infraestrutura...',
                    'autofocus': True
                }
            ),
        }

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        # Verifica se já existe uma categoria com o mesmo nome (ignorando maiúsculas/minúsculas)
        if CategoriaDespesa.objects.filter(nome__iexact=nome).exists():
            raise forms.ValidationError("Já existe uma categoria cadastrada com este nome.")
        return nome


class VendaForm(forms.Form):
    
    data_venda = forms.DateField(
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        initial=timezone.localdate()
    )
    peso_venda = forms.DecimalField(
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Kg'}
        )
    )   
    valor_total = forms.DecimalField(
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'R$'}
        )
    )   
    comprador = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Nome do comprador ou frigorífico'}
        )
    )
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observações adicionais sobre a venda'}
        )
    )
    animais = forms.ModelMultipleChoiceField(
        queryset=Animal.objects.filter(situacao='VIVO'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'animal-checkbox'}),
        label="Selecione os animais",
    )


    def clean_valor_total(self):
        valor = self.cleaned_data.get('valor_total')
        if valor and valor <= 0:
            raise forms.ValidationError("O valor da venda deve ser maior que zero.")
        return valor

    def clean_peso_venda(self):
        peso = self.cleaned_data.get('peso_venda')
        if peso and peso <= 0:
            raise forms.ValidationError("O peso de venda deve ser um número positivo.")
        return peso
    

class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        # Incluímos apenas os campos que o usuário deve preencher manualmente
        fields = ['data_pagamento', 'descricao', 'valor', 'categoria', 'tipo']
        initial = {'data_pagamento': timezone.localdate()}
       
        widgets = {
            'data_pagamento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'descricao': forms.TextInput(
                attrs={'placeholder': 'Ex: Compra de vacinas contra febre aftosa', 'class': 'form-control'}
            ),
            'valor': forms.NumberInput(
                attrs={'step': '0.01', 'class': 'form-control', 'placeholder': '0,00'}
            ),
            'categoria': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'tipo': forms.Select(
                attrs={'class': 'form-select'}
            ),
        }

    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor <= 0:
            raise forms.ValidationError("O valor da despesa deve ser maior que zero.")
        return valor