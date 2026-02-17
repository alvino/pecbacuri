from django.shortcuts import render,  get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, DetailView,  CreateView, UpdateView, FormView
from django.contrib.auth.decorators import login_required # Importe o decorador
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg,  Q, Sum
from datetime import timedelta
from django.utils import timezone


from .models import  Pasto
from rebanho.models import Animal
from financeiro.models import CustoAnimalDetalhe

from .forms import PastoForm,  MovimentacaoPastoForm




@login_required
def relatorio_desempenho_pasto(request):

    # 1. Filtros e Parâmetros Padrão
    hoje = timezone.localdate()
    trinta_dias_atras = hoje - timedelta(days=30)
    
    # Pega os filtros da URL
    pasto_id = request.GET.get('pasto')
    data_inicio = request.GET.get('data_inicio', trinta_dias_atras.strftime('%Y-%m-%d'))
    data_fim = request.GET.get('data_fim', hoje.strftime('%Y-%m-%d'))
    
    pastos = Pasto.objects.all().order_by('nome')
    animais_desempenho = []
    
    # --- CORREÇÃO: Inicialize as variáveis que serão usadas no context! ---
    pasto_selecionado = None
    relatorio_resumo = {}
    

    if pasto_id:
        try:
            pasto_selecionado = Pasto.objects.get(pk=pasto_id)
            
            # 2. Identificar animais que estiveram no pasto durante o período
            # Esta lógica é mais precisa para o desempenho do pasto
            animais_no_pasto = Animal.objects.filter(
                movimentacoes_pasto__pasto_destino=pasto_selecionado,
                movimentacoes_pasto__data_entrada__lte=data_fim
            ).filter(
                Q(movimentacoes_pasto__data_saida__gte=data_inicio) | Q(movimentacoes_pasto__data_saida__isnull=True)
            ).distinct()
            
            total_gpmd = 0
            total_custo = 0
            total_animais = 0
            
            for animal in animais_no_pasto:
                # 3. Calcular GPMD, Peso e Custo para CADA ANIMAL no Período
                
                # a) GPMD Médio no período
                # Filtra as pesagens cuja data_pesagem está entre o período
                pesagens_periodo = animal.pesagens.filter(
                    data_pesagem__range=[data_inicio, data_fim],
                    gpmd__isnull=False
                )
                gpmd_medio = pesagens_periodo.aggregate(Avg('gpmd'))['avg']
                
                # b) Último Peso (para peso médio)
                ultima_pesagem = animal.pesagens.filter(data_pesagem__lte=data_fim).order_by('-data_pesagem').first()
                peso_atual = ultima_pesagem.peso if ultima_pesagem else None
                
                # c) Custo Alocado no Período
                custo_periodo = CustoAnimalDetalhe.objects.filter(
                    animal=animal,
                    registro_de_custo__data_custo__range=[data_inicio, data_fim]
                ).aggregate(total=Sum('valor_alocado'))['total'] or 0.00
                
                if gpmd_medio is not None:
                    total_gpmd += gpmd_medio
                    total_custo += custo_periodo
                    total_animais += 1
                    
                    animais_desempenho.append({
                        'identificacao': animal.identificacao,
                        'link': animal.get_absolute_url(),
                        'gpmd_medio': gpmd_medio,
                        'peso_atual': peso_atual,
                        'custo_periodo': custo_periodo,
                    })

            # 4. Resumo do Pasto/Lote
            if total_animais > 0:
                relatorio_resumo = {
                    'pasto_nome': pasto_selecionado.nome,
                    'total_animais': total_animais,
                    'media_gpmd_lote': total_gpmd / total_animais,
                    'custo_total_lote': total_custo,
                    'custo_medio_animal': total_custo / total_animais,
                }
                
        except Pasto.DoesNotExist:
            pasto_selecionado = None
            
    context = {
        'pastos': pastos,
        'pasto_selecionado': pasto_selecionado,
        'data_inicio_filtro': data_inicio,
        'data_fim_filtro': data_fim,
        'animais_desempenho': animais_desempenho,
        'relatorio_resumo': relatorio_resumo,
    }
    
    return render(request, 'infraestrutura/relatorio_desempenho_pasto.html', context)


