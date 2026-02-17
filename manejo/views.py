# ControleRebanho/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, UpdateView, FormView
from django.contrib.auth.decorators import login_required # Importe o decorador
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Sum
from datetime import  timedelta
from django.utils import timezone
from decimal import Decimal

from financeiro.models import CustoAnimalDetalhe
from rebanho.models import Animal


from .models import  TratamentoSaude, Reproducao, Pesagem,  TarefaManejo
from .forms import  TratamentoForm, ReproducaoForm,  PesagemForm, PesagemForm,  PesagemModelForm


# --------------------------------
# CreateViews do projeto de Pecuária
# --------------------------------

class PesagemCreateView(LoginRequiredMixin,FormView):
    form_class = PesagemForm
    template_name = 'manejo/pesagem_form.html'

    def get_form_kwargs(self):
        """
        FORÇA A REMOÇÃO DO 'instance'. 
        Este é o ponto exato onde o erro TypeError acontece.
        """
        kwargs = super().get_form_kwargs()
        kwargs.pop('instance', None)  # Se houver uma 'instance', nós a removemos
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal_id = self.request.GET.get('animal_id')
        if animal_id:
            context['animal_individual'] = get_object_or_404(Animal, pk=animal_id)
        return context

    def get_initial(self):
        initial = super().get_initial()
        animal_id = self.request.GET.get('animal_id')
        if animal_id:
            # ModelMultipleChoiceField exige uma lista de IDs
            initial['animais'] = [animal_id] 
        initial['data_pesagem'] = timezone.localdate()
        return initial

    def form_valid(self, form):
        data_pesagem = form.cleaned_data['data_pesagem']
        peso_kg = form.cleaned_data['peso_kg']
        evento = form.cleaned_data.get('evento', '')
        animais = form.cleaned_data['animais']

        quantidade = 0
        for animal in animais:
            Pesagem.objects.create(
                animal=animal,
                data_pesagem=data_pesagem,
                peso_kg=peso_kg,
                evento=evento
            )
            quantidade += 1 
        
        messages.success(
            self.request, 
            f"Sucesso! {quantidade} animal(is) pesado(s) com {peso_kg}kg."
        )

        return redirect(self.get_success_url())
    
    def get_success_url(self):
        animal_id = self.request.GET.get('animal_id')
        if animal_id:
            return reverse('animal_detail', kwargs={'pk': animal_id})
        return reverse('controle_peso_list')


