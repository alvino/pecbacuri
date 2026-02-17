# ControleRebanho/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages, auth
from django.views.generic import ListView, DetailView, TemplateView, CreateView, UpdateView, FormView
from django.contrib.auth.decorators import login_required # Importe o decorador
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, F, Q, Count, Sum, Count, Case, When, IntegerField, ExpressionWrapper, FloatField
from django.db.models.functions import Coalesce
from datetime import date, timedelta
from django.utils import timezone
from decimal import Decimal

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import AnimalSerializer 
from .filters import AnimalFilter
from .models import Animal,  Lote,  BaixaAnimal
from .forms import AnimalForm

# -----------------------------------------------
# API - Módulo Básico de Rebanho
# -----------------------------------------------

class AnimalViewSet(viewsets.ModelViewSet):
    # Define o QuerySet base: todos os animais vivos
    queryset = Animal.objects.filter(situacao='VIVO').select_related('pasto_atual') 
    
    # Define o Serializer que será usado
    serializer_class = AnimalSerializer
    
    # Restrição de permissão: apenas usuários logados podem acessar a API
    # permission_classes = [IsAuthenticated] # Descomente em produção!

    # Exemplo de Endpoint customizado (Mapeamento de Rebanho)
    @action(detail=False, methods=['get'])
    def resumo_rebanho(self, request):
        """ Endpoint customizado para o frontend, retorna o resumo do inventário. """
        total_animais = self.queryset.count()
        
        # Agregação por pasto
        resumo_por_pasto = self.queryset.values('pasto_atual__nome').annotate(
            count=Count('pasto_atual__nome')
        ).order_by('pasto_atual__nome')
        
        return Response({
            'total_animais': total_animais,
            'por_pasto': resumo_por_pasto
        })


# --------------------------------
# CreateViews do projeto de Pecuária
# --------------------------------

class AnimalCreateView(LoginRequiredMixin, CreateView):
    model = Animal
    form_class = AnimalForm
    template_name = 'rebanho/animal_form.html'
    success_url = reverse_lazy('animal_list') # Redireciona para a lista após salvar



# --------------------------------
# Updated Views do projeto de Pecuária
# --------------------------------


class AnimalUpdateView(LoginRequiredMixin, UpdateView):
    model = Animal
    form_class = AnimalForm
    template_name = 'rebanho/animal_form.html'
    success_url = reverse_lazy('animal_list')



# --------------------------------
# ListViews do projeto de Pecuária
# --------------------------------

class AnimalListView(ListView):
    model = Animal
    template_name = 'rebanho/animal_list.html'
    context_object_name = 'animais'
    # Filtra apenas os animais ativos por padrão
    queryset = Animal.objects.filter(situacao='VIVO')
    paginate_by = 50 # Opção para paginar os resultados
    
    def get_queryset(self):
        # 1. Obtém o queryset base (todos os animais)
        queryset = super().get_queryset()
        
        # 2. Cria o objeto Filter com os dados GET (query string) e o queryset
        self.filter = AnimalFilter(self.request.GET, queryset=queryset)
        
        # 3. Retorna o queryset filtrado
        return self.filter.qs
    
    # Adicionando contexto extra (se precisar de contagens ou filtros)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Exemplo de contexto extra para o template:
        context['total_ativo'] = Animal.objects.filter(situacao='VIVO').count()
        context['filter'] = self.filter
        return context
      

