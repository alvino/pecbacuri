
from django.contrib import admin
from django import forms

from django.utils import timezone
from .models import  BaixaAnimal, Lote, Animal


   

class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ['identificacao','nome','sexo','data_nascimento','lote_atual', 'pasto_atual','observacoes']
        initial = {'data_nascimento': timezone.localdate()}
        widgets = {
            'identificacao': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),   
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'data_nascimento': forms.DateInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date'}),
            'lote_atual': forms.Select(attrs={'class': 'form-select'}),
            'pasto_atual': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }



class MudarLoteAnimalForm(forms.Form):
    lote_destino = forms.ModelChoiceField(
        queryset=Lote.objects.all(), # Assumindo que Lote foi importado
        required=True,
        label="Lote de Destino",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    data_entrada = forms.DateField(
        initial=timezone.localdate(),
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
        label="Data da mudaca de Lote"
    )
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False,
        label="Observações da Mudança de Lote"
    )


class BaixaAnimalForm(forms.Form):
    
    data_baixa = forms.DateField(
        initial=timezone.localdate(),
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
        label="Data de Baixa"
    )
    CAUSA_CHOICES = (
        ('DOENCA', 'Doença'),
        ('ACIDENTE', 'Acidente'),
        ('PREDACAO', 'Predação'),
        ('OUTRO', 'Outro'),
    )

    causa = forms.ChoiceField(
        choices=CAUSA_CHOICES,
        initial='DOENCA',
        label="Causa da Morte",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False,
        label="Observações da Baixa"
    )
    Animal = forms.ModelChoiceField(
        queryset=Animal.objects.all(),
        required=True,
        label="Animal",
        widget=forms.Select(attrs={'class': 'form-select'})
    )