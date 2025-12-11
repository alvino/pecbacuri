import django_filters
from .models import Animal

class AnimalFilter(django_filters.FilterSet):
    identificacao = django_filters.CharFilter(
        field_name='identificacao', 
        lookup_expr='icontains', # Busca por identificação que *contém* o texto (case-insensitive)
        label='Buscar por Identificação'
    )
    
    # Exemplo opcional: filtrar por faixa de idade
    # idade__gt = django_filters.NumberFilter(field_name='idade', lookup_expr='gt', label='Idade Maior que')

    class Meta:
        model = Animal
        fields = ['identificacao',] # Lista de campos que serão filtrados