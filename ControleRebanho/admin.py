from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin # 1. Importar o mixin
from import_export import resources
from .models import Animal, Pasto, TratamentoSaude, Reproducao, Pesagem, Lote, MovimentacaoPasto, TipoCusto, RegistroDeCusto, CategoriaDespesa, CustoAnimalDetalhe, TarefaManejo, Venda, Abate, BaixaAnimal, Despesa
from .actions import mover_pasto_animais, mudar_pasto_lote, mudar_lote_animais

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


@admin.register(BaixaAnimal)
class BaixaAnimalAdmin(admin.ModelAdmin):
    list_display = ('animal', 'data_baixa', 'causa')
    search_fields = ('animal__identificacao', 'observacoes')
    list_filter = ('causa', 'data_baixa')


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('animal', 'data_venda', 'valor_total', 'comprador')
    search_fields = ('animal__identificacao', 'comprador')
    list_filter = ('data_venda',)

@admin.register(Abate)
class AbateAdmin(admin.ModelAdmin):
    list_display = ('animal', 'data_abate', 'peso_carcaca_quente', 'rendimento_carcaca')
    search_fields = ('animal__identificacao', 'destino_carcaca')
    list_filter = ('data_abate',)


@admin.register(TarefaManejo)
class TarefaManejoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data_prevista', 'tipo', 'animal', 'pasto', 'concluida')
    list_filter = ('tipo', 'concluida', 'data_prevista')
    search_fields = ('titulo', 'descricao', 'animal__identificacao', 'pasto__nome')
    date_hierarchy = 'data_prevista'
    raw_id_fields = ('animal', 'pasto')


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


class AnimalResource(resources.ModelResource):
    class Meta:
        model = Animal
        # Campos que podem ser importados/exportados
        fields = ('identificacao', 'nome', 'data_nascimento', 'sexo', 'situacao', 'mae', 'pai', 'observacoes')
        # Campos que o sistema deve usar para identificar se o registro já existe
        import_id_fields = ['identificacao'] 
        

class PastoResource(resources.ModelResource):
    class Meta:
        model = Pasto
        fields = ('nome', 'area_hectares', 'tipo_capim', 'data_ultimo_manejo', 'observacoes')
        import_id_fields = ['nome']

class LoteResource(resources.ModelResource):
    class Meta:
        model = Lote
        fields = ('nome','pasto_atual','data_entrada','finalidade')
        import_id_fields = ['nome']
    

@admin.register(Animal)
class AnimalAdmin(ImportExportModelAdmin):

    resource_class = AnimalResource

    actions = [mover_pasto_animais,mudar_lote_animais]

    list_display = ('identificacao', 'data_nascimento', 'idade_ano_mes', 'sexo', 'situacao', 'lote_atual')
    list_filter = ('situacao', 'sexo', 'lote_atual')
    search_fields = ('identificacao', 'nome', 'idade_ano_mes',)

    # NOVO: Define a ordem e quais campos aparecem no formulário de ADD/EDIT
    fieldsets = (
        ('Identificação', {
            'fields': ('identificacao', 'nome', 'data_nascimento', 'sexo', 'situacao'),
        }),
        ('Genealogia', {
            'fields': ('mae', 'pai'),
        }),
        ('Informação de manejo', {
            'fields': ('lote_atual','pasto_atual')
        }),
        ('Observações', {
            'fields': ('observacoes',),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "pai":
            kwargs["queryset"] = Animal.objects.filter(
                sexo='M', 
                situacao='VIVO' 
            )
        elif db_field.name == "mae":
            kwargs["queryset"] = Animal.objects.filter(
                sexo='F', 
                situacao='VIVO' 
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    


@admin.register(Pasto)
class PastoAdmin(ImportExportModelAdmin):
    resource_class = PastoResource 
    list_display = ('nome','area_hectares', 'tipo_capim','data_ultimo_manejo')
    list_filter = ('tipo_capim',)
    search_fields = ('nome', 'tipo_capim', 'area_hectares')

@admin.register(TratamentoSaude)
class TratamentoSaudeAdmin(admin.ModelAdmin):
    list_display = ('animal', 'data_tratamento', 'tipo_tratamento', 'produto', 'data_proximo_tratamento')
    list_filter = ('tipo_tratamento',)
    search_fields = ('animal__identificacao', 'produto')

@admin.register(Pesagem)
class PesagemAdmin(admin.ModelAdmin):
    list_display = ('animal', 'data_pesagem', 'peso_kg', 'evento')
    list_filter = ('evento',)
    search_fields = ('animal__identificacao',)
    
@admin.register(Reproducao)
class ReproducaoAdmin(admin.ModelAdmin):
    list_display = ('matriz', 'data_cio', 'tipo', 'data_dg', 'resultado')
    list_filter = ('tipo', 'resultado', 'data_dg')
    search_fields = ('matriz__identificacao', 'codigo_semen')


@admin.register(Lote)
class LoteAdmin(ImportExportModelAdmin):
    resource_class = LoteResource 
    list_display = ('nome', 'finalidade', 'pasto_atual', 'data_entrada', 'contagem_animais')
    list_filter = ('finalidade', 'pasto_atual')
    search_fields = ('nome',)

    actions = [mudar_pasto_lote]

    # Calcula a contagem de animais no lote (campo dinâmico para a lista)
    def contagem_animais(self, obj):
        return obj.animais_no_lote.count()
    contagem_animais.short_description = 'Animais'


@admin.register(MovimentacaoPasto)
class MovimentacaoPastoAdmin(admin.ModelAdmin):
    list_display = ('animal', 'pasto_origem_atual', 'pasto_destino', 'data_entrada', 'data_saida', 'motivo')
    list_filter = ('pasto_destino', 'data_entrada')
    raw_id_fields = ('animal',)
    search_fields = ('animal__identificacao', 'pasto_destino__nome')

    # Ação de Admin para finalizar a movimentação anterior automaticamente
    def save_model(self, request, obj, form, change):
        # 1. Se o campo data_saida for None (é uma nova movimentação em aberto)
        if obj.data_saida is None and obj.pk is None:
            # 2. Tenta encontrar a movimentação anterior desse animal que está em aberto
            movimentacao_anterior = MovimentacaoPasto.objects.filter(
                animal=obj.animal,
                data_saida__isnull=True
            ).exclude(pk=obj.pk).first()

            # 3. Se encontrar, feche-a automaticamente
            if movimentacao_anterior:
                movimentacao_anterior.data_saida = obj.data_entrada
                movimentacao_anterior.save() # Salva o registro anterior (Dispara signal do MovimentacaoPasto)
                
        super().save_model(request, obj, form, change) # Salva a nova movimentação (Dispara signal)

    # Campo customizado para mostrar o pasto de origem
    def pasto_origem_atual(self, obj):
        # Se for um novo registro ou já tiver pasto de origem, exibe o campo
        if obj.pasto_origem:
            return obj.pasto_origem
        
        # Se for um novo registro sem pasto de origem, tenta buscar o pasto atual do animal
        try:
            return Animal.objects.get(pk=obj.animal_id).pasto_atual or 'N/A'
        except Animal.DoesNotExist:
            return 'N/A'
            
    pasto_origem_atual.short_description = 'Pasto de Origem (Auto)'


