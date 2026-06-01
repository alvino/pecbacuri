from django.contrib import admin
from import_export.admin import ImportExportModelAdmin # 1. Importar o mixin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Animal,  Lote, BaixaAnimal
from .actions import mover_pasto_animais, mudar_lote_animais, mudar_pasto_lote


class AnimalResource(resources.ModelResource):
    class Meta:
        model = Animal
        # Campos que podem ser importados/exportados
        fields = ('identificacao', 'nome', 'data_nascimento', 'sexo', 'situacao', 'mae', 'pai', 'observacoes')
        # Campos que o sistema deve usar para identificar se o registro já existe
        import_id_fields = ['identificacao'] 
 
class LoteResource(resources.ModelResource):
    class Meta:
        model = Lote
        fields = ('nome','pasto_atual','data_entrada','finalidade')
        import_id_fields = ['nome']


class BaixaAnimalResource(resources.ModelResource):
    # Aqui está o segredo:
    # Dizemos que o campo 'animal' na planilha deve ser buscado 
    # no modelo Animal usando o campo 'identificacao' (ou o nome do campo de brinco que você usa)
    animal = fields.Field(
        column_name='animal',
        attribute='animal',
        widget=ForeignKeyWidget(Animal, 'identificacao') # <-- Troque 'identificacao' pelo nome exato do seu campo de brinco
    )

    class Meta:
        model = BaixaAnimal
        import_id_fields = ('id',) 
        fields = ('id', 'animal', 'data_baixa', 'causa', 'observacoes')


@admin.register(BaixaAnimal)
class BaixaAnimalAdmin(ImportExportModelAdmin):
    resource_class = BaixaAnimalResource

    list_display = ('animal', 'data_baixa', 'causa')
    search_fields = ('animal__identificacao', 'observacoes')
    list_filter = ('causa', 'data_baixa')


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

