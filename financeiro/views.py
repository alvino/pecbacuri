# ControleRebanho/views.py

from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import  CreateView, FormView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Avg, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal

from .filters import DespesaFilter, RegistroCustoFilter

from .forms import CategoriaDespesaForm, DespesaForm, VendaForm
from infraestrutura.models import Pasto
from rebanho.models import Animal, BaixaAnimal
from .models import  CategoriaDespesa, Despesa, RegistroDeCusto, CustoAnimalDetalhe,  Venda


class RegistroCustoListView(LoginRequiredMixin, ListView):
    model = RegistroDeCusto
    template_name = 'financeiro/custo_list.html'
    context_object_name = 'custos'
    paginate_by = 20

    def get_queryset(self):
        # Pega os dados e aplica o filtro
        queryset = RegistroDeCusto.objects.all().order_by('-data_custo')
        self.filter = RegistroCustoFilter(self.request.GET, queryset=queryset)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter
        
        # Soma total dos valores filtrados para o rodapé
        total = self.filter.qs.aggregate(Sum('valor'))['valor__sum']
        context['total_geral'] = total or 0
        return context


class DespesaListView(LoginRequiredMixin, ListView):
    model = Despesa
    template_name = 'financeiro/despesa_list.html' # Nome do seu arquivo HTML
    context_object_name = 'despesas'
    paginate_by = 20

    def get_queryset(self):
        # 1. Pega todas as despesas
        queryset = Despesa.objects.all().order_by('-data_pagamento')
        
        # 2. Aplica os filtros (Data, Categoria, etc) vindos da URL (?categoria=...)
        self.filter = DespesaFilter(self.request.GET, queryset=queryset)
        
        # 3. Retorna o queryset filtrado para a ListView usar
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adiciona o formulário de filtro ao contexto para aparecer no HTML
        context['filter'] = self.filter
        
        # CÁLCULO DO TOTAL: Soma o campo 'valor' apenas dos itens que aparecem após o filtro
        total = self.filter.qs.aggregate(Sum('valor'))['valor__sum']
        context['total_valor'] = total or 0
        
        return context

class VendaCreateView(LoginRequiredMixin,FormView):
    template_name = 'financeiro/venda_form.html'
    form_class = VendaForm
    success_url = reverse_lazy('dashboard_financeiro')

    def get_initial(self):
        initial = super().get_initial()
        
        return initial
    
    def form_valid(self, form):
        """Executa a movimentação no banco de dados"""
        data_venda = form.cleaned_data['data_venda']
        peso_venda = form.cleaned_data['peso_venda']
        valor_total = form.cleaned_data['valor_total']
        comprador = form.cleaned_data['comprador']
        observacoes = form.cleaned_data['observacoes']
        animais = form.cleaned_data['animais']
        
        quantidade = 0
        for animal in animais:
            Venda.objects.create(
                animal=animal,
                data_venda=data_venda,
                peso_venda=peso_venda,
                valor_total=valor_total,
                comprador=comprador,
                observacoes=observacoes
            )
            animal.situacao = 'VENDIDO'
            animal.save(update_fields=['situacao'])
            quantidade += 1 
        
        messages.success(
            self.request, 
            f"Sucesso! {quantidade} animal(is) vendido(s)."
        )
        return super().form_valid(form)
    

class CategoriaDespesaCreateView(LoginRequiredMixin, CreateView):
    model = CategoriaDespesa
    form_class = CategoriaDespesaForm
    template_name = 'financeiro/categoria_despesa_form.html'
    success_url = reverse_lazy('despesa_create')  # Redireciona para a criação de despesa após criar categoria


class DespesaCreateView(LoginRequiredMixin, CreateView):
    model = Despesa
    form_class = DespesaForm
    template_name = 'financeiro/despesa_form.html'
    success_url = reverse_lazy('dashboard_financeiro')


