import django_filters
from .models import Pesagem, Reproducao

class ReproducaoFilter(django_filters.FilterSet):
    matriz = django_filters.CharFilter(
        field_name='matriz__identificacao', 
        lookup_expr='icontains', # Busca por identificação que *contém* o texto (case-insensitive)
        label='Buscar por matriz'
    )
    
    # Exemplo opcional: filtrar por faixa de idade
    # idade__gt = django_filters.NumberFilter(field_name='idade', lookup_expr='gt', label='Idade Maior que')

    class Meta:
        model = Reproducao
        fields = ['matriz',] # Lista de campos que serão filtrados


class PesagemFilter(django_filters.FilterSet):
    animal = django_filters.CharFilter(
        field_name='animal__identificacao', 
        lookup_expr='icontains', 
        label='Buscar por animal'
    )
    

    class Meta:
        model = Pesagem
        fields = ['animal']