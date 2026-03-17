import django_filters
from django import forms
from .models import Despesa, RegistroDeCusto

class DespesaFilter(django_filters.FilterSet):
    # Filtro por descrição que busca parte do texto (icontains)
    descricao = django_filters.CharFilter(lookup_expr='icontains', label="Descrição")
    

    class Meta:
        model = Despesa
        fields = ['categoria', 'descricao'] # Campos que viram dropdowns automáticos



class RegistroCustoFilter(django_filters.FilterSet):
    # Filtro por descrição que busca parte do texto (icontains)
    descricao = django_filters.CharFilter(lookup_expr='icontains', label="Descrição")
    

    class Meta:
        model = RegistroDeCusto
        fields = ['tipo_custo', 'descricao'] # Campos que viram dropdowns automáticos