class DashboardFinanceiroCBV(TemplateView):
    template_name = 'financeiro/dashboard_financeiro.html'

    def get_context_data(self, **kwargs):
        # Chama a implementação da classe base para obter o contexto
        context = super().get_context_data(**kwargs)
        
        # --- LÓGICA REUTILIZADA DA FBV ---
        
        # 1. CONFIGURAÇÃO DE FILTRO DE TEMPO
        hoje = timezone.localdate()
        ano_filtro = self.request.GET.get('ano', str(hoje.year))
        
        # 2. CALCULAR MÉTRICAS GERAIS
        
        custos_totais = RegistroDeCusto.objects.filter(
            data_custo__year=ano_filtro
        ).aggregate(
            total=Coalesce(Sum('valor'), Decimal(0))
        )['total']

        receita_vendas = Venda.objects.filter(
            data_venda__year=ano_filtro
        ).aggregate(
            total=Coalesce(Sum('valor_total'), Decimal(0))
        )['total']
        
        

        receitas_totais = receita_vendas 
        lucro_geral = receitas_totais - custos_totais
        
        # 3. LUCRO POR ANIMAL (Detalhamento)
        
        # ... (Mantendo a lógica complexa de animais_saidos_ids e o loop de detalhe_lucratividade) ...
        
        # Identifica animais que saíram (vendidos, abatidos ou mortos) no ano
        animais_saidos_ids = set()
        
        vendas_periodo = Venda.objects.filter(data_venda__year=ano_filtro)
        for v in vendas_periodo:
            animais_saidos_ids.add(v.animal_id)

        baixas_periodo = BaixaAnimal.objects.filter(data_baixa__year=ano_filtro)
        for b in baixas_periodo:
            animais_saidos_ids.add(b.animal_id)
            
        animais_saidos = Animal.objects.filter(id__in=animais_saidos_ids)
        
        detalhe_lucratividade = []

        for animal in animais_saidos:
            
            custo_acumulado = CustoAnimalDetalhe.objects.filter(
                animal=animal
            ).aggregate(
                total=Coalesce(Sum('valor_alocado'), Decimal(0))
            )['total']
            
            receita_animal = Decimal(0)
            destino = "N/A"
            data_saida = None
            
            # Lógica de Destino (VENDIDO, ABATIDO, MORTO) ...
            if animal.situacao == 'VENDIDO':
                try:
                    venda = Venda.objects.get(animal=animal)
                    receita_animal = venda.valor_total
                    destino = f"Vendido a {venda.comprador}"
                    data_saida = venda.data_venda
                except Venda.DoesNotExist:
                     destino = "VENDIDO (Registro de Venda Ausente)"
                

            elif animal.situacao == 'MORTO': 
                try:
                    baixa = BaixaAnimal.objects.get(animal=animal)
                    receita_animal = Decimal(0) 
                    destino = f"Morte ({baixa.get_causa_display()})"
                    data_saida = baixa.data_baixa
                except BaixaAnimal.DoesNotExist:
                     destino = "MORTO (Registro de Baixa Ausente)"

            lucro = receita_animal - custo_acumulado
            
            detalhe_lucratividade.append({
                'identificacao': animal.identificacao,
                'link': animal.get_absolute_url(),
                'data_saida': data_saida,
                'destino': destino,
                'custo_acumulado': custo_acumulado,
                'receita_animal': receita_animal,
                'lucro': lucro,
            })
        
        # 4. Adicionar ao Contexto
        context.update({
            'ano_filtro': ano_filtro,
            'anos_disponiveis': range(hoje.year, hoje.year - 5, -1),
            'custos_totais': custos_totais,
            'receitas_totais': receitas_totais,
            'lucro_geral': lucro_geral,
            'detalhe_lucratividade': detalhe_lucratividade,
        })
        
        return context


class RelatorioDesempenhoPastoView(LoginRequiredMixin, TemplateView):
    template_name = 'financeiro/relatorio_desempenho_pasto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Filtros e Parâmetros Padrão
        hoje = timezone.localdate()
        trinta_dias_atras = hoje - timedelta(days=30)
        
        pasto_id = self.request.GET.get('pasto')
        data_inicio = self.request.GET.get('data_inicio', trinta_dias_atras.strftime('%Y-%m-%d'))
        data_fim = self.request.GET.get('data_fim', hoje.strftime('%Y-%m-%d'))
        
        # Dados iniciais
        pastos = Pasto.objects.all().order_by('nome')
        animais_desempenho = []
        pasto_selecionado = None
        relatorio_resumo = {}

        if pasto_id:
            try:
                pasto_selecionado = Pasto.objects.get(pk=pasto_id)
                
                # 2. Identificar animais (Melhorado com Prefetch para evitar N+1)
                animais_no_pasto = Animal.objects.filter(
                    movimentacoes_pasto__pasto_destino=pasto_selecionado,
                    movimentacoes_pasto__data_entrada__lte=data_fim
                ).filter(
                    Q(movimentacoes_pasto__data_saida__gte=data_inicio) | 
                    Q(movimentacoes_pasto__data_saida__isnull=True)
                ).distinct()
                
                total_gpmd = 0
                total_custo = 0
                total_animais_com_dados = 0
                
                for animal in animais_no_pasto:
                    # GPMD Médio
                    gpmd_medio = animal.pesagens.filter(
                        data_pesagem__range=[data_inicio, data_fim],
                        gpmd__isnull=False
                    ).aggregate(Avg('gpmd'))['gpmd__avg']
                    
                    # Último Peso
                    ultima_pesagem = animal.pesagens.filter(
                        data_pesagem__lte=data_fim
                    ).order_by('-data_pesagem').first()
                    
                    # Custo Alocado
                    custo_periodo = CustoAnimalDetalhe.objects.filter(
                        animal=animal,
                        registro_de_custo__data_custo__range=[data_inicio, data_fim]
                    ).aggregate(total=Sum('valor_alocado'))['total'] or 0.0
                    
                    if gpmd_medio is not None:
                        total_gpmd += gpmd_medio
                        total_custo += custo_periodo
                        total_animais_com_dados += 1
                        
                        animais_desempenho.append({
                            'identificacao': animal.identificacao,
                            'link': animal.get_absolute_url(),
                            'gpmd_medio': gpmd_medio,
                            'peso_atual': ultima_pesagem.peso if ultima_pesagem else None,
                            'custo_periodo': custo_periodo,
                        })

                # 4. Resumo
                if total_animais_com_dados > 0:
                    relatorio_resumo = {
                        'pasto_nome': pasto_selecionado.nome,
                        'total_animais': total_animais_com_dados,
                        'media_gpmd_lote': total_gpmd / total_animais_com_dados,
                        'custo_total_lote': total_custo,
                        'custo_medio_animal': total_custo / total_animais_com_dados,
                    }
                    
            except Pasto.DoesNotExist:
                pass
        
        # Atualiza o contexto
        context.update({
            'pastos': pastos,
            'pasto_selecionado': pasto_selecionado,
            'data_inicio_filtro': data_inicio,
            'data_fim_filtro': data_fim,
            'animais_desempenho': animais_desempenho,
            'relatorio_resumo': relatorio_resumo,
        })
        return context