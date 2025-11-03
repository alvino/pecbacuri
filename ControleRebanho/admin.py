from django.contrib import admin, messages
from django import forms
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin # 1. Importar o mixin
from import_export import resources
from django.utils import timezone
from .models import Animal, Pasto, TratamentoSaude, Reproducao, Pesagem, Lote, MovimentacaoPasto, TipoCusto, RegistroDeCusto, CategoriaDespesa, CustoAnimalDetalhe, TarefaManejo, Venda, Abate, BaixaAnimal, Despesa


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


# -----------------------------------------------------
# Classe Admim do django
# -----------------------------------------------------

# Formulário temporário para a Action
class MovimentacaoLoteForm(forms.Form):
    pasto_destino = forms.ModelChoiceField(
        queryset=Pasto.objects.all(),
        required=True,
        label="Pasto de Destino"
    )
    data_movimentacao = forms.DateField(
        initial=timezone.localdate(),
        widget=admin.widgets.AdminDateWidget,
        label="Data da Movimentação"
    )
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Observações da Movimentação"
    )


 # ----------------------------------------------------
# A C T I O N S
# ----------------------------------------------------

@admin.action(description='Mover animais para novo Pasto')
def movimentar_em_lote(modeladmin, request, queryset):
    # Passo 1: Verifica se é um POST do formulário
    if 'apply' in request.POST:
        form = MovimentacaoLoteForm(request.POST)
        if form.is_valid():
            pasto_destino = form.cleaned_data['pasto_destino']
            data_movimentacao = form.cleaned_data['data_movimentacao']
            observacoes = form.cleaned_data['observacoes']
            try:
                with transaction.atomic():
                    movimentados_count = 0

                    for animal in queryset:
                        pasto_origem = animal.pasto_atual
                        
                        MovimentacaoPasto.objects.create(
                            animal=animal,
                            pasto_origem=pasto_origem,
                            pasto_destino=pasto_destino,
                            data_entrada=data_movimentacao,
                            motivo=observacoes
                        )

                        animal.pasto_atual = pasto_destino
                        animal.save(update_fields=['pasto_atual'])

                        movimentados_count += 1
                modeladmin.message_user(
                        request,
                        f"{movimentados_count} animal(is) movimentado(s) com sucesso para o pasto/lote '{pasto_destino.nome}'.",
                        messages.SUCCESS
                    )
            except Exception as e:
                # Mensagem de erro
                modeladmin.message_user(
                    request,
                    f"Erro ao movimentar os animais: {e}",
                    messages.ERROR
                )
            return redirect('admin:%s_%s_changelist' % (modeladmin.model._meta.app_label, modeladmin.model._meta.model_name))
    
    else:
        # Se for o GET, inicializa o formulário vazio
        form = MovimentacaoLoteForm()

    # --- Contexto para Renderização do Template ---
    context = {
        'opts': modeladmin.model._meta, 
        'queryset': queryset,
        'action_form': form,
        'title': "Movimentar Lote",
        'media': modeladmin.media,
        'action_name': 'movimentar_em_lote', 
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }

    # Renderiza o template
    return render(
        request, 
        'admin/movimentar_lote_action.html', 
        context=context
    )
    

@admin.register(Animal)
class AnimalAdmin(ImportExportModelAdmin):

    resource_class = AnimalResource

    actions = [movimentar_em_lote]

    list_display = ('identificacao', 'data_nascimento', 'idade_meses', 'sexo', 'situacao', 'lote_atual')
    list_filter = ('situacao', 'sexo', 'lote_atual')
    search_fields = ('identificacao', 'nome', 'idade_meses',)

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


@admin.action(description='Mudar Pasto dos Lotes Selecionados')
def mudar_pasto_lote(modeladmin, request, queryset_lotes): # O queryset agora é de Lotes
    
    if 'apply' in request.POST:
        form = MudarPastoLoteForm(request.POST)
        
        if form.is_valid():
            pasto_destino = form.cleaned_data['pasto_destino']
            data_entrada = form.cleaned_data['data_entrada'] 
            observacoes = form.cleaned_data['observacoes']
            
            # --- Lógica de Movimentação Transacional ---
            try:
                with transaction.atomic():
                    total_animais_movimentados = 0
                    
                    # 1. Itera sobre os Lotes selecionados
                    for lote in queryset_lotes:

                        # --- A. ATUALIZAÇÃO DO PRÓPRIO LOTE ---
                        # Assumimos que o campo no Lote é 'pasto_atual'
                        lote.pasto_atual = pasto_destino
                        lote.save(update_fields=['pasto_atual'])

                        # 2. Encontra TODOS os animais NESTES lotes (usando lote_atual)
                        animais_do_lote = Animal.objects.filter(lote_atual=lote)
                        
                        # Se não houver animais, pule para o próximo lote
                        if not animais_do_lote.exists():
                            continue

                        # 3. Executa a movimentação para cada animal
                        for animal in animais_do_lote:
                            pasto_origem = animal.pasto_atual

                            # Cria o registro de MovimentacaoPasto
                            MovimentacaoPasto.objects.create(
                                animal=animal,
                                pasto_origem=pasto_origem,      
                                pasto_destino=pasto_destino,  
                                data_entrada=data_entrada,   
                                motivo=observacoes
                            )
                            
                            # Atualiza o campo pasto_atual do Animal
                            animal.pasto_atual = pasto_destino
                            animal.save(update_fields=['pasto_atual'])
                            
                            total_animais_movimentados += 1
                
                # Mensagem de sucesso
                messages.success(
                    request,
                    f"{total_animais_movimentados} animal(is) de {queryset_lotes.count()} lote(s) movimentado(s) para o pasto '{pasto_destino.nome}'.",
                )
                
            except Exception as e:
                messages.error(
                    request,
                    f"Erro ao movimentar os lotes: {e}",
                )

            # Redireciona de volta para a changelist de Lotes
            return redirect('admin:%s_%s_changelist' % (modeladmin.model._meta.app_label, modeladmin.model._meta.model_name))
            
    # Lida com GET (renderização inicial)
    else:
        form = MudarPastoLoteForm()

    context = {
        'opts': modeladmin.model._meta,
        'queryset_lotes': queryset_lotes, # Passa o queryset de Lotes
        'action_form': form,
        'title': f"Mudar Pasto de {queryset_lotes.count()} Lote(s)",
        'media': modeladmin.media,
        'action_name': 'mudar_pasto_lote',
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }

    # Você precisará criar este template, baseado no anterior!
    return render(
        request, 
        'admin/mudar_pasto_lote_action.html', 
        context=context
    )


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


