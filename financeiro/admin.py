from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import  TipoCusto, RegistroDeCusto, CategoriaDespesa, CustoAnimalDetalhe,  Venda,  Despesa

@admin.register(CategoriaDespesa)
class CategoriaDespesaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ('data_pagamento', 'descricao', 'valor', 'categoria', 'tipo')
    list_filter = ('categoria', 'tipo', 'data_pagamento')
    search_fields = ('descricao',)
    
    # Campos que serão exibidos no formulário (agrupamento opcional)
    fieldsets = (
        (None, {
            'fields': ('data_pagamento', 'descricao', 'valor', 'categoria', 'tipo')
        }),
        ('Rastreamento', {
            'fields': ('registro_de_custo',),
            'classes': ('collapse',), # Oculta este campo por padrão
            'description': 'Este campo é preenchido automaticamente para sincronização com o Registro de Custo.'
        }),
    )
    # Permite a edição do RegistroDeCusto, mas o signal faz a maioria do trabalho
    readonly_fields = ('registro_de_custo',)



@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('animal', 'data_venda', 'valor_total', 'comprador')
    search_fields = ('animal__identificacao', 'comprador')
    list_filter = ('data_venda',)


class CustoAnimalDetalheInline(admin.TabularInline):
    model = CustoAnimalDetalhe
    # fk_name = 'animal'
    fields = ('animal', 'valor_alocado')
    readonly_fields = ('animal', 'valor_alocado')
    can_delete = False
    max_num = 0 
    verbose_name = "Resultado da Alocação (Automático)"


# --- NOVO REGISTRO FINANCEIRO ---

@admin.register(TipoCusto)
class TipoCustoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao')
    search_fields = ('nome',)

@admin.register(RegistroDeCusto)
class RegistroDeCustoAdmin(admin.ModelAdmin):
    list_display = ('data_custo', 'tipo_custo', 'valor', 'animal_link', 'pasto_link')
    list_filter = ('tipo_custo', 'data_custo', 'animal', 'pasto')
    search_fields = ('descricao', 'animal__identificacao', 'pasto__nome')
    raw_id_fields = ('animal', 'pasto') # Facilita a busca de FKs

    inlines = [CustoAnimalDetalheInline]

    # Adiciona links para os objetos relacionados no list_display (para melhor UX)
    def animal_link(self, obj):
        if obj.animal:
            return format_html('<a href="{}">{}</a>',
                               reverse("admin:ControleRebanho_animal_change", args=[obj.animal.pk]),
                               obj.animal.identificacao)
        return "-"
    animal_link.short_description = 'Animal'

    def pasto_link(self, obj):
        if obj.pasto:
            return format_html('<a href="{}">{}</a>',
                               reverse("admin:ControleRebanho_pasto_change", args=[obj.pasto.pk]),
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

# -----------------------------------------------------
# Classe Resource para mapear campos
# -----------------------------------------------------



