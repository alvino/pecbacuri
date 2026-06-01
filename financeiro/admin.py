from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from rebanho.models import Animal
from .models import  ReceitaGeral, TipoCusto, RegistroDeCusto, CategoriaDespesa, CustoAnimalDetalhe,  Venda,  Despesa


class CategoriaDespesaResource(resources.ModelResource):
    
    class Meta:
        model = CategoriaDespesa
        # Campos que podem ser importados/exportados
        fields = ('nome')
        # Campos que o sistema deve usar para identificar se o registro já existe
        import_id_fields = [''] 


@admin.register(CategoriaDespesa)
class CategoriaDespesaAdmin(ImportExportModelAdmin):
    resources_class = CategoriaDespesaResource
    
    list_display = ('nome',)
    search_fields = ('nome',)



@admin.register(TipoCusto)
class TipoCustoAdmin(admin.ModelAdmin):
    
    list_display = ('nome', 'descricao')
    search_fields = ('nome',)


class DespesaResource(resources.ModelResource):
    categoria = fields.Field(
        column_name='categoria',
        attribute='categoria',
        widget=ForeignKeyWidget(CategoriaDespesa, 'nome')
    )
    class Meta:
        model = Despesa
        # Campos que podem ser importados/exportados
        fields = ('data_pagamento', 'descricao', 'valor_total', 'categoria', 'tipo',)
        # Campos que o sistema deve usar para identificar se o registro já existe
        import_id_fields = ['id']  # Usar o ID para evitar duplicações


@admin.register(Despesa)
class DespesaAdmin(ImportExportModelAdmin):
    resources_class = DespesaResource
    list_display = ('data_pagamento', 'descricao', 'valor_total', 'categoria', 'tipo')
    list_filter = ('categoria', 'tipo', 'data_pagamento')
    search_fields = ('descricao',)
    
    # Campos que serão exibidos no formulário (agrupamento opcional)
    fieldsets = (
        (None, {
            'fields': ('data_pagamento', 'descricao', 'valor_total', 'categoria', 'tipo')
        }),
        ('Rastreamento', {
            'fields': ('registro_de_custo',),
            'classes': ('collapse',), # Oculta este campo por padrão
            'description': 'Este campo é preenchido automaticamente para sincronização com o Registro de Custo.'
        }),
    )
    # Permite a edição do RegistroDeCusto, mas o signal faz a maioria do trabalho
    readonly_fields = ('registro_de_custo',)


class VendaResource(resources.ModelResource):
    animal = fields.Field(
        column_name='animal',
        attribute='animal',
        widget=ForeignKeyWidget(Animal, 'identificacao')
    )
    class Meta:
        model = Venda
        
        # Campos que podem ser importados/exportados
        fields = ('animal','peso_venda', 'data_entrada', 'valor_total', 'origem_pagador','observacoes',)
        # Campos que o sistema deve usar para identificar se o registro já existe
        import_id_fields = ['animal']  # Usar o ID para evitar duplicações

@admin.register(Venda)
class VendaAdmin(ImportExportModelAdmin):
    resource_class = VendaResource
    list_display = ('animal', 'data_entrada', 'valor_total', 'origem_pagador')
    search_fields = ('animal__identificacao', 'origem_pagador')
    list_filter = ('data_entrada',)


class CustoAnimalDetalheInline(admin.TabularInline):
    model = CustoAnimalDetalhe
    # fk_name = 'animal'
    fields = ('animal', 'valor_alocado',)
    readonly_fields = ('animal', 'valor_alocado')
    can_delete = False
    max_num = 0 
    verbose_name = "Resultado da Alocação (Automático)"


@admin.register(RegistroDeCusto)
class RegistroDeCustoAdmin(admin.ModelAdmin):
    list_display = ('data_pagamento', 'tipo_custo', 'valor_total', 'animal_link', 'pasto_link')
    list_filter = ('tipo_custo', 'data_pagamento', 'animal', 'pasto')
    search_fields = ('descricao', 'animal__identificacao', 'pasto__nome')
    raw_id_fields = ('animal', 'pasto') # Facilita a busca de FKs

    inlines = [CustoAnimalDetalheInline]

    # Adiciona links para os objetos relacionados no list_display (para melhor UX)
    def animal_link(self, obj):
        if obj.animal:
            return format_html('<a href="{}">{}</a>',
                               reverse("admin:rebanho_animal_change", args=[obj.animal.pk]),
                               obj.animal.identificacao)
        return "-"
    animal_link.short_description = 'Animal'

    def pasto_link(self, obj):
        if obj.pasto:
            return format_html('<a href="{}">{}</a>',
                               reverse("admin:infraestrutura_pasto_change", args=[obj.pasto.pk]),
                               obj.pasto.nome)
        return "-"
    pasto_link.short_description = 'Pasto'

    # Ajuste o fieldset para agrupar as informações
    fieldsets = (
        ('Informações Básicas do Custo', {
            'fields': ('data_custo', 'tipo_custo', 'valor', 'quantidade', 'descricao'),
        }),
        ('Alocação do Custo (Opcional)', {
            'fields': ('animal', 'pasto'),
            'description': 'Associe o custo a um animal ou a um pasto (adubação, manutenção).',
        }),
    )


class ReceitaResource(resources.ModelResource):
    
    class Meta:
        model = ReceitaGeral
        # Campos que podem ser importados/exportados
        fields = ('categoria','data_entrada', 'descricao', 'valor_total', 'origem_pagador',)
        # Campos que o sistema deve usar para identificar se o registro já existe
        import_id_fields = ['id']  # Usar o ID para evitar duplicações



@admin.register(ReceitaGeral)
class ReceitaAdmin(ImportExportModelAdmin):
    resource_class = ReceitaResource
    list_display = ('categoria', 'data_entrada', 'descricao', 'valor_total', 'origem_pagador')
    search_fields = ('descricao', 'origem_pagador')
    list_filter = ('data_entrada',)

