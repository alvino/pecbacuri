from django.contrib import admin
from django import forms

from django.utils import timezone
from .models import Pasto, Lote, Animal, TratamentoSaude, Reproducao, Pasto, Pesagem


class PesagemForm(forms.ModelForm):
    class Meta:
        model = Pesagem
        fields = ['animal', 'data_pesagem', 'peso_kg', 'evento']
        widgets = {
            'animal': forms.Select(attrs={'class': 'form-select'}),
            'data_pesagem': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'peso_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'evento': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


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


class AnimalPesagemForm(forms.ModelForm):
    class Meta:
        model = Pesagem
        fields = [ 'data_pesagem', 'peso_kg', 'evento']
        widgets = {
            'data_pesagem': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'peso_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'evento': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }




class AnimalTratamentoForm(forms.ModelForm):
    class Meta:
        model = TratamentoSaude
        fields = ['data_tratamento', 'tipo_tratamento', 'produto', 'dose', 'descricao', 'data_proximo_tratamento']
    
        widgets = {
            'data_tratamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_tratamento': forms.Select(attrs={'class': 'form-select'}),
            'produto': forms.TextInput(attrs={'class': 'form-control'}),
            'dose': forms.TextInput(attrs={'class': 'form-control'}),
            'data_proximo_tratamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AnimalReproducaoForm(forms.ModelForm):
    class Meta:
        model = Reproducao
        fields = ['data_cio', 'tipo', 'touro', 'codigo_semen', 'data_dg', 'resultado', 'bezerro', 'data_parto_prevista']
        widgets = {
            'data_cio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'touro': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_semen': forms.TextInput(attrs={'class': 'form-control'}),
            'data_dg': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'bezerro': forms.TextInput(attrs={'class': 'form-control'}),
            'data_parto_prevista': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
         

class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ['identificacao','nome','sexo','data_nascimento','lote_atual', 'pasto_atual','observacoes']
        # Adiciona classes do Bootstrap para todos os campos
        widgets = {
            'identificacao': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),   
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'data_nascimento': forms.DateInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date'}),
            'lote_atual': forms.Select(attrs={'class': 'form-select'}),
            'pasto_atual': forms.Select(attrs={'class': 'form-select'}),
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


class MudarLoteAnimalForm(forms.Form):
    lote_destino = forms.ModelChoiceField(
        queryset=Lote.objects.all(), # Assumindo que Lote foi importado
        required=True,
        label="Lote de Destino"
    )
    data_entrada = forms.DateField(
        initial=timezone.localdate(),
        widget=admin.widgets.AdminDateWidget,
        label="Data da mudaca de Lote"
    )
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Observações da Mudança de Lote"
    )