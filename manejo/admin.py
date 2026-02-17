from django.contrib import admin
from .models import TratamentoSaude, Reproducao, Pesagem,  TarefaManejo


@admin.register(TarefaManejo)
class TarefaManejoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data_prevista', 'tipo', 'animal', 'pasto', 'concluida')
    list_filter = ('tipo', 'concluida', 'data_prevista')
    search_fields = ('titulo', 'descricao', 'animal__identificacao', 'pasto__nome')
    date_hierarchy = 'data_prevista'
    raw_id_fields = ('animal', 'pasto')


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
    list_display = ('matriz', 'data_cio','escore', 'tipo', 'data_dg', 'resultado')
    list_filter = ('tipo','escore', 'resultado', 'data_dg')
    search_fields = ('matriz__identificacao', 'codigo_semen')