class MovimentacaoPastoCreateView(LoginRequiredMixin,FormView):
    template_name = 'infraestrutura/movimentacao_pasto.html'
    form_class = MovimentacaoPastoForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal_id = self.request.GET.get('animal_id')
        
        if animal_id:
            # Busca o animal específico para mostrar no template
            context['animal_individual'] = get_object_or_404(Animal, pk=animal_id)
        return context

    def get_initial(self):
        initial = super().get_initial()
        animal_id = self.request.GET.get('animal_id')
        if animal_id:
            initial['animais'] = [animal_id]
        return initial

    def form_valid(self, form):
        """Executa a movimentação no banco de dados"""
        pasto_destino = form.cleaned_data['pasto_destino']
        data_entrada = form.cleaned_data['data_entrada']  
        observacoes = form.cleaned_data['observacoes']    
        animais = form.cleaned_data['animais']
        
        # O método update() é eficiente para 1 ou 100 animais
        quantidade = 0
        for animal in animais:
            # Cria o registro de movimentação
            animal.movimentacoes_pasto.create(
                pasto_destino=pasto_destino,
                data_entrada=data_entrada,
                motivo=observacoes
            )
            # Atualiza o pasto atual do animal
            animal.pasto_atual = pasto_destino
            animal.save()
            quantidade += 1 
        
        messages.success(
            self.request, 
            f"Sucesso! {quantidade} animal(is) movido(s) para {pasto_destino.nome}."
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        animal_id = self.request.GET.get('animal_id')
        if animal_id:
            return reverse('animal_detail', kwargs={'pk': animal_id})
        return reverse('movimentar_animais')


class PastoCreateView(LoginRequiredMixin, CreateView):
    model = Pasto
    form_class = PastoForm
    template_name = 'infraestrutura/pasto_form.html'
    success_url = reverse_lazy('pasto_list') # Redireciona para a lista após salvar


class PastoUpdateView(LoginRequiredMixin, UpdateView):
    model = Pasto
    form_class = PastoForm
    template_name = 'infraestrutura/pasto_form.html'
    success_url = reverse_lazy('pasto_list')


class PastoListView(ListView):
    """Lista todos os pastos cadastrados na fazenda."""
    model = Pasto
    template_name = 'infraestrutura/pasto_list.html'
    context_object_name = 'pastos'
    ordering = ['nome']


class PastoDetailView( DetailView):
    model = Pasto
    template_name = 'infraestrutura/pasto_detail.html'
    context_object_name = 'pasto'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Animais Atualmente no Pasto (usando o related_name 'animais_atuais')
        context['animais_no_pasto'] = context['pasto'].animais_atuais.all().order_by('identificacao')
        
        # 2. Histórico de Movimentações Recentes (opcional, para um histórico)
        context['movimentacoes_recentes'] = context['pasto'].entradas_pasto.all().order_by('-data_entrada')[:10]
        
        return context

@login_required
def relatorio_desempenho_pasto(request):

    # 1. Filtros e Parâmetros Padrão
    hoje = timezone.localdate()
    trinta_dias_atras = hoje - timedelta(days=30)
    
    # Pega os filtros da URL
    pasto_id = request.GET.get('pasto')
    data_inicio = request.GET.get('data_inicio', trinta_dias_atras.strftime('%Y-%m-%d'))
    data_fim = request.GET.get('data_fim', hoje.strftime('%Y-%m-%d'))
    
    pastos = Pasto.objects.all().order_by('nome')
    animais_desempenho = []
    
    # --- CORREÇÃO: Inicialize as variáveis que serão usadas no context! ---
    pasto_selecionado = None
    relatorio_resumo = {}
    

    if pasto_id:
        try:
            pasto_selecionado = Pasto.objects.get(pk=pasto_id)
            
            # 2. Identificar animais que estiveram no pasto durante o período
            # Esta lógica é mais precisa para o desempenho do pasto
            animais_no_pasto = Animal.objects.filter(
                movimentacoes_pasto__pasto_destino=pasto_selecionado,
                movimentacoes_pasto__data_entrada__lte=data_fim
            ).filter(
                Q(movimentacoes_pasto__data_saida__gte=data_inicio) | Q(movimentacoes_pasto__data_saida__isnull=True)
            ).distinct()
            
            total_gpmd = 0
            total_custo = 0
            total_animais = 0
            
            for animal in animais_no_pasto:
                # 3. Calcular GPMD, Peso e Custo para CADA ANIMAL no Período
                
                # a) GPMD Médio no período
                # Filtra as pesagens cuja data_pesagem está entre o período
                pesagens_periodo = animal.pesagens.filter(
                    data_pesagem__range=[data_inicio, data_fim],
                    gpmd__isnull=False
                )
                gpmd_medio = pesagens_periodo.aggregate(Avg('gpmd'))['avg']
                
                # b) Último Peso (para peso médio)
                ultima_pesagem = animal.pesagens.filter(data_pesagem__lte=data_fim).order_by('-data_pesagem').first()
                peso_atual = ultima_pesagem.peso if ultima_pesagem else None
                
                # c) Custo Alocado no Período
                custo_periodo = CustoAnimalDetalhe.objects.filter(
                    animal=animal,
                    registro_de_custo__data_custo__range=[data_inicio, data_fim]
                ).aggregate(total=Sum('valor_alocado'))['total'] or 0.00
                
                if gpmd_medio is not None:
                    total_gpmd += gpmd_medio
                    total_custo += custo_periodo
                    total_animais += 1
                    
                    animais_desempenho.append({
                        'identificacao': animal.identificacao,
                        'link': animal.get_absolute_url(),
                        'gpmd_medio': gpmd_medio,
                        'peso_atual': peso_atual,
                        'custo_periodo': custo_periodo,
                    })

            # 4. Resumo do Pasto/Lote
            if total_animais > 0:
                relatorio_resumo = {
                    'pasto_nome': pasto_selecionado.nome,
                    'total_animais': total_animais,
                    'media_gpmd_lote': total_gpmd / total_animais,
                    'custo_total_lote': total_custo,
                    'custo_medio_animal': total_custo / total_animais,
                }
                
        except Pasto.DoesNotExist:
            pasto_selecionado = None
            
    context = {
        'pastos': pastos,
        'pasto_selecionado': pasto_selecionado,
        'data_inicio_filtro': data_inicio,
        'data_fim_filtro': data_fim,
        'animais_desempenho': animais_desempenho,
        'relatorio_resumo': relatorio_resumo,
    }
    
    return render(request, 'pecuaria/relatorio_desempenho_pasto.html', context)