class AnimalDetailView( DetailView):
    model = Animal
    template_name = 'rebanho/animal_detail.html'
    context_object_name = 'animal'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = self.object
        
        # --- 1. Lógica de Idade ---
        if animal.data_nascimento:
            hoje = date.today()
            idade_dias = (hoje - animal.data_nascimento).days
            context['idade_anos'] = idade_dias // 365
            context['idade_meses'] = (idade_dias % 365) // 30

        # --- 2. Histórico de Pesagem (GPMD) ---
        pesagens = animal.historico_pesagens.all().order_by('-data_pesagem')
        context['pesagens'] = pesagens
        
        # Última Pesagem
        if pesagens.exists():
            context['ultima_pesagem'] = pesagens.first()
            
            # Usa o método que você já criou para calcular os dados de GPMD
            dados_gpmd = self.calcular_gpmd(pesagens)
            context['gpmd_medio'] = animal.calcular_gpmd_animal()
            context['gpmd_recente'] = dados_gpmd['gpmd'] # GPMD em gramas entre as duas últimas pesagens
            context['detalhe_gpmd'] = dados_gpmd # Contém dias, peso anterior, etc.
        else:
            context['ultima_pesagem'] = None
            context['gpmd_recente'] = 0

        # --- 3. Histórico de Movimentação de Pasto ---
        context['movimentacoes_pasto'] = animal.movimentacoes_pasto.all().order_by('-data_entrada')

        # --- 4. Histórico Financeiro (Custo Acumulado) ---
        # Soma todos os detalhes de custo alocados a este animal
        custo_acumulado = animal.custos_alocados.aggregate(total=Sum('valor_alocado'))['total']
        context['custo_acumulado'] = custo_acumulado or 0.00
        
        # Detalhe dos custos (para a tabela)
        context['custos_detalhados'] = animal.custos_alocados.all().order_by('-registro_de_custo__data_custo')


        # --- 5. Histórico de Reprodução (Se existir o modelo) ---
        try:
            context['reproducoes'] = animal.reproducoes_matriz.all().order_by('-data_cio')
        except:
             context['reproducoes'] = []

        # --- 6. Histórico de Saúde (Se existir o modelo) ---
        try:
             context['tratamentos'] = animal.tratamentos.all().order_by('-data_tratamento')
        except:
             context['tratamentos'] = []

        return context

    def calcular_gpmd(self, pesagens):
        # Apenas tenta calcular se houver pelo menos 2 pesagens
        if pesagens.count() >= 2:
            # Pega as duas últimas pesagens
            pesagem_recente = pesagens.last()
            pesagem_anterior = pesagens[pesagens.count() - 2] 

            peso_recente = pesagem_recente.peso_kg
            data_recente = pesagem_recente.data_pesagem
            
            peso_anterior = pesagem_anterior.peso_kg
            data_anterior = pesagem_anterior.data_pesagem
            
            # Cálculo da Diferença
            diferenca_peso = peso_recente - peso_anterior
            diferenca_dias = (data_recente - data_anterior).days

            # Evita divisão por zero
            if diferenca_dias > 0:
                gpmd = diferenca_peso / diferenca_dias
            else:
                gpmd = None # Não é possível calcular
                
            return {
                'gpmd_dias': diferenca_dias,
                'gpmd_peso_anterior': peso_anterior,
                'gpmd_data_anterior': data_anterior,
                'gpmd_peso_recente': peso_recente,
                'gpmd': round(gpmd * 1000) if gpmd else None # GPMD em gramas
            }
        
        return {
            'gpmd_dias': 0, 
            'gpmd': None,
            'gpmd_peso_recente': pesagens.last().peso_kg if pesagens.count() == 1 else None # Mostra 1ª pesagem
        }



class AnalisePorIdadeView(TemplateView):
    template_name = 'rebanho/analise_por_idade.html'
    # Define as categorias de idade em meses
    # Você pode ajustar estas faixas conforme a sua necessidade zootécnica
    IDADE_CATEGORIAS = [
        (12, '0 a 12 Meses (Cria)'),
        (24, '13 a 24 Meses (Recria)'),
        (36, '25 a 36 Meses (Recria Avançada)'),
        (999, 'Acima de 36 Meses (Matrizes/Reprodutores)'),
    ]

    # Limites para a análise detalhada de bezerros (1 a 9 meses)
    BEZERRO_LIMITES = list(range(1, 10)) 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        
        # 1. CÁLCULO DA IDADE CORRIGIDO
        # Calcula a diferença de datas (DurationField)
        duration_expr = today - F('data_nascimento')
        
        # Converte a Duration para dias (dividindo pela duração de um dia) e define o resultado como Float
        idade_em_dias_expr = ExpressionWrapper(
            duration_expr / timedelta(days=1),
            output_field=FloatField() # Garante que o resultado é um número (dias)
        )
        
        # Converte dias para meses (dividindo por 30.4 dias/mês)
        idade_em_meses_expr = ExpressionWrapper(
            idade_em_dias_expr / 30.4,
            output_field=IntegerField() # O resultado final que queremos para categorização
        )

        # Filtra animais vivos com data de nascimento válida
        animais_base = Animal.objects.filter(
            situacao='VIVO',
            data_nascimento__isnull=False,
        ).annotate(
            idade_meses=idade_em_meses_expr # Usa a nova expressão corrigida
        )
        
        # --- 2. Análise Detalhada dos Bezerros (0 a 9 meses) ---
        analise_bezerros = []
        limite_anterior = 0

        for limite_meses in self.BEZERRO_LIMITES:
            
            # Filtra os animais na faixa atual (maior que o limite anterior, menor ou igual ao limite atual)
            animais_na_faixa = animais_base.filter(
                idade_meses__gt=limite_anterior,
                idade_meses__lte=limite_meses
            )
            
            # Conta machos e fêmeas na faixa
            contagem_sexo = animais_na_faixa.aggregate(
                machos=Count(Case(When(sexo='M', then=1), output_field=IntegerField())),
                femeas=Count(Case(When(sexo='F', then=1), output_field=IntegerField())),
                total=Count('id')
            )
            
            # Cria o nome da categoria
            nome_categoria = f'{limite_anterior} a {limite_meses} Meses'
            
            analise_bezerros.append({
                'categoria': nome_categoria,
                'machos': contagem_sexo['machos'],
                'femeas': contagem_sexo['femeas'],
                'total': contagem_sexo['total'],
                'porcentagem': 0 # Será calculado no template
            })
            
            limite_anterior = limite_meses # O novo limite anterior será o limite atual (9 meses)


        # --- 3. Análise Geral (começa após 9 meses) ---
        analise_geral = []
        limite_anterior = 0 # Continua de onde os bezerros pararam

        for limite_meses, nome_categoria in self.IDADE_CATEGORIAS:
            
            animais_na_faixa = animais_base.filter(
                idade_meses__gt=limite_anterior,
                idade_meses__lte=limite_meses
            )
            
            contagem_sexo = animais_na_faixa.aggregate(
                machos=Count(Case(When(sexo='M', then=1), output_field=IntegerField())),
                femeas=Count(Case(When(sexo='F', then=1), output_field=IntegerField())),
                total=Count('id')
            )
            
            analise_geral.append({
                'categoria': nome_categoria,
                'machos': contagem_sexo['machos'],
                'femeas': contagem_sexo['femeas'],
                'total': contagem_sexo['total'],
                'porcentagem': 0
            })
            
            limite_anterior = limite_meses

        context['analise_bezerros'] = analise_bezerros
        context['analise_geral'] = analise_geral
        context['total_geral'] = animais_base.count() # Total de animais na análise
        
        return context


