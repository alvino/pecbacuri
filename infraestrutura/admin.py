from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin # 1. Importar o mixin
from import_export import resources
from .models import  Pasto,  MovimentacaoPasto
from rebanho.models import Animal


class PastoResource(resources.ModelResource):
    class Meta:
        model = Pasto
        fields = ('nome', 'area_hectares', 'tipo_capim', 'data_ultimo_manejo', 'observacoes')
        import_id_fields = ['nome']
 

@admin.register(Pasto)
class PastoAdmin(ImportExportModelAdmin):
    resource_class = PastoResource 
    list_display = ('nome','area_hectares', 'tipo_capim','data_ultimo_manejo')
    list_filter = ('tipo_capim',)
    search_fields = ('nome', 'tipo_capim', 'area_hectares')


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


