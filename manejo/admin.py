from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from rebanho.models import Animal
from .models import TratamentoSaude, Reproducao, Pesagem,  TarefaManejo


class ReproducaoResource(resources.ModelResource):
    # Substitui o ID da matriz pela identificação (brinco)
    matriz = fields.Field(
        column_name='matriz_id', # Nome da coluna no seu CSV
        attribute='matriz',      # Nome do campo no seu Model Reproducao
        widget=ForeignKeyWidget(Animal, 'identificacao') # Busca pelo brinco no novo banco
    )
    
    # Substitui o ID do touro pela identificação (brinco)
    touro = fields.Field(
        column_name='touro_id', 
        attribute='touro', 
        widget=ForeignKeyWidget(Animal, 'identificacao')
    )

    class Meta:
        model = Reproducao
        # Importante: não importe o 'id' do CSV de reprodução para evitar conflitos
        fields = ('data_cio', 'tipo', 'codigo_semen', 'data_dg', 'resultado', 
                  'data_parto_prevista', 'matriz', 'touro', 'escore')
        import_id_fields = [] # Deixa o Django criar novos IDs
        # ESTA LINHA ABAIXO PODE AJUDAR A IDENTIFICAR O ERRO:
        skip_unchanged = True
        report_skipped = True

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
class ReproducaoAdmin(ImportExportModelAdmin):
    resource_class = ReproducaoResource   

    list_display = ('matriz', 'data_cio', 'tipo', 'resultado', 'data_parto_prevista')
    list_filter = ('tipo', 'resultado')
    search_fields = ('matriz__identificacao', 'touro__identificacao', 'codigo_semen')