class AnaliseDesempenhoLotesCBV(TemplateView):
    template_name = 'rebanho/analise_lotes.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Obter todos os lotes (usando Pasto como Lote)
        lotes = Lote.objects.all()
        
        dados_lotes = []
        
        for lote in lotes:
            animais_no_lote = Animal.objects.filter(lote_atual=lote, situacao='VIVO')
            
            gpmds_dos_animais = []
            
            # 2. Calcular o GPMD Médio individualmente (em Python)
            for animal in animais_no_lote:
                gpmd_animal = animal.calcular_gpmd_animal()
                if gpmd_animal is not None:
                    gpmds_dos_animais.append(gpmd_animal)
            
            gpmd_medio = None
            if gpmds_dos_animais:
                gpmd_medio = sum(gpmds_dos_animais) / len(gpmds_dos_animais)
            
            # 3. Reunir os dados
            dados_lotes.append({
                'lote': lote,
                'pasto_atual': lote.nome, 
                'total_animais': animais_no_lote.count(),
                'gpmd_medio': round(gpmd_medio, 2) if gpmd_medio is not None else 'N/A'
            })

        # 4. Ordenação
        dados_lotes.sort(key=lambda x: x['gpmd_medio'] if x['gpmd_medio'] != 'N/A' else -1, reverse=True)

        context.update({
            'dados_lotes': dados_lotes,
        })
        
        return context
    


class AnaliseDesempenhoLotesCBV(TemplateView):
    template_name = 'pecuaria/analise_lotes.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Obter todos os lotes (usando Pasto como Lote)
        lotes = Lote.objects.all()
        
        dados_lotes = []
        
        for lote in lotes:
            animais_no_lote = Animal.objects.filter(lote_atual=lote, situacao='VIVO')
            
            gpmds_dos_animais = []
            
            # 2. Calcular o GPMD Médio individualmente (em Python)
            for animal in animais_no_lote:
                gpmd_animal = animal.calcular_gpmd_animal()
                if gpmd_animal is not None:
                    gpmds_dos_animais.append(gpmd_animal)
            
            gpmd_medio = None
            if gpmds_dos_animais:
                gpmd_medio = sum(gpmds_dos_animais) / len(gpmds_dos_animais)
            
            # 3. Reunir os dados
            dados_lotes.append({
                'lote': lote,
                'pasto_atual': lote.nome, 
                'total_animais': animais_no_lote.count(),
                'gpmd_medio': round(gpmd_medio, 2) if gpmd_medio is not None else 'N/A'
            })

        # 4. Ordenação
        dados_lotes.sort(key=lambda x: x['gpmd_medio'] if x['gpmd_medio'] != 'N/A' else -1, reverse=True)

        context.update({
            'dados_lotes': dados_lotes,
        })
        
        return context