class ReproducaoCreateView(LoginRequiredMixin,FormView):
    model = Reproducao
    form_class = ReproducaoForm
    template_name = 'manejo/reproducao_form.html'

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
            initial['matriz'] = animal_id 
        initial['data_cio'] = timezone.localdate()
        return initial

    def form_valid(self, form):
        """Executa a movimentação no banco de dados"""
        data_cio = form.cleaned_data['data_cio']
        tipo = form.cleaned_data['tipo']
        touro = form.cleaned_data['touro']
        codigo_semen = form.cleaned_data['codigo_semen']
        data_dg = form.cleaned_data['data_dg']
        resultado = form.cleaned_data['resultado']
        matrizes = form.cleaned_data['matriz']

        # O método update() é eficiente para 1 ou 100 animais
        quantidade = 0
        for animal in matrizes:
            # Cria o registro de movimentação
            animal.reproducoes_matriz.create(
                data_cio=data_cio,
                tipo=tipo,
                touro=touro,
                codigo_semen=codigo_semen,
                data_dg=data_dg,
                resultado=resultado
            )
            animal.save()
            quantidade += 1 
        
        messages.success(
            self.request, 
            f"Sucesso! {quantidade} matriz(es) {touro} {codigo_semen} {resultado}."
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        animal_id = self.request.GET.get('animal_id')
        if animal_id:
            return reverse('animal_detail', kwargs={'pk': animal_id})
        return reverse('tratamentos_saude_list')
    

class TratamentoCreateView(LoginRequiredMixin,FormView):
    model = TratamentoSaude
    form_class = TratamentoForm
    template_name = 'manejo/tratamento_form.html'

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
        initial['data_tratamento'] = timezone.localdate()
        return initial

    def form_valid(self, form):
        """Executa a movimentação no banco de dados"""
        data_tratamento = form.cleaned_data['data_tratamento']
        tipo_tratamento = form.cleaned_data['tipo_tratamento']
        produto = form.cleaned_data['produto']
        dose = form.cleaned_data['dose']
        descricao = form.cleaned_data['descricao']
        data_proximo_tratamento = form.cleaned_data['data_proximo_tratamento']   
        animais = form.cleaned_data['animais']
        
        # O método update() é eficiente para 1 ou 100 animais
        quantidade = 0
        for animal in animais:
            # Cria o registro de movimentação
            animal.tratamentos.create(
                data_tratamento=data_tratamento,
                tipo_tratamento=tipo_tratamento,
                produto=produto,
                dose=dose,
                descricao=descricao,
                data_proximo_tratamento=data_proximo_tratamento
            )
            animal.save()
            quantidade += 1 
        
        messages.success(
            self.request, 
            f"Sucesso! {quantidade} animal(is) {tipo_tratamento} {produto}."
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        animal_id = self.request.GET.get('animal_id')
        if animal_id:
            return reverse('animal_detail', kwargs={'pk': animal_id})
        return reverse('tratamentos_saude_list')


# --------------------------------
# Updated Views do projeto de Pecuária
# --------------------------------


class PesagemUpdateView(LoginRequiredMixin, UpdateView):
    model = Pesagem
    form_class = PesagemModelForm
    template_name = 'manejo/pesagem_form.html'
    success_url = reverse_lazy('controle_peso_list')


# --------------------------------
# ListViews do projeto de Pecuária
# --------------------------------

class ReproducaoListView(ListView):
    model = Reproducao
    template_name = 'manejo/reproducao_list.html'
    context_object_name = 'manejos'
    paginate_by = 25

    def get_queryset(self):
        # Filtra para mostrar os registros mais recentes primeiro
        # e prioriza quem tem data de parto prevista
        return Reproducao.objects.select_related('matriz').order_by('matriz', 'data_parto_prevista', '-data_cio')


class AlertaRiscoListView(ListView):
    model = Animal
    template_name = 'manejo/alertas_risco.html'
    context_object_name = 'animais_em_risco'
    
    # Exclui animais que já saíram do rebanho
    queryset = Animal.objects.filter(situacao='VIVO')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        animais = context[self.context_object_name]
        animais_em_risco_list = []
        
        # --- Configurações de Limite ---
        HOJE = timezone.localdate()
        DIAS_PESAGEM_LIMITE = 60 # Máximo de dias sem pesagem
        GPMD_MINIMO = Decimal('0.20') # GPMD mínimo aceitável (kg/dia)
        
        # 1. Calcular a média de custo do rebanho para o Alerta de Custo
        avg_custo_anual = CustoAnimalDetalhe.objects.filter(
            registro_de_custo__data_custo__year=HOJE.year
        ).aggregate(
            media=Avg('valor_alocado')
        )['media'] or Decimal(0)
        
        CUSTO_LIMITE = avg_custo_anual * Decimal('1.20') # 20% acima da média

        
        for animal in animais:
            riscos = []
            
            # ----------------------------------------------------
            # Risco 1: GPMD Baixo/Negativo
            # ----------------------------------------------------
            gpmd_30d = animal.calcular_gpmd_animal(dias_filtro=30)
            
            if gpmd_30d is not None and gpmd_30d < GPMD_MINIMO:
                riscos.append(f"GPMD de 30 dias ({gpmd_30d:.2f} kg) está abaixo do mínimo ({GPMD_MINIMO:.2f}).")
            
            # ----------------------------------------------------
            # Risco 2: Perda de Pesagem Recente
            # ----------------------------------------------------
            ultima_pesagem = animal.ultima_pesagem
            if ultima_pesagem is None or (HOJE - ultima_pesagem).days > DIAS_PESAGEM_LIMITE:
                 riscos.append(f"Última pesagem é de {(HOJE - (ultima_pesagem or HOJE)).days} dias atrás. Limite: {DIAS_PESAGEM_LIMITE} dias.")

            # ----------------------------------------------------
            # Risco 3: Alto Custo Acumulado
            # ----------------------------------------------------
            custo_acumulado = CustoAnimalDetalhe.objects.filter(
                animal=animal,
                registro_de_custo__data_custo__year=HOJE.year
            ).aggregate(
                total=Sum('valor_alocado')
            )['total'] or Decimal(0)
            
            if custo_acumulado > CUSTO_LIMITE:
                 riscos.append(f"Custo Acumulado ({custo_acumulado:.2f}) está acima da média do rebanho ({CUSTO_LIMITE:.2f}).")
            
            
            if riscos:
                animais_em_risco_list.append({
                    'animal': animal,
                    'riscos': riscos,
                    'gpmd_recente': gpmd_30d,
                    'custo_acumulado': custo_acumulado,
                })

        context['animais_em_risco'] = animais_em_risco_list
        context['media_custo_rebanho'] = avg_custo_anual
        
        return context


class TratamentoSaudeListView(LoginRequiredMixin, ListView):
    model = TratamentoSaude
    template_name = 'manejo/tratamentos_saude_list.html'
    context_object_name = 'tratamentos'
    # Ordena os registros pela data do tratamento mais recente
    ordering = ['-data_tratamento']


class PesagemListView(ListView):
    model = Pesagem
    template_name = 'manejo/pesagem_list.html'
    context_object_name = 'pesagens'
    # Ordena os registros pela data mais recente
    ordering = ['-data_pesagem'] 


@login_required
def alertas_de_manejo(request):
    hoje = timezone.localdate()
    futuro_proximo = hoje + timedelta(days=90) # Alerta para os próximos 90 dias
    
    alertas = []

    # 1. Alertas de Partos Esperados (Partos Previstos)
    # Filtra registros de reprodução onde o resultado ainda não é conhecido (pendente)
    partos_previstos = Reproducao.objects.filter(
        data_parto_prevista__range=[hoje, futuro_proximo],
        # Supondo que 'PENDENTE' seja a situação inicial do resultado
        # Ajuste o filtro 'resultado' conforme o seu modelo de Reproducao:
        # Q(resultado__isnull=True) | Q(resultado='PE') 
    ).order_by('data_parto_prevista')
    
    for repro in partos_previstos:
        dias_restantes = (repro.data_parto_prevista - hoje).days

        if dias_restantes <= 7:
            status_class = 'list-group-item-danger'
            icon_class = 'fas fa-exclamation-triangle'
            status_text = 'Crítico'
        else:
            status_class = 'list-group-item-warning'
            icon_class = 'fas fa-baby'
            status_text = 'Atenção'

        alertas.append({
            'data': repro.data_parto_prevista,
            'titulo': f"Parto Esperado da Matriz {repro.matriz.identificacao}",
            'tipo': 'Parto',
            'animal_link': repro.matriz.get_absolute_url(),
            'animal_identificacao': repro.matriz.identificacao,
            'dias_restantes': dias_restantes,
            'status_class': status_class,
            'icon_class': icon_class,    
            'status': status_text
        })
        
    # 2. Tarefas de Manejo Agendadas
    tarefas_agendadas = TarefaManejo.objects.filter(
        data_prevista__range=[hoje, futuro_proximo],
        concluida=False
    ).order_by('data_prevista')
    
    for tarefa in tarefas_agendadas:
        dias_restantes = (tarefa.data_prevista - hoje).days
        alertas.append({
            'data': tarefa.data_prevista,
            'titulo': tarefa.titulo,
            'tipo': tarefa.get_tipo_display(),
            'animal_link': tarefa.animal.get_absolute_url() if tarefa.animal else None,
            'dias_restantes': dias_restantes,
            'status': 'Crítico' if dias_restantes <= 7 else 'Atenção'
        })
        
    # 3. Ordenar a lista final por data
    alertas.sort(key=lambda x: x['data'])
    
    context = {
        'alertas': alertas,
        'hoje': hoje,
        'futuro_proximo': futuro_proximo
    }
    
    return render(request, 'manejo/alertas_de_manejo.html', context)

