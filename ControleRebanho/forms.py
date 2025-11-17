from django.contrib import admin
from django import forms

from django.utils import timezone
from .models import Pasto, Lote


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